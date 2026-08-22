"""Run a small scrape from the command line."""

import argparse
from playwright.sync_api import sync_playwright

from config import DATABASE_PATH, get_site_config
from scraper.browser import create_browser_context
from scraper.pipeline import collect_postings
from scraper.storage import save_postings


def main() -> None:
    site = get_site_config("remoteok")

    parser = argparse.ArgumentParser(description="Scrape job postings")
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help=f"Max listing pages to crawl (default: site config = {site.max_pages})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Max total postings to collect before stopping (default: 5)",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Show the browser window (default: headless)",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default=DATABASE_PATH,
        help="Path to SQLite database",
    )
    args = parser.parse_args()

    # If --max-pages was not explicitly provided on CLI, fall back to site config value
    max_pages = args.max_pages if args.max_pages is not None else site.max_pages

    with sync_playwright() as playwright:
        browser, context = create_browser_context(playwright, headless=not args.headed)
        try:
            page = context.new_page()
            postings_generator = collect_postings(
                page, site=site, max_pages=max_pages
            )

            postings_to_save = []
            try:
                for index, posting in enumerate(postings_generator):
                    postings_to_save.append(posting)
                    if index + 1 >= args.limit:
                        break
            finally:
                # Forces detail_page.close() to run while Playwright is active
                postings_generator.close()

            saved_count = save_postings(postings_to_save, db_path=args.db_path)
            print(
                f"Successfully processed {len(postings_to_save)} postings. "
                f"Inserted {saved_count} new entries to {args.db_path}."
            )

        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    main()