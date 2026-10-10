# Ugovor: paper trading (data_service, osoba A; panel u UI-ju osoba B)
Lokalna simulacija, bez Alpace. Početni kapital 100.000 USD. Tržišni nalozi po zadnjoj cijeni (`/quote`). UI ide preko agenta (`/paper/*` prosljeđuje na `DATA_URL`).

- `POST /paper/orders` tijelo: `{"project_id","ticker","side":"buy"|"sell","qty":10}` → portfelj (kao dolje) + `"fill":{"ticker","side","qty","price","at"}`. Greške: `{"error","detail"}`: 422 (qty<=0 ili neispravan ticker), 409 `insufficient_cash` / `insufficient_position`.
- `GET /paper/portfolio?project_id=` → mocks/portfolio.demo.json
- `POST /paper/reset?project_id=` → prazan portfelj s 100000 USD
Pohrana je jedan modul (danas fajl po projektu), da se kasnije može zamijeniti.

## Limit i stop nalozi (prijedlog B, 2026-10-10; čeka pregled A)
Dodatak, kompatibilan unazad: nalog bez `type` je i dalje tržišni.

**POST /paper/orders** dodatna polja:
- `type`: `"market"` (zadano) | `"limit"` | `"stop"`
- `limit_price` (obavezno za `limit`, > 0), `stop_price` (obavezno za `stop`, > 0). `stop` je samo `side:"sell"` (stop-loss), inače 422 `invalid_order`.

Pravila izvršenja (provjera pri svakom osvježavanju cijene, vidi niže):
| Tip | Uslov | Cijena izvršenja |
|---|---|---|
| limit buy | cijena ≤ `limit_price` | `limit_price` |
| limit sell | cijena ≥ `limit_price` | `limit_price` |
| stop sell (stop-loss) | cijena ≤ `stop_price` | `stop_price` |
Ako je uslov ispunjen već pri slanju, nalog se odmah izvršava po trenutnoj cijeni (kao na berzi, nikad lošije od zadane).

Rezervacija dok je nalog otvoren:
- limit buy rezerviše `qty × limit_price` gotovine; `insufficient_cash` ako slobodne gotovine nema.
- limit/stop sell rezerviše `qty` dionica; `insufficient_position` ako slobodnih dionica nema.
- Rezervacija se ne skida iz pohranjene gotovine (leaderboard i dalje računa iz izvršenih `orders`); portfelj je samo prikazuje.

Odgovor na POST:
- izvršen odmah: kao danas (`fill` + portfelj), `order.type` dodan;
- na čekanju: portfelj + `"fill": null` + `"pending": OpenOrder`.

`OpenOrder = {"id","ticker","side","type","qty","limit_price"|null,"stop_price"|null,"reserved":<USD ili broj dionica>,"created_at"}`

**Portfelj** (GET /paper/portfolio i svi odgovori) dodaje:
- `cash` = slobodna gotovina (ukupna − rezervisana); `reserved_cash`; `equity` uključuje rezervisanu gotovinu.
- `positions[].reserved_qty` (dionice zaključane u sell nalozima).
- `open_orders: [OpenOrder]`
- `recent_orders: [{"id","ticker","side","type","qty","price","value","created_at"}]` (zadnjih 10 izvršenih, najnoviji prvi).

**DELETE /paper/orders/{id}?project_id=** otkazuje otvoreni nalog i oslobađa rezervaciju → portfelj. 404 `order_not_found`.

**Provjera naloga:** data_service u pozadini svakih 10 s (`PAPER_CHECK_SECONDS`) provjerava otvorene naloge svih projekata po zadnjoj cijeni (`/quote` keš), a i pri svakom GET /paper/portfolio. Nalozi se izvršavaju **samo dok servis radi**; nakon ponovnog pokretanja se provjeravaju po tadašnjoj cijeni (nema izvršenja "unazad"). Reset briše i otvorene naloge.
