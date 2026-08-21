"""Run a small RemoteOK scrape from the command line."""

import argparse

from playwright.sync_api import sync_playwright

from config import get_site_config
from scraper.browser import create_browser_context
from scraper.pipeline import collect_postings


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape job postings from RemoteOK")
    parser.add_argument("--max-pages", type=int, default=1)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--headed", action="store_true", help="Show the browser window")
    args = parser.parse_args()

    site = get_site_config("remoteok")
    with sync_playwright() as playwright:
        browser, context = create_browser_context(playwright, headless=not args.headed)
        try:
            page = context.new_page()
            postings = collect_postings(page, site=site, max_pages=args.max_pages)
            for index, posting in enumerate(postings):
                print(f"{index + 1}. {posting.title} | {posting.company}")
                print(f"   URL: {posting.url}")
                if posting.salary:
                    print(f"   Salary: {posting.salary}")
                if index + 1 >= args.limit:
                    break
        finally:
            page.pause()
            context.close()
            browser.close()


if __name__ == "__main__":
    main()