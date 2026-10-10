# Log varijante A (data service)
Osoba A: dopisuj ovdje isti format kao u LOG-B.md (datum · korak · šta · zašto · provjera · sljedeće).

## 2026-10-05 · Korak 1: data_service jezgro (quote, history, financials, risk-factors)
- Napravljeno: `data_service/` (FastAPI): `GET /quote/{t}`, `/history/{t}?period=1y`, `/financials/{t}` (yfinance), `/filings/{t}/risk-factors` (SEC EDGAR, najnoviji 10-K, Item 1A), `/health`. Provider interfejs (`app/providers/base.py`), keš na disku s TTL-om, offline mod (`DATA_OFFLINE=1`) i commitovani demo snapshot za AAPL, MSFT, NVDA (`data_service/demo_cache/`).
- Ugovor: odgovori sadrže sva polja iz `contracts/mocks/*.AAPL.json` istog imena i tipa (rast/marže kao udjeli, `change_pct` u procentima kao u mocku); ostalo su dodaci (`meta`, `risks[]` s kategorijom i tekstom, `annual[]`…). `contracts/` nije mijenjan.
- EDGAR parser provjeren na AAPL, MSFT, NVDA, JPM, KO, AMZN, TSLA, GOOGL, META (21–44 rizika). Strani emitenti (20-F, npr. TSM) vraćaju 404 `filing_not_found`.
- Provjera: `cd data_service && pytest -q` (25 testova, bez mreže, uklj. usklađenost s mockovima); ručno: agent sa `DATA_URL=http://localhost:8001` vraća brief za AAPL/MSFT/NVDA s pravim brojevima i rizicima.
- Za B: kad nema LLM-a, `/brief` vraća `agent_service/demo_cache/<T>.json` (stari mock brojevi, npr. AAPL 227.5) umjesto pravih podataka iz data_service; `/compare` i `/history` već koriste prave. Možda regenerisati demo briefove nad pravim data_service-om.
- Pokretanje: vidi `data_service/README.md` (port 8001, `SEC_USER_AGENT` u `.env`).
- Sljedeće: zajednički test cijelog toka na 3 tickera s B; zatim opcionalno `/peers` (zamjena za PEERS u agentu).

## 2026-10-05 · Korak 2: faza 2 (učenje od korisnika + paper trading), grana `feature/a-learning-paper`
- Napravljeno: `learning_service/` (port 8003): `POST/GET /feedback`, `GET/DELETE /profile`, `POST /demo/seed`. Profil iz pravila (odmah, offline; BS/EN, s i bez kvačica, zadnje mišljenje pobjeđuje) + AI sažetak u pozadini (API ključ ili `claude` CLI), vezan za otisak ocjena pa nikad nije zastario. Demo: `learning_service/demo/` (2 ocjene + unaprijed AI profil).
- Paper trading u `data_service/app/paper.py`: `POST /paper/orders`, `GET /paper/portfolio`, `POST /paper/reset`; zamjenjiva pohrana (`PaperStore`), cijene iz `/quote` (keš/offline vrijedi i ovdje).
- Ugovori: PRIJEDLOG u `contracts/README.md` (sekcija Faza 2) + mockovi `profile.demo.json`, `feedback.demo.json`, `paper-portfolio.demo.json`, `paper-order.demo.json`. Čeka potvrdu B (CODEOWNERS na contracts/). Dodato polje `label` za „Naučeno: …".
- Provjera: `data_service` 33 testa, `learning_service` 16 testova (bez mreže, uklj. usklađenost s mockovima). Uživo: kopija agenta koja ubacuje `profile.instructions` u prompt → nakon 2 ocjene teza AAPL počinje FCF-om umjesto cijenom; paper kupovina/portfelj/greška; `/demo/seed` bez AI-ja daje spremljeni AI profil.
- Za B: (1) u `write_thesis` dodati `instructions` iz `GET {LEARNING_URL}/profile` (primjer u `learning_service/README.md`); (2) prompt fiksno traži 3–4 rečenice, pa „kraće" nema puni efekat; (3) project_id isti slug kao u agentu.
- Grana je napravljena iz `featureA` (još nije u `dev`); nakon squash-merge PR-a featureA treba `git rebase --onto origin/dev featureA feature/a-learning-paper`.
- Sljedeće: dogovor ugovora s B (utorak ujutro), PR-ovi; `/peers` ako ostane vremena.

## 2026-10-05 · Korak 3: usklađeno s B-ovim ugovorima (learning.md, paper.md)
- B je paralelno napisao `contracts/learning.md`, `contracts/paper.md`, `mocks/portfolio.demo.json`, `mocks/profile.demo.json` (grana `feature/b-ui-faza2`). Moj prijedlog je povučen; preuzeti su njegovi fajlovi bajt-po-bajt (spajanje bez konflikta).
- Paper: `POST /paper/orders` vraća portfelj + `fill {ticker, side, qty, price, at}` (dodatno `order`); greške 409 `insufficient_cash` / `insufficient_position`.
- Learning: `POST /feedback` vraća `{"ok": true, "feedback_count": n}` (+ sačuvana ocjena), `DELETE /profile` vraća `{"ok": true}` (+ prazan profil). Profil ima i `label`, `recent_notes` (dodatno).
- Ispravljena utrka: kad dvije ocjene stignu brzo, sporiji AI sažetak starije ocjene je mogao pregaziti noviji; sada se zastarjeli odbacuje (test + provjereno uživo).
- Provjera: B-ov agent s `feature/b-ui-faza2` nad mojim servisima: 2 ocjene preko agenta → profil; kupovina AAPL i 409 preko agenta; brief NVDA s naučenim profilom: tačno 3 rečenice, počinje zaduženošću (D/E 0,17) i FCF-om, bez opisa proizvoda. Testovi: data_service 33, learning_service 17.
- Za B: `proxy()` u agentu prosljeđuje grešku kao tekst (`{"detail": "{\"error\":...}"}`), pa UI prikaže sirovi JSON; predlog: `raise HTTPException(r.status_code, r.json().get("detail", r.text))` ili proslijediti JSON kakav jeste.

## 2026-10-06 · Korak 4: priprema za predaju (grana `feature/a-predaja`, po dogovoru vlasnika)
- Agent (B-ov folder, uz odobrenje vlasnika; molim pregled u PR-u): greške A-ovih servisa više ne ruše brief (500). `call()`/`upstream_error()` u `agent_service/main.py` pretvaraju `{"error","detail"}` u poruku na bosanskom (nepoznat ticker 404, nema 10-K 404, offline bez keša 503, premalo novca / dionica 409). `proxy()` koristi isto, pa UI prikazuje rečenicu, ne sirovi JSON.
- Agent: kad podaci nisu dostupni (offline, ticker van A-ovog keša), brief pada na `agent_service/demo_cache/<T>.json` ako postoji (TSLA, GOOGL offline sada rade).
- `run.sh`: koristi `python3` (ili `python`, ili `PYTHON=...`), ne pregazi `SEC_USER_AGENT` lažnom adresom, ispiše link.
- Dodano: `LICENSE` (MIT), `docs/SOURCES.md` (izvori i licence za prijavu), `learning_service` u CODEOWNERS; README (pokretanje, AI ključ, šta aplikacija radi), DEMO.md (brzina AI-ja).
- Provjereno (API, run.sh): offline AAPL/TSLA brief iz keša, XXXX → 503 s porukom; online XXXX → 404 „Nepoznat ticker…", TSM → 404 „Nema 10-K…"; paper 409 poruke. Testovi data 33, learning 17. UI nije vizuelno provjeren (preglednik na Möbius hostu se nije mogao pokrenuti) – proći TESTING.md na laptopu.

## 2026-10-08 · Korak 5: UI/UX popravke po listi vlasnika (grana `feature/a-ui-v2`, iz `feature/a-predaja`)
Funkcionalno:
- Graf: `fixLeftEdge`/`fixRightEdge` – ne može se odzumirati van podataka (provjereno: 40 wheel-out i dalje pun period); wheel zumira, drag pomjera, dupli klik na osu resetuje.
- Paper trading: novac se i ranije skidao, ali UI je krupno pokazivao ukupnu vrijednost (~100k). Sada je naslov "Cash available", plus Invested/Total/P&L/Return, procjena troška prije kupovine, toast "Cash $X → $Y", lista zadnjih naloga, Sell onemogućen bez pozicije.
- Cijena uživo: data_service `/quote` vraća `market_state`/`market_open` (Yahoo), novi periodi `1d` (5 min) i `5d` (30 min) s kešom 60 s. UI pokazuje "Live · vrijeme" samo dok je berza otvorena, inače "Market closed" ili "Offline data"; cijena treperi pri promjeni. Izvor se mijenja ~svakih 25 s u radno vrijeme (provjereno AAPL 337.35→337.11).
Estetika:
- Sve na engleskom: UI, AI teza i chat (prompt), šablon, poruke grešaka, profil učenja ("Personalised: …"), demo briefovi u `agent_service/demo_cache` (regenerisani AI-jem), demo ocjene u learning_service.
- Novi frontend: dizajn tokeni (boje, razmaci, radijusi), font Inter ugrađen (`frontend/vendor`, OFL), veći logo, pretraga s jasnim "Generate AI brief", "Workspace" umjesto nejasnog projekta, početni ekran (šta je aplikacija, šta možeš, kako radi; inspiracija naga.com), vlastiti modal i toast umjesto `confirm`/`prompt`, mobilni prikaz.
- Provjera: Playwright screenshoti desktop + mobile (landing, brief, kupovina, modal, 1D graf, zoom-out); testovi data 34, learning 17; JS `node --check`.
- Napomena za B: ovo dira `frontend/` i `agent_service/` (uz odobrenje vlasnika); molim pregled u PR-u.

## 2026-10-08 · Korak 6: ispravke nakon testiranja (grana `feature/a-ui-v2`)
- Cijena se nije osvježavala kod vlasnika: `/quote` je zvao Yahoo "info" (quoteSummary), koji se često ograničava/blokira (EU kolačići) pa je servis tiho vraćao staru keširanu cijenu. Sada cijena ide preko laganog chart endpointa (`fast_info`, ~0,1–0,2 s), naziv firme se kešira 6 h i nije obavezan, a status berze se računa po njujorškom radnom vremenu (`us_market_state`, test). Provjereno: MSFT 531.45 → 531.43 → 531.42 u 16 s razmaka.
- Graf: crosshair u "Magnet" modu (vrijednost = cijena dionice na tom danu, ne visina miša) + natpis s cijenom i datumom iznad grafa.
- Učitavanje: graf ima loader i štiti se od zastarjelih odgovora (promjena perioda/dionice); desni panel se odmah iscrtava iz zadnjeg stanja, Buy/Sell su onemogućeni dok ne stigne živa cijena ("Getting live price…"); spremljeni brief se otvara iz već učitane liste; povratak na početnu odmah skida trade box; promjena workspacea odmah prazni stari račun; tokom naloga dugme pokazuje spinner.
- UI osvježava cijenu i portfelj svakih 10 s.
- Testovi: data 42 (novi test za status berze), learning 17; `node --check`.

## 2026-10-08 · Korak 7: watchlist + "teza kroz vrijeme" (engagement, po izboru vlasnika)
- Kartica "Saved briefs" je sada **Watchlist**: za svaki brief živa cijena, promjena danas i promjena od dana briefa ("% since brief"); osvježava se svakih 20 s.
- **Dnevnik teza** iznad liste: "X of Y researched stocks are up since your brief · average … · best …".
- **Alarm cijene** (zvonce): unos cijene → alarm "above"/"below" prema trenutnoj cijeni; kad se pređe: toast + browser notifikacija (ako je dozvoljena), alarm se briše. Čuva se lokalno po workspaceu (localStorage); radi dok je aplikacija otvorena.
- Samo frontend (koristi postojeće `/briefs` i `/quote`); bez promjena servisa i ugovora.

## 2026-10-10 · Korak 8: lokalni leaderboard workspaceova (grana `feature/a-leaderboard`, po izboru vlasnika)
- Zašto: vlasnik je tražio dnevni/sedmični/mjesečni leaderboard po PnL-u (%) s trajnom statistikom 1./2./3. mjesta. Dijeljena verzija među Möbius korisnicima (~10–13 h + identitet) nije stala u rok, pa je urađena lokalna: rang svih workspaceova na jednoj instalaciji. Ugovor je pisan tako da se kasnije pohrana može zamijeniti serverskom bez promjene UI-ja.
- Ugovor: `contracts/leaderboard.md` + `mocks/leaderboard.demo.json` (novo; molim B za pregled).
- data_service: `app/leaderboard.py` + `GET /paper/leaderboard?period=day|week|month`. Prinos se računa iz sačuvanih naloga i dnevnih cijena zatvaranja prije granice perioda (Europe/Sarajevo), bez procesa u pozadini. Zatvoreni periodi se pri prvom čitanju trajno upisuju u `paper_data/leaderboard/podiums.json` (medalje). Period bez ikakvog pomaka (vikend) nema medalja.
- Paper: račun sada pamti `created_at` i `resets[]`; reset i dalje briše naloge, ali čuva vrijeme reseta → reset usred perioda = diskvalifikacija za taj period. Stari fajlovi bez tih polja rade (početak = prvi nalog).
- agent_service (B-ov folder, uz odobrenje vlasnika): proxy `GET /paper/leaderboard`. frontend (B-ov folder): kartica „Leaderboard" ispod paper računa (Day/Week/Month, 🥇🥈🥉, „Reset · out", zadnji podij, tabela medalja, odbrojavanje do kraja perioda; osvježava se nakon naloga/reseta i svakih 40 s); tekst modala za reset spominje izlazak iz ranga.
- Provjera: testovi data 55 (13 novih: granice perioda i DST, vrednovanje, rang, reset, vikend bez medalja, trajnost medalja, ugovor rute), `node --check`; uživo sa pravim yfinance cijenama i 4 probna workspacea (u privremenom DATA_PAPER_DIR), reset preko agenta → odmah „reset"; Playwright desktop 1440 i mobilni 390 bez JS grešaka.
- Ograničenja: rang je lokalan (jedan korisnik, više workspaceova); nalozi stariji od reseta se ne mogu vratiti pa se medalje za period prije reseta upisuju samo ako je leaderboard otvoren prije reseta; offline bez istorije cijena vrednuje se po zadnjoj cijeni naloga.
- Sljedeće: pregled B-a (frontend, agent, ugovor), PR u dev uz odobrenje vlasnika; kasnije dijeljena verzija = isti ugovor, server vodi takmičarske račune.
