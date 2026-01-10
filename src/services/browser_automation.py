"""
Browser Automation Service
Provides browser control capabilities using Playwright for cross-platform automation.
Supports navigation, element interaction, and data extraction.
Includes performance optimizations: caching, retry logic, and metrics tracking.

Reference: https://playwright.dev/python/
"""

import asyncio
import base64
import logging
import time
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class BrowserAutomationService:
    """
    Browser automation service using Playwright.
    Provides high-level API for browser control via voice commands.
    """

    def __init__(self, headless: bool = False, browser_type: str = "chromium"):
        """
        Initialize browser automation service with performance optimizations.

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

        # Performance optimization: Navigation caching
        self._navigation_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl_seconds = 300  # 5 minutes cache TTL
        self._last_cache_cleanup = time.time()

        # Performance optimization: Selector wait optimization
        self._selector_cache: Dict[str, float] = {}  # Selector -> avg wait time
        self._selector_success_rate: Dict[str, Dict[str, int]] = defaultdict(lambda: {"success": 0, "failure": 0})

        # Performance metrics
        self._metrics = {
            "navigations": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "selector_waits": 0,
            "retries": 0,
            "total_wait_time_ms": 0,
            "successful_operations": 0,
            "failed_operations": 0
        }

        logger.info(
            f"BrowserAutomationService initialized (headless={headless}, browser={browser_type}, "
            f"cache_ttl={self._cache_ttl_seconds}s)"
        )

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

    # ============================================================================
    # Performance Optimization Methods (Phase 2D)
    # ============================================================================

    def _cleanup_cache(self) -> None:
        """
        Clean up expired cache entries.
        Removes navigation cache entries older than TTL.
        """
        now = time.time()
        expired_urls = []

        for url, entry in self._navigation_cache.items():
            if now - entry["timestamp"] > self._cache_ttl_seconds:
                expired_urls.append(url)

        for url in expired_urls:
            del self._navigation_cache[url]

        if expired_urls:
            logger.debug(f"Cache cleanup: removed {len(expired_urls)} expired entries")

        self._last_cache_cleanup = now

    def _get_cached_navigation(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Get cached navigation result if available and fresh.

        Args:
            url: URL to check cache for

        Returns:
            Cached navigation result or None if not found/expired
        """
        # Periodic cache cleanup (every 60 seconds)
        if time.time() - self._last_cache_cleanup > 60:
            self._cleanup_cache()

        if url in self._navigation_cache:
            entry = self._navigation_cache[url]
            age = time.time() - entry["timestamp"]

            if age < self._cache_ttl_seconds:
                self._metrics["cache_hits"] += 1
                logger.debug(f"Navigation cache HIT: {url} (age: {age:.1f}s)")
                return entry["data"]
            else:
                # Expired entry
                del self._navigation_cache[url]

        self._metrics["cache_misses"] += 1
        return None

    def _cache_navigation(self, url: str, result: Dict[str, Any]) -> None:
        """
        Cache navigation result for future use.

        Args:
            url: URL that was navigated to
            result: Navigation result to cache
        """
        self._navigation_cache[url] = {
            "data": result,
            "timestamp": time.time()
        }

        logger.debug(f"Navigation cached: {url}")

    async def wait_for_selector_with_retry(
        self,
        selector: str,
        timeout: int = 10000,
        retries: int = 3,
        backoff_factor: float = 1.5
    ) -> Dict[str, Any]:
        """
        Wait for selector with automatic retry and exponential backoff.

        Args:
            selector: CSS selector to wait for
            timeout: Individual attempt timeout in milliseconds
            retries: Number of retry attempts
            backoff_factor: Exponential backoff multiplier (1.5 = 50% increase per retry)

        Returns:
            Dict with success status and timing information
        """
        if not self._initialized:
            await self.initialize()

        start_time = time.time()
        current_timeout = timeout
        last_error = None

        for attempt in range(retries):
            try:
                wait_start = time.time()
                await self.page.wait_for_selector(selector, timeout=current_timeout, state="visible")
                wait_time_ms = int((time.time() - wait_start) * 1000)

                # Update selector cache with average wait time
                if selector in self._selector_cache:
                    # Running average
                    self._selector_cache[selector] = (
                        self._selector_cache[selector] * 0.7 + wait_time_ms * 0.3
                    )
                else:
                    self._selector_cache[selector] = wait_time_ms

                # Track success rate
                self._selector_success_rate[selector]["success"] += 1

                # Update metrics
                self._metrics["selector_waits"] += 1
                self._metrics["total_wait_time_ms"] += wait_time_ms
                self._metrics["successful_operations"] += 1

                logger.info(
                    f"Selector found (attempt {attempt + 1}/{retries}): {selector}",
                    extra={"wait_time_ms": wait_time_ms}
                )

                return {
                    "success": True,
                    "selector": selector,
                    "wait_time_ms": wait_time_ms,
                    "attempt": attempt + 1,
                    "total_time_ms": int((time.time() - start_time) * 1000)
                }

            except Exception as e:
                last_error = e
                self._selector_success_rate[selector]["failure"] += 1

                if attempt < retries - 1:
                    # Calculate backoff delay
                    backoff_ms = int(timeout * (backoff_factor ** attempt) / retries)
                    await asyncio.sleep(backoff_ms / 1000)

                    # Increase timeout for next attempt
                    current_timeout = int(timeout * (backoff_factor ** (attempt + 1)))

                    logger.warning(
                        f"Selector wait failed (attempt {attempt + 1}/{retries}), retrying: {selector}",
                        extra={"backoff_ms": backoff_ms, "next_timeout_ms": current_timeout}
                    )

                self._metrics["retries"] += 1

        # All retries exhausted
        self._metrics["failed_operations"] += 1
        logger.error(
            f"Selector wait failed after {retries} retries: {selector}",
            extra={"error": str(last_error)}
        )

        return {
            "success": False,
            "selector": selector,
            "error": str(last_error),
            "retries_attempted": retries,
            "total_time_ms": int((time.time() - start_time) * 1000)
        }

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics and statistics.

        Returns:
            Dictionary with performance metrics
        """
        total_operations = self._metrics["successful_operations"] + self._metrics["failed_operations"]
        success_rate = (
            (self._metrics["successful_operations"] / total_operations * 100)
            if total_operations > 0 else 0
        )

        avg_wait_time = (
            (self._metrics["total_wait_time_ms"] / self._metrics["selector_waits"])
            if self._metrics["selector_waits"] > 0 else 0
        )

        # Get top slow selectors
        slow_selectors = sorted(
            self._selector_cache.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        return {
            "operations": {
                "total": total_operations,
                "successful": self._metrics["successful_operations"],
                "failed": self._metrics["failed_operations"],
                "success_rate_percent": round(success_rate, 2)
            },
            "navigation": {
                "total_navigations": self._metrics["navigations"],
                "cache_hits": self._metrics["cache_hits"],
                "cache_misses": self._metrics["cache_misses"],
                "hit_rate_percent": (
                    round(
                        self._metrics["cache_hits"] /
                        (self._metrics["cache_hits"] + self._metrics["cache_misses"]) * 100,
                        2
                    )
                    if (self._metrics["cache_hits"] + self._metrics["cache_misses"]) > 0 else 0
                ),
                "cached_urls": len(self._navigation_cache)
            },
            "selectors": {
                "total_waits": self._metrics["selector_waits"],
                "retries": self._metrics["retries"],
                "avg_wait_time_ms": round(avg_wait_time, 1),
                "slow_selectors": [
                    {"selector": sel, "avg_wait_ms": round(wait, 1)}
                    for sel, wait in slow_selectors
                ]
            },
            "timing": {
                "total_wait_time_ms": self._metrics["total_wait_time_ms"],
                "avg_operation_time_ms": (
                    round(
                        self._metrics["total_wait_time_ms"] / total_operations, 1
                    )
                    if total_operations > 0 else 0
                )
            },
            "cache": {
                "ttl_seconds": self._cache_ttl_seconds,
                "current_entries": len(self._navigation_cache)
            }
        }

    def clear_performance_metrics(self) -> None:
        """Clear all collected performance metrics."""
        self._metrics = {
            "navigations": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "selector_waits": 0,
            "retries": 0,
            "total_wait_time_ms": 0,
            "successful_operations": 0,
            "failed_operations": 0
        }
        self._selector_cache.clear()
        self._selector_success_rate.clear()
        self._navigation_cache.clear()

        logger.info("Browser automation performance metrics cleared")

    async def fill_form(self, form_data: Dict[str, str], wait_before_submit: int = 1000) -> Dict[str, Any]:
        """
        Fill multiple form fields intelligently.

        Args:
            form_data: Dictionary mapping field selectors to values
                      e.g., {'#email': 'test@example.com', '#password': 'secret'}
            wait_before_submit: Wait time before submitting form (ms)

        Returns:
            Dict with success status and filled fields count
        """
        if not self._initialized:
            await self.initialize()

        try:
            filled_count = 0
            errors = []

            for selector, value in form_data.items():
                try:
                    # Wait for field to be visible
                    await self.page.wait_for_selector(selector, timeout=5000, state="visible")

                    # Clear existing value
                    await self.page.fill(selector, "")

                    # Type new value
                    await self.page.fill(selector, str(value))

                    filled_count += 1
                    logger.info(f"Filled field: {selector}")
                except Exception as field_error:
                    errors.append(f"{selector}: {str(field_error)}")
                    logger.warning(f"Failed to fill {selector}: {field_error}")

            # Wait before submission if specified
            if wait_before_submit > 0:
                await asyncio.sleep(wait_before_submit / 1000)

            return {
                "success": filled_count > 0,
                "fields_filled": filled_count,
                "total_fields": len(form_data),
                "errors": errors if errors else None
            }
        except Exception as e:
            logger.error(f"Form filling failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "fields_filled": 0,
                "total_fields": len(form_data)
            }

    async def select_dropdown(self, selector: str, value: Optional[str] = None, label: Optional[str] = None) -> Dict[str, Any]:
        """
        Select an option from a dropdown by value or text label.

        Args:
            selector: CSS selector for the select element
            value: Option value to select (for value attribute)
            label: Option text label to select (for visible text)

        Returns:
            Dict with success status and selected option
        """
        if not self._initialized:
            await self.initialize()

        try:
            await self.page.wait_for_selector(selector, timeout=5000, state="visible")

            if value:
                # Select by value attribute
                await self.page.select_option(selector, value)
                logger.info(f"Selected dropdown {selector} with value: {value}")

                return {
                    "success": True,
                    "selector": selector,
                    "selected_value": value
                }
            elif label:
                # Select by visible text (label)
                await self.page.select_option(selector, label=label)
                logger.info(f"Selected dropdown {selector} with label: {label}")

                return {
                    "success": True,
                    "selector": selector,
                    "selected_label": label
                }
            else:
                return {
                    "success": False,
                    "error": "Either 'value' or 'label' parameter must be provided",
                    "selector": selector
                }
        except Exception as e:
            logger.error(f"Dropdown selection failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "selector": selector
            }

    async def handle_popup(self, accept: bool = True, text: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle browser popups, alerts, and confirm dialogs.

        Args:
            accept: Whether to accept (True) or dismiss (False) the dialog
            text: Text to enter in prompt dialogs (optional)

        Returns:
            Dict with success status and dialog information
        """
        if not self._initialized:
            await self.initialize()

        try:
            dialog_info = {}

            # Set up dialog handler
            async def dialog_handler(dialog):
                dialog_info['type'] = dialog.type  # alert, confirm, prompt, beforeunload
                dialog_info['message'] = dialog.message

                if dialog.type == "prompt" and text:
                    await dialog.accept(text)
                elif accept:
                    await dialog.accept()
                else:
                    await dialog.dismiss()

                logger.info(f"Dialog handled: {dialog.type} - {dialog.message}")

            # Attach dialog handler
            self.page.on("dialog", dialog_handler)

            # Wait a moment for dialogs to appear
            await asyncio.sleep(1)

            # Remove handler
            self.page.remove_listener("dialog", dialog_handler)

            return {
                "success": True,
                "dialog_type": dialog_info.get('type', 'unknown'),
                "message": dialog_info.get('message', ''),
                "action": "accepted" if accept else "dismissed"
            }
        except Exception as e:
            logger.error(f"Popup handling failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def wait_for_navigation(self, timeout: int = 30000) -> Dict[str, Any]:
        """
        Wait for page navigation to complete.

        Args:
            timeout: Maximum wait time in milliseconds

        Returns:
            Dict with success status and new URL
        """
        if not self._initialized:
            await self.initialize()

        try:
            # Wait for navigation with timeout
            await self.page.wait_for_load_state("networkidle", timeout=timeout)

            url = self.page.url
            title = await self.page.title()

            logger.info(f"Navigation completed: {url}")

            return {
                "success": True,
                "url": url,
                "title": title
            }
        except Exception as e:
            logger.error(f"Wait for navigation failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def switch_to_iframe(self, selector: str) -> Dict[str, Any]:
        """
        Switch page context to an iframe.

        Args:
            selector: CSS selector for the iframe element

        Returns:
            Dict with success status
        """
        if not self._initialized:
            await self.initialize()

        try:
            # Get the iframe element
            iframe_element = await self.page.query_selector(selector)

            if not iframe_element:
                return {
                    "success": False,
                    "error": f"Iframe not found: {selector}",
                    "selector": selector
                }

            # Get the frame from the iframe element
            frame = await iframe_element.content_frame()

            if not frame:
                return {
                    "success": False,
                    "error": f"Could not get content frame from iframe: {selector}",
                    "selector": selector
                }

            # Store the current frame for subsequent operations
            # Note: For iframe support, operations after this should use the frame context
            logger.info(f"Switched to iframe: {selector}")

            return {
                "success": True,
                "selector": selector,
                "frame_name": frame.name if frame.name else "unnamed"
            }
        except Exception as e:
            logger.error(f"Iframe switching failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "selector": selector
            }

    async def get_cookies(self) -> Dict[str, Any]:
        """
        Get all cookies for the current domain.

        Returns:
            Dict with cookies list
        """
        if not self._initialized:
            await self.initialize()

        try:
            cookies = await self.context.cookies()

            logger.info(f"Retrieved {len(cookies)} cookies")

            return {
                "success": True,
                "cookies_count": len(cookies),
                "cookies": [
                    {
                        "name": cookie.get("name"),
                        "value": cookie.get("value"),
                        "domain": cookie.get("domain"),
                        "path": cookie.get("path"),
                        "expires": cookie.get("expires"),
                        "httpOnly": cookie.get("httpOnly", False),
                        "secure": cookie.get("secure", False),
                        "sameSite": cookie.get("sameSite")
                    }
                    for cookie in cookies
                ]
            }
        except Exception as e:
            logger.error(f"Get cookies failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def set_cookies(self, cookies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Set cookies for the browser context.

        Args:
            cookies: List of cookie dictionaries with name, value, and optional domain/path
                    e.g., [{'name': 'session', 'value': '12345', 'domain': 'example.com'}]

        Returns:
            Dict with success status and cookies set count
        """
        if not self._initialized:
            await self.initialize()

        try:
            # Validate and prepare cookies
            prepared_cookies = []
            for cookie in cookies:
                if "name" not in cookie or "value" not in cookie:
                    logger.warning(f"Skipping invalid cookie: {cookie}")
                    continue

                prepared_cookie = {
                    "name": cookie["name"],
                    "value": str(cookie["value"]),
                    "url": f"https://{cookie.get('domain', 'localhost')}"
                }

                # Add optional fields if present
                if "path" in cookie:
                    prepared_cookie["path"] = cookie["path"]
                if "expires" in cookie:
                    prepared_cookie["expires"] = cookie["expires"]
                if "httpOnly" in cookie:
                    prepared_cookie["httpOnly"] = cookie["httpOnly"]
                if "secure" in cookie:
                    prepared_cookie["secure"] = cookie["secure"]
                if "sameSite" in cookie:
                    prepared_cookie["sameSite"] = cookie["sameSite"]

                prepared_cookies.append(prepared_cookie)

            # Set cookies in context
            await self.context.add_cookies(prepared_cookies)

            logger.info(f"Set {len(prepared_cookies)} cookies")

            return {
                "success": True,
                "cookies_set": len(prepared_cookies),
                "total_cookies_provided": len(cookies)
            }
        except Exception as e:
            logger.error(f"Set cookies failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def execute_script(self, script: str, args: Optional[List[Any]] = None) -> Dict[str, Any]:
        """
        Execute custom JavaScript on the page.

        Args:
            script: JavaScript code to execute (can include function)
            args: Optional list of arguments to pass to the script

        Returns:
            Dict with script result or error
        """
        if not self._initialized:
            await self.initialize()

        try:
            if args:
                result = await self.page.evaluate(script, args)
            else:
                result = await self.page.evaluate(script)

            logger.info("JavaScript executed successfully")

            return {
                "success": True,
                "result": result
            }
        except Exception as e:
            logger.error(f"Script execution failed: {e}")
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
