"""Paper trading rules and routes (no network: prices come from a dict)."""

import pytest
from fastapi.testclient import TestClient

from app import main
from app.paper import InsufficientCash, InsufficientPosition, JsonPaperStore, OrderIn, PaperService


@pytest.fixture
def prices():
    return {"AAPL": 230.0, "MSFT": 500.0}


@pytest.fixture
def paper(tmp_path, prices):
    def price_of(t):
        if t not in prices:
            raise KeyError(t)
        return prices[t]

    return PaperService(JsonPaperStore(tmp_path), price_of)


def buy(p, t, q, pid="demo"):
    return p.place(OrderIn(project_id=pid, ticker=t, side="buy", qty=q), t)


def sell(p, t, q, pid="demo"):
    return p.place(OrderIn(project_id=pid, ticker=t, side="sell", qty=q), t)


def test_new_project_starts_with_100k(paper):
    pf = paper.portfolio("Novi Projekt")
    assert pf.project_id == "novi-projekt"  # same slug as agent_service
    assert pf.cash == pf.equity == 100_000 and pf.positions == []


def test_buy_marks_to_market_like_contract_example(paper, prices):
    buy(paper, "AAPL", 10)
    prices["AAPL"] = 233.9
    pf = paper.portfolio("demo")
    pos = pf.positions[0]
    assert pf.cash == 97_700
    assert (pos.qty, pos.avg_price, pos.market_value, pos.pnl, pos.pnl_pct) == (10, 230.0, 2339.0, 39.0, 1.7)
    assert pf.equity == 100_039 and pf.pnl == 39


def test_average_price_and_realized_pnl(paper, prices):
    buy(paper, "AAPL", 10)
    prices["AAPL"] = 250.0
    buy(paper, "AAPL", 10)
    assert paper.portfolio("demo").positions[0].avg_price == 240.0
    res = sell(paper, "AAPL", 20)
    assert res.positions == [] and res.fill.side == "sell" and res.fill.qty == 20
    assert res.realized_pnl == 200.0
    assert res.cash == 100_200


def test_cannot_overspend_or_oversell(paper):
    with pytest.raises(InsufficientCash):
        buy(paper, "MSFT", 1000)
    with pytest.raises(InsufficientPosition):
        sell(paper, "AAPL", 1)
    assert paper.portfolio("demo").cash == 100_000  # nothing changed


def test_projects_are_separate_and_reset_works(paper):
    buy(paper, "AAPL", 1, pid="a")
    assert paper.portfolio("b").cash == 100_000
    pf = paper.reset("a", starting_cash=50_000)
    assert pf.cash == 50_000 and pf.positions == []


def test_missing_quote_values_position_at_last_trade(paper, prices):
    buy(paper, "AAPL", 2)
    del prices["AAPL"]
    pf = paper.portfolio("demo")
    assert pf.stale_prices is True and pf.positions[0].price == 230.0


def test_routes_and_error_codes(paper):
    main.app.dependency_overrides[main.get_paper] = lambda: paper
    try:
        c = TestClient(main.app)
        r = c.post("/paper/orders", json={"project_id": "demo", "ticker": "aapl", "side": "buy", "qty": 10})
        assert r.status_code == 200
        body = r.json()
        assert body["fill"] == {"ticker": "AAPL", "side": "buy", "qty": 10, "price": 230.0, "at": body["fill"]["at"]}
        assert body["cash"] == 97_700 and body["positions"][0]["ticker"] == "AAPL"
        assert c.get("/paper/portfolio?project_id=demo").json()["cash"] == 97_700
        r = c.post("/paper/orders", json={"project_id": "demo", "ticker": "MSFT", "side": "buy", "qty": 1000})
        assert r.status_code == 409 and r.json()["error"] == "insufficient_cash"
        r = c.post("/paper/orders", json={"project_id": "demo", "ticker": "MSFT", "side": "sell", "qty": 1})
        assert r.status_code == 409 and r.json()["error"] == "insufficient_position"
        r = c.post("/paper/orders", json={"project_id": "demo", "ticker": "AAPL", "side": "sell", "qty": 0})
        assert r.status_code == 422 and r.json()["error"] == "invalid_parameter"
        assert c.post("/paper/reset?project_id=demo").json()["cash"] == 100_000
    finally:
        main.app.dependency_overrides.clear()


def test_responses_match_contract_mocks(paper):
    import json

    from tests.test_contract import MOCKS, _assert_conforms

    portfolio_mock = json.loads((MOCKS / "portfolio.demo.json").read_text(encoding="utf-8"))
    res = buy(paper, "AAPL", 10).model_dump(mode="json")
    _assert_conforms(portfolio_mock, res)  # order response = portfolio + fill (contracts/paper.md)
    assert set(res["fill"]) == {"ticker", "side", "qty", "price", "at"}
    _assert_conforms(portfolio_mock, paper.portfolio("demo").model_dump(mode="json"))


def test_open_creates_an_account_once_and_never_resets_it(paper, tmp_path):
    paper.open("Player")
    buy(paper, "AAPL", 10, pid="Player")
    pf = paper.open("Player")
    assert pf.cash == 100_000 - 2_300 and len(pf.positions) == 1
    assert JsonPaperStore(tmp_path).load("player")["resets"] == []
