# data_service (Osoba A)

Backend 1 Finance Deska: **samo podaci**, bez LLM-a i bez UI-ja. FastAPI servis
koji agent_service poziva kao alate, a frontend direktno za grafikon.

## Pokretanje

```bash
cd data_service
python3 -m venv .venv        # ~250 MB (pandas): na malom disku napravi ga negdje drugdje i symlinkaj
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env          # pa upiši svoj SEC_USER_AGENT
.venv/bin/uvicorn app.main:app --port 8001 --reload --env-file .env
```

Dokumentacija i isprobavanje: <http://localhost:8001/docs>

Testovi (bez interneta): `.venv/bin/python -m pytest -q`

## Endpointi

| Ruta | Izvor | Šta vraća |
|---|---|---|
| `GET /quote/{ticker}` | yfinance | ugovor: `ticker, name, price, currency, change_pct, market_cap, as_of`; dodatno: 52w raspon, volumen… |
| `GET /history/{ticker}?period=1y` | yfinance | ugovor: `ticker, period, points[{time:"YYYY-MM-DD", close}]`; dodatno: open/high/low/volume u tačkama. `period`: 1mo 3mo 6mo 1y 2y 5y max (5y sedmično, max mjesečno) |
| `GET /financials/{ticker}` | yfinance | ugovor: `ticker, pe, revenue, revenue_growth_yoy, net_income, net_margin, fiscal_year` (zadnja fiskalna godina); dodatno: marže, EPS, FCF, opis firme, `annual[]` po godinama |
| `GET /filings/{ticker}/risk-factors` | SEC EDGAR | ugovor: `ticker, filing ("10-K 2025"), url, items[{text, source}]` (svi rizici iz Item 1A); dodatno: `risks[{category, title, text}]` s punim tekstom |
| `GET /health` | – | offline mod, uključeni opcionalni izvori, keširani tickeri |

**Ugovor** je `../contracts/` (README + `mocks/*.AAPL.json`). Svako polje iz mockova postoji
na istom mjestu, s istim imenom i tipom; sve ostalo je dodatak koji agent smije ignorisati.
`tests/test_contract.py` to provjerava za sve demo tickere.

### Konvencije
- Rast i marže su **udjeli**: `0.064` = 6,4 %. Izuzetak po ugovoru: `quote.change_pct` je u procentima (`0.8` = 0,8 %).
- Novac je u `currency`, neskaliran (bez hiljada/miliona).
- Nedostupna vrijednost je `null`, nikad `0`.
- Svaki odgovor ima i `meta`: `provider`, `fetched_at`, `cached`, `stale`, `sources[{label,url}]`.
- Greške su uvijek `{"error": kod, "detail": tekst}`:
  `invalid_ticker`/`invalid_parameter` (422), `ticker_not_found`/`filing_not_found` (404),
  `upstream_unavailable` (502), `not_in_cache` (503, samo offline).

## Keš i demo bez interneta

Redoslijed za svaki zahtjev:
1. svjež runtime keš (`cache/`, nije u gitu), TTL: quote 15 min, history 6 h, financials 24 h, rizici 7 dana
2. živi poziv (preskače se u offline modu)
3. stari runtime keš (`meta.stale = true`) ako izvor padne
4. **demo snapshot** `demo_cache/` (u gitu): AAPL, MSFT, NVDA
5. greška

Demo bez interneta: `DATA_OFFLINE=1 .venv/bin/uvicorn app.main:app --port 8001 --env-file .env`

Osvježavanje snapshota (pa commitaj `demo_cache/`):
```bash
.venv/bin/python -m scripts.warm_demo_cache            # AAPL MSFT NVDA
.venv/bin/python -m scripts.warm_demo_cache TSLA GOOGL # dodatni tickeri
```

Spajanje s agentom: `cd agent_service && DATA_URL=http://localhost:8001 uvicorn main:app --port 8002`.

## Struktura

```
app/
  main.py                 rute, mapiranje grešaka na HTTP
  service.py              DataService: politika keša, validacija tickera/perioda
  cache.py                JSON keš na disku (runtime + demo snapshot)
  models.py               oblici odgovora (ugovor + dodaci)
  config.py               env postavke
  providers/
    base.py               interfejsi MarketDataProvider / FilingsProvider + greške
    yfinance_provider.py
    edgar_provider.py     10-K → Item 1A → pojedinačni rizici
scripts/                  warm_demo_cache
tests/                    bez mreže: lažni provideri, sintetički 10-K, usklađenost s contracts/mocks
```

Novi izvor = nova klasa iza interfejsa u `providers/base.py`; opcionalni izvori
(`/peers`, `/news`, `/macro`) se uključuju preko `DATA_OPTIONAL=peers,news`.

## EDGAR napomene
- SEC traži `User-Agent` u obliku `"Ime Firme kontakt@email"`; bez njega vraća 403. Postavi `SEC_USER_AGENT`.
- Limit je 10 zahtjeva/s; servis drži 5/s.
- Parser je provjeren na 10-K filinzima AAPL, MSFT, NVDA, JPM, KO, AMZN, TSLA, GOOGL i META
  (21–44 rizika po firmi, s kategorijama). Pokriva naslove u boldu/italicu, kategorije
  VELIKIM SLOVIMA, "run-in" naslove (bold rečenica na početku paragrafa) i podnaslove unutar rizika.
- Strani emitenti (npr. TSM) podnose 20-F, ne 10-K, pa dobijaju `filing_not_found`.
- Tekst svakog rizika je skraćen na ~1500 znakova (cijela rečenica), da prompt ostane kratak.
