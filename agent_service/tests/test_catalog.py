"""Katalog (contracts/catalog.md): pretraga po imenu, Yahoo fallback, keš i offline ponašanje. Bez mreže (fetcheri zamijenjeni)."""
import importlib, json, os, sys, time
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

SEC = [["NVDA", "NVIDIA CORP", 1045810], ["AAPL", "Apple Inc.", 320193], ["APLE", "Apple Hospitality REIT, Inc.", 1418121],
       ["MSFT", "MICROSOFT CORP", 789019], ["XOM", "EXXON MOBIL CORP", 34088]]

@pytest.fixture
def cat(tmp_path, monkeypatch):
    monkeypatch.setenv("CATALOG_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.delenv("DATA_OFFLINE", raising=False)
    import catalog
    c = importlib.reload(catalog)
    snap = tmp_path / "snap"; snap.mkdir()
    (snap / "sec_tickers.snapshot.json").write_text(json.dumps(SEC[:2]), encoding="utf-8")
    monkeypatch.setattr(c, "SNAPSHOT_DIR", snap)
    calls = {"sec": 0, "yahoo": 0, "screen": 0, "sector": 0, "prices": 0}
    def sec():
        calls["sec"] += 1; return SEC
    def yahoo(q):
        calls["yahoo"] += 1; return [{"ticker": "TM", "name": "Toyota Motor Corporation", "sector": "Consumer Cyclical", "cik": None}]
    def screen(name):
        calls["screen"] += 1
        return [{"ticker": "NVDA", "name": "NVIDIA Corporation", "price": 190.0, "change_pct": 2.5},
                {"ticker": "ZZZZ", "name": "Not in SEC", "price": 1.0, "change_pct": 9.0}]
    def sector(key):
        calls["sector"] += 1
        return {"key": key, "name": key.title(), "stocks": [{"ticker": "XOM" if key == "energy" else "AAPL", "name": "Some Name"}]}
    def prices(ts):
        calls["prices"] += 1; return {t: (100.0, -1.5) for t in ts}
    monkeypatch.setattr(c, "_fetch_sec", sec); monkeypatch.setattr(c, "_fetch_yahoo_search", yahoo)
    monkeypatch.setattr(c, "_fetch_screen", screen); monkeypatch.setattr(c, "_fetch_sector", sector)
    monkeypatch.setattr(c, "_fetch_prices", prices)
    c.calls = calls
    return c

def test_company_name_finds_ticker(cat):
    cat.sec_rows(block=True)
    r = cat.search("nvidia")
    assert r["source"] == "sec" and r["results"][0]["ticker"] == "NVDA"

def test_exact_ticker_ranks_first_and_name_prefix_matches(cat):
    cat.sec_rows(block=True)
    assert cat.search("aple")["results"][0]["ticker"] == "APLE"
    assert [x["ticker"] for x in cat.search("apple")["results"]][:2] == ["AAPL", "APLE"]

def test_yahoo_fallback_only_without_local_hit(cat):
    cat.sec_rows(block=True)
    cat.search("nvidia"); assert cat.calls["yahoo"] == 0
    r = cat.search("toyota")
    assert r["source"] == "yahoo" and r["results"][0]["ticker"] == "TM" and cat.calls["yahoo"] == 1

def test_sec_list_refreshes_once_a_day_and_is_cached_to_disk(cat):
    assert len(cat.sec_rows(block=True)) == len(SEC) and cat.calls["sec"] == 1
    assert (cat.CACHE_DIR / "sec_tickers.json").exists()
    cat.sec_rows(block=True); assert cat.calls["sec"] == 1          # fresh cache, no second download

def test_offline_uses_snapshot_and_never_calls_network(cat, monkeypatch):
    monkeypatch.setenv("DATA_OFFLINE", "1")
    assert [r[0] for r in cat.sec_rows(block=True)] == ["NVDA", "AAPL"]   # snapshot
    assert cat.search("toyota")["source"] == "none"
    m = cat.markets()
    assert m["live"] is False and sum(cat.calls.values()) == 0

def test_failed_download_keeps_last_cache(cat, monkeypatch):
    cat.sec_rows(block=True)
    monkeypatch.setattr(cat, "_fetch_sec", lambda: (_ for _ in ()).throw(OSError("no network")))
    cat._sec["mtime"] = 0
    assert len(cat.sec_rows(block=True)) == len(SEC)

def test_markets_lists_only_supported_tickers_with_prices_and_ttl_cache(cat):
    cat.sec_rows(block=True)
    m = cat.markets()
    assert m["live"] is True
    assert [r["ticker"] for r in m["lists"]["most_actives"]] == ["NVDA"]          # ZZZZ is not in the SEC list
    energy = next(s for s in m["sectors"] if s["key"] == "energy")
    assert energy["stocks"][0] == {"ticker": "XOM", "name": "Some Name", "price": 100.0, "change_pct": -1.5}
    n = dict(cat.calls); cat.markets()
    assert cat.calls == n                                                          # served from the few-minute cache
    cat._mk["mtime"] = time.time() - cat.MARKETS_TTL - 1; cat.markets()
    assert cat.calls["screen"] == n["screen"] + 3 and cat.calls["sector"] == n["sector"]   # sectors cached for a day

def test_markets_falls_back_to_last_cache_when_yahoo_fails(cat, monkeypatch):
    cat.sec_rows(block=True); cat.markets()
    monkeypatch.setattr(cat, "_fetch_screen", lambda n: (_ for _ in ()).throw(RuntimeError("yahoo down")))
    cat._mk["mtime"] = 0
    m = cat.markets()
    assert m["live"] is False and m["lists"]["most_actives"][0]["ticker"] == "NVDA"

def test_sector_shown_in_search_from_markets(cat):
    cat.sec_rows(block=True); cat.markets()
    assert cat.search("xom")["results"][0]["sector"] == "Energy"
