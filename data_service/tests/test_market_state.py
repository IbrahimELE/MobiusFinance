"""US session by the clock (New York time), used for the Live / Market closed badge."""
from datetime import datetime, timezone

import pytest

from app.providers.yfinance_provider import us_market_state


@pytest.mark.parametrize("utc,state", [
    ("2026-10-08T13:00", "REGULAR"),   # Thu 09:00 ET -> pre-market
    ("2026-10-08T13:30", "REGULAR"),   # 09:30 ET open
    ("2026-10-08T19:59", "REGULAR"),   # 15:59 ET
    ("2026-10-08T20:00", "POST"),      # 16:00 ET close
    ("2026-10-08T09:00", "PRE"),       # 05:00 ET
    ("2026-10-09T02:00", "CLOSED"),    # 22:00 ET
    ("2026-10-10T15:00", "CLOSED"),    # Saturday
    ("2026-12-15T14:31", "REGULAR"),   # winter time: 09:31 EST
])
def test_us_market_state(utc, state):
    expected = "PRE" if utc == "2026-10-08T13:00" else state
    assert us_market_state(datetime.fromisoformat(utc).replace(tzinfo=timezone.utc)) == expected


def test_crypto_pairs_are_recognised():
    from app.providers.yfinance_provider import is_crypto
    assert is_crypto("BTC-USD") and is_crypto("eth-usd")
    assert not is_crypto("AAPL") and not is_crypto("BRK-B")
