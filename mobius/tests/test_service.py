"""Möbius service routing and error contract (no network: market data is faked).

Run from mobius/ after sync.sh:  python -m pytest -q tests
"""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import service  # noqa: E402
from fd_data.providers.base import TickerNotFound  # noqa: E402


class FakeData:
    def __init__(self):
        self.prices = {"AAPL": 200.0}

    def quote(self, t):
        t = t.upper()
        if t not in self.prices:
            raise TickerNotFound(t)
        return SimpleNamespace(price=self.prices[t], name=t, model_dump=lambda **_: {"ticker": t, "price": self.prices[t]})

    def history(self, t, period):
        return SimpleNamespace(points=[])


@pytest.fixture
def call(tmp_path, monkeypatch):
    real_init = service.App.__init__

    def init(self, root):
        real_init(self, root)
        self.data = FakeData()

    monkeypatch.setattr(service.App, "__init__", init)

    def do(method, path, body=None, **query):
        req = {"schema": 1, "method": method, "path": path, "query": {k: [v] for k, v in query.items()}, "body": body}
        return service.handle(req, tmp_path)
    return do


def test_workspaces_and_saved_briefs_round_trip(call):
    assert call("POST", "projects", {"name": "Tech Stocks"}) == (200, {"project_id": "tech-stocks"})
    brief = {"ticker": "AAPL", "thesis": "x", "metrics": {"price": 200}}
    assert call("POST", "briefs", {"project_id": "tech-stocks", "brief": brief})[0] == 200
    assert call("GET", "briefs", project_id="tech-stocks")[1] == [brief]
    assert call("GET", "projects")[1] == ["tech-stocks"]
    assert call("DELETE", "briefs/AAPL", project_id="tech-stocks")[1] == {"ok": True}
    assert call("GET", "briefs", project_id="tech-stocks")[1] == []


def test_saving_a_brief_without_a_valid_ticker_is_refused(call):
    status, body = call("POST", "briefs", {"brief": {"ticker": "../etc"}})
    assert status == 422 and body["error"] == "invalid_parameter"


def test_paper_order_and_leaderboard_use_the_shared_trading_rules(call):
    status, pf = call("POST", "paper/orders", {"project_id": "default", "ticker": "AAPL", "side": "buy", "qty": 10})
    assert status == 200 and pf["cash"] == 98_000
    status, body = call("POST", "paper/orders", {"project_id": "default", "ticker": "AAPL", "side": "sell", "qty": 99})
    assert (status, body["error"]) == (409, "insufficient_position")
    status, board = call("GET", "paper/leaderboard", period="day")
    assert status == 200 and board["standings"][0]["project_id"] == "default"
    assert call("GET", "paper/leaderboard", period="year")[0] == 422


def test_domain_errors_keep_the_data_service_contract(call):
    status, body = call("GET", "quote/ZZZZ")
    assert (status, body["error"]) == (404, "ticker_not_found")


def test_chat_without_briefs_answers_without_ai(call):
    status, body = call("POST", "chat/prompt", {"message": "hi", "project_id": "empty"})
    assert status == 200 and "no briefs" in body["answer"] and "prompt" not in body


def test_unknown_routes_and_public_calls_are_not_found(call):
    assert call("GET", "nope")[0] == 404
    status, _ = service.handle({"schema": 1, "public": True, "method": "GET", "path": "features"}, Path("/tmp"))
    assert status == 404
