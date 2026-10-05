"""API + cache policy with fake providers (no network)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app import main
from app.config import Settings
from app.models import Financials, History, Meta, PricePoint, Quote, RiskFactor, RiskFactors, RiskItem
from app.providers.base import TickerNotFound, UpstreamError
from app.service import DataService


def _meta(provider="fake"):
    return Meta(provider=provider, fetched_at=datetime.now(timezone.utc).isoformat(), cached=False)


class FakeMarket:
    name = "fake"

    def __init__(self):
        self.calls = 0
        self.fail = False

    def _check(self, t):
        self.calls += 1
        if self.fail:
            raise UpstreamError("rate limited")
        if t == "NOPE":
            raise TickerNotFound(t)

    def quote(self, t):
        self._check(t)
        return Quote(ticker=t, price=100.0 + self.calls, meta=_meta())

    def history(self, t, period, interval):
        self._check(t)
        pts = [PricePoint(time="2026-10-01", open=1, high=2, low=0.5, close=1.5, volume=10)]
        return History(ticker=t, period=period, interval=interval, points=pts, meta=_meta())

    def financials(self, t):
        self._check(t)
        return Financials(ticker=t, pe=20, net_margin=0.2, revenue_growth_yoy=0.05, meta=_meta())


class FakeFilings:
    name = "fake_edgar"

    def risk_factors(self, t):
        return RiskFactors(
            ticker=t, filing="10-K 2025", url="https://sec.gov/x",
            items=[RiskItem(text="Risk.", source="10-K 2025, Item 1A")],
            cik="1", filing_date="2025-10-31", accession_number="x",
            risks=[RiskFactor(title="Risk.", text="Body")], meta=_meta(),
        )


@pytest.fixture
def env(tmp_path):
    market = FakeMarket()

    def make(offline=False):
        s = Settings(cache_dir=tmp_path / "cache", demo_cache_dir=tmp_path / "demo", offline=offline)
        svc = DataService(s, market, FakeFilings())
        main.app.dependency_overrides[main.get_service] = lambda: svc
        return TestClient(main.app), svc

    yield market, make, tmp_path
    main.app.dependency_overrides.clear()


def test_live_then_cached(env):
    market, make, _ = env
    client, _ = make()
    first = client.get("/quote/aapl").json()
    second = client.get("/quote/AAPL").json()
    assert first["ticker"] == "AAPL" and first["meta"]["cached"] is False
    assert second["meta"]["cached"] is True and second["price"] == first["price"]
    assert market.calls == 1


def test_upstream_failure_serves_stale_cache(env):
    market, make, tmp = env
    client, svc = make()
    client.get("/quote/AAPL")
    # Age the entry past its TTL, then break the upstream.
    p = tmp / "cache" / "quote" / "AAPL.json"
    raw = json.loads(p.read_text())
    raw["stored_at"] = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    p.write_text(json.dumps(raw))
    market.fail = True
    r = client.get("/quote/AAPL").json()
    assert r["meta"]["cached"] is True and r["meta"]["stale"] is True


def test_upstream_failure_without_cache_is_502(env):
    market, make, _ = env
    client, _ = make()
    market.fail = True
    r = client.get("/financials/MSFT")
    assert r.status_code == 502 and r.json()["error"] == "upstream_unavailable"


def test_offline_uses_demo_snapshot_and_never_calls_upstream(env):
    market, make, tmp = env
    client, svc = make()
    svc.demo.put("history", "NVDA", client.get("/history/NVDA?period=1y").json(), "1y")
    calls = market.calls
    client, _ = make(offline=True)
    r = client.get("/history/NVDA?period=1y")
    assert r.status_code == 200 and r.json()["meta"]["cached"] is True
    assert market.calls == calls
    missing = client.get("/quote/TSLA")
    assert missing.status_code == 503 and missing.json()["error"] == "not_in_cache"


def test_errors_have_one_shape(env):
    _, make, _ = env
    client, _ = make()
    assert client.get("/quote/NOPE").json()["error"] == "ticker_not_found"
    for url in ("/quote/bad%20ticker", "/history/AAPL?period=7y"):
        r = client.get(url)
        assert r.status_code == 422 and set(r.json()) == {"error", "detail"}


def test_risk_factors_route(env):
    _, make, _ = env
    client, _ = make()
    r = client.get("/filings/aapl/risk-factors").json()
    assert r["filing"] == "10-K 2025" and r["items"][0] == {"text": "Risk.", "source": "10-K 2025, Item 1A"}
