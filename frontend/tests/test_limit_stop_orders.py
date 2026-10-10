"""Item 3: limit and stop-loss paper orders in the Trade panel (offline stack, static prices)."""
import re

def open_trade(page, ticker="AAPL"):
    page.fill("#t", ticker)
    page.press("#t", "Enter")
    page.wait_for_selector("#pf .trade button[data-s=buy]:not([disabled])", timeout=30000)

def money(s):
    return float(re.sub(r"[^0-9.\-]", "", s))

def test_limit_buy_waits_reserves_cash_and_can_be_cancelled(page):
    open_trade(page)
    page.click('#pf [data-ot="limit"]')
    assert "only while Finance Desk is running" in page.inner_text("#pf .trade")
    page.fill("#lpx", "100")
    page.click('#pf [data-quick="10"]')
    assert "reserves $1,000.00" in page.inner_text("#pv")
    page.click("#pf [data-s=buy]")
    page.wait_for_selector("#opens [data-cancel]")
    assert "Limit" in page.inner_text("#opens") and "at ≤ $100.00" in page.inner_text("#opens")
    assert money(page.inner_text("#cashv")) == 99_000
    assert "reserved for open buy orders" in page.inner_text("#pf")
    page.click("#opens [data-cancel]")
    page.wait_for_selector("#opens", state="detached")
    assert money(page.inner_text("#cashv")) == 100_000

def test_limit_already_met_fills_now_and_recent_orders_show_type(page):
    open_trade(page)
    page.click('#pf [data-ot="limit"]')
    page.fill("#lpx", "1000")                     # above the market: fills at once at the market price
    page.fill("#qty", "2")
    page.click("#pf [data-s=buy]")
    page.wait_for_selector("#recent li")
    assert "Limit" in page.inner_text("#recent") and "Bought" in page.inner_text("#recent")

def test_stop_loss_is_sell_only_and_locks_shares(page):
    open_trade(page)
    page.click('#pf [data-quick="10"]')
    page.click("#pf [data-s=buy]")                # market buy 10
    page.wait_for_selector("#recent li")
    page.click('#pf [data-ot="stop"]')
    assert page.locator("#pf [data-s=buy]").is_disabled()
    page.fill("#lpx", "100")
    page.fill("#qty", "4")
    page.click("#pf [data-s=sell]")
    page.wait_for_selector("#opens [data-cancel]")
    assert "Stop-loss" in page.inner_text("#opens") and "(4 in open orders)" in page.inner_text("#pf .trade")
