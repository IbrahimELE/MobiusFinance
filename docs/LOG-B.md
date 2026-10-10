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

## 2026-10-05 · Korak 8: Windows bugfix
- Internal Server Error na Windowsu: read_text()/write_text() bez encodinga (cp1252) lomili su UTF-8 mockove s č/ž. Svi fajlovi sada eksplicitno utf-8; subprocess koristi tempfile.gettempdir() umjesto /tmp.

## 2026-10-05 · Korak 9: cijeli plan varijante B (feature/b-core-complete)
- Agent: build_brief() s keširanim demo briefovima (`agent_service/demo_cache/`, generisani pravim LLM-om; koriste se kad AI nije dostupan, mode="cache"); projekti (/projects), /compare, /chat (odgovara samo iz briefova), DELETE /briefs; PEERS tablica je privremena do A-ovog /peers.
- Mockovi za NVDA i GOOGL (ilustrativni brojevi).
- UI: odabir/kreiranje projekta, značka načina (AI/keš/šablon), konkurenti kao linkovi, usporedba označenih, brisanje, chat.
- `claude -p` se zove s `--strict-mcp-config` (bez toga CLI je dodavao strane napomene o konektorima).
- Dokumenti: DEMO.md, PRESENTATION.md, TESTING.md. UI nije vizualno provjeren u pregledniku; API jest (uklj. test bez AI-ja).
- Otvoreno: spajanje na pravi data_service, FinRobot (preskočeno prema planu), snimak demoa (pet).

## 2026-10-05 · Korak 10: spajanje na pravi data_service (feature/b-real-data)
- Provjereno sa `DATA_URL=http://localhost:8001`: AAPL/MSFT/NVDA/TSLA/GOOGL daju brief s pravim brojevima i rizicima iz 10-K (AAPL 333.69 USD, P/E 38.3); /compare i /history rade s pravim podacima.
- Brief nosi 5 ključnih rizika (tekst skraćen na 350 znakova) umjesto cijelog Item 1A (27–40 stavki), što je ubrzalo i LLM poziv.
- `agent_service/demo_cache/` regenerisan nad pravim podacima (AAPL, MSFT, NVDA, TSLA, GOOGL). Ranije su sadržavali stare mock brojeve (primijetio A u LOG-A).
- `run.sh` pokreće oba servisa; `DATA_OFFLINE=1` = A-ov offline keš (AAPL, MSFT, NVDA).
- Poznato: ako je data_service ugašen, a DATA_URL postavljen, /brief vraća grešku (namjerno, da se ne prikriju kvarovi).

## 2026-10-05 · Korak 11: Faza 2, UI redesign + priprema za učenje i paper (feature/b-ui-faza2)
- Agent: rizici po kategorijama (`pick_risks`, raznoliko, naslov + detalji), `extras` (52w raspon, marže, dug, FCF, godišnji brojevi), `/quote/{t}`, `/features`, proxy `/paper/*` → DATA_URL i `/feedback`, `/profile` → LEARNING_URL (bez URL-a 503, UI skriva funkciju), profil (`instructions`) ulazi u prompt a brief dobija `learned`.
- UI: novi "desk" izgled (header, sidebar, hero s cijenom i promjenom, izbor perioda, KPI kartice + 52w traka, kategorije rizika, mini grafikoni, "Naučeno", ocjena 👍/👎 + bilješka, paper panel s oznakom "simulacija", teza kroz vrijeme).
- Contracts: `contracts/learning.md`, `contracts/paper.md`, mockovi `profile.demo.json`, `portfolio.demo.json` (prijedlog, čeka A-ov pregled).
- Provjereno: API (brief MSFT s kategorijama i extras, 503/404 za neuključene servise), JS sintaksa. Vizualna provjera u toku (preglednik je instaliran, sesije su se prekidale zbog memorije).
- Vizualno provjereno (Playwright, desktop 1280 i mobilni 390): bez JS grešaka; ispravljen preljev na mobitelu (min-width:0, chart autoSize).

## 2026-10-05 · Korak 12: run.sh pokreće i learning_service
- run.sh: data_service 8001, learning_service 8003, agent+UI 8002 (LEARNING_URL postavljen). API tok provjeren (ocjena → profil → drugi brief s fokusom na dug i FCF → paper kupovina). Browser test usporen opterećenjem hosta; kad AI poziv ne uspije, brief pada na keš (bez 'Naučeno').

## 2026-10-05 · Korak 13: skoro-uživo cijene (feature/b-live-quotes)
- UI osvježava cijenu, promjenu, 'teza od…' traku, zadnju tačku grafikona i paper portfelj svakih 15 s (pauza kad je tab skriven), oznaka '● uživo HH:MM:SS' ili '○ bez veze'; količina u paper panelu se čuva pri osvježavanju.
- data_service/app/service.py (A-ov folder, jedna linija): TTL cijene 15 min → 15 s (env QUOTE_TTL, 900 vraća staro). Dogovoriti s A-om.
- Provjereno: dva /quote poziva u razmaku 16 s daju različite cijene; u browseru #px se promijenio (33.53 → 33.49). Ograničenje: yfinance je skoro uživo (ne tick po tick), a izvan radnog vremena berze (15:30–22:00 CET) cijena stoji. Offline demo ne može biti uživo.

## 2026-10-10 · Korak 14: brzi iznosi naloga (feature/b-quick-qty)
- Šta: u "Trade" panelu ispod +/- polja dugmad 10 / 20 / 50 / 100 / Max. Klik postavlja količinu; procjena troška i "cash after" se odmah ažuriraju; aktivno dugme je označeno (oznaka nestaje kad se upiše druga količina).
- Max = najveći broj cijelih dionica koje gotovina može kupiti (floor(cash / cijena)); onemogućen dok nema žive cijene; ako nema gotovine ni za jednu, poruka umjesto 0.
- Zašto: brži unos za početnike, bez kucanja.
- Testovi: `frontend/tests/` (pytest + Playwright, novi e2e okvir koji diže offline stack: data_service s DATA_OFFLINE=1 i privremenim paper računom + agent_service bez LLM-a). Pokretanje: `pip install playwright && python -m playwright install chromium`, pa `python -m pytest frontend/tests`. 3 testa prolaze (~4 s).
- Napomena: `conftest.py` skriva `claude` CLI iz PATH-a servisa, inače brief zove LLM (do 120 s) i test visi.
- Contracts: ne dira. Offline demo: provjeren (testovi rade upravo na DATA_OFFLINE=1).
- Sljedeće: stavka 2 (pretraga po imenu + Browse stocks).

## 2026-10-10 · Korak 15: pretraga po imenu + Markets / Browse stocks (feature/b-browse-stocks)
- Provjereno prije kodiranja (yfinance 1.7.0): `yf.Search`, `yf.screen` (predefinisani `most_actives`, `day_gainers`, `day_losers`), `yf.Sector` (11 sektora, `top_companies`) postoje. `EquityQuery` ne filtrira po tickeru, pa cijene po sektorima idu jednim `yf.download` pozivom (~5 s za ~90 tickera, keširano).
- Ugovor prvo: `contracts/catalog.md` (GET /search, GET /markets).
- Agent (`agent_service/catalog.py`): SEC `company_tickers.json` (~10 400 kompanija, User-Agent iz `SEC_USER_AGENT`) keš na disku `agent_service/cache/` (gitignored), osvježava se najviše jednom dnevno u pozadini; bez mreže ili s `DATA_OFFLINE=1` zadnji keš, a za prvi offline start commitovani snimci `agent_service/catalog/*.snapshot.json`.
  /search: prvo SEC lista (tačan ticker > početak tickera > riječ imena > sadrži), sektor i lijepo ime iz tržišnih podataka; bez pogotka yfinance Search (samo EQUITY). /markets: screeneri + sektori, samo tickeri iz SEC liste, keš 5 min (`MARKETS_TTL`), sastav sektora 1 dan; offline/greška → zadnji keš s `live:false`.
- UI: polje "Company or ticker" s listom prijedloga (ticker, ime, sektor; strelice, Enter, Esc). Enter bez odabira: tačan ticker > najbolji pogodak po imenu ("nvidia" → NVDA). Dugme "Markets" u zaglavlju i "Browse stocks →" na početnoj: Most active / Top gainers / Top losers + 11 sektora s cijenom i dnevnom promjenom, oznaka "● Live" ili "○ Saved prices"; klik otvara brief; osvježava se svake minute dok je otvoreno.
- Testovi: `agent_service/tests/test_catalog.py` (9, bez mreže) + `frontend/tests/test_search_markets.py` (5 e2e, offline iz snimka). Ukupno 17 prolazi: `python -m pytest frontend/tests agent_service/tests`.
- Vizualno provjereno (Playwright 1280 i 390, živi podaci): ispravljen sudar klase `.px` s velikom cijenom u briefu; ime kompanije ispod tickera.
- Ograničenja: sektor u prijedlozima je poznat samo za dionice iz Markets lista (SEC lista nema sektor). Offline brief i dalje radi samo za keširane tickere (AAPL, MSFT, NVDA); ostale iz Browse liste offline daju jasnu grešku.
- Grana sadrži i commit iz PR #16 (test okvir); nakon spajanja #16 rebase na dev ga sam izbaci.
- Sljedeće: stavka 3 (limit i stop nalozi).
