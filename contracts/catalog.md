# Katalog dionica: pretraga po imenu i "Browse stocks" (osoba B, agent_service)
Servira agent_service (UI ih zove direktno). Samo dodatak, ne mijenja postojeće endpointe.
Izvori: SEC `company_tickers.json` (ticker, ime, CIK) i yfinance (`Search`, `screen`, `Sector`, `download`).

## GET /search?q=nvidia&limit=8
Prvo traži u keširanoj SEC listi (ticker tačno > ticker počinje s q > riječ imena počinje s q > ime sadrži q).
Ako nema pogotka i nije offline, pita yfinance Search (samo EQUITY).
```json
{"query": "nvidia", "source": "sec",            // "sec" | "yahoo" | "none"
 "results": [{"ticker": "NVDA", "name": "NVIDIA CORP", "sector": "Technology", "cik": 1045810}]}
```
`sector` je `null` kad nije poznat (SEC lista nema sektor; popunjava se iz yfinance sektora i Search-a). `cik` je `null` za Yahoo pogotke.

## GET /markets
Liste iz yfinance screenera i dionice po sektorima (`yf.Sector(key).top_companies`), samo tickeri iz SEC liste (= podržani, imaju SEC filinge).
Keš u memoriji i na disku 5 min (`MARKETS_TTL`, sekunde); sastav sektora keš 1 dan. Offline ili bez mreže: zadnji keš sa `"live": false`.
```json
{"as_of": "2026-10-10T12:00:00+00:00", "live": true,
 "lists": {"most_actives": [Row], "day_gainers": [Row], "day_losers": [Row]},
 "sectors": [{"key": "technology", "name": "Technology", "stocks": [Row]}]}
```
`Row = {"ticker": "NVDA", "name": "NVIDIA Corporation", "price": 190.1, "change_pct": 1.23}` (`change_pct` u procentima; `price`/`change_pct` mogu biti `null`).

## Keš i offline
- SEC lista: `agent_service/cache/sec_tickers.json` (gitignored), osvježava se najviše jednom dnevno u pozadini; User-Agent iz `SEC_USER_AGENT`.
- Snimak za prvi offline start: `agent_service/catalog/sec_tickers.snapshot.json` i `agent_service/catalog/markets.snapshot.json` (commitovani).
- `DATA_OFFLINE=1`: nikakvi mrežni pozivi, samo keš/snimak.
