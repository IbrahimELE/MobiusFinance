"""Learning service without network: rules, LLM layer via a fake, API and contract."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import main
from app.llm import LLMUnavailable
from app.models import FeedbackIn
from app.rules import build_profile, read_note
from app.service import LearningService, feedback_key
from app.store import LearningStore

MOCKS = Path(__file__).resolve().parents[2] / "contracts" / "mocks"


# --- rules ----------------------------------------------------------------------------

@pytest.mark.parametrize("note,topics,style", [
    ("Više o dugu i slobodnom novčanom toku, kraće.", {"debt": 1, "free_cash_flow": 1}, {"length": "short"}),
    ("Manje o proizvodima.", {"product_details": -1}, {}),
    ("Previše teksta, ne razumijem pojmove", {}, {"length": "short", "tone": "simple"}),
    ("Fali poredjenje s konkurencijom i valuacija (P/E)", {"competition": 1, "valuation": 1}, {}),
    ("vise o dugu", {"debt": 1}, {}),  # typed without diacritics
    ("More on cash flow, less about products", {"free_cash_flow": 1, "product_details": -1}, {}),
])
def test_reads_notes(note, topics, style):
    assert read_note(note) == (topics, style)


def test_latest_opinion_wins_and_tags_count():
    p = build_profile([
        {"rating": "down", "note": "Manje o proizvodima."},
        {"rating": "up", "note": "Ipak mi treba više o proizvodima.", "tags": ["margins", "simple"]},
    ])
    assert set(p.focus) == {"product_details", "margins"}
    assert p.avoid == [] and p.style["tone"] == "simple"


def test_demo_feedback_gives_visible_profile():
    items = json.loads((Path(__file__).resolve().parents[1] / "demo" / "feedback.json").read_text(encoding="utf-8"))
    p = build_profile(items)
    assert p.focus == ["debt", "free_cash_flow"] and p.avoid == ["product_details"] and p.style["length"] == "short"
    assert "zaduženost" in p.instructions() and "kraće" in p.label()


def test_empty_feedback_means_no_instructions():
    p = build_profile([{"rating": "up", "note": "Super!"}])
    assert p.empty and p.instructions() == "" and p.label() == ""


# --- service + LLM layer ----------------------------------------------------------------

@pytest.fixture
def make(tmp_path):
    def _make(use_llm=True, summarise=None):
        def fake(items, rules):
            return {"instructions": f"AI: {len(items)} ocjena, fokus {rules['focus']}", "label": "AI label"}
        return LearningService(LearningStore(tmp_path), use_llm=use_llm, summarise=summarise or fake)
    return _make


def fb(note, rating="down", ticker="AAPL", pid="Demo Projekt", tags=()):
    return FeedbackIn(project_id=pid, ticker=ticker, rating=rating, note=note, tags=list(tags))


def test_rules_profile_is_immediate_and_llm_follows(make):
    svc = make()
    svc.add(fb("Više o dugu"))
    p = svc.profile("Demo Projekt")
    assert p.project_id == "demo-projekt" and p.mode == "rules" and p.focus == ["debt"]
    assert svc.refresh_llm("Demo Projekt") is True
    p = svc.profile("demo-projekt")
    assert p.mode == "llm" and p.instructions.startswith("AI: 1 ocjena") and p.label == "AI label"
    assert svc.refresh_llm("demo-projekt") is False  # nothing new to summarise


def test_new_feedback_invalidates_llm_summary(make):
    svc = make()
    svc.add(fb("Više o dugu"))
    svc.refresh_llm("demo-projekt")
    svc.add(fb("Manje o proizvodima"))
    assert svc.profile("demo-projekt").mode == "rules"  # old summary no longer matches


def test_llm_failure_keeps_rules(make):
    def broken(items, rules):
        raise LLMUnavailable("offline")
    svc = make(summarise=broken)
    svc.add(fb("kraće"))
    assert svc.refresh_llm("demo-projekt") is False
    assert svc.profile("demo-projekt").mode == "rules"


def test_llm_off(make):
    svc = make(use_llm=False)
    svc.add(fb("kraće"))
    assert svc.refresh_llm("demo-projekt") is False


def test_forget_and_seed_demo(make):
    svc = make(use_llm=False)
    svc.add(fb("kraće", pid="demo"))
    svc.forget("demo")
    assert svc.profile("demo").feedback_count == 0
    p = svc.seed_demo("demo")
    assert p.feedback_count == 2 and p.focus == ["debt", "free_cash_flow"]


def test_feedback_key_ignores_ids_and_projects():
    a = [{"id": "1", "project_id": "x", "ticker": "AAPL", "rating": "down", "note": "n", "tags": []}]
    b = [{"id": "2", "project_id": "y", "ticker": "AAPL", "rating": "down", "note": "n", "tags": []}]
    assert feedback_key(a) == feedback_key(b)


# --- API + contract ---------------------------------------------------------------------

def _conforms(mock, real, path="$"):
    if isinstance(mock, dict):
        for k, v in mock.items():
            assert k in real, f"{path}.{k} missing"
            if v is not None and real[k] is not None:
                _conforms(v, real[k], f"{path}.{k}")
    elif isinstance(mock, list):
        assert isinstance(real, list), path
        if mock and real:
            _conforms(mock[0], real[0], f"{path}[0]")
    else:
        num = (int, float)
        assert (isinstance(mock, num) and isinstance(real, num)) or type(mock) is type(real), path


def test_api_flow_matches_contract(make):
    svc = make(use_llm=False)
    main.app.dependency_overrides[main.get_service] = lambda: svc
    try:
        c = TestClient(main.app)
        r = c.post("/feedback", json={"project_id": "demo", "ticker": "aapl", "rating": "down",
                                      "note": "Više o dugu i slobodnom novčanom toku, kraće."})
        assert r.status_code == 200 and r.json()["ticker"] == "AAPL"
        c.post("/feedback", json={"project_id": "demo", "ticker": "MSFT", "rating": "down",
                                  "note": "Manje o proizvodima.", "tags": ["short"]})
        prof = c.get("/profile?project_id=demo").json()
        _conforms(json.loads((MOCKS / "profile.demo.json").read_text(encoding="utf-8")), prof)
        assert prof["focus"] == ["debt", "free_cash_flow"] and prof["avoid"] == ["product_details"]
        items = c.get("/feedback?project_id=demo").json()
        _conforms(json.loads((MOCKS / "feedback.demo.json").read_text(encoding="utf-8")), items)
        assert [i["ticker"] for i in items] == ["AAPL", "MSFT"]
        bad = c.post("/feedback", json={"project_id": "demo", "ticker": "AAPL", "rating": "meh"})
        assert bad.status_code == 422 and bad.json()["error"] == "invalid_parameter"
        bad = c.post("/feedback", json={"project_id": "demo", "ticker": "AAPL", "rating": "up", "tags": ["x"]})
        assert bad.status_code == 422
        assert c.delete("/profile?project_id=demo").json()["feedback_count"] == 0
        assert c.post("/demo/seed?project_id=demo").json()["feedback_count"] == 2
    finally:
        main.app.dependency_overrides.clear()
