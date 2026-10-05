"""The data service must serve every field of the team contract mocks
(../contracts/mocks/<kind>.AAPL.json) with the same JSON type, so the agent
works unchanged when DATA_URL points here. Checked against the committed demo
snapshot, i.e. real responses."""

import json
from pathlib import Path

import pytest

from app.cache import DiskCache
from app.config import DEMO_TICKERS, SERVICE_DIR
from app.models import Financials, History, Quote, RiskFactors

MOCKS = SERVICE_DIR.parent / "contracts" / "mocks"
DEMO = DiskCache(SERVICE_DIR / "demo_cache")

CASES = [  # (mock file kind, demo cache kind, variant, model)
    ("quote", "quote", None, Quote),
    ("history", "history", "1y", History),
    ("financials", "financials", None, Financials),
    ("risk-factors", "risk_factors", None, RiskFactors),
]


def _type(v):
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, (int, float)):
        return "number"
    return type(v).__name__


def _assert_conforms(mock, real, path="$"):
    if isinstance(mock, dict):
        assert isinstance(real, dict), f"{path}: expected object"
        for k, v in mock.items():
            assert k in real, f"{path}.{k} missing"
            if v is not None and real[k] is not None:
                _assert_conforms(v, real[k], f"{path}.{k}")
    elif isinstance(mock, list):
        assert isinstance(real, list), f"{path}: expected list"
        if mock and real:
            _assert_conforms(mock[0], real[0], f"{path}[0]")
    else:
        assert _type(mock) == _type(real), f"{path}: {_type(real)} instead of {_type(mock)}"


@pytest.mark.parametrize("ticker", DEMO_TICKERS)
@pytest.mark.parametrize("mock_kind,kind,variant,model", CASES)
def test_demo_snapshot_matches_contract(mock_kind, kind, variant, model, ticker):
    mock = json.loads((MOCKS / f"{mock_kind}.AAPL.json").read_text(encoding="utf-8"))
    entry = DEMO.get(kind, ticker, variant)
    assert entry, f"demo snapshot missing {kind} {ticker}; run scripts.warm_demo_cache"
    real = model.model_validate(entry.payload).model_dump(mode="json")
    _assert_conforms(mock, real)


def test_core_numbers_present_for_demo_tickers():
    for t in DEMO_TICKERS:
        f = DEMO.get("financials", t).payload
        assert all(f[k] is not None for k in ("pe", "revenue_growth_yoy", "net_margin")), t
        assert DEMO.get("risk_factors", t).payload["items"], t
        assert DEMO.get("quote", t).payload["price"], t
