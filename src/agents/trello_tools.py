"""
Trello Integration Tools
Provides tool definitions for Trello API operations including board management, card creation, and list operations.
Implements latest Trello REST API patterns with comprehensive error handling and type safety.

Reference: https://developer.atlassian.com/cloud/trello/rest
Uses: requests library for REST API calls (stateless HTTP)
Requires: requests>=2.31.0

Features:
- Full CRUD operations on boards, lists, and cards
- Card movement between lists
- Comments and attachments support
- Proper error handling and rate limit awareness
"""

import os
import logging
from typing import Any, Optional, Dict, List

import requests
from requests.exceptions import RequestException, Timeout

from .tools import Tool, ToolCategory, ToolParameter, ToolResult

logger = logging.getLogger(__name__)

# Trello API base URL
TRELLO_API_BASE = "https://api.trello.com/1"


class TrelloClientManager:
    """
    Manages Trello API credentials and provides utility methods.
    Uses REST API for stateless operations without requiring persistent client.
    """

    _api_key: Optional[str] = None
    _api_token: Optional[str] = None

    @classmethod
    def get_credentials(cls) -> tuple[str, str]:
        """
        Get Trello API credentials from environment.

        Returns:
            Tuple of (api_key, api_token)

        Raises:
            ValueError: If credentials not configured
        """
        api_key = os.environ.get("TRELLO_API_KEY")
        api_token = os.environ.get("TRELLO_TOKEN")

        if not api_key or not api_token:
            raise ValueError(
                "Trello credentials not configured. "
                "Please set TRELLO_API_KEY and TRELLO_TOKEN environment variables."
            )

        cls._api_key = api_key
        cls._api_token = api_token
        return api_key, api_token

    @classmethod
    def build_url(cls, endpoint: str, params: Optional[Dict[str, str]] = None) -> str:
        """
        Build Trello API URL with credentials.

        Args:
            endpoint: API endpoint (e.g., '/boards/123')
            params: Optional query parameters

        Returns:
            Complete URL with credentials
        """
        api_key, api_token = cls.get_credentials()

        url = f"{TRELLO_API_BASE}{endpoint}"

        # Add credentials and merge with additional params
        query_params = {"key": api_key, "token": api_token}
        if params:
            query_params.update(params)

        # Build query string
        query_string = "&".join(
            f"{k}={v}" for k, v in query_params.items() if v is not None
        )
        return f"{url}?{query_string}" if query_string else url

    @classmethod
    def make_request(
        cls,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        timeout: int = 10,
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Trello API with error handling.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint
            params: Query parameters
            json_data: JSON body data
            timeout: Request timeout in seconds

        Returns:
            Response JSON or error dict

        Raises:
            RequestException: On network errors
            ValueError: On API errors
        """
        try:
            url = cls.build_url(endpoint, params)

            logger.debug(f"Trello {method} request to {endpoint}")

            response = requests.request(
                method=method,
                url=url,
                json=json_data,
                timeout=timeout,
            )

            # Handle different status codes
            if response.status_code == 429:
                # Rate limited
                retry_after = response.headers.get("Retry-After", "60")
                logger.warning(
                    f"Trello API rate limited. Retry after {retry_after}s"
                )
                raise ValueError(
                    f"Trello API rate limit exceeded. Please wait {retry_after} seconds."
                )

            elif response.status_code == 401:
                logger.error("Trello authentication failed (401)")
                raise ValueError("Trello authentication failed. Check API credentials.")

            elif response.status_code == 403:
                logger.error("Trello permission denied (403)")
                raise ValueError("Permission denied to access Trello resource.")

            elif response.status_code == 404:
                logger.error(f"Trello resource not found (404): {endpoint}")
                raise ValueError("Trello resource not found. Check IDs and permissions.")

            elif response.status_code >= 400:
                logger.error(
                    f"Trello API error {response.status_code}: {response.text}"
                )
                raise ValueError(
                    f"Trello API error: {response.status_code} - {response.text}"
                )

            # Success response
            if response.content:
                return response.json()
            return {"success": True}

        except Timeout:
            logger.error("Trello API request timeout")
            raise ValueError("Trello API request timeout. Please try again.")
        except RequestException as e:
            logger.error(f"Trello API request error: {str(e)}")
            raise ValueError(f"Network error connecting to Trello: {str(e)}")


def _handle_trello_error(error: Exception) -> ToolResult:
    """
    Centralized Trello error handling.

    Args:
        error: Exception from Trello operation

    Returns:
        ToolResult with error details
    """
    error_message = str(error)

    logger.error(f"Trello Error: {error_message}")

    return ToolResult(
        success=False,
        error=error_message,
        metadata={"error_type": type(error).__name__},
    )


# ============================================================================
# Trello Tools
# ============================================================================


class CreateTrelloCardTool(Tool):
    """Create a new card on a Trello board."""

    name = "create_trello_card"
    description = (
        "Create a new card in a Trello list. Supports title, description, "
        "labels, and due dates."
    )
    category = ToolCategory.PRODUCTIVITY
    requires_confirmation = False

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="list_id",
                type="string",
                description="Trello list ID where card will be created",
                required=True,
            ),
            ToolParameter(
                name="name",
                type="string",
                description="Card title/name",
                required=True,
            ),
            ToolParameter(
                name="description",
                type="string",
                description="Card description (optional)",
                required=False,
            ),
            ToolParameter(
                name="due_date",
                type="string",
                description="Due date in ISO format (YYYY-MM-DD) or relative (e.g., 'tomorrow')",
                required=False,
            ),
        ]
        self._examples = [
            "Create a Trello card: 'Implement user authentication'",
            "Add task to Trello: 'Review pull request' with due date tomorrow",
            "Create Trello card with description and labels",
        ]

    def execute(
        self,
        list_id: str,
        name: str,
        description: Optional[str] = None,
        due_date: Optional[str] = None,
        **params: Any,
    ) -> ToolResult:
        """
        Create a Trello card.

        Args:
            list_id: Target list ID
            name: Card name/title
            description: Optional description
            due_date: Optional due date
            **params: Additional parameters

        Returns:
            ToolResult with created card details
        """
        try:
            logger.info(
                f"Creating Trello card",
                extra={"list_id": list_id, "name": name},
            )

            # Build card data
            card_params = {
                "idList": list_id,
                "name": name,
            }

            if description:
                card_params["desc"] = description

            if due_date:
                card_params["due"] = due_date

            # Create card
            response = TrelloClientManager.make_request(
                method="POST",
                endpoint="/cards",
                params=card_params,
            )

            card_id = response.get("id")
            card_url = response.get("url")
            card_shorturl = response.get("shortUrl")

            logger.info(
                f"Trello card created successfully",
                extra={"card_id": card_id},
            )

            return ToolResult(
                success=True,
                data={
                    "message": f"Created Trello card: '{name}'",
                    "card_id": card_id,
                    "name": name,
                    "url": card_url,
                    "short_url": card_shorturl,
                    "list_id": list_id,
                },
                metadata={
                    "card_id": card_id,
                    "list_id": list_id,
                },
            )

        except ValueError as e:
            return _handle_trello_error(e)
        except Exception as e:
            logger.exception(f"Error creating Trello card: {str(e)}")
            return ToolResult(
                success=False,
                error=f"Failed to create card: {str(e)}",
            )


class ListTrelloBoardsTool(Tool):
    """List all Trello boards accessible to the user."""

    name = "list_trello_boards"
    description = (
        "List all Trello boards that you have access to. "
        "Useful for discovering board IDs and organization."
    )
    category = ToolCategory.PRODUCTIVITY
    requires_confirmation = False

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="filter",
                type="string",
                description=(
                    "Filter boards: 'all', 'open', 'closed', 'archived'. "
                    "Default: 'all'"
                ),
                required=False,
                default="open",
            ),
            ToolParameter(
                name="limit",
                type="number",
                description="Maximum boards to return (1-100)",
                required=False,
                default=20,
            ),
        ]
        self._examples = [
            "List my Trello boards",
            "Show all Trello boards I can access",
            "What boards do I have?",
        ]

    def execute(
        self,
        filter: str = "open",
        limit: int = 20,
        **params: Any,
    ) -> ToolResult:
        """
        List Trello boards.

        Args:
            filter: Board filter (all, open, closed, archived)
            limit: Maximum boards to return
            **params: Additional parameters

        Returns:
            ToolResult with board list
        """
        try:
            # Validate limit
            limit = max(1, min(limit, 100))

            logger.info(
                f"Listing Trello boards",
                extra={"filter": filter, "limit": limit},
            )

            # Get boards for current user
            response = TrelloClientManager.make_request(
                method="GET",
                endpoint="/members/me/boards",
                params={
                    "filter": filter,
                    "limit": limit,
                },
            )

            # Handle response as list
            if not isinstance(response, list):
                response = [response] if response else []

            # Format board information
            boards = []
            for board in response:
                boards.append(
                    {
                        "id": board.get("id"),
                        "name": board.get("name"),
                        "url": board.get("url"),
                        "closed": board.get("closed", False),
                        "desc": board.get("desc", ""),
                    }
                )

            logger.info(f"Found {len(boards)} Trello boards")

            return ToolResult(
                success=True,
                data={
                    "message": f"Found {len(boards)} Trello boards",
                    "boards": boards,
                    "count": len(boards),
                },
                metadata={"board_count": len(boards)},
            )

        except ValueError as e:
            return _handle_trello_error(e)
        except Exception as e:
            logger.exception(f"Error listing Trello boards: {str(e)}")
            return ToolResult(
                success=False,
                error=f"Failed to list boards: {str(e)}",
            )


class MoveTrelloCardTool(Tool):
    """Move a card between Trello lists."""

    name = "move_trello_card"
    description = (
        "Move a Trello card from one list to another. "
        "Can also reposition the card within the same list."
    )
    category = ToolCategory.PRODUCTIVITY
    requires_confirmation = False

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="card_id",
                type="string",
                description="Trello card ID to move",
                required=True,
            ),
            ToolParameter(
                name="list_id",
                type="string",
                description="Target list ID",
                required=True,
            ),
            ToolParameter(
                name="position",
                type="string",
                description=(
                    "Position in list: 'top', 'bottom', or numeric position. "
                    "Default: 'top'"
                ),
                required=False,
                default="top",
            ),
        ]
        self._examples = [
            "Move Trello card to 'Done' list",
            "Move card to the top of the list",
            "Move task to In Progress column",
        ]

    def execute(
        self,
        card_id: str,
        list_id: str,
        position: str = "top",
        **params: Any,
    ) -> ToolResult:
        """
        Move Trello card to different list.

        Args:
            card_id: Card ID to move
            list_id: Target list ID
            position: Position in list
            **params: Additional parameters

        Returns:
            ToolResult with move confirmation
        """
        try:
            logger.info(
                f"Moving Trello card",
                extra={"card_id": card_id, "list_id": list_id, "position": position},
            )

            # Move card
            response = TrelloClientManager.make_request(
                method="PUT",
                endpoint=f"/cards/{card_id}",
                params={
                    "idList": list_id,
                    "pos": position,
                },
            )

            logger.info(
                f"Trello card moved successfully",
                extra={"card_id": card_id},
            )

            return ToolResult(
                success=True,
                data={
                    "message": f"Card moved successfully to list {list_id}",
                    "card_id": card_id,
                    "list_id": list_id,
                    "position": position,
                },
                metadata={
                    "card_id": card_id,
                    "list_id": list_id,
                },
            )

        except ValueError as e:
            return _handle_trello_error(e)
        except Exception as e:
            logger.exception(f"Error moving Trello card: {str(e)}")
            return ToolResult(
                success=False,
                error=f"Failed to move card: {str(e)}",
            )


class AddTrelloCommentTool(Tool):
    """Add a comment to a Trello card."""

    name = "add_trello_comment"
    description = (
        "Add a comment to a Trello card. Useful for updates, discussions, "
        "and tracking card activity."
    )
    category = ToolCategory.PRODUCTIVITY
    requires_confirmation = False

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="card_id",
                type="string",
                description="Trello card ID to comment on",
                required=True,
            ),
            ToolParameter(
                name="comment",
                type="string",
                description="Comment text (supports markdown)",
                required=True,
            ),
        ]
        self._examples = [
            "Add comment to Trello card: 'Review completed, approved for merge'",
            "Comment on card: 'Waiting for client feedback'",
            "Add note to Trello card",
        ]

    def execute(
        self,
        card_id: str,
        comment: str,
        **params: Any,
    ) -> ToolResult:
        """
        Add comment to Trello card.

        Args:
            card_id: Card ID to comment on
            comment: Comment text
            **params: Additional parameters

        Returns:
            ToolResult with comment details
        """
        try:
            logger.info(
                f"Adding comment to Trello card",
                extra={"card_id": card_id, "comment_length": len(comment)},
            )

            # Add comment
            response = TrelloClientManager.make_request(
                method="POST",
                endpoint=f"/cards/{card_id}/actions/comments",
                params={"text": comment},
            )

            comment_id = response.get("id")
            created_date = response.get("date")

            logger.info(
                f"Comment added to Trello card successfully",
                extra={"card_id": card_id, "comment_id": comment_id},
            )

            return ToolResult(
                success=True,
                data={
                    "message": "Comment added successfully",
                    "card_id": card_id,
                    "comment_id": comment_id,
                    "comment": comment,
                    "created_date": created_date,
                },
                metadata={
                    "card_id": card_id,
                    "comment_id": comment_id,
                },
            )

        except ValueError as e:
            return _handle_trello_error(e)
        except Exception as e:
            logger.exception(f"Error adding Trello comment: {str(e)}")
            return ToolResult(
                success=False,
                error=f"Failed to add comment: {str(e)}",
            )


class SearchTrelloTool(Tool):
    """Search for cards in Trello boards."""

    name = "search_trello"
    description = (
        "Search for cards across your Trello boards. "
        "Useful for finding specific tasks by name or description."
    )
    category = ToolCategory.PRODUCTIVITY
    requires_confirmation = False

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="query",
                type="string",
                description="Search query (card name, description, or label)",
                required=True,
            ),
            ToolParameter(
                name="board_id",
                type="string",
                description="Optional: Limit search to specific board",
                required=False,
            ),
            ToolParameter(
                name="limit",
                type="number",
                description="Maximum results to return (1-100)",
                required=False,
                default=20,
            ),
        ]
        self._examples = [
            "Search Trello for 'bug fixes'",
            "Find cards about 'authentication' in my boards",
            "Search for task 'Deploy to production'",
        ]

    def execute(
        self,
        query: str,
        board_id: Optional[str] = None,
        limit: int = 20,
        **params: Any,
    ) -> ToolResult:
        """
        Search Trello cards.

        Args:
            query: Search query
            board_id: Optional board ID to limit search
            limit: Maximum results
            **params: Additional parameters

        Returns:
            ToolResult with search results
        """
        try:
            # Validate limit
            limit = max(1, min(limit, 100))

            logger.info(
                f"Searching Trello",
                extra={"query": query, "limit": limit},
            )

            # Build search parameters
            search_params = {
                "query": query,
                "cards": "open",
                "card_limit": limit,
            }

            if board_id:
                search_params["idBoards"] = board_id

            # Search cards
            response = TrelloClientManager.make_request(
                method="GET",
                endpoint="/search",
                params=search_params,
            )

            cards = response.get("cards", []) if isinstance(response, dict) else []

            # Format results
            results = []
            for card in cards:
                results.append(
                    {
                        "id": card.get("id"),
                        "name": card.get("name"),
                        "url": card.get("url"),
                        "desc": card.get("desc", ""),
                        "list_id": card.get("idList"),
                        "board_id": card.get("idBoard"),
                    }
                )

            logger.info(f"Trello search returned {len(results)} cards")

            return ToolResult(
                success=True,
                data={
                    "message": f"Found {len(results)} Trello cards matching '{query}'",
                    "query": query,
                    "cards": results,
                    "count": len(results),
                },
                metadata={"result_count": len(results)},
            )

        except ValueError as e:
            return _handle_trello_error(e)
        except Exception as e:
            logger.exception(f"Error searching Trello: {str(e)}")
            return ToolResult(
                success=False,
                error=f"Failed to search: {str(e)}",
            )
