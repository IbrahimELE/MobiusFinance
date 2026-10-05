# Git workflow (A i B)
Lagan gitflow za 5 dana. Cilj: nikad isti fajlovi, spajanje barem jednom dnevno, `main` uvijek radi.

## Grane
- `main`: uvijek pokretljiv i demo-spreman. Niko ne pusha direktno; samo preko PR-a.
- `feat/a-<tema>` (osoba A), `feat/b-<tema>` (osoba B): kratkotrajne grane, npr. `feat/a-edgar-risk-factors`, `feat/b-brief-prompt`. Jedna tema = jedna grana = jedan PR.
- `contracts/` mijenja se samo posebnom granom `contract/<tema>` uz pregled druge osobe.
- Nema `develop` grane: s dvoje ljudi i 5 dana je suvišna.

## Vlasništvo (vidi .github/CODEOWNERS)
| Folder | Vlasnik |
|---|---|
| `data_service/` | A |
| `agent_service/`, `frontend/` | B |
| `contracts/` | oba (pregled obavezan) |
| `docs/LOG-A.md` / `docs/LOG-B.md` | A / B |
| `AGENTS.md`, `docs/GITFLOW.md` | oba, rijetko |
Zato se konflikti ne dešavaju: svako dira samo svoje.

## Dnevni ritam
1. Ujutro: `git checkout main && git pull`, nova grana `git checkout -b feat/b-<tema>`.
2. Mali commitovi, poruka `tip(opseg): šta`, npr. `feat(agent): LLM teza s izvorima`. Tipovi: feat, fix, docs, chore, test.
3. Prije PR-a: `git fetch && git rebase origin/main` (ili merge main u granu), provjeri da se pokreće.
4. PR u `main` s kratkim opisom (šablon u .github/). Druga osoba (ili njen agent) pregleda; za vlastite foldere dovoljno brzo odobrenje.
5. Merge: **squash and merge**, brisanje grane. Navečer `main` mora raditi na mockovima.
6. Dopiši zapis u svoj `docs/LOG-*.md` (dio PR-a).

## Pravila
- Promjena ugovora (`contracts/`) = prvo napiši u `docs/QUESTIONS.md` / javi drugoj strani, tek onda PR.
- Pet 9.10: samo demo/prijava, bez novog koda; ako treba hotfix, `fix/<tema>` s odobrenjem oboje.
- Prije predaje oznaka: `git tag v1-demo` na `main`.
- Tajne (API ključevi, FRED/Finnhub/Alpaca) nikad u repo; `.env` je u .gitignore, a `.env.example` se commituje.
- Licence: prije kopiranja tuđeg koda provjeri licencu i navedi izvor u README-u.

## Postavljanje (jednom, vlasnik repoa)
1. Napravi GitHub repo (npr. `finance-desk`), dodaj drugu osobu kao collaboratora (Settings → Collaborators).
2. Push početnog stanja na `main`.
3. Settings → Branches → zaštiti `main`: zahtijevaj PR, zabrani force-push. (Opcionalno: obavezno 1 odobrenje.)
4. Oba: `git clone`, pa slijedi dnevni ritam.
Napomena za AI agente: push, PR i komentari na GitHubu su javne akcije; rade se samo uz izričito odobrenje vlasnika.
