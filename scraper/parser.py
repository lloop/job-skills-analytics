"""Parse structured fields from a job posting page."""

from dataclasses import dataclass

from playwright.sync_api import Page


@dataclass
class JobPosting:
    """Normalized job posting data."""

    title: str
    company: str
    salary: str | None
    description: str
    url: str


def parse_job_posting(page: Page) -> JobPosting:
    """Extract a posting from the current page.

    Selectors are intentionally kept local so they can be adapted to a target job board.
    """
    return JobPosting(
        title=page.locator("[data-job-title], h1").first.inner_text().strip(),
        company=page.locator("[data-company], .company").first.inner_text().strip(),
        salary=_optional_text(page, "[data-salary], .salary"),
        description=page.locator("[data-description], .description, main").first.inner_text().strip(),
        url=page.url,
    )


def _optional_text(page: Page, selector: str) -> str | None:
    locator = page.locator(selector).first
    return locator.inner_text().strip() if locator.count() else None
