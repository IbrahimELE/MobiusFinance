# Ugovor: paper trading (data_service, osoba A; panel u UI-ju osoba B)
Lokalna simulacija, bez Alpace. Početni kapital 100.000 USD. Tržišni nalozi po zadnjoj cijeni (`/quote`). UI ide preko agenta (`/paper/*` prosljeđuje na `DATA_URL`).

- `POST /paper/orders` tijelo: `{"project_id","ticker","side":"buy"|"sell","qty":10}` → portfelj (kao dolje) + `"fill":{"ticker","side","qty","price","at"}`. Greške: `{"error","detail"}`: 422 (qty<=0 ili neispravan ticker), 409 `insufficient_cash` / `insufficient_position`.
- `GET /paper/portfolio?project_id=` → mocks/portfolio.demo.json
- `POST /paper/reset?project_id=` → prazan portfelj s 100000 USD
Pohrana je jedan modul (danas fajl po projektu), da se kasnije može zamijeniti.
