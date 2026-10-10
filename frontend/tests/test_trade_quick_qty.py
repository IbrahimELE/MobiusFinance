"""Item 1: quick amount buttons (10/20/50/100/Max) in the Trade panel."""
import re

def money(s):
    return float(re.sub(r"[^0-9.\-]", "", s))

def open_trade(page, ticker="AAPL"):
    page.fill("#t", ticker)
    page.press("#t", "Enter")
    page.wait_for_selector("#pf .trade button[data-s=buy]:not([disabled])", timeout=30000)

def test_quick_buttons_set_qty_and_update_preview(page):
    open_trade(page)
    for n in (10, 20, 50, 100):
        page.click(f'#pf [data-quick="{n}"]')
        assert page.input_value("#qty") == str(n)
        assert page.locator(f'#pf [data-quick="{n}"]').get_attribute("class") == "on"
        assert f"Buying {n} costs" in page.inner_text("#pv")

def test_max_buys_most_affordable_whole_shares(page):
    open_trade(page)
    page.click('#pf [data-quick="max"]')
    q = int(page.input_value("#qty"))
    pv = page.inner_text("#pv")
    cost, after = (money(x) for x in re.findall(r"\$[\d,]+\.\d+", pv)[:2])
    price = cost / q
    assert q > 0 and after >= 0 and after < price + 0.01, pv   # one more share would not fit
    assert "on" in page.locator('#pf [data-quick="max"]').get_attribute("class")

def test_typed_qty_still_works_and_clears_highlight(page):
    open_trade(page)
    page.click('#pf [data-quick="20"]')
    page.fill("#qty", "7")
    assert "Buying 7 costs" in page.inner_text("#pv")
    assert page.locator("#pf .quick .on").count() == 0
