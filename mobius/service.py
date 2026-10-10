"""Finance Desk service for Möbius: one request per process (JSON on stdin, {status, body} on stdout).

Routes mirror agent_service + data_service + learning_service, so the UI keeps the same paths.
Domain logic lives in fd_data / fd_learning (copied from the repo by mobius/sync.sh) and fd_desk.
Errors use the services' contract shape {"error", "detail"} with the same status codes.
"""
import json
import os
import sys
from pathlib import Path

# Heavy imports (pandas via yfinance) happen once per accepted revision, then each request forks.
MOBIUS_PRELOAD = True

import fd_desk
from fd_data.config import Settings
from fd_data.leaderboard import Leaderboard
from fd_data.paper import InsufficientCash, InsufficientPosition, JsonPaperStore, OrderIn, PaperService
from fd_data.providers.base import FilingNotFound, TickerNotFound, UpstreamError
from fd_data.providers.edgar_provider import EdgarProvider
from fd_data.providers.yfinance_provider import YFinanceProvider
from fd_data.service import DataService, InvalidParameter, InvalidTicker, NotInCache, normalize_ticker
from fd_learning.models import FeedbackIn
from fd_learning.service import LearningService
from fd_learning.store import LearningStore

# Same user-facing wording as agent_service.ERROR_TEXT.
ERRORS = [
    (InvalidTicker, 422, "invalid_ticker", "That doesn't look like a ticker symbol."),
    (InsufficientCash, 409, "insufficient_cash", "Not enough cash in your paper account for this order."),
    (InsufficientPosition, 409, "insufficient_position", "You don't own that many shares to sell."),
    (InvalidParameter, 422, "invalid_parameter", None),
    (TickerNotFound, 404, "ticker_not_found", "Unknown ticker. Check the symbol (e.g. AAPL, MSFT, NVDA)."),
    (FilingNotFound, 404, "filing_not_found", "No 10-K annual report for this company (foreign companies file a 20-F instead)."),
    (UpstreamError, 502, "upstream_unavailable", "The data source isn't responding. Try again in a few seconds."),
    (NotInCache, 503, "not_in_cache", "No saved data for this ticker while the data source is unavailable."),
]


class Problem(Exception):
    def __init__(self, status: int, error: str, detail: str):
        super().__init__(detail)
        self.status, self.error, self.detail = status, error, detail


class App:
    """Everything one request needs, rooted in the app's own storage directory."""

    def __init__(self, root: Path):
        settings = Settings(cache_dir=root / "cache", demo_cache_dir=root / "demo_cache", paper_dir=root / "paper")
        self.data = DataService(settings, YFinanceProvider(), EdgarProvider(settings.sec_user_agent))
        self.paper = PaperService(JsonPaperStore(settings.paper_dir), lambda t: self.data.quote(t).price)
        self.board = Leaderboard(self.paper.store, self.paper, self._closes,
                                 settings.paper_dir / "leaderboard" / "podiums.json")
        # Rules only: the learning LLM summary would outlive the 15 s request limit.
        self.learning = LearningService(LearningStore(root / "learning"), use_llm=False)
        self.desk = fd_desk.Desk(root / "briefs")

    def _closes(self, ticker: str) -> list[tuple[str, float]]:
        try:
            points = self.data.history(ticker, "1y").points
        except Exception:
            return []
        return [(p.time, p.close) for p in points if isinstance(p.time, str)]


def _one(query: dict, name: str, default=None):
    v = query.get(name)
    return v[0] if isinstance(v, list) and v else (v if isinstance(v, str) else default)


def _dump(x):
    return x.model_dump(mode="json") if hasattr(x, "model_dump") else x


def route(app: App, method: str, path: str, query: dict, body) -> object:
    parts = [p for p in path.split("/") if p]
    pid = _one(query, "project_id", "default")
    body = body if isinstance(body, dict) else {}
    key = (method, parts[0] if parts else "", len(parts))

    if key == ("GET", "features", 1):
        return {"paper": True, "learning": True, "live_data": True, "ai": True}
    if key == ("GET", "projects", 1):
        return app.desk.projects()
    if key == ("POST", "projects", 1):
        name = str(body.get("name") or "").strip()
        if not name:
            raise Problem(422, "invalid_parameter", "A workspace needs a name.")
        return {"project_id": app.desk.create_project(name)}

    # --- briefs ---
    if key == ("POST", "brief", 2) and parts[1] == "prepare":
        t = normalize_ticker(str(body.get("ticker", "")))
        q, f, r = app.data.quote(t), app.data.financials(t), app.data.risk_factors(t)
        prof = _dump(app.learning.profile(body.get("project_id") or pid))
        return fd_desk.prepare(t, _dump(q), _dump(f), _dump(r), prof)
    if key == ("GET", "briefs", 1):
        return app.desk.briefs(pid)
    if key == ("POST", "briefs", 1):
        try:
            return app.desk.save(body.get("project_id") or pid, body.get("brief") or {})
        except ValueError as e:
            raise Problem(422, "invalid_parameter", str(e)) from e
    if key == ("DELETE", "briefs", 2):
        app.desk.delete(pid, parts[1])
        return {"ok": True}
    if key == ("POST", "chat", 2) and parts[1] == "prompt":
        bs = app.desk.briefs(body.get("project_id") or pid)
        if not bs:
            return {"answer": "This workspace has no briefs yet. Analyze a ticker first, then ask."}
        return {"prompt": fd_desk.CHAT_PROMPT.format(briefs=json.dumps(bs, ensure_ascii=False),
                                                     question=str(body.get("message", ""))[:2000])}
    if key == ("GET", "compare", 1):
        rows = []
        for t in [x.strip().upper() for x in (_one(query, "tickers", "") or "").split(",") if x.strip()][:4]:
            q, f = app.data.quote(t), app.data.financials(t)
            rows.append({"ticker": t, "name": q.name, "price": q.price, "pe": f.pe,
                         "revenue_growth_yoy": f.revenue_growth_yoy, "net_margin": f.net_margin})
        return rows

    # --- market data ---
    if key == ("GET", "quote", 2):
        return _dump(app.data.quote(parts[1]))
    if key == ("GET", "history", 2):
        return _dump(app.data.history(parts[1], _one(query, "period", "1y")))

    # --- paper trading + leaderboard ---
    if parts[:1] == ["paper"] and len(parts) == 2:
        op = (method, parts[1])
        if op == ("GET", "portfolio"):
            return _dump(app.paper.portfolio(pid))
        if op == ("POST", "orders"):
            try:
                req = OrderIn(**body)
            except Exception as e:
                raise Problem(422, "invalid_parameter", "Order needs ticker, side buy|sell and qty > 0.") from e
            return _dump(app.paper.place(req, normalize_ticker(req.ticker)))
        if op == ("POST", "reset"):
            return _dump(app.paper.reset(pid))
        if op == ("GET", "leaderboard"):
            period = _one(query, "period", "day")
            if period not in ("day", "week", "month"):
                raise Problem(422, "invalid_parameter", "period must be day, week or month")
            return _dump(app.board.standings(period))

    # --- learning ---
    if key == ("POST", "feedback", 1):
        try:
            req = FeedbackIn(**body)
        except Exception as e:
            raise Problem(422, "invalid_parameter", "Feedback needs ticker, rating up|down and the brief time.") from e
        fb = app.learning.add(req)
        return {**fb.model_dump(mode="json"), "ok": True,
                "feedback_count": len(app.learning.store.feedback(fb.project_id))}
    if key == ("GET", "feedback", 1):
        return [_dump(f) for f in app.learning.feedback(pid)]
    if key == ("GET", "profile", 1):
        return _dump(app.learning.profile(pid))
    if key == ("DELETE", "profile", 1):
        app.learning.forget(pid)
        return {"ok": True, **_dump(app.learning.profile(pid))}

    raise Problem(404, "not_found", "Unknown Finance Desk route.")


def handle(req: dict, root: Path) -> tuple[int, object]:
    try:
        if not isinstance(req, dict) or req.get("schema") != 1:
            raise Problem(400, "invalid_request", "Invalid service request.")
        if req.get("public"):
            raise Problem(404, "not_found", "Finance Desk has no public routes.")
        body = route(App(root), str(req.get("method", "GET")).upper(), str(req.get("path", "")),
                     req.get("query") or {}, req.get("body"))
        return 200, body
    except Problem as e:
        return e.status, {"error": e.error, "detail": e.detail}
    except Exception as e:
        for cls, status, code, text in ERRORS:
            if isinstance(e, cls):
                return status, {"error": code, "detail": text or str(e)}
        print(f"{type(e).__name__}: {e}", file=sys.stderr)
        return 500, {"error": "internal", "detail": "Finance Desk could not complete this request. Please retry."}


if __name__ == "__main__":
    status, body = handle(json.load(sys.stdin), Path(os.environ["APP_STORAGE_DIR"]))
    print(json.dumps({"status": status, "body": body}, ensure_ascii=False, default=str))
