"""FastAPI app for the data service.

Run:  uvicorn app.main:app --port 8001 --reload   (from data_service/)
Docs: http://localhost:8001/docs
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
import os
import threading
import time
from functools import lru_cache
from typing import Literal

from fastapi import Depends, FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import DEMO_TICKERS, load_settings
from .models import ErrorBody, Financials, History, Quote, RiskFactors
from .providers.base import FilingNotFound, TickerNotFound, UpstreamError
from .providers.edgar_provider import EdgarProvider
from .providers.yfinance_provider import YFinanceProvider
from .leaderboard import Leaderboard, LeaderboardOut, PeriodKind
from .paper import (InsufficientCash, InsufficientPosition, JsonPaperStore, OrderIn, OrderNotFound, OrderResult,
                    PaperService, Portfolio)
from .service import DataService, InvalidParameter, InvalidTicker, NotInCache, normalize_ticker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

@asynccontextmanager
async def _lifespan(_: FastAPI):
    every = float(os.getenv("PAPER_CHECK_SECONDS", "10"))
    if every > 0:
        threading.Thread(target=_check_open_orders_forever, args=(every,), daemon=True, name="paper-orders").start()
    yield


app = FastAPI(
    lifespan=_lifespan,
    title="MobiusFinance data service",
    version="0.1.0",
    description="Market data and SEC filings for the Finance Desk. No LLM, no UI.",
)
# The frontend and agent run on other ports during the hackathon.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST", "DELETE"], allow_headers=["*"])


@lru_cache
def get_service() -> DataService:
    settings = load_settings()
    return DataService(settings, YFinanceProvider(), EdgarProvider(settings.sec_user_agent))


@lru_cache
def get_paper() -> PaperService:
    svc = get_service()
    return PaperService(JsonPaperStore(svc.settings.paper_dir), lambda t: svc.quote(t).price)


def _daily_closes(svc: DataService, ticker: str) -> list[tuple[str, float]]:
    try:
        points = svc.history(ticker, "1y").points
    except Exception:  # offline/unknown ticker: the leaderboard falls back to the last trade price
        return []
    return [(p.time, p.close) for p in points if isinstance(p.time, str)]


@lru_cache
def get_leaderboard() -> Leaderboard:
    svc, paper = get_service(), get_paper()
    # A subdirectory, so no workspace slug can collide with the podium file.
    return Leaderboard(paper.store, paper, lambda t: _daily_closes(svc, t),
                       svc.settings.paper_dir / "leaderboard" / "podiums.json")


ERRORS = {404: {"model": ErrorBody}, 409: {"model": ErrorBody}, 422: {"model": ErrorBody}, 502: {"model": ErrorBody}, 503: {"model": ErrorBody}}


def _err(status: int, code: str, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": code, "detail": detail})


@app.exception_handler(InvalidTicker)
async def _invalid(_: Request, e: InvalidTicker):
    return _err(422, "invalid_ticker", f"Not a valid ticker symbol: {e}")


@app.exception_handler(InsufficientCash)
async def _no_cash(_: Request, e: InsufficientCash):
    return _err(409, "insufficient_cash", str(e))


@app.exception_handler(InsufficientPosition)
async def _no_position(_: Request, e: InsufficientPosition):
    return _err(409, "insufficient_position", str(e))


@app.exception_handler(OrderNotFound)
async def _no_order(_: Request, e: OrderNotFound):
    return _err(404, "order_not_found", str(e))


@app.exception_handler(InvalidParameter)
async def _bad_param(_: Request, e: InvalidParameter):
    return _err(422, "invalid_parameter", str(e))


@app.exception_handler(RequestValidationError)
async def _validation(_: Request, e: RequestValidationError):
    msg = "; ".join(f"{'.'.join(str(x) for x in err['loc'][1:])}: {err['msg']}" for err in e.errors())
    return _err(422, "invalid_parameter", msg)


@app.exception_handler(TickerNotFound)
async def _not_found(_: Request, e: TickerNotFound):
    return _err(404, "ticker_not_found", f"Unknown ticker: {e}")


@app.exception_handler(FilingNotFound)
async def _no_filing(_: Request, e: FilingNotFound):
    return _err(404, "filing_not_found", str(e))


@app.exception_handler(UpstreamError)
async def _upstream(_: Request, e: UpstreamError):
    return _err(502, "upstream_unavailable", str(e))


@app.exception_handler(NotInCache)
async def _offline(_: Request, e: NotInCache):
    return _err(503, "not_in_cache", str(e))


@app.get("/health")
def health(svc: DataService = Depends(get_service)):
    s = svc.settings
    return {
        "status": "ok",
        "offline": s.offline,
        "optional": sorted(s.optional),
        "demo_tickers": list(DEMO_TICKERS),
        "cached_tickers": sorted(set(svc.cache.tickers()) | set(svc.demo.tickers())),
    }


@app.get("/quote/{ticker}", response_model=Quote, responses=ERRORS)
def quote(ticker: str, svc: DataService = Depends(get_service)):
    return svc.quote(ticker)


@app.get("/history/{ticker}", response_model=History, responses=ERRORS)
def history(
    ticker: str,
    period: Literal["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "max"] = Query("1y"),
    svc: DataService = Depends(get_service),
):
    return svc.history(ticker, period)


@app.get("/financials/{ticker}", response_model=Financials, responses=ERRORS)
def financials(ticker: str, svc: DataService = Depends(get_service)):
    return svc.financials(ticker)


@app.get("/filings/{ticker}/risk-factors", response_model=RiskFactors, responses=ERRORS)
def risk_factors(ticker: str, svc: DataService = Depends(get_service)):
    return svc.risk_factors(ticker)


# --- paper trading (simulation, not advice) ------------------------------------------

@app.post("/paper/orders", response_model=OrderResult, responses=ERRORS)
def paper_order(req: OrderIn, paper: PaperService = Depends(get_paper)):
    return paper.place(req, normalize_ticker(req.ticker))


@app.delete("/paper/orders/{order_id}", response_model=Portfolio, responses=ERRORS)
def paper_cancel(order_id: str, project_id: str = "default", paper: PaperService = Depends(get_paper)):
    """Cancel an open limit/stop order and release its reserved cash or shares."""
    return paper.cancel(project_id, order_id)


def _check_open_orders_forever(every: float) -> None:
    """Open limit/stop orders are checked here while the service runs (contracts/paper.md)."""
    log = logging.getLogger("paper.orders")
    while True:
        time.sleep(every)
        try:
            n = get_paper().check_all()
            if n:
                log.info("filled %d open order(s)", n)
        except Exception as e:  # keep checking; a failed round is retried next time
            log.warning("open order check failed: %s", e)


@app.get("/paper/portfolio", response_model=Portfolio)
def paper_portfolio(project_id: str = "default", paper: PaperService = Depends(get_paper)):
    return paper.portfolio(project_id)


@app.post("/paper/reset", response_model=Portfolio, responses=ERRORS)
def paper_reset(project_id: str = "default", starting_cash: float = 100_000.0, paper: PaperService = Depends(get_paper)):
    return paper.reset(project_id, starting_cash)


@app.get("/paper/leaderboard", response_model=LeaderboardOut, responses=ERRORS)
def paper_leaderboard(period: PeriodKind = "day", board: Leaderboard = Depends(get_leaderboard)):
    """Workspaces ranked by return for the current day/week/month; see contracts/leaderboard.md."""
    return board.standings(period)
