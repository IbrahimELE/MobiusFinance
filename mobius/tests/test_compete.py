"""Shared competition: a player instance and the host, simulated in one process (no network).

The fake platform plays the Möbius identity API and directory; `peer` delivers HTTP calls to the
other instance's service exactly as the public route would.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fd_compete  # noqa: E402
import service  # noqa: E402

HOST, PLAYER, OTHER = fd_compete.HOST_DEFAULT, "player.example.app", "someone-else.example.app"
DIRECTORY = {"ibrahim": [HOST], "amra": [PLAYER]}


class FakeData:
    def quote(self, t):
        return SimpleNamespace(price={"AAPL": 200.0, "MSFT": 500.0}[t.upper()])

    def history(self, t, period):
        return SimpleNamespace(points=[])


class World:
    """Two instances: their storage roots, who is signed in where, and which one is 'current'."""

    def __init__(self, tmp_path, monkeypatch):
        self.roots = {HOST: tmp_path / "host", PLAYER: tmp_path / "player"}
        self.users = {HOST: "ibrahim", PLAYER: "amra"}
        self.current = PLAYER
        self.tamper = None
        real_init = service.App.__init__

        def init(app, root):
            real_init(app, root)
            app.data = FakeData()
        monkeypatch.setattr(service.App, "__init__", init)
        monkeypatch.setattr(service, "own_host", lambda: self.current)
        monkeypatch.setattr(service, "platform", self.platform)
        monkeypatch.setattr(service, "peer", self.peer)

    def platform(self, path):
        if path == "/api/identity":
            return {"profile": {"handle": self.users[self.current]}}
        name = path.rsplit("/", 1)[1]
        return {"linked": name in DIRECTORY, "hosts": DIRECTORY.get(name, [])}

    def peer(self, target, path, body=None):
        caller, self.current = self.current, target
        try:
            if self.tamper and body is not None:
                body = self.tamper(body)
            status, data = service.handle({"schema": 1, "public": True, "method": "POST" if body is not None else "GET",
                                           "path": path, "query": {}, "body": body}, self.roots[target])
        finally:
            self.current = caller
        if status >= 400:
            raise fd_compete.Refused(status, data["error"], data["detail"])
        return data

    def call(self, where, action, body=None, rid=None):
        self.current = where
        req = {"schema": 1, "method": "POST", "path": f"compete/{action}", "query": {},
               "body": {**(body or {}), "request_id": rid or "a0a0a0a0-0000-0000-0001"}}
        return service.handle(req, self.roots[where])


@pytest.fixture
def world(tmp_path, monkeypatch):
    return World(tmp_path, monkeypatch)


def test_player_joins_and_trades_on_the_host_at_host_prices(world):
    assert world.call(PLAYER, "join")[0] == 200
    status, pf = world.call(PLAYER, "order", {"ticker": "aapl", "side": "buy", "qty": 10}, rid="b1b1b1b1-0000-0000-0001")
    assert status == 200 and pf["cash"] == 98_000            # filled by the host's price (200), not the player's
    accounts = world.roots[HOST] / "competition" / "accounts"
    assert sorted(p.name for p in accounts.glob("*.json")) == ["amra.json"]
    assert not (world.roots[PLAYER] / "competition" / "accounts").exists()


def test_host_owner_plays_locally_and_everyone_shares_one_ranking(world):
    world.call(PLAYER, "join")
    world.call(HOST, "join")
    world.call(HOST, "order", {"ticker": "MSFT", "side": "buy", "qty": 1}, rid="b1b1b1b1-0000-0000-0002")
    status, board = world.call(PLAYER, "standings", {"period": "week"})
    assert status == 200 and board["players"] == 2 and board["joined"] is True
    assert sorted(r["project_id"] for r in board["standings"]) == ["@ibrahim"]  # only traded accounts rank


def test_retried_order_does_not_trade_twice(world):
    world.call(PLAYER, "join")
    first = world.call(PLAYER, "order", {"ticker": "AAPL", "side": "buy", "qty": 1}, rid="c2c2c2c2-0000-0000-0001")
    again = world.call(PLAYER, "order", {"ticker": "AAPL", "side": "buy", "qty": 1}, rid="c2c2c2c2-0000-0000-0001")
    assert first == again and again[1]["cash"] == 99_800
    reused = world.call(PLAYER, "order", {"ticker": "AAPL", "side": "buy", "qty": 5}, rid="c2c2c2c2-0000-0000-0001")
    assert reused[0] == 409


def test_orders_before_joining_are_refused(world):
    status, body = world.call(PLAYER, "order", {"ticker": "AAPL", "side": "buy", "qty": 1})
    assert (status, body["error"]) == (409, "not_joined")


def test_a_forged_actor_is_rejected_because_the_proof_does_not_match(world):
    world.call(PLAYER, "join")

    def impersonate(body):
        if "request" in body:
            body = {**body, "request": {**body["request"], "actor": "@ibrahim"}}
        return body
    world.tamper = impersonate
    status, body = world.call(PLAYER, "order", {"ticker": "AAPL", "side": "buy", "qty": 1})
    assert status == 403 and body["error"] in ("wrong_host", "bad_proof")


def test_a_changed_order_body_breaks_the_proof(world):
    world.call(PLAYER, "join")

    def bigger(body):
        if "request" in body:
            body = {**body, "request": {**body["request"], "body": {"ticker": "AAPL", "side": "buy", "qty": 400}}}
        return body
    world.tamper = bigger
    status, body = world.call(PLAYER, "order", {"ticker": "AAPL", "side": "buy", "qty": 1})
    assert (status, body["error"]) == (403, "bad_proof")


def test_an_instance_not_registered_to_the_handle_cannot_play(world):
    world.roots[OTHER] = world.roots[PLAYER].parent / "other"
    world.users[OTHER] = "amra"                                  # signed in as @amra, but not in her directory
    status, body = world.call(OTHER, "join")
    assert (status, body["error"]) == (409, "host_not_registered")


def test_only_the_host_accepts_exchanges(world):
    world.current = PLAYER
    status, _ = service.handle({"schema": 1, "public": True, "method": "POST", "path": "exchange", "query": {},
                                "body": {"sender": HOST, "proof": "0" * 64, "request": {}}}, world.roots[PLAYER])
    assert status == 404


def test_competition_accounts_cannot_be_reset(world):
    world.call(PLAYER, "join")
    assert world.call(PLAYER, "reset")[0] == 404


def test_the_host_refuses_an_exchange_claiming_to_come_from_itself(world):
    world.current = HOST
    status, body = service.handle({"schema": 1, "public": True, "method": "POST", "path": "exchange", "query": {},
                                   "body": {"sender": HOST, "proof": "0" * 64, "request": {}}}, world.roots[HOST])
    assert (status, body["error"]) == (400, "invalid_request")


def test_board_shows_top_ten_by_money_made_plus_the_players_own_place(world, monkeypatch):
    world.call(PLAYER, "join")
    comp = service.App(world.roots[HOST]).competition
    store = comp.paper.store
    for i in range(1, 13):                                # 12 other players with growing profits
        name = f"p{i:02d}"
        store.save(name, {"cash": 100_000 - 10 * (200.0 - i), "starting_cash": 100_000.0, "realized_pnl": 0.0,
                          "positions": {"AAPL": {"qty": 10.0, "avg_price": 200.0 - i, "last_price": 200.0}},
                          "orders": [{"id": name, "ticker": "AAPL", "side": "buy", "qty": 10.0, "price": 200.0 - i,
                                      "value": 10 * (200.0 - i), "created_at": "2026-10-01T15:00:00+00:00"}],
                          "created_at": "2026-10-01T15:00:00+00:00", "resets": []})
    world.call(PLAYER, "order", {"ticker": "AAPL", "side": "buy", "qty": 1}, rid="d3d3d3d3-0000-0000-0001")
    status, board = world.call(PLAYER, "standings", {"period": "month"})
    assert status == 200 and len(board["standings"]) == 10 and board["ranked"] == 13
    profits = [r["profit"] for r in board["standings"]]
    assert profits == sorted(profits, reverse=True) and board["standings"][0]["project_id"] == "@p12"
    assert board["me"]["project_id"] == "@amra" and board["me"]["rank"] == 13
