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

## Gitflow u 6 koraka
1. `git checkout main && git pull`
2. Nova grana: A `git checkout -b feat/a-<tema>`, B `git checkout -b feat/b-<tema>` (npr. `feat/a-edgar-risk-factors`).
3. Mali commitovi: `feat(data): ...`, `fix(agent): ...`, `docs: ...` (tipovi: feat, fix, docs, chore, test).
4. Prije PR-a: `git fetch && git rebase origin/main`, provjeri da se pokreće.
5. Otvori PR u `main`, druga osoba pregleda. Merge: **Squash and merge**, obriši granu.
6. Dopiši zapis u svoj `docs/LOG-*.md` (u istom PR-u).

Pravila: nema direktnog pusha na `main`; `main` navečer mora raditi na mockovima; spajanje barem jednom dnevno; tajne nikad u repo (`.env` ignoriran, `.env.example` commitovan); petak 9.10. samo demo, bez novog koda; prije predaje tag `v1-demo`. Detalji: `docs/GITFLOW.md`.

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
