"""Leaderboard rules (contracts/leaderboard.md): periods, ranking, reset disqualification, permanent medals."""

import json
from pathlib import Path
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app import main
from app.leaderboard import TZ, Leaderboard, equity_at, next_start, period_start
from app.paper import JsonPaperStore, OrderIn, PaperService

UTC = timezone.utc
# Daily closes as the data service returns them (US trading dates).
CLOSES = {"AAPL": [("2026-10-07", 100.0), ("2026-10-08", 110.0), ("2026-10-09", 120.0)],
          "MSFT": [("2026-10-07", 200.0), ("2026-10-08", 190.0), ("2026-10-09", 180.0)]}


def order(ticker, side, qty, price, at):
    return {"id": at, "ticker": ticker, "side": side, "qty": qty, "price": price, "value": round(qty * price, 2),
            "created_at": at}


def account(orders, created_at=None, resets=(), starting_cash=100_000.0):
    cash, positions = starting_cash, {}
    for o in orders:
        sign = 1 if o["side"] == "buy" else -1
        cash -= sign * o["value"]
        p = positions.setdefault(o["ticker"], {"qty": 0.0, "avg_price": o["price"], "last_price": o["price"]})
        p["qty"] += sign * o["qty"]
        p["last_price"] = o["price"]
    return {"cash": cash, "starting_cash": starting_cash, "realized_pnl": 0.0,
            "positions": {t: p for t, p in positions.items() if p["qty"] > 0}, "orders": orders,
            "created_at": created_at or orders[0]["created_at"], "resets": list(resets)}


class Clock:
    def __init__(self, at):
        self.at = at

    def __call__(self):
        return self.at


@pytest.fixture
def world(tmp_path):
    store = JsonPaperStore(tmp_path)
    prices = {"AAPL": 120.0, "MSFT": 180.0}
    clock = Clock(datetime(2026, 10, 10, 9, 0, tzinfo=UTC))  # Saturday 11:00 in Sarajevo
    paper = PaperService(store, prices.get)
    board = Leaderboard(store, paper, lambda t: CLOSES.get(t, []), tmp_path / "leaderboard" / "podiums.json", clock)
    return store, prices, clock, board


# --- periods ---

def test_periods_start_at_sarajevo_midnight_monday_and_first_of_month():
    at = datetime(2026, 10, 9, 22, 30, tzinfo=UTC)  # already Saturday 00:30 in Sarajevo
    assert period_start("day", at).isoformat() == "2026-10-10T00:00:00+02:00"
    assert period_start("week", at).isoformat() == "2026-10-05T00:00:00+02:00"
    assert period_start("month", at).isoformat() == "2026-10-01T00:00:00+02:00"
    assert next_start("month", datetime(2026, 12, 1, tzinfo=TZ)).isoformat() == "2027-01-01T00:00:00+01:00"


def test_day_after_dst_change_still_starts_at_local_midnight():
    assert next_start("day", datetime(2026, 10, 25, tzinfo=TZ)).isoformat() == "2026-10-26T00:00:00+01:00"


# --- valuation ---

def test_start_equity_uses_last_close_before_the_boundary_not_later_trades():
    acc = account([order("AAPL", "buy", 100, 100.0, "2026-10-07T15:00:00+00:00"),
                   order("AAPL", "buy", 100, 125.0, "2026-10-10T08:00:00+00:00")])
    # Before Friday 9.10. midnight: 100 AAPL bought at 100, valued at Thursday's close 110.
    assert equity_at(acc, datetime(2026, 10, 9, tzinfo=TZ), lambda t: CLOSES[t]) == 100_000 + 100 * 10
    # Without closes the last trade price is used.
    assert equity_at(acc, datetime(2026, 10, 9, tzinfo=TZ), lambda t: []) == 100_000


# --- ranking ---

def test_workspaces_ranked_by_return_with_live_end_value(world):
    store, prices, clock, board = world
    store.save("winner", account([order("AAPL", "buy", 500, 100.0, "2026-10-06T15:00:00+00:00")]))
    store.save("loser", account([order("MSFT", "buy", 500, 200.0, "2026-10-06T15:00:00+00:00")]))
    week = board.standings("week")
    assert [s.project_id for s in week.standings] == ["winner", "loser"]
    assert week.standings[0].rank == 1 and week.standings[0].return_pct == 10.0   # 500 AAPL bought at 100, now 120
    assert week.standings[1].return_pct == -10.0
    assert week.start == "2026-10-05T00:00:00+02:00" and week.end == "2026-10-12T00:00:00+02:00"


def test_workspace_opened_mid_period_starts_from_starting_cash(world):
    store, prices, clock, board = world
    store.save("new", account([order("AAPL", "buy", 100, 110.0, "2026-10-10T08:00:00+00:00")]))
    (row,) = board.standings("day").standings
    assert row.start_equity == 100_000 and row.return_pct == 1.0


def test_untraded_workspace_is_not_ranked(world):
    store, prices, clock, board = world
    store.save("idle", {"cash": 100_000, "starting_cash": 100_000, "realized_pnl": 0, "positions": {},
                        "orders": [], "created_at": "2026-10-01T10:00:00+00:00", "resets": []})
    assert board.standings("week").standings == []


def test_reset_in_period_disqualifies_and_cannot_hide_a_loss(world):
    store, prices, clock, board = world
    store.save("cheater", account([order("AAPL", "buy", 10, 120.0, "2026-10-10T08:30:00+00:00")],
                                  created_at="2026-10-10T08:00:00+00:00", resets=["2026-10-10T08:00:00+00:00"]))
    store.save("honest", account([order("MSFT", "buy", 10, 200.0, "2026-10-06T15:00:00+00:00")]))
    week = board.standings("week").standings
    assert [(s.project_id, s.rank, s.disqualified, s.note) for s in week] == [
        ("honest", 1, False, None), ("cheater", None, True, "reset")]


def test_reset_with_no_new_trades_still_shows_as_disqualified(world):
    store, prices, clock, board = world
    PaperService(store, prices.get).reset("quitter")
    clock.at = datetime.now(UTC)
    rows = board.standings("day").standings
    assert [(s.project_id, s.disqualified) for s in rows] == [("quitter", True)]


def test_reset_in_an_earlier_period_does_not_disqualify_the_current_one(world):
    store, prices, clock, board = world
    store.save("fresh", account([order("AAPL", "buy", 10, 120.0, "2026-10-10T08:30:00+00:00")],
                                created_at="2026-10-09T08:00:00+00:00", resets=["2026-10-09T08:00:00+00:00"]))
    (row,) = board.standings("day").standings
    assert row.rank == 1 and not row.disqualified


# --- permanent medals ---

def test_closed_days_award_permanent_medals_that_survive_a_later_reset(world, tmp_path):
    store, prices, clock, board = world
    store.save("a", account([order("AAPL", "buy", 500, 100.0, "2026-10-07T15:00:00+00:00")]))
    store.save("b", account([order("MSFT", "buy", 500, 200.0, "2026-10-07T15:00:00+00:00")]))
    out = board.standings("day")
    # Wed 7.10.: both flat, so no podium; Thu and Fri: AAPL rises, MSFT falls.
    by_id = {m.project_id: (m.gold, m.silver, m.bronze) for m in out.medals}
    assert by_id == {"a": (2, 0, 0), "b": (0, 2, 0)}
    assert out.last_podium.start == "2026-10-09T00:00:00+02:00"
    assert [p.project_id for p in out.last_podium.places] == ["a", "b"]

    # Reading again does not count the same days twice; a later reset does not remove medals.
    PaperService(store, prices.get).reset("a")
    again = board.standings("day")
    assert {m.project_id: m.gold for m in again.medals} == {"a": 2, "b": 0}
    state = json.loads((tmp_path / "leaderboard" / "podiums.json").read_text())
    assert state["finalized"]["day"] == "2026-10-09T00:00:00+02:00"


def test_next_day_finalizes_only_the_newly_closed_day(world):
    store, prices, clock, board = world
    store.save("a", account([order("AAPL", "buy", 10, 110.0, "2026-10-08T19:00:00+00:00")]))
    clock.at = datetime(2026, 10, 9, 9, 0, tzinfo=UTC)  # Friday: Thursday was flat (bought at its close)
    assert board.standings("day").medals == []
    clock.at = datetime(2026, 10, 10, 9, 0, tzinfo=UTC)  # Saturday: Friday closed with AAPL at 120
    out = board.standings("day")
    assert out.last_podium.start == "2026-10-09T00:00:00+02:00"
    assert [(m.project_id, m.gold) for m in out.medals] == [("a", 1)]


# --- route ---

def test_route_follows_the_contract_mock(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_PAPER_DIR", str(tmp_path))
    monkeypatch.setenv("DATA_OFFLINE", "1")
    for f in (main.get_service, main.get_paper, main.get_leaderboard):
        f.cache_clear()
    try:
        client = TestClient(main.app)
        client.post("/paper/orders", json={"project_id": "demo", "ticker": "AAPL", "side": "buy", "qty": 1})
        body = client.get("/paper/leaderboard", params={"period": "week"}).json()
        mock = json.loads((Path(__file__).resolve().parents[2] / "contracts/mocks/leaderboard.demo.json")
                          .read_text(encoding="utf-8"))
        assert set(body) == set(mock)
        assert set(body["standings"][0]) == set(mock["standings"][0])
        assert body["standings"][0]["project_id"] == "demo"
        assert client.get("/paper/leaderboard", params={"period": "year"}).status_code == 422
    finally:
        for f in (main.get_service, main.get_paper, main.get_leaderboard):
            f.cache_clear()


def test_flat_weekend_days_award_no_medals_by_name_tie_break(world):
    store, prices, clock, board = world
    store.save("a", account([order("AAPL", "buy", 10, 120.0, "2026-10-09T21:00:00+00:00")]))
    store.save("b", account([order("MSFT", "buy", 10, 180.0, "2026-10-09T21:00:00+00:00")]))
    clock.at = datetime(2026, 10, 12, 9, 0, tzinfo=UTC)  # Monday: Sat 10. and Sun 11. are closed
    out = board.standings("day")
    assert out.medals == [] and out.last_podium is None
