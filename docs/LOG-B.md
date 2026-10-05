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

## 2026-10-05 · Korak 4: gitflow s dev granom i hookovima
- Dodano: .githooks (pre-commit, commit-msg, pre-merge-commit, pre-rebase), setup.sh, nova GITFLOW.md i README sekcija; grana `dev`; push main+dev na IbrahimELE/MobiusFinance.
- Napomena: PR šablon i CODEOWNERS ciljaju main; prebaciti default branch na dev u GitHub postavkama.

## 2026-10-05 · Korak 5: LLM teza (feature/brief-llm)
- `write_thesis()` poziva Anthropic Messages API (httpx, bez novih ovisnosti) kad je postavljen `ANTHROPIC_API_KEY` (opcionalno `LLM_MODEL`, default claude-sonnet-4-5); inače/uz grešku šablon, pa demo radi offline.
- Prompt traži oznake izvora [n]; `sources[0]`=Yahoo, `sources[1]`=10-K, redoslijed je dio dogovora s promptom.
- Testirano samo šablonom (nema ključa). Ključ treba unijeti preko sealed card-a u `.env` (ne u repo).
- Sljedeće: mockovi za još 2 tickera, grafikon bez CDN-a, UI da prikaže [n] kao linkove.

## 2026-10-05 · Korak 6: LLM bez API ključa
- `llm()`: ANTHROPIC_API_KEY ako postoji, inače `claude -p` (u Möbiusu je Claude već prijavljen, radi bez ključa; testirano), inače šablon.
- Ograničenje: na drugom računaru bez prijavljenog `claude` CLI-ja pada na šablon. Za demo snimiti keširane briefove.

## 2026-10-05 · Korak 7: offline UI, više tickera, izvori
- Lightweight Charts lokalno u `frontend/vendor/` (nema CDN-a, demo radi offline).
- Mockovi za MSFT i TSLA (quote, financials, history, risk-factors); vrijednosti su ilustrativne, ne prave. Brief mock postoji samo za AAPL; briefovi se generišu.
- UI: oznake [n] u tezi su linkovi na `sources[n-1]`; HTML se escapuje.
- Napomena o objavi: Store paket mora biti Möbius mini-app (index.jsx), vidi /data/apps/finance-desk; ovaj repo je izvor za hackathon.
