"""
Gmail and Google Drive API Tools
Provides tool definitions for Gmail and Drive operations via Google APIs.
"""

from typing import Any

from .tools import Tool, ToolCategory, ToolParameter, ToolResult
from ..services.gmail_api import get_gmail_service
from ..services.drive_api import get_drive_service


# ============================================================================
# Gmail API Tools
# ============================================================================

class ListEmailsTool(Tool):
    """List recent emails from Gmail"""
    name = "list_emails"
    description = "List recent emails from Gmail inbox"
    category = ToolCategory.COMMUNICATION
    requires_confirmation = False

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="max_results",
                type="number",
                description="Maximum number of emails to list",
                required=False,
                default=10
            ),
            ToolParameter(
                name="unread_only",
                type="boolean",
                description="Only show unread emails",
                required=False,
                default=False
            )
        ]
        self._examples = [
            "List my emails",
            "Show recent emails",
            "Check my inbox"
        ]

    def execute(self, max_results: int = 10, unread_only: bool = False, **params) -> ToolResult:
        """List emails"""
        try:
            gmail = get_gmail_service()
            result = gmail.list_messages(max_results=max_results, unread_only=unread_only)

            if result["success"]:
                # Get details for each message
                messages_details = []
                for msg in result["messages"][:5]:  # Get details for first 5
                    msg_detail = gmail.get_message(msg['id'])
                    if msg_detail["success"]:
                        messages_details.append(msg_detail["message"])

                return ToolResult(
                    success=True,
                    data={
                        "message": f"Found {result['count']} emails",
                        "emails": messages_details,
                        "total_count": result["count"]
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get("error", "Failed to list emails")
                )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Gmail API error: {str(e)}"
            )


class ReadEmailTool(Tool):
    """Read a specific email"""
    name = "read_email"
    description = "Read the content of a specific email by ID"
    category = ToolCategory.COMMUNICATION
    requires_confirmation = False

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="message_id",
                type="string",
                description="Gmail message ID",
                required=True
            )
        ]
        self._examples = [
            "Read email with ID abc123",
            "Show me the email"
        ]

    def execute(self, message_id: str, **params) -> ToolResult:
        """Read email"""
        try:
            gmail = get_gmail_service()
            result = gmail.get_message(message_id)

            if result["success"]:
                return ToolResult(
                    success=True,
                    data=result["message"]
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get("error", "Failed to read email")
                )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Gmail API error: {str(e)}"
            )


class SearchEmailsTool(Tool):
    """Search emails"""
    name = "search_emails"
    description = "Search emails using Gmail search syntax"
    category = ToolCategory.COMMUNICATION
    requires_confirmation = False

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="query",
                type="string",
                description="Gmail search query (e.g., 'from:sender@example.com subject:important')",
                required=True
            ),
            ToolParameter(
                name="max_results",
                type="number",
                description="Maximum number of results",
                required=False,
                default=10
            )
        ]
        self._examples = [
            "Search for emails from john@example.com",
            "Find emails with subject invoice",
            "Search unread emails"
        ]

    def execute(self, query: str, max_results: int = 10, **params) -> ToolResult:
        """Search emails"""
        try:
            gmail = get_gmail_service()
            result = gmail.search_messages(query=query, max_results=max_results)

            if result["success"]:
                return ToolResult(
                    success=True,
                    data={
                        "message": f"Found {result['count']} emails matching '{query}'",
                        "count": result["count"],
                        "messages": result["messages"]
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
                error=f"Gmail API error: {str(e)}"
            )


class SendEmailTool(Tool):
    """Send an email"""
    name = "send_email"
    description = "Send an email via Gmail"
    category = ToolCategory.COMMUNICATION
    requires_confirmation = True  # Requires confirmation

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="to",
                type="string",
                description="Recipient email address",
                required=True
            ),
            ToolParameter(
                name="subject",
                type="string",
                description="Email subject",
                required=True
            ),
            ToolParameter(
                name="body",
                type="string",
                description="Email body",
                required=True
            )
        ]
        self._examples = [
            "Send email to john@example.com",
            "Email the report to team@company.com"
        ]

    def execute(self, to: str, subject: str, body: str, **params) -> ToolResult:
        """Send email"""
        try:
            gmail = get_gmail_service()
            result = gmail.send_email(to=to, subject=subject, body=body)

            if result["success"]:
                return ToolResult(
                    success=True,
                    data={
                        "message": f"Email sent to {to}",
                        "message_id": result["message_id"]
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get("error", "Failed to send email")
                )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Gmail API error: {str(e)}"
            )


# ============================================================================
# Google Drive API Tools
# ============================================================================

class ListDriveFilesTool(Tool):
    """List files in Google Drive"""
    name = "list_drive_files"
    description = "List files in Google Drive"
    category = ToolCategory.PRODUCTIVITY
    requires_confirmation = False

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="max_results",
                type="number",
                description="Maximum number of files to list",
                required=False,
                default=10
            )
        ]
        self._examples = [
            "List my Drive files",
            "Show recent files in Drive",
            "What's in my Google Drive"
        ]

    def execute(self, max_results: int = 10, **params) -> ToolResult:
        """List Drive files"""
        try:
            drive = get_drive_service()
            result = drive.list_files(max_results=max_results)

            if result["success"]:
                return ToolResult(
                    success=True,
                    data={
                        "message": f"Found {result['count']} files",
                        "files": result["files"],
                        "count": result["count"]
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get("error", "Failed to list files")
                )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Drive API error: {str(e)}"
            )


class SearchDriveFilesTool(Tool):
    """Search files in Drive"""
    name = "search_drive_files"
    description = "Search for files in Google Drive by name or query"
    category = ToolCategory.PRODUCTIVITY
    requires_confirmation = False

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="query",
                type="string",
                description="Search query (filename or Drive query syntax)",
                required=True
            ),
            ToolParameter(
                name="max_results",
                type="number",
                description="Maximum number of results",
                required=False,
                default=10
            )
        ]
        self._examples = [
            "Search for report.pdf in Drive",
            "Find presentation files",
            "Search for documents about project"
        ]

    def execute(self, query: str, max_results: int = 10, **params) -> ToolResult:
        """Search Drive files"""
        try:
            drive = get_drive_service()
            result = drive.search_files(query=query, max_results=max_results)

            if result["success"]:
                return ToolResult(
                    success=True,
                    data={
                        "message": f"Found {result['count']} files matching '{query}'",
                        "files": result["files"],
                        "count": result["count"]
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
                error=f"Drive API error: {str(e)}"
            )


class DownloadDriveFileTool(Tool):
    """Download file from Drive"""
    name = "download_drive_file"
    description = "Download a file from Google Drive"
    category = ToolCategory.PRODUCTIVITY
    requires_confirmation = False

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="file_id",
                type="string",
                description="Drive file ID",
                required=True
            ),
            ToolParameter(
                name="destination",
                type="string",
                description="Local path to save file (optional)",
                required=False
            )
        ]
        self._examples = [
            "Download file with ID abc123",
            "Download the document",
            "Get the file from Drive"
        ]

    def execute(self, file_id: str, destination: str = None, **params) -> ToolResult:
        """Download Drive file"""
        try:
            drive = get_drive_service()
            result = drive.download_file(file_id=file_id, destination=destination)

            if result["success"]:
                return ToolResult(
                    success=True,
                    data={
                        "message": result["message"],
                        "path": result.get("path"),
                        "filename": result.get("filename"),
                        "size_bytes": result["size_bytes"]
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get("error", "Download failed")
                )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Drive API error: {str(e)}"
            )


class UploadDriveFileTool(Tool):
    """Upload file to Drive"""
    name = "upload_drive_file"
    description = "Upload a local file to Google Drive"
    category = ToolCategory.PRODUCTIVITY
    requires_confirmation = True  # Requires confirmation

    def _setup_parameters(self) -> None:
        self._parameters = [
            ToolParameter(
                name="file_path",
                type="string",
                description="Local file path to upload",
                required=True
            ),
            ToolParameter(
                name="folder_id",
                type="string",
                description="Drive folder ID (optional)",
                required=False
            )
        ]
        self._examples = [
            "Upload file report.pdf to Drive",
            "Upload document to my folder",
            "Put this file in Google Drive"
        ]

    def execute(self, file_path: str, folder_id: str = None, **params) -> ToolResult:
        """Upload to Drive"""
        try:
            drive = get_drive_service()
            result = drive.upload_file(file_path=file_path, folder_id=folder_id)

            if result["success"]:
                return ToolResult(
                    success=True,
                    data={
                        "message": result["message"],
                        "file_id": result["file_id"],
                        "web_view_link": result["web_view_link"]
                    }
                )
            else:
                return ToolResult(
                    success=False,
                    error=result.get("error", "Upload failed")
                )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Drive API error: {str(e)}"
            )
