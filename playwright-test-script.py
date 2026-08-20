import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        # Launch headless Chromium
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Navigate to target page
        print("Navigating to target page...")
        await page.goto("https://quotes.toscrape.com/js/")

        # Wait for dynamic JS content to load
        await page.wait_for_selector(".quote")

        # Extract items from DOM
        quotes = await page.query_selector_all(".quote")
        print(f"Successfully scraped {len(quotes)} dynamic elements!")

        for quote in quotes[:3]:
            text = await quote.query_selector(".text")
            print("-", await text.inner_text())

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())