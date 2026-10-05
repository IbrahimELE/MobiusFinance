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

## Pokretanje
- **Data service (A):** port 8001 (`uvicorn` iz `data_service/`), endpointi iz `contracts/README.md`.
- **Agent + UI (B):** `cd agent_service && pip install -r requirements.txt && uvicorn main:app --port 8002`, otvori http://localhost:8002/. Bez `DATA_URL` koristi mockove; sa `DATA_URL=http://localhost:8001` pravi data service.

## Dnevni plan
| Dan | A (podaci) | B (agent + UI) |
|---|---|---|
| Pon 5.10 | kostur, yfinance | ugovori + mockovi, kostur UI/agenta |
| Uto 6.10 | EDGAR Item 1A | prvi pravi brief, grafikon, kartica |
| Sri 7.10 | keš, demo tickeri, /peers | spajanje na A, projekti |
| Čet 8.10 | opcionalno /news /macro | konkurenti u UI, test 4–5 tickera |
| Pet 9.10 | podrška | demo, prezentacija, prijava |
