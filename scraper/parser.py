"""Parse structured fields from a job posting page."""

from dataclasses import dataclass
from playwright.sync_api import Page
from config import SiteConfig
from playwright.sync_api import Locator, Page
from models import JobPosting

# @dataclass
# class JobPosting:
#     """Normalized job posting data."""

#     title: str
#     company: str
#     salary: str | None
#     description: str
#     url: str
#     tags: tuple[str, ...] = ()


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
        tags_selector=".action-add-tag h3, .tag h3",
    )

    # Extract tags directly using the selector
    tags_selector = getattr(selectors, "tags_selector", ".action-add-tag h3, .tag h3")
    raw_tags = page.locator(tags_selector).all_inner_texts()
    cleaned_tags = tuple(dict.fromkeys(t.strip() for t in raw_tags if t.strip()))

    return JobPosting(
        title=page.locator(selectors.title_selector).first.inner_text().strip(),
        company=page.locator(selectors.company_selector).first.inner_text().strip(),
        salary=_optional_text(page, selectors.salary_selector),
        description=page.locator(selectors.description_selector).first.inner_text().strip(),
        url=page.url,
        tags=cleaned_tags,
    )

def _optional_text(page: Page, selector: str) -> str | None:
    locator = page.locator(selector).first
    return locator.inner_text().strip() if locator.count() else None


# def extract_job_tags(context: Page | Locator) -> tuple[str, ...]:
#     """Extract tag strings from elements matching `.action-add-tag h3` or `.tag h3`.

#     Works on either a full `page` or a scoped row `locator`.
#     """
#     tag_elements = context.locator(".action-add-tag h3, .tag h3").all()

#     tags: list[str] = []
#     for el in tag_elements:
#         text = el.inner_text().strip()
#         if text:
#             tags.append(text)

#     # Deduplicate while preserving order
#     return tuple(dict.fromkeys(tags))
