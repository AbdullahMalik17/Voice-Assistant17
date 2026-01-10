"""
Browser Automation Tools
Provides tool definitions for browser automation via Playwright.
Includes basic navigation, form filling, popup handling, and advanced browser control.
"""

import asyncio
from typing import Any, Dict, List, Optional

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


# ============================================================================
# Enhanced Browser Tools (Phase 1D)
# ============================================================================


class FillFormTool(Tool):
    """Fill multiple form fields at once with intelligent form handling"""

    name = "fill_form"
    description = (
        "Fill multiple form fields at once. Handles text inputs, selects, and other form elements. "
        "Pass field selectors and values as a JSON object."
    )
    category = ToolCategory.AUTOMATION
    requires_confirmation = True

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="form_data",
                type="object",
                description=(
                    "Form fields to fill as JSON object: "
                    "{'#email': 'test@example.com', '.password-field': 'mypassword'}"
                ),
                required=True
            ),
            ToolParameter(
                name="wait_before_submit",
                type="integer",
                description="Wait time in milliseconds before submission (default: 1000)",
                required=False,
                default=1000
            )
        ]
        self._examples = [
            "Fill the login form with email and password",
            "Fill out the registration form with user details",
            "Complete the checkout form"
        ]

    def execute(self, form_data: Dict[str, str], wait_before_submit: int = 1000, **params) -> ToolResult:
        """Execute form filling"""
        try:
            browser = get_browser_service(headless=False)
            result = asyncio.run(browser.fill_form(form_data, wait_before_submit))

            if result["success"]:
                return ToolResult(
                    success=True,
                    data={
                        "message": f"Filled {result['fields_filled']} form fields",
                        "fields_filled": result["fields_filled"],
                        "total_fields": result["total_fields"],
                        "errors": result.get("errors")
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get("error", "Form filling failed")
                )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Form fill error: {str(e)}"
            )


class SelectDropdownTool(Tool):
    """Select an option from a dropdown menu"""

    name = "select_dropdown"
    description = (
        "Select an option from a dropdown/select element by value or visible text label. "
        "Useful for form selections and filtering."
    )
    category = ToolCategory.AUTOMATION
    requires_confirmation = True

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="selector",
                type="string",
                description="CSS selector for the select element",
                required=True
            ),
            ToolParameter(
                name="value",
                type="string",
                description="Option value to select (for value attribute)",
                required=False
            ),
            ToolParameter(
                name="label",
                type="string",
                description="Option text label to select (for visible text)",
                required=False
            )
        ]
        self._examples = [
            "Select 'USD' from the currency dropdown",
            "Choose 'Monthly' from the billing period select",
            "Select the country from the dropdown"
        ]

    def execute(
        self,
        selector: str,
        value: Optional[str] = None,
        label: Optional[str] = None,
        **params
    ) -> ToolResult:
        """Execute dropdown selection"""
        try:
            if not value and not label:
                return ToolResult(
                    success=False,
                    error="Either 'value' or 'label' parameter must be provided"
                )

            browser = get_browser_service(headless=False)
            result = asyncio.run(browser.select_dropdown(selector, value, label))

            if result["success"]:
                selected = result.get("selected_value") or result.get("selected_label")
                return ToolResult(
                    success=True,
                    data={
                        "message": f"Selected option: {selected}",
                        "selector": selector,
                        "selected": selected
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get("error", "Dropdown selection failed")
                )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Dropdown selection error: {str(e)}"
            )


class HandlePopupTool(Tool):
    """Handle browser popups, alerts, and dialogs"""

    name = "handle_popup"
    description = (
        "Handle browser popups, alerts, confirm dialogs, and prompt dialogs. "
        "Can accept, dismiss, or provide text input for prompts."
    )
    category = ToolCategory.AUTOMATION
    requires_confirmation = False

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="accept",
                type="boolean",
                description="Accept (True) or dismiss (False) the dialog",
                required=False,
                default=True
            ),
            ToolParameter(
                name="text",
                type="string",
                description="Text to enter in prompt dialogs (optional)",
                required=False
            )
        ]
        self._examples = [
            "Accept the popup dialog",
            "Dismiss the confirmation popup",
            "Answer the prompt with 'yes'"
        ]

    def execute(self, accept: bool = True, text: Optional[str] = None, **params) -> ToolResult:
        """Execute popup handling"""
        try:
            browser = get_browser_service(headless=False)
            result = asyncio.run(browser.handle_popup(accept, text))

            if result["success"]:
                return ToolResult(
                    success=True,
                    data={
                        "message": f"Dialog handled: {result['dialog_type']}",
                        "dialog_type": result["dialog_type"],
                        "message": result["message"],
                        "action": result["action"]
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get("error", "Popup handling failed")
                )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Popup handling error: {str(e)}"
            )


class WaitForNavigationTool(Tool):
    """Wait for page navigation to complete"""

    name = "wait_for_navigation"
    description = (
        "Wait for page navigation to complete after clicking a link or button. "
        "Useful after actions that trigger page loads."
    )
    category = ToolCategory.AUTOMATION
    requires_confirmation = False

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="timeout",
                type="integer",
                description="Maximum wait time in milliseconds (default: 30000)",
                required=False,
                default=30000
            )
        ]
        self._examples = [
            "Wait for the page to load",
            "Wait for navigation to complete",
            "Hold until the new page loads"
        ]

    def execute(self, timeout: int = 30000, **params) -> ToolResult:
        """Execute wait for navigation"""
        try:
            browser = get_browser_service(headless=False)
            result = asyncio.run(browser.wait_for_navigation(timeout))

            if result["success"]:
                return ToolResult(
                    success=True,
                    data={
                        "message": f"Navigation completed: {result['title']}",
                        "url": result["url"],
                        "title": result["title"]
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get("error", "Wait for navigation timeout")
                )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Navigation wait error: {str(e)}"
            )


class SwitchToIframeTool(Tool):
    """Switch browser context to an iframe"""

    name = "switch_to_iframe"
    description = (
        "Switch page context to an iframe element. Useful for interacting with content "
        "inside iframes like payment forms or embedded content."
    )
    category = ToolCategory.AUTOMATION
    requires_confirmation = False

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="selector",
                type="string",
                description="CSS selector for the iframe element",
                required=True
            )
        ]
        self._examples = [
            "Switch to the payment iframe",
            "Access the embedded form in the iframe",
            "Enter the Stripe payment iframe"
        ]

    def execute(self, selector: str, **params) -> ToolResult:
        """Execute iframe switching"""
        try:
            browser = get_browser_service(headless=False)
            result = asyncio.run(browser.switch_to_iframe(selector))

            if result["success"]:
                return ToolResult(
                    success=True,
                    data={
                        "message": f"Switched to iframe: {result['frame_name']}",
                        "selector": selector,
                        "frame_name": result["frame_name"]
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get("error", "Iframe switching failed")
                )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Iframe switch error: {str(e)}"
            )


class GetCookiesTool(Tool):
    """Get all cookies from the browser"""

    name = "get_cookies"
    description = (
        "Retrieve all cookies from the current browser context. "
        "Useful for extracting session tokens or other cookie data."
    )
    category = ToolCategory.AUTOMATION
    requires_confirmation = False

    def _setup_parameters(self) -> None:
        self._parameters = []
        self._examples = [
            "Get the cookies from this page",
            "Show all stored cookies",
            "Extract the session cookie"
        ]

    def execute(self, **params) -> ToolResult:
        """Get cookies"""
        try:
            browser = get_browser_service(headless=False)
            result = asyncio.run(browser.get_cookies())

            if result["success"]:
                return ToolResult(
                    success=True,
                    data={
                        "message": f"Retrieved {result['cookies_count']} cookies",
                        "cookies_count": result["cookies_count"],
                        "cookies": result["cookies"]
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get("error", "Failed to get cookies")
                )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Get cookies error: {str(e)}"
            )


class SetCookiesTool(Tool):
    """Set cookies in the browser"""

    name = "set_cookies"
    description = (
        "Set cookies for the browser context. Useful for restoring sessions "
        "or testing with specific cookie values."
    )
    category = ToolCategory.AUTOMATION
    requires_confirmation = True

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="cookies",
                type="array",
                description=(
                    "List of cookies to set. Each cookie should have 'name' and 'value'. "
                    "Example: [{'name': 'session', 'value': '12345', 'domain': 'example.com'}]"
                ),
                required=True,
                items_type="object"
            )
        ]
        self._examples = [
            "Set the session cookie",
            "Restore cookies from backup",
            "Set authentication cookies"
        ]

    def execute(self, cookies: List[Dict[str, Any]], **params) -> ToolResult:
        """Set cookies"""
        try:
            browser = get_browser_service(headless=False)
            result = asyncio.run(browser.set_cookies(cookies))

            if result["success"]:
                return ToolResult(
                    success=True,
                    data={
                        "message": f"Set {result['cookies_set']} cookies",
                        "cookies_set": result["cookies_set"],
                        "total_cookies_provided": result["total_cookies_provided"]
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get("error", "Failed to set cookies")
                )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Set cookies error: {str(e)}"
            )


class ExecuteScriptTool(Tool):
    """Execute custom JavaScript on the page"""

    name = "execute_script"
    description = (
        "Execute custom JavaScript code on the current page. "
        "Useful for advanced automation, data extraction, or DOM manipulation."
    )
    category = ToolCategory.AUTOMATION
    requires_confirmation = True

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="script",
                type="string",
                description=(
                    "JavaScript code to execute. Can include functions. "
                    "Example: 'return document.title' or '() => { return document.querySelectorAll(\"a\").length }'"
                ),
                required=True
            ),
            ToolParameter(
                name="args",
                type="array",
                description="Optional arguments to pass to the script",
                required=False,
                items_type="string"
            )
        ]
        self._examples = [
            "Get the page title",
            "Count all links on the page",
            "Extract all text content",
            "Execute a function to get data"
        ]

    def execute(self, script: str, args: Optional[List[Any]] = None, **params) -> ToolResult:
        """Execute script"""
        try:
            browser = get_browser_service(headless=False)
            result = asyncio.run(browser.execute_script(script, args))

            if result["success"]:
                return ToolResult(
                    success=True,
                    data={
                        "message": "Script executed successfully",
                        "result": result["result"]
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get("error", "Script execution failed")
                )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Script execution error: {str(e)}"
            )
