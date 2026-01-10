"""
Slack Integration Tools
Provides tool definitions for Slack API operations including messaging, channel management, and search.
Implements latest slack-sdk patterns with comprehensive error handling and type safety.

Reference: https://context7.com/slackapi/python-slack-sdk
Requires: slack_sdk>=3.31.0
"""

import os
import logging
from typing import Any, Optional, List, Dict

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.web.slack_response import SlackResponse

from .tools import Tool, ToolCategory, ToolParameter, ToolResult

logger = logging.getLogger(__name__)


class SlackClientManager:
    """
    Manages Slack WebClient instances with singleton pattern.
    Provides centralized token management and error handling.
    """

    _instance: Optional[WebClient] = None
    _token: Optional[str] = None

    @classmethod
    def get_client(cls) -> WebClient:
        """Get or create Slack WebClient instance."""
        token = os.environ.get("SLACK_BOT_TOKEN")

        if not token:
            raise ValueError(
                "SLACK_BOT_TOKEN environment variable not set. "
                "Please configure your Slack bot token."
            )

        # Recreate if token changed
        if cls._token != token or cls._instance is None:
            cls._token = token
            cls._instance = WebClient(token=token)
            logger.info("Slack WebClient initialized successfully")

        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset client instance (for testing)."""
        cls._instance = None
        cls._token = None


def _handle_slack_error(error: SlackApiError) -> ToolResult:
    """
    Centralized Slack error handling with proper logging and user-friendly messages.

    Args:
        error: SlackApiError from Slack API

    Returns:
        ToolResult with error details
    """
    error_code = error.response.get("error", "unknown_error")
    status_code = error.response.status_code

    error_messages = {
        "channel_not_found": "The specified Slack channel was not found. Please verify the channel name.",
        "invalid_auth": "Slack authentication failed. Please check your bot token.",
        "missing_scope": "The Slack bot lacks required permissions. Check bot scopes.",
        "account_inactive": "Slack account is inactive.",
        "token_revoked": "Slack token has been revoked.",
        "no_permission": "You don't have permission to perform this action.",
        "user_not_found": "The specified Slack user was not found.",
        "rate_limited": "Rate limit exceeded. Please wait before retrying.",
    }

    user_message = error_messages.get(error_code, f"Slack API error: {error_code}")

    logger.error(
        f"Slack API Error: {error_code} (Status: {status_code})",
        extra={
            "error_code": error_code,
            "status_code": status_code,
            "error_response": error.response,
        },
    )

    return ToolResult(
        success=False,
        error=user_message,
        metadata={"error_code": error_code, "status_code": status_code},
    )


# ============================================================================
# Slack Tools
# ============================================================================


class SendSlackMessageTool(Tool):
    """Send a message to a Slack channel or user."""

    name = "send_slack_message"
    description = (
        "Send a text message to a Slack channel or direct message to a user. "
        "Use channel names like #general or user IDs."
    )
    category = ToolCategory.COMMUNICATION
    requires_confirmation = True  # Require user approval for sending messages

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="channel",
                type="string",
                description=(
                    "Target Slack channel (e.g., '#general' or '@username' or channel ID)"
                ),
                required=True,
            ),
            ToolParameter(
                name="text",
                type="string",
                description="Message text to send (supports Slack markdown formatting)",
                required=True,
            ),
            ToolParameter(
                name="thread_ts",
                type="string",
                description=(
                    "Optional: Thread timestamp to reply to. "
                    "Format: timestamp from the parent message."
                ),
                required=False,
            ),
            ToolParameter(
                name="unfurl_links",
                type="boolean",
                description="Whether to unfurl links in the message",
                required=False,
                default=True,
            ),
        ]
        self._examples = [
            "Send a message to #general: Team sync in 5 minutes",
            "Message @john: Can you review the latest PR?",
            "Post to #announcements: System maintenance tonight at 8 PM",
        ]

    def execute(
        self,
        channel: str,
        text: str,
        thread_ts: Optional[str] = None,
        unfurl_links: bool = True,
        **params: Any,
    ) -> ToolResult:
        """
        Send a message to Slack.

        Args:
            channel: Target channel or user
            text: Message text
            thread_ts: Optional thread timestamp for replies
            unfurl_links: Whether to unfurl links
            **params: Additional parameters

        Returns:
            ToolResult with sent message details
        """
        try:
            client = SlackClientManager.get_client()

            # Build message parameters
            message_params = {
                "channel": channel,
                "text": text,
                "unfurl_links": unfurl_links,
            }

            # Add thread timestamp if replying to thread
            if thread_ts:
                message_params["thread_ts"] = thread_ts

            logger.info(
                f"Sending Slack message to {channel}",
                extra={"message_length": len(text)},
            )

            response: SlackResponse = client.chat_postMessage(**message_params)

            # Verify response
            if not response["ok"]:
                return ToolResult(
                    success=False,
                    error=f"Slack API returned error: {response.get('error', 'unknown')}",
                )

            message_ts = response.get("ts")
            channel_id = response.get("channel")

            logger.info(
                f"Message sent successfully",
                extra={"channel": channel_id, "timestamp": message_ts},
            )

            return ToolResult(
                success=True,
                data={
                    "message": f"Message sent successfully to {channel}",
                    "channel": channel_id,
                    "timestamp": message_ts,
                    "text": text,
                },
                metadata={
                    "message_ts": message_ts,
                    "channel_id": channel_id,
                },
            )

        except SlackApiError as e:
            return _handle_slack_error(e)
        except Exception as e:
            logger.exception(f"Unexpected error sending Slack message: {str(e)}")
            return ToolResult(
                success=False,
                error=f"Failed to send message: {str(e)}",
            )


class ListSlackChannelsTool(Tool):
    """List available Slack channels the bot has access to."""

    name = "list_slack_channels"
    description = (
        "List available Slack channels (public and private channels the bot can access). "
        "Useful for discovering channels or verifying channel names."
    )
    category = ToolCategory.COMMUNICATION
    requires_confirmation = False

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="exclude_archived",
                type="boolean",
                description="Exclude archived channels from the list",
                required=False,
                default=True,
            ),
            ToolParameter(
                name="limit",
                type="number",
                description="Maximum number of channels to return (1-1000)",
                required=False,
                default=50,
            ),
            ToolParameter(
                name="types",
                type="string",
                description=(
                    "Channel types to include. Options: "
                    "'public_channel', 'private_channel', 'mpim', 'im'. "
                    "Comma-separated for multiple types."
                ),
                required=False,
                default="public_channel,private_channel",
            ),
        ]
        self._examples = [
            "What Slack channels are available?",
            "List all channels",
            "Show me the channels I can message",
        ]

    def execute(
        self,
        exclude_archived: bool = True,
        limit: int = 50,
        types: str = "public_channel,private_channel",
        **params: Any,
    ) -> ToolResult:
        """
        List Slack channels.

        Args:
            exclude_archived: Exclude archived channels
            limit: Maximum channels to return
            types: Channel types to include
            **params: Additional parameters

        Returns:
            ToolResult with list of channels
        """
        try:
            # Validate limit
            limit = max(1, min(limit, 1000))

            client = SlackClientManager.get_client()

            logger.info(
                "Listing Slack channels",
                extra={"limit": limit, "exclude_archived": exclude_archived},
            )

            # Fetch channels using conversations.list (latest API)
            response: SlackResponse = client.conversations_list(
                exclude_archived=exclude_archived,
                types=types,
                limit=limit,
            )

            if not response["ok"]:
                return ToolResult(
                    success=False,
                    error=f"Failed to list channels: {response.get('error')}",
                )

            channels = response.get("channels", [])

            # Format channel information
            formatted_channels = [
                {
                    "name": ch.get("name"),
                    "id": ch.get("id"),
                    "is_private": ch.get("is_private", False),
                    "is_archived": ch.get("is_archived", False),
                    "topic": ch.get("topic", {}).get("value", ""),
                    "member_count": ch.get("num_members", 0),
                }
                for ch in channels
            ]

            logger.info(
                f"Found {len(formatted_channels)} Slack channels",
            )

            return ToolResult(
                success=True,
                data={
                    "message": f"Found {len(formatted_channels)} Slack channels",
                    "channels": formatted_channels,
                    "count": len(formatted_channels),
                },
                metadata={"total_channels": len(formatted_channels)},
            )

        except SlackApiError as e:
            return _handle_slack_error(e)
        except Exception as e:
            logger.exception(f"Error listing Slack channels: {str(e)}")
            return ToolResult(
                success=False,
                error=f"Failed to list channels: {str(e)}",
            )


class SearchSlackMessagesTool(Tool):
    """Search through Slack message history."""

    name = "search_slack_messages"
    description = (
        "Search through Slack message history in a specific channel. "
        "Supports keyword search and filtering by date range."
    )
    category = ToolCategory.COMMUNICATION
    requires_confirmation = False

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="channel",
                type="string",
                description="Channel to search in (channel name or ID)",
                required=True,
            ),
            ToolParameter(
                name="query",
                type="string",
                description="Search keywords or phrase",
                required=True,
            ),
            ToolParameter(
                name="limit",
                type="number",
                description="Maximum number of messages to return (1-100)",
                required=False,
                default=10,
            ),
        ]
        self._examples = [
            "Search #general for 'meeting notes'",
            "Find messages about deployment in #engineering",
            "Look for 'bug fix' in #bugs channel",
        ]

    def execute(
        self,
        channel: str,
        query: str,
        limit: int = 10,
        **params: Any,
    ) -> ToolResult:
        """
        Search Slack messages in a channel.

        Args:
            channel: Channel to search
            query: Search query
            limit: Maximum messages to return
            **params: Additional parameters

        Returns:
            ToolResult with search results
        """
        try:
            # Validate limit
            limit = max(1, min(limit, 100))

            client = SlackClientManager.get_client()

            logger.info(
                f"Searching Slack messages",
                extra={"channel": channel, "query": query, "limit": limit},
            )

            # Get channel ID from name if necessary
            channel_id = channel
            if channel.startswith("#"):
                # Convert channel name to ID
                conv_response: SlackResponse = client.conversations_list(
                    exclude_archived=False
                )
                if conv_response["ok"]:
                    for ch in conv_response["channels"]:
                        if ch["name"] == channel.lstrip("#"):
                            channel_id = ch["id"]
                            break

            # Get conversation history (channel messages)
            response: SlackResponse = client.conversations_history(
                channel=channel_id,
                limit=limit,
            )

            if not response["ok"]:
                return ToolResult(
                    success=False,
                    error=f"Failed to search messages: {response.get('error')}",
                )

            messages = response.get("messages", [])

            # Filter messages by query (simple keyword matching)
            query_lower = query.lower()
            matching_messages = [
                {
                    "timestamp": msg.get("ts"),
                    "user": msg.get("user", "unknown"),
                    "text": msg.get("text", ""),
                    "reactions": msg.get("reactions", []),
                    "reply_count": msg.get("reply_count", 0),
                }
                for msg in messages
                if query_lower in msg.get("text", "").lower()
            ]

            logger.info(
                f"Found {len(matching_messages)} matching messages",
            )

            return ToolResult(
                success=True,
                data={
                    "message": f"Found {len(matching_messages)} messages matching '{query}'",
                    "query": query,
                    "channel": channel,
                    "messages": matching_messages,
                    "count": len(matching_messages),
                },
                metadata={"matches": len(matching_messages)},
            )

        except SlackApiError as e:
            return _handle_slack_error(e)
        except Exception as e:
            logger.exception(f"Error searching Slack messages: {str(e)}")
            return ToolResult(
                success=False,
                error=f"Failed to search messages: {str(e)}",
            )


class GetSlackThreadTool(Tool):
    """Read a conversation thread in Slack."""

    name = "get_slack_thread"
    description = (
        "Retrieve all messages in a Slack thread (conversation). "
        "Useful for reviewing discussions and decisions."
    )
    category = ToolCategory.COMMUNICATION
    requires_confirmation = False

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="channel",
                type="string",
                description="Channel containing the thread",
                required=True,
            ),
            ToolParameter(
                name="thread_ts",
                type="string",
                description="Thread timestamp (from the parent message)",
                required=True,
            ),
            ToolParameter(
                name="limit",
                type="number",
                description="Maximum number of messages to return (1-100)",
                required=False,
                default=50,
            ),
        ]
        self._examples = [
            "Get thread starting at timestamp 1234567890.123456",
            "Show me the discussion in #general from that message",
            "Retrieve the entire thread about the project proposal",
        ]

    def execute(
        self,
        channel: str,
        thread_ts: str,
        limit: int = 50,
        **params: Any,
    ) -> ToolResult:
        """
        Get messages from a Slack thread.

        Args:
            channel: Channel containing thread
            thread_ts: Thread parent timestamp
            limit: Maximum messages to return
            **params: Additional parameters

        Returns:
            ToolResult with thread messages
        """
        try:
            # Validate limit
            limit = max(1, min(limit, 100))

            client = SlackClientManager.get_client()

            logger.info(
                f"Retrieving Slack thread",
                extra={"channel": channel, "thread_ts": thread_ts},
            )

            # Get thread messages
            response: SlackResponse = client.conversations_replies(
                channel=channel,
                ts=thread_ts,
                limit=limit,
            )

            if not response["ok"]:
                return ToolResult(
                    success=False,
                    error=f"Failed to get thread: {response.get('error')}",
                )

            messages = response.get("messages", [])

            # Format thread messages
            formatted_messages = [
                {
                    "timestamp": msg.get("ts"),
                    "user": msg.get("user", "unknown"),
                    "text": msg.get("text", ""),
                    "type": msg.get("type", "message"),
                    "reply_count": msg.get("reply_count", 0),
                }
                for msg in messages
            ]

            logger.info(
                f"Retrieved {len(formatted_messages)} thread messages",
            )

            return ToolResult(
                success=True,
                data={
                    "message": f"Retrieved {len(formatted_messages)} messages from thread",
                    "channel": channel,
                    "thread_ts": thread_ts,
                    "messages": formatted_messages,
                    "count": len(formatted_messages),
                },
                metadata={"message_count": len(formatted_messages)},
            )

        except SlackApiError as e:
            return _handle_slack_error(e)
        except Exception as e:
            logger.exception(f"Error retrieving Slack thread: {str(e)}")
            return ToolResult(
                success=False,
                error=f"Failed to retrieve thread: {str(e)}",
            )


class PostSlackFileTool(Tool):
    """Upload and share a file to Slack."""

    name = "post_slack_file"
    description = (
        "Upload a file to a Slack channel or user. "
        "Can share file content directly or from a file path."
    )
    category = ToolCategory.COMMUNICATION
    requires_confirmation = True  # Require confirmation for file uploads

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="channel",
                type="string",
                description="Target channel or user",
                required=True,
            ),
            ToolParameter(
                name="content",
                type="string",
                description="File content (text/code) to upload",
                required=True,
            ),
            ToolParameter(
                name="filename",
                type="string",
                description="Name for the file (e.g., 'report.txt', 'code.py')",
                required=True,
            ),
            ToolParameter(
                name="title",
                type="string",
                description="Optional title for the file",
                required=False,
            ),
            ToolParameter(
                name="initial_comment",
                type="string",
                description="Optional message to accompany the file",
                required=False,
            ),
        ]
        self._examples = [
            "Upload a log file to #logs channel",
            "Share code snippet with the team",
            "Post a report to #reports",
        ]

    def execute(
        self,
        channel: str,
        content: str,
        filename: str,
        title: Optional[str] = None,
        initial_comment: Optional[str] = None,
        **params: Any,
    ) -> ToolResult:
        """
        Upload a file to Slack.

        Args:
            channel: Target channel or user
            content: File content
            filename: File name
            title: Optional file title
            initial_comment: Optional accompany message
            **params: Additional parameters

        Returns:
            ToolResult with upload details
        """
        try:
            client = SlackClientManager.get_client()

            logger.info(
                f"Uploading file to Slack",
                extra={
                    "channel": channel,
                    "filename": filename,
                    "size": len(content),
                },
            )

            # Build upload parameters
            upload_params = {
                "channels": channel,
                "file": content,
                "filename": filename,
            }

            if title:
                upload_params["title"] = title

            if initial_comment:
                upload_params["initial_comment"] = initial_comment

            # Upload file
            response: SlackResponse = client.files_upload_v2(**upload_params)

            if not response["ok"]:
                return ToolResult(
                    success=False,
                    error=f"Failed to upload file: {response.get('error')}",
                )

            file_id = response.get("file", {}).get("id")

            logger.info(
                f"File uploaded successfully",
                extra={"file_id": file_id, "filename": filename},
            )

            return ToolResult(
                success=True,
                data={
                    "message": f"File '{filename}' uploaded successfully to {channel}",
                    "file_id": file_id,
                    "filename": filename,
                    "channel": channel,
                },
                metadata={"file_id": file_id},
            )

        except SlackApiError as e:
            return _handle_slack_error(e)
        except Exception as e:
            logger.exception(f"Error uploading file to Slack: {str(e)}")
            return ToolResult(
                success=False,
                error=f"Failed to upload file: {str(e)}",
            )
