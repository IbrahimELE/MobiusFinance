# Test plan (osoba B), čet 8.10: 4–5 tickera
Tickeri: AAPL, MSFT, TSLA, NVDA, GOOGL. Za svaki: Generate AI brief (UI je na engleskom), provjeri:
- [ ] Brief se pojavi < 20 s (ili odmah iz keša), nema "Greška"
- [ ] Grafikon se crta; 4 pokazatelja imaju brojeve
- [ ] Teza ima [1]/[2] i linkovi se otvaraju
- [ ] Rizici (3 stavke) s izvorom
- [ ] Brief se pojavi u "Sačuvani briefovi" i nakon osvježavanja
- [ ] Usporedba 2–4 označena radi; × briše brief
- [ ] Novi projekt: prazan, odvojen od drugih
- [ ] Bez AI-ja (bez ključa i claudea): značka "iz keša", puna teza
- [ ] Offline (isključen internet): sve radi
- [ ] Neznani ticker (npr. XXXX): jasna greška, ne pad
Poznato: s pravim data_service-om provjeriti da polja ugovora i period (`?period=1y`) odgovaraju.
