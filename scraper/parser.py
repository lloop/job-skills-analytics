"""Parse structured fields from a job posting page."""

from dataclasses import dataclass

from playwright.sync_api import Page

from config import SiteConfig


@dataclass
class JobPosting:
    """Normalized job posting data."""

    title: str
    company: str
    salary: str | None
    description: str
    url: str


def parse_job_posting(page: Page, site: SiteConfig | None = None) -> JobPosting:
    """Extract a posting using a site profile or generic fallback selectors."""
    selectors = site or SiteConfig(
        name="generic",
        listing_url="",
        job_link_selector="a[data-job-link], a.job-link",
        title_selector="[data-job-title], h1",
        company_selector="[data-company], .company",
        salary_selector="[data-salary], .salary",
        description_selector="[data-description], .description, main",
    )
    return JobPosting(
        title=page.locator(selectors.title_selector).first.inner_text().strip(),
        company=page.locator(selectors.company_selector).first.inner_text().strip(),
        salary=_optional_text(page, selectors.salary_selector),
        description=page.locator(selectors.description_selector).first.inner_text().strip(),
        url=page.url,
    )


def _optional_text(page: Page, selector: str) -> str | None:
    locator = page.locator(selector).first
    return locator.inner_text().strip() if locator.count() else None
