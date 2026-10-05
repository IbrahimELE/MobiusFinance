# Prezentacija (skica slajdova, osoba B)
1. **Problem:** financijsko istraživanje = sati kopiranja iz više izvora, bez provjerljivosti.
2. **Rješenje:** Finance Desk, AI radni prostor: ticker → brief (teza, rizici, brojevi, izvori), grafikon, sačuvano po projektu. Nije broker ni terminal.
3. **Demo** (vidi docs/DEMO.md).
4. **Arhitektura:** tri nezavisna modula preko ugovora (`contracts/`): data_service (A), agent_service + frontend (B). Mock → pravi servis zamjenom jednog URL-a.
5. **Pouzdanost:** svaka tvrdnja ima izvor [n]; rizici iz 10-K Item 1A; demo radi offline (keširani briefovi); AI padne → šablon.
6. **Šta dalje:** vijesti, makro (FRED), paper trading, objava kao Möbius aplikacija u Storeu.
7. **Izvori i licence:** yfinance, SEC EDGAR, TradingView Lightweight Charts (Apache 2.0), Claude (Anthropic).
