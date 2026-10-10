"""Item 4: Crypto tab, price-only crypto brief and fractional paper trading (offline stack, demo snapshots)."""

def test_crypto_tab_lists_coins_and_opens_a_brief_without_risks(page):
    page.click("#cry")
    page.wait_for_selector('#crypto [data-open="BTC-USD"]')
    assert "Saved prices" in page.inner_text("#crypto")             # offline: last snapshot, clearly labelled
    page.click('#crypto [data-open="BTC-USD"]')
    page.wait_for_selector("#pf .trade button[data-s=buy]:not([disabled])", timeout=30000)
    main = page.inner_text("#main")
    assert "Cryptocurrency · trades 24/7" in main and "1-year return" in main
    assert "Key risks" not in main and "no risk section" in main and "P/E" not in main

def test_search_by_coin_name(page):
    page.fill("#t", "bitcoin")
    page.wait_for_selector("#ac li[data-i]")
    assert page.locator("#ac li[data-i]").first.locator("b").inner_text() == "BTC-USD"
    page.press("#t", "Enter")
    page.wait_for_function("document.getElementById('t').value==='BTC-USD'")

def test_fractional_crypto_buy(page):
    page.fill("#t", "ETH-USD")
    page.press("#t", "Enter")
    page.wait_for_selector("#pf .trade button[data-s=buy]:not([disabled])", timeout=30000)
    assert page.locator('#pf [data-quick="0.1"]').count() == 1 and page.locator('#pf [data-quick="10"]').count() == 0
    page.click('#pf [data-quick="0.5"]')
    assert page.input_value("#qty") == "0.5"
    page.click('#pf [data-q="1"]')
    assert page.input_value("#qty") == "0.51"
    page.click("#pf [data-s=buy]")
    page.wait_for_selector("#recent li")
    assert "0.51 ETH-USD" in page.inner_text("#recent")
    assert "0.51" in page.inner_text("#pf table")
