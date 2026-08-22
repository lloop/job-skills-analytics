"""Search and site configuration for job collection."""

from dataclasses import dataclass


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
	listing_ready_selector: str | None = None
	detail_ready_selector: str | None = None
	next_page_selector: str | None = None
	max_pages: int = 5


SEARCH_TERMS = ["Python", "SQL", "Data Analyst"]
LOCATIONS = ["Remote"]
ACTIVE_SITE = "remoteok"
MAX_PAGES = 5
SCROLL_PAUSE_SECONDS = 1.0
REQUEST_TIMEOUT_MS = 30_000
DATABASE_PATH = "jobs.sqlite3"



SITE_CONFIGS = {
	"remoteok": SiteConfig(
		name="Remote OK",
		listing_url="https://remoteok.com/remote-dev-jobs",
		job_link_selector="td.company.position.company_and_position a.preventLink[href]",
		title_selector='h2[itemprop="title"]',
		company_selector='h3[itemprop="name"]',
		salary_selector=".salary, [data-salary]",
		description_selector=".description, [data-description], main",
		listing_ready_selector="tr.job",
		detail_ready_selector="h1, .position h1, [data-job-title]",
	),
}


def get_site_config(site_name: str = ACTIVE_SITE) -> SiteConfig:
	"""Return a configured site profile by name."""
	try:
		return SITE_CONFIGS[site_name]
	except KeyError as error:
		available_sites = ", ".join(sorted(SITE_CONFIGS))
		raise ValueError(f"Unknown site {site_name!r}; available sites: {available_sites}") from error
