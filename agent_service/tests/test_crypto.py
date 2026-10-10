"""Item 4: crypto briefs (price data only, no invented risks) and the Crypto tab list."""
import importlib, json, sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import crypto  # noqa: E402

POINTS = [{"time": f"d{i}", "close": 100 + i} for i in range(60)] + [{"time": "x", "close": 80.0}]
QUOTE = {"ticker": "BTC-USD", "name": "Bitcoin USD", "price": 80.0, "year_high": 159.0, "year_low": 80.0, "volume": 1e9}


def test_recognises_crypto_pairs_only():
    assert crypto.is_crypto("BTC-USD") and crypto.is_crypto("doge-usd")
    assert not crypto.is_crypto("AAPL") and not crypto.is_crypto("BRK-B")


def test_stats_from_price_history():
    st = crypto.stats(POINTS)
    assert st["return_1y"] == round(80 / 100 - 1, 4)
    assert st["max_drawdown_1y"] == round(80 / 159 - 1, 4)
    assert st["volatility_30d"] > 0 and "return_30d" in st


def test_brief_has_one_source_and_no_risks_or_fundamentals():
    st = crypto.stats(POINTS)
    b = crypto.brief("BTC-USD", QUOTE, st, crypto.template_thesis("Bitcoin", "BTC-USD", QUOTE, st), "template")
    assert b["asset_class"] == "crypto" and b["name"] == "Bitcoin"
    assert b["risks"] == [] and len(b["sources"]) == 1 and "[2]" not in b["thesis"]
    assert b["metrics"]["pe"] is None and b["extras"]["return_1y"] == st["return_1y"]
    assert "10-K" in crypto.prompt("BTC-USD", "Bitcoin", QUOTE, st)   # the prompt forbids it explicitly
    assert "Never invent" in crypto.prompt("BTC-USD", "Bitcoin", QUOTE, st)


def test_agent_builds_crypto_brief_without_llm(monkeypatch, tmp_path):
    import main
    monkeypatch.setattr(main, "CACHE", tmp_path)
    monkeypatch.setattr(main, "fetch", lambda kind, t, path: QUOTE if kind == "quote" else {"points": POINTS})
    monkeypatch.setattr(main, "llm", lambda p: (_ for _ in ()).throw(RuntimeError("no LLM")))
    b = main.build_brief("BTC-USD")       # ETF filing answer is malformed here: still a brief, without risks
    assert b["mode"] == "template" and b["risks"] == [] and b["thesis"].count("[1]") >= 2


@pytest.fixture
def cat(tmp_path, monkeypatch):
    monkeypatch.setenv("CATALOG_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.delenv("DATA_OFFLINE", raising=False)
    import catalog
    c = importlib.reload(catalog)
    snap = tmp_path / "snap"; snap.mkdir()
    (snap / "sec_tickers.snapshot.json").write_text(json.dumps([["BTC", "Grayscale Bitcoin Mini Trust ETF", 1]]), encoding="utf-8")
    monkeypatch.setattr(c, "SNAPSHOT_DIR", snap)
    monkeypatch.setattr(c, "_fetch_sec", lambda: [["BTC", "Grayscale Bitcoin Mini Trust ETF", 1]])
    return c


def test_search_finds_coins_by_name_and_symbol(cat):
    assert cat.search("bitcoin")["results"][0] == {"ticker": "BTC-USD", "name": "Bitcoin", "sector": "Crypto", "cik": None}
    assert [r["ticker"] for r in cat.search("btc")["results"]][:2] == ["BTC-USD", "BTC"]


def test_crypto_list_is_cached_and_offline_safe(cat, monkeypatch):
    calls = []
    monkeypatch.setattr(cat, "_fetch_prices", lambda ts: calls.append(ts) or {t: (1.0, 2.0) for t in ts})
    m = cat.crypto_market()
    assert m["live"] and len(m["coins"]) == len(crypto.COINS) and m["coins"][0]["price"] == 1.0
    cat.crypto_market(); assert len(calls) == 1
    monkeypatch.setenv("DATA_OFFLINE", "1"); cat._cr["mtime"] = 0
    assert cat.crypto_market()["live"] is False and len(calls) == 1


ETF_RISKS = {"ticker": "IBIT", "filing": "10-K 2025", "url": "https://www.sec.gov/ibit-10k",
             "items": [{"text": "Bitcoin prices are highly volatile.", "source": "10-K 2025, Item 1A"}]}


def test_btc_cites_spot_etf_10k_as_source_2(monkeypatch, tmp_path):
    import main
    monkeypatch.setattr(main, "CACHE", tmp_path)
    data = {"quote": QUOTE, "history": {"points": POINTS}, "risk-factors": ETF_RISKS}
    seen = []
    monkeypatch.setattr(main, "fetch", lambda kind, t, path: seen.append(t) or data[kind])
    monkeypatch.setattr(main, "llm", lambda p: (_ for _ in ()).throw(RuntimeError("no LLM")))
    b = main.build_brief("BTC-USD")
    assert "IBIT" in seen and b["risks"][0]["source"] == "iShares Bitcoin Trust (IBIT) 10-K 2025, Item 1A"
    assert b["sources"][1] == {"label": "iShares Bitcoin Trust (IBIT) 10-K 2025, Item 1A", "url": "https://www.sec.gov/ibit-10k"}
    assert "[2]" in b["thesis"] and "iShares Bitcoin Trust" in b["thesis"]
    assert "not to Bitcoin itself" in crypto.prompt("BTC-USD", "Bitcoin", QUOTE, {}, "", b["risks"])


def test_coin_without_etf_source_or_missing_filing_has_no_risks(monkeypatch, tmp_path):
    import main
    from fastapi import HTTPException
    monkeypatch.setattr(main, "CACHE", tmp_path)
    monkeypatch.setattr(main, "llm", lambda p: (_ for _ in ()).throw(RuntimeError("no LLM")))
    def fetch(kind, t, path):
        if kind == "risk-factors":
            raise HTTPException(503, "offline")
        return {**QUOTE, "ticker": t} if kind == "quote" else {"points": POINTS}
    monkeypatch.setattr(main, "fetch", fetch)
    for t in ("SOL-USD", "ETH-USD"):          # SOL: no ETF source; ETH: filing unavailable
        b = main.build_brief(t)
        assert b["risks"] == [] and len(b["sources"]) == 1 and "[2]" not in b["thesis"]
