"""Playwright browser context initialization."""

from playwright.sync_api import BrowserContext, Playwright


def create_browser_context(playwright: Playwright, *, headless: bool = True) -> tuple[object, BrowserContext]:
    """Launch Chromium and return the browser plus an isolated context."""
    browser = playwright.chromium.launch(headless=headless)
    context = browser.new_context()
    return browser, context
