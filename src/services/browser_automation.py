"""
Browser Automation Service
Provides browser control capabilities using Playwright for cross-platform automation.
Supports navigation, element interaction, and data extraction.
"""

import asyncio
import base64
import logging
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


class BrowserAutomationService:
    """
    Browser automation service using Playwright.
    Provides high-level API for browser control via voice commands.
    """

    def __init__(self, headless: bool = False, browser_type: str = "chromium"):
        """
        Initialize browser automation service.

        Args:
            headless: Run browser in headless mode (no UI)
            browser_type: Browser to use (chromium, firefox, webkit)
        """
        self.headless = headless
        self.browser_type = browser_type
        self.browser = None
        self.page = None
        self.context = None
        self.playwright = None
        self._initialized = False

        logger.info(f"BrowserAutomationService initialized (headless={headless}, browser={browser_type})")

    async def initialize(self):
        """Initialize Playwright and launch browser."""
        if self._initialized:
            return

        try:
            from playwright.async_api import async_playwright

            self.playwright = await async_playwright().start()

            # Select browser type
            if self.browser_type == "firefox":
                browser_engine = self.playwright.firefox
            elif self.browser_type == "webkit":
                browser_engine = self.playwright.webkit
            else:
                browser_engine = self.playwright.chromium

            # Launch browser
            self.browser = await browser_engine.launch(
                headless=self.headless,
                args=['--start-maximized'] if not self.headless else []
            )

            # Create context
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080} if self.headless else None
            )

            # Create page
            self.page = await self.context.new_page()

            self._initialized = True
            logger.info("Browser automation initialized successfully")

        except ImportError:
            logger.error("Playwright not installed. Install with: pip install playwright && playwright install")
            raise RuntimeError("Playwright library not available. Install with: pip install playwright")
        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            raise

    async def close(self):
        """Close browser and cleanup resources."""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()

            self._initialized = False
            logger.info("Browser automation closed")
        except Exception as e:
            logger.error(f"Error closing browser: {e}")

    async def navigate(self, url: str, wait_until: str = "domcontentloaded") -> Dict[str, Any]:
        """
        Navigate to a URL.

        Args:
            url: URL to navigate to
            wait_until: When to consider navigation complete
                       (load, domcontentloaded, networkidle)

        Returns:
            Dict with status and page info
        """
        if not self._initialized:
            await self.initialize()

        try:
            # Ensure URL has protocol
            if not url.startswith(('http://', 'https://')):
                url = f"https://{url}"

            response = await self.page.goto(url, wait_until=wait_until, timeout=30000)
            title = await self.page.title()

            logger.info(f"Navigated to {url}")

            return {
                "success": True,
                "url": url,
                "title": title,
                "status": response.status if response else None
            }
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "url": url
            }

    async def click(self, selector: str, timeout: int = 5000) -> Dict[str, Any]:
        """
        Click an element on the page.

        Args:
            selector: CSS selector or text selector
            timeout: Maximum time to wait for element (ms)

        Returns:
            Dict with success status
        """
        if not self._initialized:
            await self.initialize()

        try:
            await self.page.click(selector, timeout=timeout)
            logger.info(f"Clicked element: {selector}")

            return {
                "success": True,
                "selector": selector
            }
        except Exception as e:
            logger.error(f"Click failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "selector": selector
            }

    async def type_text(self, selector: str, text: str, delay: int = 50) -> Dict[str, Any]:
        """
        Type text into an input field.

        Args:
            selector: CSS selector for input element
            text: Text to type
            delay: Delay between keystrokes (ms)

        Returns:
            Dict with success status
        """
        if not self._initialized:
            await self.initialize()

        try:
            await self.page.fill(selector, text)
            logger.info(f"Typed text into: {selector}")

            return {
                "success": True,
                "selector": selector,
                "text_length": len(text)
            }
        except Exception as e:
            logger.error(f"Type text failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "selector": selector
            }

    async def extract_text(self, selector: str) -> Dict[str, Any]:
        """
        Extract text from an element.

        Args:
            selector: CSS selector for element

        Returns:
            Dict with extracted text
        """
        if not self._initialized:
            await self.initialize()

        try:
            text = await self.page.text_content(selector)
            logger.info(f"Extracted text from: {selector}")

            return {
                "success": True,
                "selector": selector,
                "text": text
            }
        except Exception as e:
            logger.error(f"Extract text failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "selector": selector
            }

    async def screenshot(
        self,
        path: Optional[str] = None,
        full_page: bool = False
    ) -> Dict[str, Any]:
        """
        Take a screenshot of the current page.

        Args:
            path: File path to save screenshot (optional)
            full_page: Capture full scrollable page

        Returns:
            Dict with screenshot data (base64 if no path)
        """
        if not self._initialized:
            await self.initialize()

        try:
            if path:
                await self.page.screenshot(path=path, full_page=full_page)
                logger.info(f"Screenshot saved to: {path}")

                return {
                    "success": True,
                    "path": path,
                    "full_page": full_page
                }
            else:
                # Return base64 encoded screenshot
                screenshot_bytes = await self.page.screenshot(full_page=full_page)
                screenshot_b64 = base64.b64encode(screenshot_bytes).decode()

                logger.info("Screenshot captured (base64)")

                return {
                    "success": True,
                    "screenshot": screenshot_b64,
                    "full_page": full_page
                }
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def wait_for_selector(
        self,
        selector: str,
        timeout: int = 10000,
        state: str = "visible"
    ) -> Dict[str, Any]:
        """
        Wait for an element to appear.

        Args:
            selector: CSS selector
            timeout: Maximum wait time (ms)
            state: Element state (visible, hidden, attached, detached)

        Returns:
            Dict with success status
        """
        if not self._initialized:
            await self.initialize()

        try:
            await self.page.wait_for_selector(selector, timeout=timeout, state=state)
            logger.info(f"Element found: {selector}")

            return {
                "success": True,
                "selector": selector,
                "state": state
            }
        except Exception as e:
            logger.error(f"Wait for selector failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "selector": selector
            }

    async def get_page_content(self) -> Dict[str, Any]:
        """
        Get the current page HTML content.

        Returns:
            Dict with page content and metadata
        """
        if not self._initialized:
            await self.initialize()

        try:
            content = await self.page.content()
            title = await self.page.title()
            url = self.page.url

            return {
                "success": True,
                "content": content,
                "title": title,
                "url": url,
                "content_length": len(content)
            }
        except Exception as e:
            logger.error(f"Get page content failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def search_google(self, query: str) -> Dict[str, Any]:
        """
        Perform a Google search.

        Args:
            query: Search query

        Returns:
            Dict with search results
        """
        try:
            # Navigate to Google
            await self.navigate("https://www.google.com")

            # Wait for search box
            await self.wait_for_selector('textarea[name="q"]', timeout=5000)

            # Type query
            await self.type_text('textarea[name="q"]', query)

            # Press Enter
            await self.page.keyboard.press("Enter")

            # Wait for results
            await self.wait_for_selector("#search", timeout=10000)

            # Get page title
            title = await self.page.title()

            logger.info(f"Google search completed: {query}")

            return {
                "success": True,
                "query": query,
                "title": title,
                "url": self.page.url
            }
        except Exception as e:
            logger.error(f"Google search failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "query": query
            }

    async def open_gmail(self) -> Dict[str, Any]:
        """
        Open Gmail in browser.

        Returns:
            Dict with success status
        """
        try:
            result = await self.navigate("https://mail.google.com")

            if result["success"]:
                # Wait for Gmail to load
                await asyncio.sleep(2)
                logger.info("Gmail opened")

            return result
        except Exception as e:
            logger.error(f"Failed to open Gmail: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def open_google_drive(self) -> Dict[str, Any]:
        """
        Open Google Drive in browser.

        Returns:
            Dict with success status
        """
        try:
            result = await self.navigate("https://drive.google.com")

            if result["success"]:
                # Wait for Drive to load
                await asyncio.sleep(2)
                logger.info("Google Drive opened")

            return result
        except Exception as e:
            logger.error(f"Failed to open Google Drive: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Singleton instance for reuse
_browser_service: Optional[BrowserAutomationService] = None


def get_browser_service(
    headless: bool = False,
    browser_type: str = "chromium"
) -> BrowserAutomationService:
    """
    Get or create browser automation service instance.

    Args:
        headless: Run in headless mode
        browser_type: Browser type (chromium, firefox, webkit)

    Returns:
        BrowserAutomationService instance
    """
    global _browser_service

    if _browser_service is None:
        _browser_service = BrowserAutomationService(
            headless=headless,
            browser_type=browser_type
        )

    return _browser_service
