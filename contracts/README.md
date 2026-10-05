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
