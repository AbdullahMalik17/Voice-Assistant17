"""
Notion Integration Tools
Provides tool definitions for Notion API operations including page creation, database queries, and updates.
Implements latest notion-sdk-py patterns with comprehensive error handling and type safety.

Reference: https://github.com/ramnes/notion-sdk-py
Requires: notion-client>=2.2.1

Features:
- Full CRUD operations on Notion pages and databases
- Complex filtering and sorting support
- Proper error handling for API responses
- Type-safe parameter construction
"""

import os
import logging
from typing import Any, Optional, Dict, List

from notion_client import Client, APIResponseError, APIErrorCode

from .tools import Tool, ToolCategory, ToolParameter, ToolResult

logger = logging.getLogger(__name__)


class NotionClientManager:
    """
    Manages Notion Client instances with proper authentication and error handling.
    Uses singleton pattern for efficient token management.
    """

    _instance: Optional[Client] = None
    _token: Optional[str] = None

    @classmethod
    def get_client(cls) -> Client:
        """
        Get or create Notion Client instance.

        Returns:
            Notion Client instance

        Raises:
            ValueError: If NOTION_API_KEY is not configured
        """
        token = os.environ.get("NOTION_API_KEY")

        if not token:
            raise ValueError(
                "NOTION_API_KEY environment variable not set. "
                "Please configure your Notion integration secret token."
            )

        # Recreate if token changed
        if cls._token != token or cls._instance is None:
            cls._token = token
            cls._instance = Client(auth=token)
            logger.info("Notion Client initialized successfully")

        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset client instance (for testing)."""
        cls._instance = None
        cls._token = None


def _handle_notion_error(error: APIResponseError) -> ToolResult:
    """
    Centralized Notion error handling with proper logging and user-friendly messages.

    Args:
        error: APIResponseError from Notion API

    Returns:
        ToolResult with error details
    """
    error_code = error.code
    error_message = str(error)

    error_messages = {
        APIErrorCode.ObjectNotFound: (
            "The specified Notion page or database was not found. "
            "Please verify the ID and ensure it's shared with your integration."
        ),
        APIErrorCode.RateLimited: (
            "Notion API rate limit exceeded. Please wait before retrying."
        ),
        APIErrorCode.Unauthorized: (
            "Notion authentication failed. Please check your API key."
        ),
        APIErrorCode.Forbidden: (
            "You don't have permission to access this Notion resource."
        ),
        APIErrorCode.ValidationError: (
            "Invalid parameters sent to Notion API. Please check your input."
        ),
    }

    user_message = error_messages.get(
        error_code,
        f"Notion API error: {error_code}",
    )

    logger.error(
        f"Notion API Error: {error_code}",
        extra={
            "error_code": str(error_code),
            "error_message": error_message,
        },
    )

    return ToolResult(
        success=False,
        error=user_message,
        metadata={"error_code": str(error_code)},
    )


# ============================================================================
# Notion Tools
# ============================================================================


class CreateNotionPageTool(Tool):
    """Create a new page in a Notion database."""

    name = "create_notion_page"
    description = (
        "Create a new page in a Notion database with specified properties. "
        "Supports title, text, numbers, checkboxes, selects, and multi-selects."
    )
    category = ToolCategory.PRODUCTIVITY
    requires_confirmation = False

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="database_id",
                type="string",
                description="Notion database ID (without hyphens or as UUID)",
                required=True,
            ),
            ToolParameter(
                name="title",
                type="string",
                description="Page title (primary property)",
                required=True,
            ),
            ToolParameter(
                name="properties",
                type="object",
                description=(
                    "Additional page properties as JSON. "
                    "Example: {'Status': {'select': {'name': 'In Progress'}}, "
                    "'Priority': {'number': 1}}"
                ),
                required=False,
            ),
        ]
        self._examples = [
            "Create a Notion page titled 'Project Kickoff' in my tasks database",
            "Add a task to Notion with status 'In Progress'",
            "Create a new meeting note in Notion",
        ]

    def execute(
        self,
        database_id: str,
        title: str,
        properties: Optional[Dict[str, Any]] = None,
        **params: Any,
    ) -> ToolResult:
        """
        Create a new page in Notion database.

        Args:
            database_id: Target database ID
            title: Page title
            properties: Additional properties
            **params: Additional parameters

        Returns:
            ToolResult with created page details
        """
        try:
            client = NotionClientManager.get_client()

            # Normalize database ID (remove hyphens if present)
            db_id = database_id.replace("-", "")

            logger.info(
                f"Creating Notion page",
                extra={"database_id": db_id, "title": title},
            )

            # Build page properties
            page_properties = {
                "title": [{"text": {"content": title}}]  # Primary property
            }

            # Add additional properties if provided
            if properties and isinstance(properties, dict):
                page_properties.update(properties)

            # Create page
            response = client.pages.create(
                parent={"database_id": db_id},
                properties=page_properties,
            )

            # Check for errors in response
            if response.get("object") == "error":
                return ToolResult(
                    success=False,
                    error=f"Failed to create page: {response.get('message')}",
                )

            page_id = response.get("id")
            page_url = response.get("url")
            created_time = response.get("created_time")

            logger.info(
                f"Notion page created successfully",
                extra={"page_id": page_id, "url": page_url},
            )

            return ToolResult(
                success=True,
                data={
                    "message": f"Created Notion page: '{title}'",
                    "page_id": page_id,
                    "title": title,
                    "url": page_url,
                    "created_time": created_time,
                },
                metadata={
                    "page_id": page_id,
                    "database_id": db_id,
                },
            )

        except APIResponseError as e:
            return _handle_notion_error(e)
        except Exception as e:
            logger.exception(f"Error creating Notion page: {str(e)}")
            return ToolResult(
                success=False,
                error=f"Failed to create page: {str(e)}",
            )


class QueryNotionDatabaseTool(Tool):
    """Query a Notion database with filters and sorting."""

    name = "query_notion_database"
    description = (
        "Query a Notion database with optional filters and sorting. "
        "Retrieve pages that match specific criteria."
    )
    category = ToolCategory.PRODUCTIVITY
    requires_confirmation = False

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="database_id",
                type="string",
                description="Notion database ID",
                required=True,
            ),
            ToolParameter(
                name="filter_property",
                type="string",
                description="Property name to filter by (optional)",
                required=False,
            ),
            ToolParameter(
                name="filter_value",
                type="string",
                description="Value to filter by (optional)",
                required=False,
            ),
            ToolParameter(
                name="limit",
                type="number",
                description="Maximum number of pages to return (1-100)",
                required=False,
                default=10,
            ),
        ]
        self._examples = [
            "Query my Notion tasks database",
            "Find all pages with status 'In Progress'",
            "Show me high priority items in my Notion database",
        ]

    def execute(
        self,
        database_id: str,
        filter_property: Optional[str] = None,
        filter_value: Optional[str] = None,
        limit: int = 10,
        **params: Any,
    ) -> ToolResult:
        """
        Query Notion database.

        Args:
            database_id: Database ID to query
            filter_property: Optional property to filter by
            filter_value: Optional value to match
            limit: Maximum results to return
            **params: Additional parameters

        Returns:
            ToolResult with query results
        """
        try:
            # Validate limit
            limit = max(1, min(limit, 100))

            client = NotionClientManager.get_client()

            # Normalize database ID
            db_id = database_id.replace("-", "")

            logger.info(
                f"Querying Notion database",
                extra={
                    "database_id": db_id,
                    "filter_property": filter_property,
                    "limit": limit,
                },
            )

            # Build query parameters
            query_params = {
                "database_id": db_id,
                "page_size": limit,
            }

            # Add filter if provided
            if filter_property and filter_value:
                query_params["filter"] = {
                    "property": filter_property,
                    "rich_text": {"contains": filter_value},
                }

            # Execute query
            response = client.databases.query(**query_params)

            # Check for errors
            if response.get("object") == "error":
                return ToolResult(
                    success=False,
                    error=f"Query failed: {response.get('message')}",
                )

            results = response.get("results", [])

            # Extract page information
            pages = []
            for page in results:
                page_id = page.get("id")
                page_url = page.get("url")
                properties = page.get("properties", {})

                # Extract title if available
                title = "Untitled"
                for prop_name, prop_value in properties.items():
                    if prop_value.get("type") == "title":
                        title_list = prop_value.get("title", [])
                        if title_list:
                            title = title_list[0].get("text", {}).get("content", "")
                        break

                pages.append(
                    {
                        "id": page_id,
                        "title": title,
                        "url": page_url,
                    }
                )

            logger.info(
                f"Query returned {len(pages)} Notion pages",
            )

            return ToolResult(
                success=True,
                data={
                    "message": f"Found {len(pages)} pages in database",
                    "pages": pages,
                    "count": len(pages),
                    "database_id": db_id,
                },
                metadata={"page_count": len(pages)},
            )

        except APIResponseError as e:
            return _handle_notion_error(e)
        except Exception as e:
            logger.exception(f"Error querying Notion database: {str(e)}")
            return ToolResult(
                success=False,
                error=f"Failed to query database: {str(e)}",
            )


class UpdateNotionPageTool(Tool):
    """Update properties of an existing Notion page."""

    name = "update_notion_page"
    description = (
        "Update properties of an existing Notion page. "
        "Can update text, numbers, checkboxes, selects, and other property types."
    )
    category = ToolCategory.PRODUCTIVITY
    requires_confirmation = False

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="page_id",
                type="string",
                description="Notion page ID to update",
                required=True,
            ),
            ToolParameter(
                name="properties",
                type="object",
                description=(
                    "Properties to update as JSON. "
                    "Example: {'Status': {'select': {'name': 'Done'}}, "
                    "'Priority': {'number': 2}}"
                ),
                required=True,
            ),
        ]
        self._examples = [
            "Update Notion page status to 'Completed'",
            "Mark task as high priority in Notion",
            "Update meeting notes in Notion",
        ]

    def execute(
        self,
        page_id: str,
        properties: Dict[str, Any],
        **params: Any,
    ) -> ToolResult:
        """
        Update Notion page properties.

        Args:
            page_id: Page ID to update
            properties: Properties to update
            **params: Additional parameters

        Returns:
            ToolResult with update details
        """
        try:
            client = NotionClientManager.get_client()

            # Normalize page ID
            pg_id = page_id.replace("-", "")

            logger.info(
                f"Updating Notion page",
                extra={"page_id": pg_id, "properties": list(properties.keys())},
            )

            # Validate properties is a dict
            if not isinstance(properties, dict):
                return ToolResult(
                    success=False,
                    error="Properties must be a dictionary object",
                )

            # Update page
            response = client.pages.update(
                page_id=pg_id,
                properties=properties,
            )

            # Check for errors
            if response.get("object") == "error":
                return ToolResult(
                    success=False,
                    error=f"Update failed: {response.get('message')}",
                )

            last_edited = response.get("last_edited_time")
            page_url = response.get("url")

            logger.info(
                f"Notion page updated successfully",
                extra={"page_id": pg_id},
            )

            return ToolResult(
                success=True,
                data={
                    "message": "Notion page updated successfully",
                    "page_id": pg_id,
                    "url": page_url,
                    "last_edited_time": last_edited,
                    "updated_properties": list(properties.keys()),
                },
                metadata={
                    "page_id": pg_id,
                    "property_count": len(properties),
                },
            )

        except APIResponseError as e:
            return _handle_notion_error(e)
        except Exception as e:
            logger.exception(f"Error updating Notion page: {str(e)}")
            return ToolResult(
                success=False,
                error=f"Failed to update page: {str(e)}",
            )


class SearchNotionTool(Tool):
    """Search across Notion workspace for pages and databases."""

    name = "search_notion"
    description = (
        "Search across your entire Notion workspace for pages, databases, and other objects. "
        "Useful for finding content by name or ID."
    )
    category = ToolCategory.PRODUCTIVITY
    requires_confirmation = False

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="query",
                type="string",
                description="Search query or page/database name",
                required=True,
            ),
            ToolParameter(
                name="object_type",
                type="string",
                description="Filter by object type: 'page', 'database', or '' for all",
                required=False,
                default="",
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
            "Search Notion for 'Project Kickoff'",
            "Find my tasks database in Notion",
            "Search for meetings in my Notion workspace",
        ]

    def execute(
        self,
        query: str,
        object_type: str = "",
        limit: int = 20,
        **params: Any,
    ) -> ToolResult:
        """
        Search Notion workspace.

        Args:
            query: Search query
            object_type: Filter by object type
            limit: Maximum results
            **params: Additional parameters

        Returns:
            ToolResult with search results
        """
        try:
            # Validate limit
            limit = max(1, min(limit, 100))

            client = NotionClientManager.get_client()

            logger.info(
                f"Searching Notion",
                extra={"query": query, "limit": limit},
            )

            # Build search parameters
            search_params = {
                "query": query,
                "page_size": limit,
            }

            # Add object type filter if specified
            if object_type:
                search_params["filter"] = {
                    "value": object_type,
                    "property": "object",
                }

            # Execute search
            response = client.search(**search_params)

            # Check for errors
            if response.get("object") == "error":
                return ToolResult(
                    success=False,
                    error=f"Search failed: {response.get('message')}",
                )

            results = response.get("results", [])

            # Format search results
            formatted_results = []
            for result in results:
                result_obj = {
                    "id": result.get("id"),
                    "type": result.get("object"),
                    "url": result.get("url"),
                }

                # Add title if available
                if "title" in result:
                    result_obj["title"] = result["title"]
                elif result.get("object") == "database":
                    # Try to get database title from properties
                    result_obj["title"] = "Unnamed Database"

                formatted_results.append(result_obj)

            logger.info(
                f"Notion search returned {len(formatted_results)} results",
            )

            return ToolResult(
                success=True,
                data={
                    "message": f"Found {len(formatted_results)} results for '{query}'",
                    "query": query,
                    "results": formatted_results,
                    "count": len(formatted_results),
                },
                metadata={"result_count": len(formatted_results)},
            )

        except APIResponseError as e:
            return _handle_notion_error(e)
        except Exception as e:
            logger.exception(f"Error searching Notion: {str(e)}")
            return ToolResult(
                success=False,
                error=f"Failed to search: {str(e)}",
            )


class RetrieveNotionPageTool(Tool):
    """Retrieve detailed information about a Notion page."""

    name = "retrieve_notion_page"
    description = (
        "Get detailed information about a specific Notion page including all properties, "
        "created/edited times, and metadata."
    )
    category = ToolCategory.PRODUCTIVITY
    requires_confirmation = False

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="page_id",
                type="string",
                description="Notion page ID to retrieve",
                required=True,
            ),
        ]
        self._examples = [
            "Get details of Notion page",
            "Show me information about this Notion page",
            "Retrieve Notion page data",
        ]

    def execute(
        self,
        page_id: str,
        **params: Any,
    ) -> ToolResult:
        """
        Retrieve Notion page details.

        Args:
            page_id: Page ID to retrieve
            **params: Additional parameters

        Returns:
            ToolResult with page details
        """
        try:
            client = NotionClientManager.get_client()

            # Normalize page ID
            pg_id = page_id.replace("-", "")

            logger.info(
                f"Retrieving Notion page",
                extra={"page_id": pg_id},
            )

            # Get page
            response = client.pages.retrieve(page_id=pg_id)

            # Check for errors
            if response.get("object") == "error":
                return ToolResult(
                    success=False,
                    error=f"Failed to retrieve page: {response.get('message')}",
                )

            # Extract key information
            page_data = {
                "id": response.get("id"),
                "url": response.get("url"),
                "created_time": response.get("created_time"),
                "last_edited_time": response.get("last_edited_time"),
                "archived": response.get("archived", False),
                "properties": {},
            }

            # Extract properties
            properties = response.get("properties", {})
            for prop_name, prop_value in properties.items():
                prop_type = prop_value.get("type")
                if prop_type == "title":
                    title_list = prop_value.get("title", [])
                    if title_list:
                        page_data["title"] = title_list[0].get("text", {}).get(
                            "content", ""
                        )
                page_data["properties"][prop_name] = {
                    "type": prop_type,
                    "value": prop_value.get(prop_type),
                }

            logger.info(
                f"Retrieved Notion page successfully",
                extra={"page_id": pg_id},
            )

            return ToolResult(
                success=True,
                data={
                    "message": "Page retrieved successfully",
                    "page": page_data,
                },
                metadata={"page_id": pg_id},
            )

        except APIResponseError as e:
            return _handle_notion_error(e)
        except Exception as e:
            logger.exception(f"Error retrieving Notion page: {str(e)}")
            return ToolResult(
                success=False,
                error=f"Failed to retrieve page: {str(e)}",
            )
