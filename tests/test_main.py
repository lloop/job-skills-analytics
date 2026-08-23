import unittest
from unittest.mock import MagicMock, patch

import main


class TestMain(unittest.TestCase):

    @patch("main.save_postings")
    @patch("main.collect_postings")
    @patch("main.create_browser_context")
    @patch("main.sync_playwright")
    @patch("main.get_site_config")
    def test_main_successful_execution(
        self,
        mock_get_site_config: MagicMock,
        mock_sync_playwright: MagicMock,
        mock_create_browser: MagicMock,
        mock_collect_postings: MagicMock,
        mock_save_postings: MagicMock,
    ) -> None:
        """Verify main() sets up playwright, collects postings up to limit, and saves them."""
        # 1. Setup CLI args mock
        test_args = ["main.py", "--limit", "2", "--max-pages", "1"]

        # 2. Setup mock generator and objects
        mock_playwright = MagicMock()
        mock_sync_playwright.return_value.__enter__.return_value = mock_playwright

        mock_browser = MagicMock()
        mock_context = MagicMock()
        mock_create_browser.return_value = (mock_browser, mock_context)

        # Mock generator returning items
        mock_posting_1 = MagicMock(title="Job 1")
        mock_posting_2 = MagicMock(title="Job 2")
        mock_gen = MagicMock()
        mock_gen.__iter__.return_value = iter([mock_posting_1, mock_posting_2])
        mock_collect_postings.return_value = mock_gen

        mock_save_postings.return_value = 2

        # 3. Execute main with patched sys.argv
        with patch("sys.argv", test_args):
            main.main()

        # 4. Assertions
        mock_get_site_config.assert_called_once_with("remoteok")
        mock_create_browser.assert_called_once_with(mock_playwright, headless=True)
        mock_save_postings.assert_called_once()
        
        # Verify browser and generator context cleanups
        mock_gen.close.assert_called_once()
        mock_context.close.assert_called_once()
        mock_browser.close.assert_called_once()

    @patch("main.save_postings")
    @patch("main.collect_postings")
    @patch("main.create_browser_context")
    @patch("main.sync_playwright")
    def test_main_headed_flag_passed_to_browser(
        self,
        mock_sync_playwright: MagicMock,
        mock_create_browser: MagicMock,
        mock_collect_postings: MagicMock,
        mock_save_postings: MagicMock,
    ) -> None:
        """Verify passing --headed disables headless mode in create_browser_context."""
        test_args = ["main.py", "--headed"]

        mock_playwright = MagicMock()
        mock_sync_playwright.return_value.__enter__.return_value = mock_playwright
        mock_create_browser.return_value = (MagicMock(), MagicMock())
        
        mock_gen = MagicMock()
        mock_gen.__iter__.return_value = iter([])
        mock_collect_postings.return_value = mock_gen

        with patch("sys.argv", test_args):
            main.main()

        mock_create_browser.assert_called_once_with(mock_playwright, headless=False)

    @patch("main.save_postings")
    @patch("main.collect_postings")
    @patch("main.create_browser_context")
    @patch("main.sync_playwright")
    def test_main_closes_generator_even_on_exception(
        self,
        mock_sync_playwright: MagicMock,
        mock_create_browser: MagicMock,
        mock_collect_postings: MagicMock,
        mock_save_postings: MagicMock,
    ) -> None:
        """Verify generator close() is executed in finally block if loop raises exception."""
        test_args = ["main.py"]

        mock_playwright = MagicMock()
        mock_sync_playwright.return_value.__enter__.return_value = mock_playwright
        mock_create_browser.return_value = (MagicMock(), MagicMock())

        # Generator raises error during iteration
        mock_gen = MagicMock()
        mock_gen.__iter__.side_effect = Exception("Scraping loop failed")
        mock_collect_postings.return_value = mock_gen

        with patch("sys.argv", test_args):
            with self.assertRaisesRegex(Exception, "Scraping loop failed"):
                main.main()

        # Ensure generator was still explicitly closed before browser context closed
        mock_gen.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()