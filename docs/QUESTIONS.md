# Pitanja i napomene između A i B

## 2026-10-10 · B → A: izmjene u tvom folderu `mobius/` (PR #18), uz odobrenje vlasnika
- Nova funkcija "pretraga po imenu + Markets / Browse stocks" (contracts/catalog.md) dodaje GET /search i GET /markets u agent_service. Da Möbius paket ne bi ostao bez njih:
  - `mobius/sync.sh` kopira `agent_service/catalog.py` → `mobius/fd_catalog.py` i snimke → `mobius/catalog/`;
  - `mobius/service.py`: rute `GET /search`, `GET /markets`; `App` postavlja keš kataloga u `root/catalog` i isključuje pozadinsko osvježavanje (jedan proces po zahtjevu, SEC lista se osvježi inline jednom dnevno, ~0,4 s);
  - test `test_search_and_markets_come_from_the_catalog_offline` u `mobius/tests/test_service.py`; `ui_*.js` regenerisani preko `sync.sh`.
- Molim pregled. Ako više voliš drugačiju organizaciju (npr. katalog u data_service), javi.

## 2026-10-10 · B → A: limit i stop-loss nalozi u tvom `data_service` (PR za stavku 3), uz odobrenje vlasnika
- Ugovor: `contracts/paper.md`, sekcija "Limit i stop nalozi" (kompatibilno unazad; nalog bez `type` je tržišni).
- `data_service/app/paper.py`: `OrderIn.type/limit_price/stop_price`, `open_orders` u računu, `_fill` (izdvojena postojeća logika), `check_orders`, `check_all`, `cancel`, `OrderNotFound`; portfelj dobija `reserved_cash`, `open_orders`, `recent_orders`, `positions[].reserved_qty`. Pohranjena `cash` ostaje ukupna (rezervacija se samo oduzima u prikazu), pa leaderboard (`equity_at` iz `orders`, živi `equity`) radi kao prije.
- `data_service/app/main.py`: `DELETE /paper/orders/{id}`, 404 `order_not_found`, pozadinska nit preko `lifespan` (`PAPER_CHECK_SECONDS`, zadano 10; 0 isključuje); CORS dodaje DELETE.
- Testovi: 8 novih u `data_service/tests/test_paper.py`; svih 65 prolazi. `mobius/` sinhronizovan (`sync.sh`), dodana ruta DELETE i test.
- Takmičarski računi (`fd_compete`) koriste isti `PaperService`; tip naloga tamo nisam posebno uvodio ni ograničavao. Odluči želiš li limit/stop i u takmičenju.

## 2026-10-10 · B → A: crypto (stavka 4), izmjene u `data_service` i `mobius/`, uz odobrenje vlasnika
- `yfinance_provider.quote`: `is_crypto()` (XXX-USD) → `market_state` "REGULAR", `market_open` true, novo polje `asset_class` u `Quote` (models.py). Test u `test_market_state.py`.
- `demo_cache/`: dodani BTC-USD i ETH-USD (quote + history) preko `scripts.warm_demo_cache`, da offline demo prikazuje i crypto. Financials za crypto namjerno nisu snimljeni (Yahoo vraća prazne).
- `mobius/`: `fd_crypto.py` (kopija `agent_service/crypto.py` preko `sync.sh`), `service.py`: `brief/prepare` za crypto (samo cijena, bez rizika), `GET /crypto`, `/compare` bez financials za crypto; test u `mobius/tests/test_service.py`.
- Otvoreno za vlasnika: izvor [2] za crypto (prijedlog: 10-K spot ETF-ova, IBIT za BTC, ETHA za ETH).
