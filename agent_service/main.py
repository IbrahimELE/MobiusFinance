"""Agent service (osoba B): ticker -> Brief JSON. Podatke uzima samo preko data endpointa iz contracts/.
DATA_URL nije postavljen -> koriste se mockovi iz contracts/mocks (rad od prvog sata, i demo offline).
"""
import json, os, shutil, subprocess, tempfile, datetime as dt
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
    return json.loads(f.read_text(encoding='utf-8'))

def template_thesis(quote, fin, risks):
    g, m = fin["revenue_growth_yoy"] * 100, fin["net_margin"] * 100
    return (f"{quote['name']} raste {g:.1f}% godišnje uz neto maržu {m:.1f}% i P/E {fin['pe']}. "
            f"Glavni rizik: {risks['items'][0]['text']} [2]")

PROMPT = """Ti si financijski analitičar. Napiši tezu (3-4 rečenice, bosanski) za {name} ({t}) ISKLJUČIVO iz podataka ispod.
Svaku tvrdnju završi oznakom izvora [n]. Ne izmišljaj brojeve. Izvori: [1] financials/quote (Yahoo Finance), [2] {filing}.
Podaci: {data}
Vrati samo tekst teze."""

def llm(prompt: str) -> str:
    """Redoslijed: ANTHROPIC_API_KEY (API) -> `claude -p` (prijavljeni Claude, npr. u Möbiusu) -> greška."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        r = httpx.post("https://api.anthropic.com/v1/messages", timeout=60,
            headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
            json={"model": os.environ.get("LLM_MODEL", "claude-sonnet-4-5"), "max_tokens": 500,
                  "messages": [{"role": "user", "content": prompt}]})
        r.raise_for_status()
        return r.json()["content"][0]["text"].strip()
    if shutil.which("claude"):
        r = subprocess.run(["claude", "-p", prompt, "--strict-mcp-config"], capture_output=True, text=True, encoding="utf-8", timeout=120, cwd=tempfile.gettempdir())
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
        raise RuntimeError(r.stderr[:200] or "claude -p prazan odgovor")
    raise RuntimeError("nema LLM-a")

def write_thesis(t, quote, fin, risks):
    """Vraća (tekst, način): 'llm' | 'template'. Uz bilo koju grešku pada na šablon."""
    data = json.dumps({"quote": quote, "financials": fin, "risks": risks["items"]}, ensure_ascii=False)
    try:
        return llm(PROMPT.format(name=quote["name"], t=t, filing=risks["filing"], data=data)), "llm"
    except Exception as e:
        print("LLM nedostupan:", e)
        return template_thesis(quote, fin, risks), "template"

CACHE = ROOT / "agent_service" / "demo_cache"   # unaprijed generisani briefovi za demo (commitovani)

def build_brief(t: str) -> dict:
    quote = fetch("quote", t, f"/quote/{t}")
    fin = fetch("financials", t, f"/financials/{t}")
    risks = fetch("risk-factors", t, f"/filings/{t}/risk-factors")
    thesis, mode = write_thesis(t, quote, fin, risks)
    cached = CACHE / f"{t}.json"
    if mode == "template" and cached.exists():      # nema LLM-a, a imamo puni brief iz keša
        b = json.loads(cached.read_text(encoding="utf-8")); b["mode"] = "cache"; return b
    return {"ticker": t, "thesis": thesis, "mode": mode,
            "metrics": {"price": quote["price"], "pe": fin["pe"],
                        "revenue_growth_yoy": fin["revenue_growth_yoy"], "net_margin": fin["net_margin"]},
            "risks": risks["items"], "peers": [p for p in PEERS.get(t, [])],
            "sources": [{"label": "Yahoo Finance", "url": f"https://finance.yahoo.com/quote/{t}"},
                        {"label": risks["filing"], "url": risks["url"]}],
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat()}

PEERS = {"AAPL": ["MSFT", "GOOGL"], "MSFT": ["AAPL", "GOOGL"], "GOOGL": ["MSFT", "AAPL"],
         "TSLA": ["NVDA"], "NVDA": ["MSFT", "TSLA"]}   # zamjena: A-ov /peers kad bude spreman

def slug(x: str) -> str:
    return "".join(c for c in x.lower().replace(" ", "-") if c.isalnum() or c in "-_")[:40] or "default"

def project_dir(pid: str) -> Path:
    d = STORE / slug(pid); d.mkdir(parents=True, exist_ok=True); return d

@app.post("/brief")
def brief(req: BriefReq):
    t = req.ticker.upper().strip()
    b = build_brief(t)
    (project_dir(req.project_id) / f"{t}.json").write_text(json.dumps(b, ensure_ascii=False, indent=1), encoding="utf-8")
    return b

@app.get("/briefs")
def briefs(project_id: str = "default"):
    d = STORE / slug(project_id)
    return [json.loads(f.read_text(encoding="utf-8")) for f in sorted(d.glob("*.json"))] if d.exists() else []

@app.delete("/briefs/{ticker}")
def delete_brief(ticker: str, project_id: str = "default"):
    (project_dir(project_id) / f"{ticker.upper()}.json").unlink(missing_ok=True)
    return {"ok": True}

class ProjectReq(BaseModel):
    name: str

@app.get("/projects")
def projects():
    STORE.mkdir(parents=True, exist_ok=True)
    names = sorted(d.name for d in STORE.iterdir() if d.is_dir())
    return names or ["default"]

@app.post("/projects")
def create_project(req: ProjectReq):
    return {"project_id": project_dir(req.name).name}

@app.get("/compare")
def compare(tickers: str):
    """Usporedba 2-4 tickera: iste metrike jedna pored druge (iz data endpointa)."""
    rows = []
    for t in [x.strip().upper() for x in tickers.split(",") if x.strip()][:4]:
        q, f = fetch("quote", t, f"/quote/{t}"), fetch("financials", t, f"/financials/{t}")
        rows.append({"ticker": t, "name": q["name"], "price": q["price"], "pe": f["pe"],
                     "revenue_growth_yoy": f["revenue_growth_yoy"], "net_margin": f["net_margin"]})
    return rows

class ChatReq(BaseModel):
    message: str
    project_id: str = "default"

@app.post("/chat")
def chat(req: ChatReq):
    """Pitanja o sačuvanim briefovima projekta. Odgovor samo iz briefova; bez LLM-a poruka objašnjava."""
    bs = briefs(req.project_id)
    if not bs:
        return {"answer": "Projekt još nema briefova. Analiziraj ticker pa pitaj."}
    ctx = json.dumps(bs, ensure_ascii=False)
    try:
        return {"answer": llm(f"Odgovori kratko na bosanskom, ISKLJUČIVO iz ovih briefova (ne izmišljaj; ako nema u njima, reci to), uz oznake izvora gdje ih ima.\nBriefovi: {ctx}\nPitanje: {req.message}")}
    except Exception:
        return {"answer": "Chat treba AI (ANTHROPIC_API_KEY ili prijavljeni claude). Sačuvani briefovi su vidljivi iznad."}

@app.get("/history/{ticker}")
def history(ticker: str, period: str = "1y"):
    return fetch("history", ticker.upper(), f"/history/{ticker.upper()}?period={period}")

app.mount("/", StaticFiles(directory=ROOT / "frontend", html=True), name="ui")
