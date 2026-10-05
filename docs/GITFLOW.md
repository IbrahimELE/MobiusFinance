# Git Workflow Guide (Finance Desk)
Repo koristi **hookove koji provode** pravila, da historija ostane čista.

## Strategija grana
- Zaštićene grane: `main`, `dev`. **Ne commituj direktno na njih.**
- `dev` = integracija (radno stanje); `main` = stabilno/demo-spremno, u njega ide samo `dev` preko PR-a (u petak, predaja).
- Radne grane se prave iz `dev`: `feature/<ime>`, `bugfix/<ime>`, `hotfix/<ime>`, `docs/<ime>`, `refactor/<ime>`, `test/<ime>` (mala slova, crtice).
  Primjeri: `feature/edgar-risk-factors` (A), `feature/brief-prompt` (B), `bugfix/chart-empty-history`.
- Predlog: dodaj prefiks osobe u ime kad treba razlikovati, npr. `feature/a-edgar`, `feature/b-brief-prompt`.

## Format commit poruke
`type(scope): opis`. Tipovi: feat, fix, docs, style, refactor, perf, test, build, ci, chore, hotfix.
Scope = modul: `data`, `agent`, `ui`, `contracts`, `docs`. Primjeri: `feat(data): dohvat Item 1A iz EDGAR-a`, `fix(ui): grafikon ne crta praznu historiju`.

## Zabranjeno (provodi se hookovima)
- Direktni commit na `main` ili `dev`
- Merge commitovi (`git merge`) lokalno
- Rebase dok si na `main` ili `dev`
- Nedozvoljeni nazivi grana i poruke commita

## Dnevni tok
```
git switch dev && git pull
git switch -c feature/tvoj-zadatak
# rad
git add . && git commit -m "feat(scope): opis"
git fetch && git rebase origin/dev          # (na radnoj grani) ažuriranje
git push -u origin HEAD                     # pa otvori PR u dev
# merge kroz PR (Squash and merge), zatim:
git switch dev && git pull
git branch -d feature/tvoj-zadatak
git push origin --delete feature/tvoj-zadatak
```
Greškom commitao na dev/main? `git stash push -u && git switch -c feature/tvoj-zadatak && git stash pop` (commit koji je već napravljen: `git switch -c feature/x` pa vrati dev na origin/dev: `git branch -f dev origin/dev`).

## Izbjegavanje merge konflikata
Vlasništvo po folderima: A `data_service/`, B `agent_service/` + `frontend/`, `contracts/` zajednički (promjena samo dogovorom), `docs/LOG-A.md` A, `docs/LOG-B.md` B. Diraj samo svoje. Vidi README.md i .github/CODEOWNERS.

## Postavljanje hookova (jednom nakon clone-a)
`./setup.sh` (kopira `.githooks/*.sh` u `.git/hooks/` bez `.sh`, postavlja `pull.ff only`).

## Privremeno zaobilaženje (rijetki slučajevi)
- Isključi: `git config --local hooks.gitflow.enabled false`
- Uključi: `git config --local hooks.gitflow.enabled true`
- Provjera: `git config --get --bool hooks.gitflow.enabled`

## Ostalo
Petak 9.10. bez novog koda; prije predaje PR `dev` → `main` i tag `v1-demo`. Tajne nikad u repo (`.env` ignoriran). Push/PR/komentari na GitHubu rade se uz odobrenje vlasnika (AI agenti: izričito).
