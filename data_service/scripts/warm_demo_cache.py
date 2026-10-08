"""Fetch the demo tickers live and write them to the committed demo snapshot.

    python -m scripts.warm_demo_cache            # AAPL MSFT NVDA
    python -m scripts.warm_demo_cache TSLA KO    # specific tickers

Run from data_service/. Commit demo_cache/ afterwards so the demo works offline.
"""

from __future__ import annotations

import sys

from app.cache import DiskCache
from app.config import DEMO_TICKERS, load_settings
from app.providers.edgar_provider import EdgarProvider
from app.providers.yfinance_provider import YFinanceProvider
from app.service import PERIOD_INTERVAL

DEMO_PERIODS = ("1d", "5d", "1mo", "6mo", "1y", "5y")


def main(tickers: list[str]) -> int:
    settings = load_settings()
    demo = DiskCache(settings.demo_cache_dir)
    market, edgar = YFinanceProvider(), EdgarProvider(settings.sec_user_agent)
    failed = 0
    for t in tickers:
        jobs = {
            ("quote", None): lambda: market.quote(t),
            ("financials", None): lambda: market.financials(t),
            ("risk_factors", None): lambda: edgar.risk_factors(t),
            **{("history", p): (lambda p=p: market.history(t, p, PERIOD_INTERVAL[p])) for p in DEMO_PERIODS},
        }
        for (kind, variant), fetch in jobs.items():
            try:
                demo.put(kind, t, fetch().model_dump(mode="json"), variant)
                print(f"ok   {t:6} {kind}{' ' + variant if variant else ''}")
            except Exception as e:  # report and continue; one bad source must not stop the rest
                failed += 1
                print(f"FAIL {t:6} {kind}{' ' + variant if variant else ''}: {type(e).__name__}: {e}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main([a.upper() for a in sys.argv[1:]] or list(DEMO_TICKERS)))
