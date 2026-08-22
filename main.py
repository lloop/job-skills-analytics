"""Run a small scrape from the command line."""

import argparse
from playwright.sync_api import sync_playwright
from config import DATABASE_PATH, get_site_config
from scraper.browser import create_browser_context
from scraper.pipeline import collect_postings
from scraper.storage import save_postings


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape job postings")
    parser.add_argument("--max-pages", type=int, default=1)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--headed", action="store_true", help="Show the browser window")
    # parser.add_argument("--db-path", type=str, default="jobs.db", help="Path to SQLite database")
    parser.add_argument(
        "--db-path", 
        type=str, 
        default=DATABASE_PATH, 
        help="Path to SQLite database"
    )
    args = parser.parse_args()

    site = get_site_config("remoteok")
    with sync_playwright() as playwright:
        browser, context = create_browser_context(playwright, headless=not args.headed)
        try:
            page = context.new_page()           
            postings_generator = collect_postings(page, site=site, max_pages=args.max_pages)
            
            # Pull postings up to the specified limit
            postings_to_save = []
            for index, posting in enumerate(postings_generator):
                postings_to_save.append(posting)
                if index + 1 >= args.limit:
                    break

            # --- PRINT LOGIC COMMENTED OUT ---
            # for index, posting in enumerate(postings):
            #     print(f"{index + 1}. {posting.title} | {posting.company}")
            #     print(f"   URL: {posting.url}")
            #     print(f"   TAGS: {posting.tags}")
            #     if posting.salary:
            #         print(f"   Salary: {posting.salary}")
            #     if index + 1 >= args.limit:
            #         break

            # Save collected postings and tags to SQLite
            saved_count = save_postings(postings_to_save, db_path=args.db_path)
            print(f"Successfully processed {len(postings_to_save)} postings. Inserted {saved_count} new entries to {args.db_path}.")

        finally:
            # page.pause()
            context.close()
            browser.close()


if __name__ == "__main__":
    main()