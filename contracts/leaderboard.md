# Ugovor: leaderboard workspaceova (data_service, osoba A; kartica u UI-ju osoba B)
Lokalno rangiranje paper računa svih workspaceova na jednoj instalaciji po prinosu (%) za dan, sedmicu i mjesec. UI ide preko agenta (`/paper/leaderboard` prosljeđuje na `DATA_URL`).

- `GET /paper/leaderboard?period=day|week|month` → mocks/leaderboard.demo.json. Greška 422 za nepoznat period.

## Pravila
- Periodi po vremenu `Europe/Sarajevo`: dan od 00:00, sedmica od ponedjeljka 00:00, mjesec od 1. u 00:00. Tekući period je uživo i nije završen.
- `return_pct` = vrijednost na kraju ÷ vrijednost na početku perioda − 1, u procentima (1.7 == +1,7 %). Kraj tekućeg perioda = trenutna vrijednost računa (žive cijene).
- Vrijednost na početku perioda računa se iz sačuvanih naloga (stanje novca i pozicija prije granice) i zadnje dnevne cijene zatvaranja prije granice. Ne treba proces u pozadini. Ako cijena zatvaranja nije dostupna, koristi se zadnja cijena naloga.
- Račun otvoren usred perioda počinje s početnim kapitalom (100.000 USD).
- U rangu je svaki workspace koji je napravio bar jedan nalog prije kraja perioda.
- **Reset računa usred perioda = diskvalifikacija za taj period** (`disqualified: true`, `note: "reset"`, bez ranga). Reset briše naloge, pa se prinos ne bi mogao pošteno izračunati, a reset ne smije brisati loš rezultat.
- Kad period završi, top 3 se trajno upisuju (`podiums`); `medals` broji koliko je puta koji workspace bio 1., 2. i 3. u toj vrsti perioda. Period u kojem se ničija vrijednost nije pomjerila (vikend, praznik, sve u gotovini) nema pobjednika ni medalja. Jednak prinos se razvrstava po imenu workspacea. Zatvoreni periodi se upisuju pri prvom čitanju nakon granice (unazad najviše 62 dana / 26 sedmica / 12 mjeseci).
- `stale_prices: true` kad je neka trenutna vrijednost izračunata bez žive cijene.

## Odgovor
```
{period, timezone, start, end, standings[{rank|null, project_id, start_equity, equity, return_pct, disqualified, note|null}],
 medals[{project_id, gold, silver, bronze}], last_podium{start, end, places[{rank, project_id, return_pct}]}|null, stale_prices, updated_at}
```
`standings`: rangirani od najboljeg, diskvalifikovani na kraju. `medals`: od najviše zlata (pa srebra, bronze).
