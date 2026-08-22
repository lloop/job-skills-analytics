import unittest
from unittest.mock import MagicMock

from config import SiteConfig
from scraper.parser import JobPosting, _optional_text, parse_job_posting


class TestParser(unittest.TestCase):

    def setUp(self) -> None:
        """Set up mock site config and page fixture."""
        self.site = SiteConfig(
            name="test_site",
            listing_url="https://example.com/jobs",
            job_link_selector="a.job",
            title_selector="h1.title",
            company_selector=".company-name",
            salary_selector=".salary-range",
            description_selector=".job-body",
            tags_selector=".tag-item",
        )

        self.mock_page = MagicMock()
        self.mock_page.url = "https://example.com/job/101"

    def test_parse_job_posting_success_with_site_config(self) -> None:
        """Verify successful extraction of all fields using a custom SiteConfig."""
        # Setup element text mocks for specific selectors
        def locator_side_effect(selector: str) -> MagicMock:
            mock_loc = MagicMock()
            if selector == self.site.title_selector:
                mock_loc.first.inner_text.return_value = "  Senior Python Developer  "
            elif selector == self.site.company_selector:
                mock_loc.first.inner_text.return_value = " Acme Corp "
            elif selector == self.site.salary_selector:
                mock_loc.first.count.return_value = 1
                mock_loc.first.inner_text.return_value = " $130,000 - $160,000 "
            elif selector == self.site.description_selector:
                mock_loc.first.inner_text.return_value = " Building scalable systems. "
            elif selector == self.site.tags_selector:
                mock_loc.all_inner_texts.return_value = [" Python ", " Django ", "Python", "  "]
            return mock_loc

        self.mock_page.locator.side_effect = locator_side_effect

        posting = parse_job_posting(self.mock_page, site=self.site)

        # Assertions
        self.assertIsInstance(posting, JobPosting)
        self.assertEqual(posting.title, "Senior Python Developer")
        self.assertEqual(posting.company, "Acme Corp")
        self.assertEqual(posting.salary, "$130,000 - $160,000")
        self.assertEqual(posting.description, "Building scalable systems.")
        self.assertEqual(posting.url, "https://example.com/job/101")
        # Deduplicated, stripped, empty strings removed
        self.assertEqual(posting.tags, ("Python", "Django"))

    def test_parse_job_posting_fallback_selectors(self) -> None:
        """Verify parse_job_posting falls back to generic selectors when site is None."""
        def locator_side_effect(selector: str) -> MagicMock:
            mock_loc = MagicMock()
            if selector == "[data-job-title], h1":
                mock_loc.first.inner_text.return_value = " Data Engineer "
            elif selector == "[data-company], .company":
                mock_loc.first.inner_text.return_value = " DataCo "
            elif selector == "[data-salary], .salary":
                mock_loc.first.count.return_value = 0  # Salary missing
            elif selector == "[data-description], .description, main":
                mock_loc.first.inner_text.return_value = " ETL Pipelines "
            elif selector == ".action-add-tag h3, .tag h3":
                mock_loc.all_inner_texts.return_value = ["SQL", "Spark"]
            return mock_loc

        self.mock_page.locator.side_effect = locator_side_effect

        posting = parse_job_posting(self.mock_page, site=None)

        self.assertEqual(posting.title, "Data Engineer")
        self.assertEqual(posting.company, "DataCo")
        self.assertIsNone(posting.salary)
        self.assertEqual(posting.tags, ("SQL", "Spark"))

    def test_optional_text_returns_none_when_element_missing(self) -> None:
        """Verify _optional_text returns None if locator count is 0."""
        mock_loc = MagicMock()
        mock_loc.first.count.return_value = 0
        self.mock_page.locator.return_value = mock_loc

        result = _optional_text(self.mock_page, ".missing-salary")
        self.assertIsNone(result)

    def test_optional_text_returns_stripped_str_when_present(self) -> None:
        """Verify _optional_text returns stripped text when element exists."""
        mock_loc = MagicMock()
        mock_loc.first.count.return_value = 1
        mock_loc.first.inner_text.return_value = "  $90k - $110k  "
        self.mock_page.locator.return_value = mock_loc

        result = _optional_text(self.mock_page, ".salary")
        self.assertEqual(result, "$90k - $110k")


if __name__ == "__main__":
    unittest.main()