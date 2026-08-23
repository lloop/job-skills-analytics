"""Search and site configuration for job collection."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SiteConfig:
    """Selectors and collection rules for one job board."""

    name: str
    listing_url: str
    job_link_selector: str
    title_selector: str
    company_selector: str
    salary_selector: str
    description_selector: str
    tags_selector: str
    listing_ready_selector: str | None = None
    detail_ready_selector: str | None = None
    next_page_selector: str | None = None
    max_pages: int = 5


# Project root directory (assumes config.py lives in the project root).
BASE_DIR = Path(__file__).parent.resolve()

SEARCH_TERMS = ["Python", "SQL", "Data Analyst"]
LOCATIONS = ["Remote"]
ACTIVE_SITE = "remoteok"
SCROLL_PAUSE_SECONDS = 1.0
REQUEST_TIMEOUT_MS = 30_000
DATABASE_PATH = str(BASE_DIR / "output" / "jobs.sqlite3")

SITE_CONFIGS = {
    "remoteok": SiteConfig(
        name="Remote OK",
        listing_url="https://remoteok.com/remote-dev-jobs",
        job_link_selector="tr.job[data-href]",
        title_selector='h2[itemprop="title"]',
        company_selector='h3[itemprop="name"]',
        salary_selector=".salary, [data-salary]",
        description_selector=".description, [data-description], main",
        tags_selector=".action-add-tag h3, .tag h3",
        listing_ready_selector="tr.job[data-href]",
        detail_ready_selector="h1, .position h1, [data-job-title]",
    ),
}


def get_site_config(site_name: str = ACTIVE_SITE) -> SiteConfig:
    """Return a configured site profile by name."""
    try:
        return SITE_CONFIGS[site_name]
    except KeyError as error:
        available_sites = ", ".join(sorted(SITE_CONFIGS))
        raise ValueError(
            f"Unknown site {site_name!r}; available sites: {available_sites}"
        ) from error
