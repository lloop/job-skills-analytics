"""Scraping pipeline orchestration."""

from collections.abc import Iterable

from playwright.sync_api import Page

from .parser import JobPosting, parse_job_posting


def collect_postings(page: Page, listing_url: str, *, max_pages: int = 5) -> Iterable[JobPosting]:
    """Navigate listings, load additional results, and parse posting pages.

    Listing and detail-page selectors are placeholders for the selected job board.
    """
    page.goto(listing_url)
    for _ in range(max_pages):
        for link in page.locator("a[data-job-link], a.job-link").all():
            detail_page = page.context.new_page()
            try:
                detail_page.goto(link.get_attribute("href") or "")
                yield parse_job_posting(detail_page)
            finally:
                detail_page.close()
        page.mouse.wheel(0, 5000)
