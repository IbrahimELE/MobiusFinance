# Log varijante A (data service)
Osoba A: dopisuj ovdje isti format kao u LOG-B.md (datum · korak · šta · zašto · provjera · sljedeće).

## 2026-10-05 · Korak 1: data_service jezgro (quote, history, financials, risk-factors)
- Napravljeno: `data_service/` (FastAPI): `GET /quote/{t}`, `/history/{t}?period=1y`, `/financials/{t}` (yfinance), `/filings/{t}/risk-factors` (SEC EDGAR, najnoviji 10-K, Item 1A), `/health`. Provider interfejs (`app/providers/base.py`), keš na disku s TTL-om, offline mod (`DATA_OFFLINE=1`) i commitovani demo snapshot za AAPL, MSFT, NVDA (`data_service/demo_cache/`).
- Ugovor: odgovori sadrže sva polja iz `contracts/mocks/*.AAPL.json` istog imena i tipa (rast/marže kao udjeli, `change_pct` u procentima kao u mocku); ostalo su dodaci (`meta`, `risks[]` s kategorijom i tekstom, `annual[]`…). `contracts/` nije mijenjan.
- EDGAR parser provjeren na AAPL, MSFT, NVDA, JPM, KO, AMZN, TSLA, GOOGL, META (21–44 rizika). Strani emitenti (20-F, npr. TSM) vraćaju 404 `filing_not_found`.
- Provjera: `cd data_service && pytest -q` (25 testova, bez mreže, uklj. usklađenost s mockovima); ručno: agent sa `DATA_URL=http://localhost:8001` vraća brief za AAPL/MSFT/NVDA s pravim brojevima i rizicima.
- Za B: kad nema LLM-a, `/brief` vraća `agent_service/demo_cache/<T>.json` (stari mock brojevi, npr. AAPL 227.5) umjesto pravih podataka iz data_service; `/compare` i `/history` već koriste prave. Možda regenerisati demo briefove nad pravim data_service-om.
- Pokretanje: vidi `data_service/README.md` (port 8001, `SEC_USER_AGENT` u `.env`).
- Sljedeće: zajednički test cijelog toka na 3 tickera s B; zatim opcionalno `/peers` (zamjena za PEERS u agentu).
