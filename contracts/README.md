# Ugovori (zajednički za A i B)
Moduli komuniciraju samo preko ovih fajlova. Mijenja se samo dogovorom obje osobe.

Data service (osoba A) servira:
- GET /quote/{ticker}                  -> mocks/quote.AAPL.json
- GET /history/{ticker}?period=1y      -> mocks/history.AAPL.json
- GET /financials/{ticker}             -> mocks/financials.AAPL.json
- GET /filings/{ticker}/risk-factors   -> mocks/risk-factors.AAPL.json
Agent service (osoba B) servira:
- POST /brief {ticker, project_id}     -> brief.schema.json (mocks/brief.AAPL.json)
- GET  /briefs?project_id=             -> lista sačuvanih briefova
Opcionalna polja (peers...) su prazna dok funkcija nije uključena.

Dodatna polja koja agent vraća uz Brief (opciona, ne lome ugovor): `mode` ("llm"|"cache"|"template"), `peers` = lista ticker stringova.
Agent endpointi: GET /projects, POST /projects {name}, DELETE /briefs/{ticker}?project_id=, GET /compare?tickers=A,B, POST /chat {message, project_id}.

## Faza 2: PRIJEDLOG (osoba A), potvrđuje osoba B u PR-u
`project_id` je isti "slug" kao u agentu (mala slova, razmak → `-`, samo slova/brojevi/`-_`, max 40; prazno → `default`).

Learning service (osoba A, port 8003, `LEARNING_URL`):
- POST /feedback {project_id, ticker, brief_generated_at, rating: "up"|"down", note?, tags?[]} -> jedan zapis kao u mocks/feedback.demo.json
- GET  /feedback?project_id=           -> mocks/feedback.demo.json (najnovije zadnje)
- GET  /profile?project_id=            -> mocks/profile.demo.json
- DELETE /profile?project_id=          -> briše ocjene i profil projekta ("zaboravi", za ponavljanje demoa)
Agentu treba samo `instructions` (ubaci u prompt; prazno = bez promjene). UI prikazuje `label` kao "Naučeno: …".
`mode`: "rules" (iz pravila, radi offline) ili "llm" (AI sažetak kad je dostupan). Dozvoljeni `tags`: debt, free_cash_flow, valuation, growth, margins, competition, risks, dividends, macro, product_details, short, long, simple.

Paper trading (osoba A, u data service-u, port 8001), simulacija, nije savjet:
- POST /paper/orders {project_id, ticker, side: "buy"|"sell", qty} -> mocks/paper-order.demo.json (tržišni nalog po zadnjoj cijeni iz /quote)
- GET  /paper/portfolio?project_id=    -> mocks/paper-portfolio.demo.json (`pnl_pct` u procentima)
- POST /paper/reset?project_id=        -> portfelj s početnih 100.000 USD
Greške kao i ostale: {"error","detail"}; `insufficient_cash` / `insufficient_shares` (422).
