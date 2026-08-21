"""Scraping pipeline orchestration."""

from collections.abc import Iterable
from urllib.parse import urljoin

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

from config import REQUEST_TIMEOUT_MS, SCROLL_PAUSE_SECONDS
from config import SiteConfig, get_site_config
from .parser import JobPosting, parse_job_posting


def collect_postings(
    page: Page,
    listing_url: str | None = None,
    *,
    max_pages: int | None = None,
    site: SiteConfig | None = None,
) -> Iterable[JobPosting]:
    """Collect unique postings from a configured listing.

    Each iteration is treated as one listing page or dynamically loaded batch. A
    configured next-page control is preferred; otherwise the listing is scrolled
    until it stops producing new links or ``max_pages`` is reached.
    """
    site = site or get_site_config()
    listing_url = listing_url or site.listing_url
    max_pages = max_pages if max_pages is not None else site.max_pages
    if max_pages < 1:
        return

    page.goto(listing_url, wait_until="domcontentloaded", timeout=REQUEST_TIMEOUT_MS)
    _wait_for_selector(page, site.listing_ready_selector)
    seen_urls: set[str] = set()

    for page_number in range(max_pages):
        links_before = _job_urls(page, site)
        for posting_url in links_before:
            if posting_url in seen_urls:
                continue
            seen_urls.add(posting_url)

            detail_page = page.context.new_page()
            try:
                detail_page.goto(
                    posting_url,
                    wait_until="domcontentloaded",
                    timeout=REQUEST_TIMEOUT_MS,
                )
                _wait_for_selector(detail_page, site.detail_ready_selector)
                yield parse_job_posting(detail_page, site)
            finally:
                detail_page.close()

        if page_number + 1 >= max_pages:
            break
        if site.next_page_selector and _go_to_next_page(page, site.next_page_selector):
            _wait_for_selector(page, site.listing_ready_selector)
            continue
        if not _load_more_results(page, site, links_before):
            break


def _job_urls(page: Page, site: SiteConfig) -> list[str]:
    """Return normalized posting URLs currently visible in the listing.

    RemoteOK stores the canonical posting path on each job row's ``data-href``.
    Supporting ``href`` as a fallback keeps profiles for other job boards usable.
    """
    urls: list[str] = []
    for job_element in page.locator(site.job_link_selector).all():
        href = job_element.get_attribute("data-href") or job_element.get_attribute("href")
        if href:
            urls.append(urljoin(page.url, href))
    return list(dict.fromkeys(urls))


def _wait_for_selector(page: Page, selector: str | None) -> None:
    if selector:
        page.locator(selector).first.wait_for(state="attached", timeout=REQUEST_TIMEOUT_MS)


def _go_to_next_page(page: Page, selector: str) -> bool:
    """Click an enabled next-page control, returning whether navigation occurred."""
    next_page = page.locator(selector).first
    if not next_page.count() or not next_page.is_enabled():
        return False
    current_url = page.url
    next_page.click()
    try:
        page.wait_for_url(lambda url: url != current_url, timeout=REQUEST_TIMEOUT_MS)
    except PlaywrightTimeoutError:
        page.wait_for_load_state("domcontentloaded", timeout=REQUEST_TIMEOUT_MS)
    return True


def _load_more_results(page: Page, site: SiteConfig, previous_urls: list[str]) -> bool:
    """Scroll a dynamic listing and report whether new posting links appeared."""
    page.mouse.wheel(0, 5000)
    page.wait_for_timeout(int(SCROLL_PAUSE_SECONDS * 1000))
    try:
        page.wait_for_function(
            """([selector, previousCount]) =>
            document.querySelectorAll(selector).length > previousCount""",
            [site.job_link_selector, len(previous_urls)],
            timeout=REQUEST_TIMEOUT_MS,
        )
    except PlaywrightTimeoutError:
        return False
    return len(_job_urls(page, site)) > len(previous_urls)
