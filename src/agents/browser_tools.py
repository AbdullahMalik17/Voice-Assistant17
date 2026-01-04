"""
Browser Automation Tools
Provides tool definitions for browser automation via Playwright.
"""

import asyncio
from typing import Any

from .tools import Tool, ToolCategory, ToolParameter, ToolResult
from ..services.browser_automation import get_browser_service


class BrowserNavigateTool(Tool):
    """Navigate to a URL in the browser"""
    name = "browser_navigate"
    description = "Navigate to a specific URL or website in the browser"
    category = ToolCategory.AUTOMATION
    requires_confirmation = False

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="url",
                type="string",
                description="URL to navigate to (e.g., 'google.com', 'https://gmail.com')",
                required=True
            )
        ]
        self._examples = [
            "Go to Gmail",
            "Open Google Drive",
            "Navigate to YouTube"
        ]

    def execute(self, url: str, **params) -> ToolResult:
        """Execute browser navigation"""
        try:
            browser = get_browser_service(headless=False)
            result = asyncio.run(browser.navigate(url))

            if result["success"]:
                return ToolResult(
                    success=True,
                    data={
                        "message": f"Navigated to {result['title']}",
                        "url": result["url"],
                        "title": result["title"]
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get("error", "Navigation failed")
                )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Browser navigation error: {str(e)}"
            )


class BrowserSearchTool(Tool):
    """Search Google in the browser"""
    name = "browser_search"
    description = "Perform a Google search in the browser"
    category = ToolCategory.AUTOMATION
    requires_confirmation = False

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="query",
                type="string",
                description="Search query",
                required=True
            )
        ]
        self._examples = [
            "Search for Python tutorials",
            "Look up weather in Tokyo",
            "Find information about AI"
        ]

    def execute(self, query: str, **params) -> ToolResult:
        """Execute Google search"""
        try:
            browser = get_browser_service(headless=False)
            result = asyncio.run(browser.search_google(query))

            if result["success"]:
                return ToolResult(
                    success=True,
                    data={
                        "message": f"Searched for: {query}",
                        "query": query,
                        "url": result["url"]
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get("error", "Search failed")
                )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Browser search error: {str(e)}"
            )


class OpenGmailTool(Tool):
    """Open Gmail in browser"""
    name = "open_gmail"
    description = "Open Gmail in the browser"
    category = ToolCategory.AUTOMATION
    requires_confirmation = False

    def _setup_parameters(self) -> None:
        self._parameters = []
        self._examples = [
            "Open Gmail",
            "Check my email",
            "Go to my inbox"
        ]

    def execute(self, **params) -> ToolResult:
        """Open Gmail"""
        try:
            browser = get_browser_service(headless=False)
            result = asyncio.run(browser.open_gmail())

            if result["success"]:
                return ToolResult(
                    success=True,
                    data={
                        "message": "Gmail opened in browser",
                        "url": result["url"]
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get("error", "Failed to open Gmail")
                )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error opening Gmail: {str(e)}"
            )


class OpenGoogleDriveTool(Tool):
    """Open Google Drive in browser"""
    name = "open_google_drive"
    description = "Open Google Drive in the browser"
    category = ToolCategory.AUTOMATION
    requires_confirmation = False

    def _setup_parameters(self) -> None:
        self._parameters = []
        self._examples = [
            "Open Google Drive",
            "Go to my Drive",
            "Show my files"
        ]

    def execute(self, **params) -> ToolResult:
        """Open Google Drive"""
        try:
            browser = get_browser_service(headless=False)
            result = asyncio.run(browser.open_google_drive())

            if result["success"]:
                return ToolResult(
                    success=True,
                    data={
                        "message": "Google Drive opened in browser",
                        "url": result["url"]
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get("error", "Failed to open Google Drive")
                )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error opening Google Drive: {str(e)}"
            )


class BrowserScreenshotTool(Tool):
    """Take a screenshot of the browser"""
    name = "browser_screenshot"
    description = "Take a screenshot of the current browser page"
    category = ToolCategory.AUTOMATION
    requires_confirmation = False

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="full_page",
                type="boolean",
                description="Capture full scrollable page",
                required=False,
                default=False
            )
        ]
        self._examples = [
            "Take a screenshot",
            "Capture the page",
            "Screenshot this"
        ]

    def execute(self, full_page: bool = False, **params) -> ToolResult:
        """Take screenshot"""
        try:
            browser = get_browser_service(headless=False)
            result = asyncio.run(browser.screenshot(full_page=full_page))

            if result["success"]:
                return ToolResult(
                    success=True,
                    data={
                        "message": "Screenshot captured",
                        "screenshot": result.get("screenshot"),
                        "full_page": full_page
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get("error", "Screenshot failed")
                )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Screenshot error: {str(e)}"
            )


class BrowserClickTool(Tool):
    """Click an element in the browser"""
    name = "browser_click"
    description = "Click an element on the current page using a selector"
    category = ToolCategory.AUTOMATION
    requires_confirmation = True  # Requires confirmation for safety

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="selector",
                type="string",
                description="CSS selector or text selector for the element to click",
                required=True
            )
        ]
        self._examples = [
            "Click the sign in button",
            "Press the submit button",
            "Click on the link"
        ]

    def execute(self, selector: str, **params) -> ToolResult:
        """Click element"""
        try:
            browser = get_browser_service(headless=False)
            result = asyncio.run(browser.click(selector))

            if result["success"]:
                return ToolResult(
                    success=True,
                    data={
                        "message": f"Clicked element: {selector}",
                        "selector": selector
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get("error", "Click failed")
                )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Click error: {str(e)}"
            )


class BrowserTypeTool(Tool):
    """Type text into an input field"""
    name = "browser_type"
    description = "Type text into an input field on the current page"
    category = ToolCategory.AUTOMATION
    requires_confirmation = True  # Requires confirmation for safety

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="selector",
                type="string",
                description="CSS selector for the input field",
                required=True
            ),
            ToolParameter(
                name="text",
                type="string",
                description="Text to type",
                required=True
            )
        ]
        self._examples = [
            "Type 'hello' in the search box",
            "Enter my email address",
            "Fill in the form"
        ]

    def execute(self, selector: str, text: str, **params) -> ToolResult:
        """Type text"""
        try:
            browser = get_browser_service(headless=False)
            result = asyncio.run(browser.type_text(selector, text))

            if result["success"]:
                return ToolResult(
                    success=True,
                    data={
                        "message": f"Typed text into: {selector}",
                        "selector": selector,
                        "text_length": result["text_length"]
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get("error", "Type failed")
                )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Type error: {str(e)}"
            )
