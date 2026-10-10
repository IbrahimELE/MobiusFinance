"""Agent service (osoba B): ticker -> Brief JSON. Podatke uzima samo preko data endpointa iz contracts/.
DATA_URL nije postavljen -> koriste se mockovi iz contracts/mocks (rad od prvog sata, i demo offline).
"""
import json, os, shutil, subprocess, tempfile, datetime as dt
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import httpx
import catalog

ROOT = Path(__file__).resolve().parent.parent
MOCKS = ROOT / "contracts" / "mocks"
STORE = ROOT / "agent_service" / "store"
DATA_URL = os.environ.get("DATA_URL")  # npr. http://localhost:8001
LEARNING_URL = os.environ.get("LEARNING_URL")  # npr. http://localhost:8003 (osoba A); bez njega nema učenja
app = FastAPI(title="Finance Desk agent")

class BriefReq(BaseModel):
    ticker: str
    project_id: str = "default"

# Kodovi grešaka A-ovih servisa ({"error","detail"}) -> poruka koju UI prikaže korisniku.
ERROR_TEXT = {
    "ticker_not_found": "Unknown ticker. Check the symbol (e.g. AAPL, MSFT, NVDA).",
    "invalid_ticker": "That doesn't look like a ticker symbol.",
    "filing_not_found": "No 10-K annual report for this company (foreign companies file a 20-F instead).",
    "not_in_cache": "Offline mode: no saved data for this ticker (demo tickers: AAPL, MSFT, NVDA).",
    "upstream_unavailable": "The data source isn't responding. Try again in a few seconds.",
    "insufficient_cash": "Not enough cash in your paper account for this order.",
    "insufficient_position": "You don't own enough free shares (some may be locked in open orders).",
    "order_not_found": "That order is no longer open (it may have just filled).",
}

def upstream_error(r: httpx.Response) -> HTTPException:
    """Pretvara grešku A-ovog servisa u HTTPException s čitljivom porukom (isti status kod)."""
    try:
        body = r.json()
    except ValueError:
        body = {}
    code = body.get("error") if isinstance(body, dict) else None
    detail = body.get("detail") if isinstance(body, dict) else None
    msg = ERROR_TEXT.get(code) or (detail if isinstance(detail, str) else None) or r.text[:200]
    return HTTPException(r.status_code, msg)

def call(method: str, url: str, **kw) -> dict:
    try:
        r = httpx.request(method, url, timeout=kw.pop("timeout", 20), **kw)
    except httpx.HTTPError as e:
        raise HTTPException(503, f"Service unavailable ({url.split('/')[2]}). Is run.sh running?") from e
    if r.status_code >= 400:
        raise upstream_error(r)
    return r.json()

def fetch(kind: str, ticker: str, path: str):
    """Jedna tačka za podatke: pravi data_service ili mock fajl."""
    if DATA_URL:
        return call("GET", f"{DATA_URL}{path}")
    f = MOCKS / f"{kind}.{ticker}.json"
    if not f.exists(): raise HTTPException(404, f"No mock data for {ticker} ({kind})")
    return json.loads(f.read_text(encoding='utf-8'))

def template_thesis(quote, fin, risks):
    g, m = fin["revenue_growth_yoy"] * 100, fin["net_margin"] * 100
    return (f"{quote['name']} grew revenue {g:.1f}% year over year with a {m:.1f}% net margin and a P/E of {fin['pe']} [1]. "
            f"Key risk: {risks['items'][0]['text']} [2]")

PROMPT = """You are an equity research analyst. Write an investment thesis in English (default 3-4 sentences; the user's preferences below, if any, take priority, including over length) for {name} ({t}) using ONLY the data below.
End every claim with its source tag [n]. Never invent numbers. Sources: [1] financials/quote (Yahoo Finance), [2] {filing}.
{instructions}Data: {data}
Return only the thesis text."""

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
        raise RuntimeError(r.stderr[:200] or "claude -p returned nothing")
    raise RuntimeError("no LLM available")

def write_thesis(t, quote, fin, risks, instructions=""):
    """Vraća (tekst, način): 'llm' | 'template'. Uz bilo koju grešku pada na šablon."""
    data = json.dumps({"quote": quote, "financials": {k: v for k, v in fin.items() if k not in ("annual", "meta", "summary")},
                       "risks": [r.get("title") or r["text"] for r in risks["items"]]}, ensure_ascii=False)
    ins = f"User preferences learned from their ratings (follow them): {instructions}\n" if instructions else ""
    try:
        return llm(PROMPT.format(name=quote["name"], t=t, filing=risks["filing"], data=data, instructions=ins)), "llm"
    except Exception as e:
        print("LLM unavailable:", e)
        return template_thesis(quote, fin, risks), "template"

CACHE = ROOT / "agent_service" / "demo_cache"   # unaprijed generisani briefovi za demo (commitovani)

def pick_risks(risks: dict, n: int = 5) -> list:
    """5 ključnih rizika, raznoliko po kategorijama (ako ih A vraća), inače prvih n iz items."""
    rich = risks.get("risks")
    if not rich:
        return [{**r, "text": r["text"][:350].rstrip() + ("…" if len(r["text"]) > 350 else "")} for r in risks["items"][:n]]
    src = f"{risks['filing']}, Item 1A"
    picked, seen = [], set()
    for r in rich:                       # prvo po jedan iz svake kategorije
        if r.get("category") not in seen:
            seen.add(r.get("category")); picked.append(r)
    picked += [r for r in rich if r not in picked]
    return [{"text": r.get("title") or r["text"][:200], "detail": r["text"][:500], "category": r.get("category", ""), "source": src}
            for r in picked[:n]]

def extras(quote: dict, fin: dict) -> dict:
    """Dodatna polja za UI (sva opciona; mockovi ih nemaju)."""
    ann = sorted(fin.get("annual") or [], key=lambda a: a["fiscal_year"])[-4:]
    keep = ("year_high", "year_low")
    return {**{k: quote[k] for k in keep if quote.get(k) is not None},
            **{k: fin[k] for k in ("gross_margin", "operating_margin", "debt_to_equity", "free_cash_flow", "forward_pe",
                                    "dividend_yield", "sector", "industry") if fin.get(k) is not None},
            "annual": [{"year": a["fiscal_year"], "revenue": a.get("revenue"), "net_income": a.get("net_income"),
                        "free_cash_flow": a.get("free_cash_flow")} for a in ann]}

def get_profile(project_id: str) -> dict:
    if not LEARNING_URL:
        return {}
    try:
        r = httpx.get(f"{LEARNING_URL}/profile", params={"project_id": slug(project_id)}, timeout=3)
        return r.json() if r.status_code == 200 else {}
    except Exception:
        return {}

def build_brief(t: str, project_id: str = "default") -> dict:
    try:
        quote = fetch("quote", t, f"/quote/{t}")
        fin = fetch("financials", t, f"/financials/{t}")
        risks = fetch("risk-factors", t, f"/filings/{t}/risk-factors")
    except HTTPException:
        cached = CACHE / f"{t}.json"   # podaci nedostupni (npr. offline, ticker van A-ovog keša): ranije spremljen brief
        if cached.exists():
            b = json.loads(cached.read_text(encoding="utf-8")); b["mode"] = "cache"; return b
        raise
    top = pick_risks(risks)
    prof = get_profile(project_id)
    thesis, mode = write_thesis(t, quote, fin, {**risks, "items": top}, prof.get("instructions", ""))
    cached = CACHE / f"{t}.json"
    if mode == "template" and cached.exists():      # nema LLM-a, a imamo puni brief iz keša
        b = json.loads(cached.read_text(encoding="utf-8")); b["mode"] = "cache"; return b
    b = {"ticker": t, "name": quote.get("name", t), "thesis": thesis, "mode": mode,
         "metrics": {"price": quote["price"], "pe": fin["pe"],
                     "revenue_growth_yoy": fin["revenue_growth_yoy"], "net_margin": fin["net_margin"]},
         "risks": top, "peers": list(PEERS.get(t, [])), "extras": extras(quote, fin),
         "sources": [{"label": "Yahoo Finance", "url": f"https://finance.yahoo.com/quote/{t}"},
                     {"label": risks["filing"], "url": risks["url"]}],
         "generated_at": dt.datetime.now(dt.timezone.utc).isoformat()}
    if prof.get("instructions"):
        b["learned"] = {"instructions": prof["instructions"], "label": prof.get("label", ""), "feedback_count": prof.get("feedback_count", 0)}
    return b

PEERS = {"AAPL": ["MSFT", "GOOGL"], "MSFT": ["AAPL", "GOOGL"], "GOOGL": ["MSFT", "AAPL"],
         "TSLA": ["NVDA"], "NVDA": ["MSFT", "TSLA"]}   # zamjena: A-ov /peers kad bude spreman

def slug(x: str) -> str:
    return "".join(c for c in x.lower().replace(" ", "-") if c.isalnum() or c in "-_")[:40] or "default"

def project_dir(pid: str) -> Path:
    d = STORE / slug(pid); d.mkdir(parents=True, exist_ok=True); return d

@app.post("/brief")
def brief(req: BriefReq):
    t = req.ticker.upper().strip()
    b = build_brief(t, req.project_id)
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
        return {"answer": "This project has no briefs yet. Analyze a ticker first, then ask."}
    ctx = json.dumps(bs, ensure_ascii=False)
    try:
        return {"answer": llm(f"Answer briefly in English using ONLY these briefs (do not invent anything; if the answer is not in them, say so), keeping source tags where available.\nBriefs: {ctx}\nQuestion: {req.message}")}
    except Exception:
        return {"answer": "Chat needs AI (set ANTHROPIC_API_KEY or log in to the claude CLI). Your saved briefs are still available."}

@app.get("/quote/{ticker}")
def quote_ep(ticker: str):
    t = ticker.upper()
    return fetch("quote", t, f"/quote/{t}")

@app.get("/features")
def features():
    return {"paper": bool(DATA_URL), "learning": bool(LEARNING_URL), "live_data": bool(DATA_URL)}

def proxy(base, method: str, path: str, params=None, body=None):
    """Prosljeđuje poziv A-ovim servisima (paper u data_service, učenje u learning_service). Bez URL-a: 503."""
    if not base:
        raise HTTPException(503, "This feature is off (its service is not running)")
    return call(method, f"{base}{path}", params=params, json=body, timeout=15)

@app.get("/paper/portfolio")
def paper_portfolio(project_id: str = "default"):
    return proxy(DATA_URL, "GET", "/paper/portfolio", {"project_id": slug(project_id)})

@app.post("/paper/orders")
def paper_order(body: dict):
    return proxy(DATA_URL, "POST", "/paper/orders", body=body)

@app.delete("/paper/orders/{order_id}")
def paper_cancel(order_id: str, project_id: str = "default"):
    return proxy(DATA_URL, "DELETE", f"/paper/orders/{order_id}", {"project_id": slug(project_id)})

@app.post("/paper/reset")
def paper_reset(project_id: str = "default"):
    return proxy(DATA_URL, "POST", "/paper/reset", {"project_id": slug(project_id)})

@app.get("/paper/leaderboard")
def paper_leaderboard(period: str = "day"):
    """Rang workspaceova (contracts/leaderboard.md); period: day|week|month."""
    return proxy(DATA_URL, "GET", "/paper/leaderboard", {"period": period})

@app.post("/feedback")
def feedback_post(body: dict):
    return proxy(LEARNING_URL, "POST", "/feedback", body=body)

@app.get("/feedback")
def feedback_list(project_id: str = "default"):
    return proxy(LEARNING_URL, "GET", "/feedback", {"project_id": slug(project_id)})

@app.get("/profile")
def profile_get(project_id: str = "default"):
    return proxy(LEARNING_URL, "GET", "/profile", {"project_id": slug(project_id)})

@app.delete("/profile")
def profile_del(project_id: str = "default"):
    return proxy(LEARNING_URL, "DELETE", "/profile", {"project_id": slug(project_id)})

@app.get("/search")
def search_ep(q: str = "", limit: int = 8):
    """Pretraga po tickeru ili imenu kompanije (contracts/catalog.md)."""
    return catalog.search(q, max(1, min(limit, 20)))

@app.get("/markets")
def markets_ep():
    """Browse stocks: most actives/gainers/losers i dionice po sektorima (contracts/catalog.md)."""
    return catalog.markets()

@app.get("/history/{ticker}")
def history(ticker: str, period: str = "1y"):
    return fetch("history", ticker.upper(), f"/history/{ticker.upper()}?period={period}")

app.mount("/", StaticFiles(directory=ROOT / "frontend", html=True), name="ui")
