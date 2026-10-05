"""FastAPI app for the data service.

Run:  uvicorn app.main:app --port 8001 --reload   (from data_service/)
Docs: http://localhost:8001/docs
"""

from __future__ import annotations

import logging
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
from .paper import (InsufficientCash, InsufficientShares, JsonPaperStore, OrderIn, OrderResult, PaperService,
                    Portfolio)
from .service import DataService, InvalidParameter, InvalidTicker, NotInCache, normalize_ticker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(
    title="MobiusFinance data service",
    version="0.1.0",
    description="Market data and SEC filings for the Finance Desk. No LLM, no UI.",
)
# The frontend and agent run on other ports during the hackathon.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"], allow_headers=["*"])


@lru_cache
def get_service() -> DataService:
    settings = load_settings()
    return DataService(settings, YFinanceProvider(), EdgarProvider(settings.sec_user_agent))


@lru_cache
def get_paper() -> PaperService:
    svc = get_service()
    return PaperService(JsonPaperStore(svc.settings.paper_dir), lambda t: svc.quote(t).price)


ERRORS = {404: {"model": ErrorBody}, 422: {"model": ErrorBody}, 502: {"model": ErrorBody}, 503: {"model": ErrorBody}}


def _err(status: int, code: str, detail: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": code, "detail": detail})


@app.exception_handler(InvalidTicker)
async def _invalid(_: Request, e: InvalidTicker):
    return _err(422, "invalid_ticker", f"Not a valid ticker symbol: {e}")


@app.exception_handler(InsufficientCash)
async def _no_cash(_: Request, e: InsufficientCash):
    return _err(422, "insufficient_cash", str(e))


@app.exception_handler(InsufficientShares)
async def _no_shares(_: Request, e: InsufficientShares):
    return _err(422, "insufficient_shares", str(e))


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
    period: Literal["1mo", "3mo", "6mo", "1y", "2y", "5y", "max"] = Query("1y"),
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


@app.get("/paper/portfolio", response_model=Portfolio)
def paper_portfolio(project_id: str = "default", paper: PaperService = Depends(get_paper)):
    return paper.portfolio(project_id)


@app.post("/paper/reset", response_model=Portfolio, responses=ERRORS)
def paper_reset(project_id: str = "default", starting_cash: float = 100_000.0, paper: PaperService = Depends(get_paper)):
    return paper.reset(project_id, starting_cash)
