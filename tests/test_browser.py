import unittest
from unittest.mock import MagicMock

from scraper.browser import create_browser_context


class TestBrowser(unittest.TestCase):

    def setUp(self) -> None:
        """Set up Playwright mock objects."""
        self.mock_playwright = MagicMock()
        self.mock_browser = MagicMock()
        self.mock_context = MagicMock()

        # Chain playwright.chromium.launch() -> mock_browser
        self.mock_playwright.chromium.launch.return_value = self.mock_browser
        # Chain browser.new_context() -> mock_context
        self.mock_browser.new_context.return_value = self.mock_context

    def test_create_browser_context_default_headless(self) -> None:
        """Verify browser launches headless by default and returns browser + context."""
        browser, context = create_browser_context(self.mock_playwright)

        # Assertions
        self.assertEqual(browser, self.mock_browser)
        self.assertEqual(context, self.mock_context)
        self.mock_playwright.chromium.launch.assert_called_once_with(headless=True)
        self.mock_browser.new_context.assert_called_once()

    def test_create_browser_context_headed_mode(self) -> None:
        """Verify headless=False flag is passed down when specified."""
        browser, context = create_browser_context(self.mock_playwright, headless=False)

        self.assertEqual(browser, self.mock_browser)
        self.assertEqual(context, self.mock_context)
        self.mock_playwright.chromium.launch.assert_called_once_with(headless=False)
        self.mock_browser.new_context.assert_called_once()


if __name__ == "__main__":
    unittest.main()