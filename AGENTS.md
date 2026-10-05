# Finance Desk: upute za AI agente (čitaj prvo)
Hackathon 2026, izazov "Private pro desk", rok petak 9.10.2026. Tim od dvoje, podjela u dvije varijante:
- **Varijanta A (data service)**: `data_service/` (Python/FastAPI, bez LLM-a i UI-ja): /quote, /history, /financials, /filings/{t}/risk-factors; yfinance + SEC EDGAR, keš na disku.
- **Varijanta B (agent + frontend)**: `agent_service/` i `frontend/`.
Vlasništvo: svaka varijanta mijenja SAMO svoje foldere. `contracts/` mijenja se samo dogovorom obje strane.

## Pravila
0. Git: radi se po `docs/GITFLOW.md` (feat/a-* ili feat/b-* grane, PR u main, squash merge, vlastiti folderi). Push/PR na GitHub samo uz odobrenje vlasnika.
1. Moduli komuniciraju samo preko `contracts/` (šeme + mockovi). Ne importaj kod iz tuđeg modula.
2. Prije mijenjanja fajlova uzmi work-claim: `mapi -X PUT /api/projects/e310249e-b859-5a09-8051-4b3734654d93/work-claim` (chat_id, path, summary); na kraju DELETE.
3. Nakon svakog koraka dopiši zapis u `docs/LOG-<varijanta>.md` (šta, zašto, kako pokrenuti, šta je sljedeće). Ovo je obavezno.
4. Ništa opcionalno dok jezgro ne radi na 3 tickera. Demo mora raditi offline (keširani tickeri). Petak = bez novog koda.
5. Pitanja drugoj strani: `list_agent_peers` pa `send_agent_message`, ili zapiši u `docs/QUESTIONS.md`.

## Pokretanje (B)
`cd agent_service && pip install -r requirements.txt && uvicorn main:app --port 8002`, pa otvori http://localhost:8002/ . Bez `DATA_URL` koristi mockove iz `contracts/mocks`; sa `DATA_URL=http://localhost:8001` koristi pravi data_service.

## Stanje
Vidi zadnji unos u `docs/LOG-B.md` i `docs/LOG-A.md`.
