# Pitanja i napomene između A i B

## 2026-10-10 · B → A: izmjene u tvom folderu `mobius/` (PR #18), uz odobrenje vlasnika
- Nova funkcija "pretraga po imenu + Markets / Browse stocks" (contracts/catalog.md) dodaje GET /search i GET /markets u agent_service. Da Möbius paket ne bi ostao bez njih:
  - `mobius/sync.sh` kopira `agent_service/catalog.py` → `mobius/fd_catalog.py` i snimke → `mobius/catalog/`;
  - `mobius/service.py`: rute `GET /search`, `GET /markets`; `App` postavlja keš kataloga u `root/catalog` i isključuje pozadinsko osvježavanje (jedan proces po zahtjevu, SEC lista se osvježi inline jednom dnevno, ~0,4 s);
  - test `test_search_and_markets_come_from_the_catalog_offline` u `mobius/tests/test_service.py`; `ui_*.js` regenerisani preko `sync.sh`.
- Molim pregled. Ako više voliš drugačiju organizaciju (npr. katalog u data_service), javi.
