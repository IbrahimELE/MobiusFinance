# Log varijante B (agent + frontend)
Format: datum · korak · šta · zašto · kako provjeriti · sljedeće.

## 2026-10-05 · Korak 1: kostur nad mockovima
- Napravljeno: `contracts/` (brief.schema.json, mockovi za AAPL: quote, history, financials, risk-factors, brief, README s endpointima), `agent_service/main.py` (POST /brief, GET /briefs, GET /history/{t}, servira frontend), `frontend/index.html` (unos tickera, Lightweight Charts, KPI kartice, teza, rizici, izvori, sačuvani briefovi).
- Odluke: `fetch()` u main.py je jedina tačka za podatke (mock ili `DATA_URL`); `write_thesis()` je šablon i jedino mjesto za LLM; briefovi se čuvaju u `agent_service/store/<project_id>/<T>.json` (gitignore).
- Provjera: curl na /brief, /briefs, /history, / radi; vizualno nije provjereno u pregledniku.
- Poznato: grafikon ide preko CDN-a (za offline demo ugraditi lokalno); mock postoji samo za AAPL; nije commitano.
- Sljedeće (uto 6.10): LLM prompt za tezu s tvrdnjama vezanim za izvore, mockovi za još 2 tickera, usklađivanje imena polja s osobom A.

## 2026-10-05 · Korak 2: Git workflow
- Dodano: `docs/GITFLOW.md`, `.github/CODEOWNERS` (placeholderi @OSOBA_A/@OSOBA_B), PR šablon, `.env.example`, `data_service/README.md`, pravilo 0 u AGENTS.md.
- Odluka: main + kratke feat grane, bez develop; vlasništvo po folderima da nema konflikata.
- Nije urađeno: GitHub repo nije kreiran niti išta pushano (javna akcija, čeka odobrenje).
- Sljedeće: napraviti repo, dodati A kao collaboratora, zamijeniti placeholdere u CODEOWNERS.

## 2026-10-05 · Korak 3: README
- Dodan README.md (struktura foldera i vlasništvo, gitflow u 6 koraka, pokretanje). Remote je već povezan: IbrahimELE/MobiusFinance. Push čeka potvrdu.
