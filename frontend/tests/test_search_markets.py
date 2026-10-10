"""Item 2: search by company name with suggestions, and Markets / Browse stocks (offline, from the committed snapshots)."""

def test_company_name_suggests_ticker_and_enter_opens_brief(page):
    page.fill("#t", "nvidia")
    page.wait_for_selector("#ac li[data-i]")
    first = page.locator("#ac li[data-i]").first
    assert first.locator("b").inner_text() == "NVDA" and "NVIDIA" in first.inner_text() and "Technology" in first.inner_text()
    page.press("#t", "Enter")
    page.wait_for_function("document.getElementById('t').value==='NVDA'")
    page.wait_for_selector("#ac", state="hidden")

def test_arrow_keys_pick_a_suggestion(page):
    page.fill("#t", "apple")
    page.wait_for_selector("#ac li[data-i]")
    page.press("#t", "ArrowDown")
    assert page.locator("#ac li.on b").inner_text() == "AAPL"
    page.press("#t", "Escape")
    assert page.locator("#ac").is_hidden()

def test_unknown_text_shows_hint(page):
    page.fill("#t", "qqzzxx")
    page.wait_for_selector("#ac .hint")
    assert "as a ticker" in page.inner_text("#ac")

def test_browse_stocks_groups_by_sector_and_opens_brief(page):
    page.click("#browse")
    page.wait_for_selector("#markets [data-sector]")
    assert page.locator("#markets [data-sector]").count() >= 5
    assert "Saved prices" in page.inner_text("#markets")          # offline -> last snapshot, clearly labelled
    tech = page.locator('#markets [data-sector="technology"]')
    assert tech.locator(".mrow").count() > 0 and "$" in tech.locator(".mrow .mpx").first.inner_text()
    tech.locator('[data-open="AAPL"]').click()
    page.wait_for_selector("#pf .trade button[data-s=buy]:not([disabled])", timeout=30000)
    assert page.locator("#markets").count() == 0

def test_header_markets_button(page):
    page.click("#mkt")
    page.wait_for_selector("#markets .mrow")
    assert page.locator("#markets").get_by_text("Most active").count() == 1
