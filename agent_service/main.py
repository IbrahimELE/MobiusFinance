"""Agent service (osoba B): ticker -> Brief JSON. Podatke uzima samo preko data endpointa iz contracts/.
DATA_URL nije postavljen -> koriste se mockovi iz contracts/mocks (rad od prvog sata, i demo offline).
"""
import json, os, datetime as dt
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import httpx

ROOT = Path(__file__).resolve().parent.parent
MOCKS = ROOT / "contracts" / "mocks"
STORE = ROOT / "agent_service" / "store"
DATA_URL = os.environ.get("DATA_URL")  # npr. http://localhost:8001
app = FastAPI(title="Finance Desk agent")

class BriefReq(BaseModel):
    ticker: str
    project_id: str = "default"

def fetch(kind: str, ticker: str, path: str):
    """Jedna tačka za podatke: pravi data_service ili mock fajl."""
    if DATA_URL:
        r = httpx.get(f"{DATA_URL}{path}", timeout=20); r.raise_for_status(); return r.json()
    f = MOCKS / f"{kind}.{ticker}.json"
    if not f.exists(): raise HTTPException(404, f"Nema mocka za {ticker} ({kind})")
    return json.loads(f.read_text())

def write_thesis(t, quote, fin, risks):
    """Mjesto za LLM. Sada šablon; kasnije prompt s tvrdnjama vezanim za izvore."""
    g, m = fin["revenue_growth_yoy"] * 100, fin["net_margin"] * 100
    return (f"{quote['name']} raste {g:.1f}% godišnje uz neto maržu {m:.1f}% i P/E {fin['pe']}. "
            f"Glavni rizik: {risks['items'][0]['text']}")

@app.post("/brief")
def brief(req: BriefReq):
    t = req.ticker.upper()
    quote = fetch("quote", t, f"/quote/{t}")
    fin = fetch("financials", t, f"/financials/{t}")
    risks = fetch("risk-factors", t, f"/filings/{t}/risk-factors")
    b = {"ticker": t, "thesis": write_thesis(t, quote, fin, risks),
         "metrics": {"price": quote["price"], "pe": fin["pe"],
                     "revenue_growth_yoy": fin["revenue_growth_yoy"], "net_margin": fin["net_margin"]},
         "risks": risks["items"], "peers": [],
         "sources": [{"label": risks["filing"], "url": risks["url"]},
                     {"label": "Yahoo Finance", "url": f"https://finance.yahoo.com/quote/{t}"}],
         "generated_at": dt.datetime.now(dt.timezone.utc).isoformat()}
    d = STORE / req.project_id; d.mkdir(parents=True, exist_ok=True)
    (d / f"{t}.json").write_text(json.dumps(b, ensure_ascii=False, indent=1))
    return b

@app.get("/briefs")
def briefs(project_id: str = "default"):
    d = STORE / project_id
    return [json.loads(f.read_text()) for f in sorted(d.glob("*.json"))] if d.exists() else []

@app.get("/history/{ticker}")
def history(ticker: str, period: str = "1y"):
    return fetch("history", ticker.upper(), f"/history/{ticker.upper()}?period={period}")

app.mount("/", StaticFiles(directory=ROOT / "frontend", html=True), name="ui")
