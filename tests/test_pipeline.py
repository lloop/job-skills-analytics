import unittest
from unittest.mock import MagicMock, call, patch

from config import SiteConfig
from scraper.parser import JobPosting
from scraper.pipeline import _job_urls, collect_postings


class TestPipeline(unittest.TestCase):

    def setUp(self) -> None:
        """Set up site config mock and mock objects for page and context."""
        self.site = SiteConfig(
            name="test_site",
            listing_url="https://example.com/jobs",
            job_link_selector="tr.job[data-href]",
            title_selector="h1",
            company_selector=".company",
            salary_selector=".salary",
            description_selector=".description",
            listing_ready_selector="tr.job",
            detail_ready_selector="h1",
            tags_selector=".action-add-tag h3, .tag h3"
        )

        # Mock Page and Context
        self.mock_page = MagicMock()
        self.mock_context = MagicMock()
        self.mock_detail_page = MagicMock()

        # Connect page to mock context
        self.mock_page.context = self.mock_context
        self.mock_context.new_page.return_value = self.mock_detail_page
        self.mock_page.url = "https://example.com/jobs"

    def test_collect_postings_max_pages_zero(self) -> None:
        """Verify collect_postings yields nothing if max_pages < 1."""
        gen = collect_postings(self.mock_page, site=self.site, max_pages=0)
        results = list(gen)

        self.assertEqual(results, [])
        self.mock_page.goto.assert_not_called()

    def test_job_urls_extraction(self) -> None:
        """Verify _job_urls extracts and normalizes URLs from elements."""
        mock_el1 = MagicMock()
        mock_el1.get_attribute.return_value = "/job/1"

        mock_el2 = MagicMock()
        mock_el2.get_attribute.return_value = "/job/2"

        # Mock locator.all()
        self.mock_page.locator.return_value.all.return_value = [mock_el1, mock_el2]

        urls = _job_urls(self.mock_page, self.site)

        self.assertEqual(
            urls,
            ["https://example.com/job/1", "https://example.com/job/2"],
        )

    @patch("scraper.pipeline.parse_job_posting")
    @patch("scraper.pipeline._job_urls")
    @patch("scraper.pipeline._wait_for_selector")
    def test_collect_postings_success(
        self,
        mock_wait: MagicMock,
        mock_job_urls: MagicMock,
        mock_parse: MagicMock,
    ) -> None:
        """Verify collect_postings navigates, parses job pages, and closes detail pages."""
        mock_job_urls.return_value = ["https://example.com/job/1"]

        parsed_posting = JobPosting(
            title="Backend Engineer",
            company="TestCo",
            salary="$100k",
            description="Build APIs",
            url="https://example.com/job/1",
            tags=("python", "fastapi"),
        )
        mock_parse.return_value = parsed_posting

        gen = collect_postings(self.mock_page, site=self.site, max_pages=1)
        results = list(gen)

        # Assertions
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "Backend Engineer")

        # Verify page navigation
        self.mock_page.goto.assert_called_once_with(
            "https://example.com/jobs",
            wait_until="domcontentloaded",
            timeout=unittest.mock.ANY,
        )

        # Verify detail page navigation & closure
        self.mock_detail_page.goto.assert_called_once_with(
            "https://example.com/job/1",
            wait_until="domcontentloaded",
            timeout=unittest.mock.ANY,
        )
        self.mock_detail_page.close.assert_called_once()

    @patch("builtins.print")
    @patch("scraper.pipeline.parse_job_posting")
    @patch("scraper.pipeline._job_urls")
    @patch("scraper.pipeline._wait_for_selector")
    def test_collect_postings_handles_exception_gracefully(
        self,
        mock_wait: MagicMock,
        mock_job_urls: MagicMock,
        mock_parse: MagicMock,
        mock_print: MagicMock,
    ) -> None:
        """Verify collect_postings handles detail page errors without breaking the loop."""
        mock_job_urls.return_value = ["https://example.com/job/error"]
        self.mock_detail_page.goto.side_effect = Exception("Network Error")

        gen = collect_postings(self.mock_page, site=self.site, max_pages=1)
        results = list(gen)

        # Should yield 0 items due to exception, but close the page properly
        self.assertEqual(results, [])
        self.mock_detail_page.close.assert_called_once()
        mock_print.assert_called_once()
        
        
if __name__ == "__main__":
    unittest.main()