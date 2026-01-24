from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    page = browser.contexts[0].pages[0]

    # 这一句是关键！它会暂停脚本并打开 Playwright Inspector
    page.pause()
