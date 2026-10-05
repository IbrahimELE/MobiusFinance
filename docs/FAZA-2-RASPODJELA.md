# Faza 2: raspodjela (A i B), dopuna FAZA-2-PODJELE
Rok: petak 9.10.2026 (petak = bez novog koda). Pravila iz AGENTS.md i docs/GITFLOW.md važe: svako mijenja samo svoje foldere, grane `feature/a-…` / `feature/b-…` iz `dev`, PR u `dev`, `contracts/` samo dogovorom.

## Izmjena u odnosu na FAZA-2-PODJELA
Paper trading endpointe (`/paper/*`) radi **A** (u `data_service/`, uz `/quote` koji već ima); **B** radi panel u UI-ju. Razlog: B ima redizajn UI-ja, ocjene, „Naučeno" i demo/prijavu, pa je opterećenje inače neuravnoteženo. Ugovor `GET /paper/portfolio` iz FAZA-2 ostaje isti.

## OSOBA A
1. **learning_service/** (port 8003): `POST /feedback`, `GET /profile`, `GET /feedback`, `DELETE /profile`; profil iz pravila (radi offline), LLM sažetak kad je dostupan; testovi bez mreže.
2. **Paper trading** u `data_service/`: `POST /paper/orders`, `GET /paper/portfolio`, `POST /paper/reset`. Lokalni fajl po projektu, tržišni nalog po zadnjoj cijeni. Pohrana u jednom modulu, da se kasnije može zamijeniti (Möbius).
3. **Demo keš za učenje:** 2 ocjene daju vidljivo drukčiji profil; spremi i očekivani profil za offline.
4. **`/peers`** u data_service-u (ako ostane vremena), da zamijeni moju fiksnu PEERS listu.
5. `docs/LOG-A.md` uz svaki korak; ugovori `contracts/learning.*` i `contracts/paper.*` (zajedno s B, utorak ujutro).

## OSOBA B (agent + UI)
1. **Ugovori + mockovi** `learning` i `paper` u `contracts/` (zajedno, utorak ujutro).
2. **Redizajn UI-ja:** hijerarhija i kartice, rizici po kategorijama, godišnji grafikoni, izbor perioda grafikona, jasne greške.
3. **Ocjena briefa** (👍/👎 + bilješka → `/feedback`) i „Naučeno: …" iz `/profile`.
4. **Panel za paper trading:** kupi/prodaj iz briefa, tabela pozicija, oznaka „simulacija, nije savjet".
5. **Agent:** `profile.instructions` u prompt (`LEARNING_URL`); bez njega sve radi kao sada. Teza kroz vrijeme (sačuvani brief vs. današnja cijena).
6. **Demo:** snimak, prezentacija, prijava; „poslije ocjene" brief pripremljen kao keš (jasno označen), a uživo stvarno generisan.

## Raspored
| Dan | A | B |
|---|---|---|
| Uto 6.10 | ugovori; kostur learning_service, /feedback, profil iz pravila, testovi | ugovori; paper panel i redizajn nad mockovima |
| Sri 7.10 | LLM sažetak profila; paper endpointi; demo keš | ocjena + „Naučeno"; profil u promptu; teza kroz vrijeme |
| Čet 8.10 | spajanje, test na 4–5 tickera; /peers ako ostane | dorada UI-ja, test, snimak demoa |
| Pet 9.10 | podrška za demo | prezentacija i prijava, bez novog koda |

## Demo uživo
Pokretanje na laptopu: `./run.sh` (ili `DATA_OFFLINE=1 ./run.sh`). Ako AI ili mreža zapnu, brief pada na keš. Uvijek imati snimljen rezervni video.
