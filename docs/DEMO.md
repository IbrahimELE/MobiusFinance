# Demo: "Analiziraj kompaniju X za 2 minute" (osoba B)
Cilj: žiriju pokazati cijeli tok bez ovisnosti o internetu ili ključu.

## Priprema (prije snimanja)
1. Pravi podaci: `./run.sh` (ili `DATA_OFFLINE=1 ./run.sh` za potpuno offline: tickeri AAPL, MSFT, NVDA), otvori http://localhost:8002/. U demou koristi ta tri tickera.
2. Bez AI-ja servis koristi `agent_service/demo_cache/*.json` (AAPL, MSFT, TSLA, NVDA, GOOGL), pa teza je puna i na laptopu bez ključa (značka "iz keša").
3. **Brzina AI-ja:** uz `ANTHROPIC_API_KEY` brief traje par sekundi; preko prijavljenog `claude` CLI-ja može trajati i preko minute. Za snimak postavi ključ, ili snimaj bez AI-ja (briefovi iz keša, značka "iz keša").
4. Napravi projekt "Hackathon demo" (+ Projekt). Isključi Wi-Fi da pokažeš offline rad.

## Scenarij (cilj 2:00)
| Vrijeme | Šta pokazati | Šta reći |
|---|---|---|
| 0:00 | Naslov, prazan projekt | Problem: financijsko istraživanje troši sate na skupljanje izvora. Finance Desk to radi u minuti, sa izvorima. |
| 0:15 | Upiši AAPL → Analiziraj | Agent uzima cijene, financije i rizike iz 10-K (Item 1A). |
| 0:35 | Grafikon + 4 pokazatelja | Cijena, P/E, rast prihoda, neto marža. |
| 0:50 | Teza: klik na [1], [2] | Svaka tvrdnja ima izvor koji se može provjeriti. |
| 1:10 | Rizici iz 10-K | Rizici direktno iz službenog filinga. |
| 1:20 | Analiziraj MSFT i NVDA, označi sve, "Usporedi" | Isti pokazatelji jedan pored drugog. |
| 1:40 | Chat: "Koji kompaniji su rizici najveći?" | Pitanja nad sačuvanim briefovima projekta; radni prostor, ne samo chat. |
| 1:55 | Osvježi stranicu: briefovi ostaju | Sve se čuva po projektu. Kraj. |

## Napomene
- Pitanja u chatu rade samo uz AI (ključ ili Claude); za snimak ih pripremi unaprijed na mašini s AI-jem.
- Uz `run.sh` brojevi i rizici su stvarni (yfinance, SEC EDGAR). Mockovi s ilustrativnim brojevima se koriste samo ako agent radi bez `DATA_URL`.
- Snimak i prijava: radi se u petak, bez novog koda.
