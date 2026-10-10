"""Crypto brief (contracts/brief.schema.json + contracts/catalog.md): price data only, no invented fundamentals.

Crypto has no 10-K, so the brief cites only [1] (Yahoo Finance price data) and has no risk section unless a
real source for [2] is added later. Pure functions, shared by agent_service and the Möbius package (fd_crypto.py).
"""
import datetime as dt
import math
import re

COINS = [  # the "Crypto" tab: large, liquid coins quoted in USD on Yahoo Finance
    ("BTC-USD", "Bitcoin"), ("ETH-USD", "Ethereum"), ("SOL-USD", "Solana"), ("XRP-USD", "XRP"),
    ("BNB-USD", "BNB"), ("DOGE-USD", "Dogecoin"), ("ADA-USD", "Cardano"), ("TRX-USD", "TRON"),
    ("AVAX-USD", "Avalanche"), ("LINK-USD", "Chainlink"), ("DOT-USD", "Polkadot"), ("LTC-USD", "Litecoin"),
]
NAMES = dict(COINS)


def is_crypto(ticker: str) -> bool:
    """Yahoo crypto pairs priced in dollars (BTC-USD, ETH-USD, ...). Same rule as data_service."""
    return re.fullmatch(r"[A-Z0-9]{2,12}-USD", (ticker or "").upper()) is not None


def display_name(ticker: str, quote_name: str | None = None) -> str:
    return NAMES.get(ticker.upper()) or (quote_name or ticker).replace(" USD", "")


def stats(points: list) -> dict:
    """Returns and risk measures from daily closes ([{time, close}], oldest first). Missing when history is short."""
    closes = [p["close"] for p in points if p.get("close")]
    out = {}
    if len(closes) >= 2:
        out["return_1y"] = closes[-1] / closes[0] - 1
    if len(closes) >= 31:
        out["return_30d"] = closes[-1] / closes[-31] - 1
        rets = [math.log(b / a) for a, b in zip(closes[-31:-1], closes[-30:])]
        mean = sum(rets) / len(rets)
        out["volatility_30d"] = math.sqrt(sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)) * math.sqrt(365)
    if closes:
        peak, dd = closes[0], 0.0
        for c in closes:
            peak = max(peak, c)
            dd = min(dd, c / peak - 1)
        out["max_drawdown_1y"] = dd
    return {k: round(v, 4) for k, v in out.items()}


PROMPT = """You are a crypto market analyst. Write a short thesis in English (default 3-4 sentences; the user's preferences below, if any, take priority, including over length) about {name} ({t}) using ONLY the price data below.
End every claim with the source tag [1] (Yahoo Finance price data). Never invent numbers, fundamentals, news, adoption figures or risks that are not in the data. Crypto has no earnings or annual report, so do not mention P/E, revenue or a 10-K; describe price, trend, volatility and drawdown instead, and say plainly that the data shows price behaviour only.
{instructions}Data: {data}
Return only the thesis text."""


def template_thesis(name: str, t: str, quote: dict, st: dict) -> str:
    parts = [f"{name} trades at ${quote['price']:,.2f}"]
    if st.get("return_1y") is not None:
        parts.append(f"{st['return_1y'] * 100:+.1f}% over the past year")
    s = ", ".join(parts) + " [1]."
    if st.get("volatility_30d") is not None:
        s += f" Its 30-day annualised volatility is {st['volatility_30d'] * 100:.0f}%"
        if st.get("max_drawdown_1y") is not None:
            s += f" and its deepest fall from a high in the last year was {st['max_drawdown_1y'] * 100:.0f}%"
        s += " [1]."
    return s + " This brief is based on price data only; crypto has no annual report [1]."


def prompt(t: str, name: str, quote: dict, st: dict, instructions: str = "") -> str:
    data = {k: quote.get(k) for k in ("price", "change_pct", "year_high", "year_low", "volume", "market_cap")}
    data.update(st)
    import json
    ins = f"User preferences learned from their ratings (follow them): {instructions}\n" if instructions else ""
    return PROMPT.format(name=name, t=t, data=json.dumps(data), instructions=ins)


def brief(t: str, quote: dict, st: dict, thesis: str, mode: str) -> dict:
    """Brief in the shared shape: crypto metrics in `extras`, no risks, a single source."""
    extras = {k: quote[k] for k in ("year_high", "year_low", "volume", "market_cap") if quote.get(k) is not None}
    extras.update(st)
    return {"ticker": t, "name": display_name(t, quote.get("name")), "asset_class": "crypto", "thesis": thesis, "mode": mode,
            "metrics": {"price": quote["price"], "pe": None, "revenue_growth_yoy": None, "net_margin": None},
            "risks": [], "peers": [c for c, _ in COINS[:3] if c != t][:2], "extras": extras,
            "sources": [{"label": "Yahoo Finance", "url": f"https://finance.yahoo.com/quote/{t}"}],
            "generated_at": dt.datetime.now(dt.timezone.utc).isoformat()}
