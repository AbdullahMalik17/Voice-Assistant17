"""
Discord Integration Tools
Provides tool definitions for Discord API operations including messaging, server management, and file sharing.
Implements latest discord.py patterns with comprehensive error handling and type safety.

Reference: https://github.com/rapptz/discord.py
Requires: discord.py>=2.4.0

Note: This implementation uses webhooks for stateless operation. For stateful bot operations,
consider using discord.Webhook.from_url() with async context managers for automatic cleanup.
"""

import os
import logging
from typing import Any, Optional, List, Dict
from urllib.parse import urlparse

import discord
from discord.errors import DiscordException, HTTPException

from .tools import Tool, ToolCategory, ToolParameter, ToolResult

logger = logging.getLogger(__name__)


class DiscordClientManager:
    """
    Manages Discord webhook clients with proper validation and error handling.
    Uses webhook-based approach for stateless operation without requiring bot intents.
    """

    _webhook_cache: Dict[str, discord.Webhook] = {}

    @classmethod
    def get_webhook(cls, webhook_url: Optional[str] = None) -> Optional[discord.Webhook]:
        """
        Get or create Discord webhook instance.

        Args:
            webhook_url: Optional override for webhook URL (defaults to env var)

        Returns:
            discord.Webhook instance or None if not configured

        Raises:
            ValueError: If webhook URL is invalid
        """
        url = webhook_url or os.environ.get("DISCORD_WEBHOOK_URL")

        if not url:
            logger.warning("DISCORD_WEBHOOK_URL environment variable not set")
            return None

        # Return cached webhook if available
        if url in cls._webhook_cache:
            return cls._webhook_cache[url]

        # Validate webhook URL format
        try:
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("Invalid webhook URL format")

            # Create webhook instance
            webhook = discord.Webhook.from_url(url)
            cls._webhook_cache[url] = webhook

            logger.info("Discord webhook initialized successfully")
            return webhook

        except ValueError as e:
            logger.error(f"Invalid Discord webhook URL: {str(e)}")
            raise ValueError(f"Invalid Discord webhook URL: {str(e)}")

    @classmethod
    def reset(cls) -> None:
        """Reset cached webhooks (for testing)."""
        cls._webhook_cache.clear()


def _handle_discord_error(error: Exception) -> ToolResult:
    """
    Centralized Discord error handling with proper logging and user-friendly messages.

    Args:
        error: Discord exception

    Returns:
        ToolResult with error details
    """
    error_messages = {
        "403 Forbidden": "The bot doesn't have permission to perform this action.",
        "404 Not Found": "The specified channel or user was not found.",
        "429 Too Many Requests": "Rate limit exceeded. Please wait before retrying.",
        "500 Internal Server Error": "Discord API is experiencing issues. Please try again later.",
    }

    # Find matching error message
    error_str = str(error)
    user_message = "An error occurred with Discord"

    for error_pattern, message in error_messages.items():
        if error_pattern.lower() in error_str.lower():
            user_message = message
            break

    logger.error(
        f"Discord API Error: {error_str}",
        extra={"error_type": type(error).__name__},
    )

    return ToolResult(
        success=False,
        error=user_message,
        metadata={"error_type": type(error).__name__},
    )


# ============================================================================
# Discord Tools
# ============================================================================


class SendDiscordMessageTool(Tool):
    """Send a message to a Discord channel via webhook."""

    name = "send_discord_message"
    description = (
        "Send a message to a Discord channel using a webhook. "
        "Supports text, embeds, and mentions. Requires DISCORD_WEBHOOK_URL environment variable."
    )
    category = ToolCategory.COMMUNICATION
    requires_confirmation = True  # Require user approval for sending messages

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="message",
                type="string",
                description="Message text to send (supports Discord markdown formatting)",
                required=True,
            ),
            ToolParameter(
                name="username",
                type="string",
                description="Optional username override for the webhook message",
                required=False,
            ),
            ToolParameter(
                name="thread_name",
                type="string",
                description="Optional thread name to create message in (if webhooks_managed enabled)",
                required=False,
            ),
        ]
        self._examples = [
            "Send to Discord: Team meeting at 3 PM",
            "Post update: Feature release ready for testing",
            "Send message as 'Bot': System maintenance scheduled",
        ]

    def execute(
        self,
        message: str,
        username: Optional[str] = None,
        thread_name: Optional[str] = None,
        **params: Any,
    ) -> ToolResult:
        """
        Send a message to Discord via webhook.

        Args:
            message: Message text
            username: Optional username override
            thread_name: Optional thread name
            **params: Additional parameters

        Returns:
            ToolResult with sent message details
        """
        try:
            webhook = DiscordClientManager.get_webhook()

            if not webhook:
                return ToolResult(
                    success=False,
                    error=(
                        "Discord webhook not configured. "
                        "Please set DISCORD_WEBHOOK_URL environment variable."
                    ),
                )

            logger.info(
                f"Sending Discord message",
                extra={"message_length": len(message)},
            )

            # Send message via webhook
            message_obj = webhook.send(
                content=message,
                username=username or "Voice Assistant",
                wait=True,  # Wait for response to get message details
            )

            logger.info(
                f"Discord message sent successfully",
                extra={"message_id": message_obj.id},
            )

            return ToolResult(
                success=True,
                data={
                    "message": "Message sent successfully to Discord",
                    "message_id": message_obj.id,
                    "timestamp": message_obj.created_at.isoformat(),
                    "text": message,
                },
                metadata={
                    "message_id": str(message_obj.id),
                    "webhook_id": webhook.id,
                },
            )

        except discord.errors.DiscordException as e:
            return _handle_discord_error(e)
        except Exception as e:
            logger.exception(f"Unexpected error sending Discord message: {str(e)}")
            return ToolResult(
                success=False,
                error=f"Failed to send message: {str(e)}",
            )


class ListDiscordServersTool(Tool):
    """List Discord servers (guilds) the bot has access to."""

    name = "list_discord_servers"
    description = (
        "List Discord servers (guilds) the bot is a member of. "
        "Note: Requires bot token with proper permissions, not webhook URL."
    )
    category = ToolCategory.COMMUNICATION
    requires_confirmation = False

    def _setup_parameters(self) -> None:
        self._parameters = []
        self._examples = [
            "What Discord servers are we in?",
            "List my Discord servers",
            "Show available Discord guilds",
        ]

    def execute(self, **params: Any) -> ToolResult:
        """
        List Discord servers.

        Returns:
            ToolResult with server information
        """
        try:
            bot_token = os.environ.get("DISCORD_BOT_TOKEN")

            if not bot_token:
                return ToolResult(
                    success=False,
                    error=(
                        "Discord bot token not configured. "
                        "This tool requires DISCORD_BOT_TOKEN environment variable. "
                        "Note: Using webhooks (DISCORD_WEBHOOK_URL) is simpler for message sending."
                    ),
                )

            logger.info("Attempting to list Discord servers...")

            # For webhook-only setup, we can't list servers without a full bot client
            return ToolResult(
                success=False,
                error=(
                    "List servers requires a Discord bot client with proper intents. "
                    "For simple message sending, use the webhook-based SendDiscordMessageTool instead."
                ),
            )

        except Exception as e:
            logger.exception(f"Error listing Discord servers: {str(e)}")
            return ToolResult(
                success=False,
                error=f"Failed to list servers: {str(e)}",
            )


class PostDiscordEmbedTool(Tool):
    """Send a rich embed message to Discord."""

    name = "post_discord_embed"
    description = (
        "Send a formatted embed message to Discord with title, description, fields, and color. "
        "Embeds are useful for structured information presentation."
    )
    category = ToolCategory.COMMUNICATION
    requires_confirmation = True

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="title",
                type="string",
                description="Embed title",
                required=True,
            ),
            ToolParameter(
                name="description",
                type="string",
                description="Embed description/body text",
                required=True,
            ),
            ToolParameter(
                name="color",
                type="string",
                description=(
                    "Hex color code (e.g., '#FF0000' for red). "
                    "Default: #5865F2 (Discord blue)"
                ),
                required=False,
            ),
            ToolParameter(
                name="fields",
                type="object",
                description=(
                    "Additional fields as JSON object: {'field_name': 'field_value'}"
                ),
                required=False,
            ),
        ]
        self._examples = [
            "Send an embed with title 'Status' and description 'System online'",
            "Post formatted report to Discord",
            "Send structured data as Discord embed",
        ]

    def execute(
        self,
        title: str,
        description: str,
        color: Optional[str] = None,
        fields: Optional[Dict[str, Any]] = None,
        **params: Any,
    ) -> ToolResult:
        """
        Send an embed message to Discord.

        Args:
            title: Embed title
            description: Embed description
            color: Optional hex color
            fields: Optional additional fields
            **params: Additional parameters

        Returns:
            ToolResult with sent message details
        """
        try:
            webhook = DiscordClientManager.get_webhook()

            if not webhook:
                return ToolResult(
                    success=False,
                    error=(
                        "Discord webhook not configured. "
                        "Please set DISCORD_WEBHOOK_URL environment variable."
                    ),
                )

            logger.info(
                f"Sending Discord embed",
                extra={"title": title},
            )

            # Parse color
            color_int = discord.Color.default()
            if color:
                try:
                    color_int = discord.Color(int(color.lstrip("#"), 16))
                except (ValueError, AttributeError):
                    logger.warning(f"Invalid color format: {color}, using default")

            # Create embed
            embed = discord.Embed(
                title=title,
                description=description,
                color=color_int,
            )

            # Add fields if provided
            if fields and isinstance(fields, dict):
                for field_name, field_value in fields.items():
                    embed.add_field(
                        name=str(field_name),
                        value=str(field_value),
                        inline=False,
                    )

            # Send embed via webhook
            message_obj = webhook.send(
                embed=embed,
                username="Voice Assistant",
                wait=True,
            )

            logger.info(
                f"Discord embed sent successfully",
                extra={"message_id": message_obj.id},
            )

            return ToolResult(
                success=True,
                data={
                    "message": "Embed sent successfully to Discord",
                    "message_id": message_obj.id,
                    "title": title,
                    "timestamp": message_obj.created_at.isoformat(),
                },
                metadata={"message_id": str(message_obj.id)},
            )

        except discord.errors.DiscordException as e:
            return _handle_discord_error(e)
        except Exception as e:
            logger.exception(f"Error sending Discord embed: {str(e)}")
            return ToolResult(
                success=False,
                error=f"Failed to send embed: {str(e)}",
            )


class PostDiscordFileTool(Tool):
    """Upload and share a file to Discord via webhook."""

    name = "post_discord_file"
    description = (
        "Upload and share a file to Discord. Supports text content or file paths. "
        "Useful for sharing logs, reports, and other documents."
    )
    category = ToolCategory.COMMUNICATION
    requires_confirmation = True

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="content",
                type="string",
                description="File content to upload (text/code)",
                required=True,
            ),
            ToolParameter(
                name="filename",
                type="string",
                description="Name for the file (e.g., 'report.txt', 'log.py')",
                required=True,
            ),
            ToolParameter(
                name="message",
                type="string",
                description="Optional message to accompany the file",
                required=False,
            ),
        ]
        self._examples = [
            "Upload a log file to Discord",
            "Share code snippet with the team",
            "Post a report to Discord",
        ]

    def execute(
        self,
        content: str,
        filename: str,
        message: Optional[str] = None,
        **params: Any,
    ) -> ToolResult:
        """
        Upload a file to Discord.

        Args:
            content: File content
            filename: File name
            message: Optional accompany message
            **params: Additional parameters

        Returns:
            ToolResult with upload details
        """
        try:
            webhook = DiscordClientManager.get_webhook()

            if not webhook:
                return ToolResult(
                    success=False,
                    error=(
                        "Discord webhook not configured. "
                        "Please set DISCORD_WEBHOOK_URL environment variable."
                    ),
                )

            logger.info(
                f"Uploading file to Discord",
                extra={"filename": filename, "size": len(content)},
            )

            # Create file object from content
            from io import BytesIO

            file_bytes = content.encode("utf-8") if isinstance(content, str) else content
            file_obj = discord.File(
                BytesIO(file_bytes),
                filename=filename,
            )

            # Send file via webhook
            message_obj = webhook.send(
                content=message or f"📎 Shared file: `{filename}`",
                file=file_obj,
                username="Voice Assistant",
                wait=True,
            )

            logger.info(
                f"File uploaded to Discord successfully",
                extra={"message_id": message_obj.id},
            )

            return ToolResult(
                success=True,
                data={
                    "message": f"File '{filename}' uploaded successfully to Discord",
                    "message_id": message_obj.id,
                    "filename": filename,
                    "timestamp": message_obj.created_at.isoformat(),
                },
                metadata={"message_id": str(message_obj.id)},
            )

        except discord.errors.DiscordException as e:
            return _handle_discord_error(e)
        except Exception as e:
            logger.exception(f"Error uploading file to Discord: {str(e)}")
            return ToolResult(
                success=False,
                error=f"Failed to upload file: {str(e)}",
            )


class SendDiscordThreadMessageTool(Tool):
    """Send a message to a Discord thread (if thread exists or create in channel)."""

    name = "send_discord_thread_message"
    description = (
        "Send a message to a Discord thread. Uses webhook for simple operation. "
        "Note: For advanced thread management, consider using a full bot client."
    )
    category = ToolCategory.COMMUNICATION
    requires_confirmation = True

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="message",
                type="string",
                description="Message text to send",
                required=True,
            ),
            ToolParameter(
                name="thread_name",
                type="string",
                description="Name of the thread (for reference)",
                required=False,
            ),
        ]
        self._examples = [
            "Send a message to the support thread",
            "Reply in the bug report discussion",
        ]

    def execute(
        self,
        message: str,
        thread_name: Optional[str] = None,
        **params: Any,
    ) -> ToolResult:
        """
        Send a message to Discord thread.

        Args:
            message: Message text
            thread_name: Thread name (for reference)
            **params: Additional parameters

        Returns:
            ToolResult with sent message details
        """
        try:
            webhook = DiscordClientManager.get_webhook()

            if not webhook:
                return ToolResult(
                    success=False,
                    error=(
                        "Discord webhook not configured. "
                        "Please set DISCORD_WEBHOOK_URL environment variable."
                    ),
                )

            logger.info(
                f"Sending Discord thread message",
                extra={"thread_name": thread_name},
            )

            # Note: Webhook limitation - cannot directly target threads
            # This sends to the channel; for thread support, use full bot client
            message_obj = webhook.send(
                content=f"[{thread_name}] {message}" if thread_name else message,
                username="Voice Assistant",
                wait=True,
            )

            return ToolResult(
                success=True,
                data={
                    "message": "Message sent successfully to Discord",
                    "message_id": message_obj.id,
                    "thread_name": thread_name,
                    "timestamp": message_obj.created_at.isoformat(),
                },
                metadata={"message_id": str(message_obj.id)},
            )

        except discord.errors.DiscordException as e:
            return _handle_discord_error(e)
        except Exception as e:
            logger.exception(f"Error sending Discord thread message: {str(e)}")
            return ToolResult(
                success=False,
                error=f"Failed to send message: {str(e)}",
            )
