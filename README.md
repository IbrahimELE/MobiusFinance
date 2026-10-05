# Finance Desk
AI radni prostor za financijsko istraživanje (Hackathon 2026, "Private pro desk", rok 9.10.2026). Unos tickera → brief (teza, rizici, brojevi, izvori) + grafikon + sačuvani briefovi. Nije broker ni terminal.

Repo: https://github.com/IbrahimELE/MobiusFinance · AI agenti: čitaju prvo `AGENTS.md`.

## Struktura i vlasništvo (da nema merge konflikata)
```
contracts/       JSON šeme + mockovi        → ZAJEDNO (promjena samo dogovorom, PR pregleda druga strana)
data_service/    Backend 1: podaci, bez LLM → OSOBA A
agent_service/   Backend 2: LLM tok, brief  → OSOBA B
frontend/        UI                         → OSOBA B
docs/LOG-A.md    dnevnik A                  → OSOBA A
docs/LOG-B.md    dnevnik B                  → OSOBA B
docs/QUESTIONS.md pitanja drugoj strani     → oba (dopisuj na kraj)
docs/GITFLOW.md, AGENTS.md, README.md       → oba, rijetko
.github/         CODEOWNERS, PR šablon
```
**Zlatno pravilo:** diraj samo svoje foldere. Ako ti treba promjena u tuđem, zapiši u `docs/QUESTIONS.md` ili javi, ne uređuj sam. Moduli komuniciraju samo preko `contracts/`.

## Git workflow (kratko, detalji u `docs/GITFLOW.md`)
Zaštićene grane `main` i `dev`; radne grane iz `dev`: `feature/`, `bugfix/`, `hotfix/`, `docs/`, `refactor/`, `test/` + `<ime>`. Commit: `type(scope): opis`. Merge samo kroz PR u `dev` (Squash and merge), bez lokalnih merge commitova. `main` dobija samo `dev` preko PR-a (predaja).
Nakon clone-a jednom: `./setup.sh` (instalira hookove koji provode pravila).
```
git switch dev && git pull
git switch -c feature/tvoj-zadatak
git add . && git commit -m "feat(agent): opis"
git push -u origin HEAD     # PR u dev
```

## Pokretanje (oba servisa jednom naredbom)
```
pip install -r data_service/requirements.txt -r learning_service/requirements.txt -r agent_service/requirements.txt
./run.sh                      # ili: DATA_OFFLINE=1 ./run.sh  (offline demo: AAPL, MSFT, NVDA iz keša)
```
Otvori http://localhost:8002/. Zasebno: data_service na 8001 (`data_service/README.md`), agent+UI na 8002 s `DATA_URL=http://localhost:8001`. Bez `DATA_URL` agent koristi mockove iz `contracts/mocks` (ilustrativni brojevi).
Prije prvog pokretanja upiši svoj `SEC_USER_AGENT` (ime + e-mail) u `data_service/.env` (EDGAR to traži).

## Status varijante B (pon 5.10.)
Urađeno: ugovori+mockovi (5 tickera), agent (/brief, /briefs, /projects, /compare, /chat, LLM teza s izvorima, keš za demo), UI (grafikon offline, kartice, projekti, usporedba, chat), docs/DEMO.md, docs/PRESENTATION.md, docs/TESTING.md.
Čeka: pravi data_service (A) → `DATA_URL`; test na pravim podacima; snimak i prijava (pet).

## Dnevni plan
| Dan | A (podaci) | B (agent + UI) |
|---|---|---|
| Pon 5.10 | kostur, yfinance | ugovori + mockovi, kostur UI/agenta |
| Uto 6.10 | EDGAR Item 1A | prvi pravi brief, grafikon, kartica |
| Sri 7.10 | keš, demo tickeri, /peers | spajanje na A, projekti |
| Čet 8.10 | opcionalno /news /macro | konkurenti u UI, test 4–5 tickera |
| Pet 9.10 | podrška | demo, prezentacija, prijava |
