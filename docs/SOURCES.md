# Izvori podataka i licence (za prijavu)

Kod Finance Deska je pod MIT licencom (`LICENSE`). Korištene komponente i izvori:

| Šta | Za šta | Licenca / uslovi |
|---|---|---|
| [TradingView Lightweight Charts](https://github.com/tradingview/lightweight-charts) v4.2.0 (`frontend/vendor/`) | grafikon cijene | Apache 2.0; zaglavlje licence ostaje u fajlu, uz atribuciju TradingViewu |
| [Inter](https://rsms.me/inter/) (`frontend/vendor/InterVariable.woff2`) | font korisničkog interfejsa (radi i offline) | SIL Open Font License 1.1 (`frontend/vendor/Inter-LICENSE.txt`) |
| [yfinance](https://github.com/ranaroussi/yfinance) | cijene, historija, fundamentals (Yahoo Finance) | Apache 2.0 (biblioteka); podaci Yahoo Finance su za ličnu/nekomercijalnu upotrebu |
| [SEC EDGAR](https://www.sec.gov/edgar) | 10-K izvještaji, Item 1A Risk Factors | javni podaci; poštujemo SEC fair-access pravila (User-Agent s kontaktom, ≤10 zahtjeva/s; servis drži 5/s) |
| [FastAPI](https://fastapi.tiangolo.com/), Uvicorn, httpx, Pydantic | backend servisi | MIT / BSD |
| Requests, Beautiful Soup, lxml | dohvat i parsiranje 10-K | Apache 2.0 / MIT / BSD |
| Claude (Anthropic), preko API ključa ili `claude` CLI | teza briefa, chat, AI sažetak profila učenja | komercijalni API; bez ključa aplikacija radi na pravilima i kešu |

Napomene za žiri:
- Finance Desk nije broker ni savjet za ulaganje; paper trading je simulacija s virtuelnim novcem.
- Svaka tvrdnja u tezi nosi oznaku izvora [n] s linkom (Yahoo Finance stranica, 10-K na sec.gov).
- Demo radi i bez interneta za AAPL, MSFT i NVDA (spremljeni podaci i briefovi).
