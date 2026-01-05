"""
Gmail API Service
Provides programmatic access to Gmail for reading and sending emails.
"""

import base64
import logging
from typing import Dict, Any, List, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from .google_auth import get_google_auth

logger = logging.getLogger(__name__)


class GmailAPIService:
    """
    Gmail API service for email operations.
    Provides methods to list, read, search, and send emails.
    """

    def __init__(self):
        """Initialize Gmail API service."""
        self.service = None
        logger.info("GmailAPIService initialized")

    def _get_service(self):
        """Get or create Gmail API service instance."""
        if self.service is None:
            try:
                from googleapiclient.discovery import build

                auth_service = get_google_auth()
                credentials = auth_service.get_credentials(auth_service.GMAIL_SCOPES)

                self.service = build('gmail', 'v1', credentials=credentials)
                logger.info("Gmail API service created")

            except ImportError:
                raise RuntimeError(
                    "Google API client not installed. "
                    "Install with: pip install google-api-python-client"
                )
            except Exception as e:
                logger.error(f"Failed to create Gmail service: {e}")
                raise

        return self.service

    def list_messages(
        self,
        max_results: int = 10,
        label_ids: Optional[List[str]] = None,
        query: Optional[str] = None,
        unread_only: bool = False
    ) -> Dict[str, Any]:
        """
        List email messages.

        Args:
            max_results: Maximum number of messages to return
            label_ids: Filter by label IDs (e.g., ['INBOX', 'UNREAD'])
            query: Gmail search query (e.g., 'from:sender@example.com')
            unread_only: Only return unread messages

        Returns:
            Dict with message list
        """
        try:
            service = self._get_service()

            # Build query
            if unread_only:
                query = f"is:unread {query or ''}".strip()

            # List messages
            params = {
                'userId': 'me',
                'maxResults': max_results
            }

            if label_ids:
                params['labelIds'] = label_ids
            if query:
                params['q'] = query

            response = service.users().messages().list(**params).execute()
            messages = response.get('messages', [])

            logger.info(f"Listed {len(messages)} messages")

            return {
                "success": True,
                "messages": messages,
                "count": len(messages),
                "next_page_token": response.get('nextPageToken')
            }

        except Exception as e:
            logger.error(f"Failed to list messages: {e}")
            return {
                "success": False,
                "error": str(e),
                "messages": []
            }

    def get_message(self, message_id: str) -> Dict[str, Any]:
        """
        Get full message details.

        Args:
            message_id: Gmail message ID

        Returns:
            Dict with message details
        """
        try:
            service = self._get_service()

            message = service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()

            # Extract key info
            headers = message.get('payload', {}).get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            from_email = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown')
            to_email = next((h['value'] for h in headers if h['name'] == 'To'), 'Unknown')

            # Extract body
            body = self._extract_message_body(message.get('payload', {}))

            # Check if unread
            labels = message.get('labelIds', [])
            is_unread = 'UNREAD' in labels

            logger.info(f"Retrieved message: {subject}")

            return {
                "success": True,
                "message": {
                    "id": message_id,
                    "subject": subject,
                    "from": from_email,
                    "to": to_email,
                    "date": date,
                    "body": body,
                    "snippet": message.get('snippet', ''),
                    "is_unread": is_unread,
                    "labels": labels
                }
            }

        except Exception as e:
            logger.error(f"Failed to get message {message_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def _extract_message_body(self, payload: Dict) -> str:
        """Extract message body from payload."""
        if 'body' in payload and payload['body'].get('data'):
            return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')

        if 'parts' in payload:
            for part in payload['parts']:
                if part.get('mimeType') == 'text/plain':
                    if part.get('body', {}).get('data'):
                        return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')

                if part.get('mimeType') == 'text/html' and not part.get('parts'):
                    if part.get('body', {}).get('data'):
                        return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')

                # Recursive for nested parts
                if 'parts' in part:
                    body = self._extract_message_body(part)
                    if body:
                        return body

        return "Could not extract message body"

    def search_messages(self, query: str, max_results: int = 10) -> Dict[str, Any]:
        """
        Search messages by query.

        Args:
            query: Gmail search query
            max_results: Maximum results

        Returns:
            Dict with search results
        """
        return self.list_messages(max_results=max_results, query=query)

    def mark_as_read(self, message_id: str) -> Dict[str, Any]:
        """
        Mark message as read.

        Args:
            message_id: Gmail message ID

        Returns:
            Dict with success status
        """
        try:
            service = self._get_service()

            service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()

            logger.info(f"Marked message {message_id} as read")

            return {
                "success": True,
                "message": "Message marked as read"
            }

        except Exception as e:
            logger.error(f"Failed to mark as read: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def mark_as_unread(self, message_id: str) -> Dict[str, Any]:
        """
        Mark message as unread.

        Args:
            message_id: Gmail message ID

        Returns:
            Dict with success status
        """
        try:
            service = self._get_service()

            service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': ['UNREAD']}
            ).execute()

            logger.info(f"Marked message {message_id} as unread")

            return {
                "success": True,
                "message": "Message marked as unread"
            }

        except Exception as e:
            logger.error(f"Failed to mark as unread: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        body_type: str = 'plain'
    ) -> Dict[str, Any]:
        """
        Send an email.

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body
            body_type: 'plain' or 'html'

        Returns:
            Dict with send status
        """
        try:
            service = self._get_service()

            # Create message
            if body_type == 'html':
                message = MIMEText(body, 'html')
            else:
                message = MIMEText(body, 'plain')

            message['to'] = to
            message['subject'] = subject

            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

            # Send
            sent_message = service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()

            logger.info(f"Email sent to {to}: {subject}")

            return {
                "success": True,
                "message": "Email sent successfully",
                "message_id": sent_message['id']
            }

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_labels(self) -> Dict[str, Any]:
        """
        Get all Gmail labels.

        Returns:
            Dict with label list
        """
        try:
            service = self._get_service()

            response = service.users().labels().list(userId='me').execute()
            labels = response.get('labels', [])

            logger.info(f"Retrieved {len(labels)} labels")

            return {
                "success": True,
                "labels": labels,
                "count": len(labels)
            }

        except Exception as e:
            logger.error(f"Failed to get labels: {e}")
            return {
                "success": False,
                "error": str(e),
                "labels": []
            }


# Singleton instance
_gmail_service: Optional[GmailAPIService] = None


def get_gmail_service() -> GmailAPIService:
    """
    Get or create Gmail API service instance.

    Returns:
        GmailAPIService instance
    """
    global _gmail_service

    if _gmail_service is None:
        _gmail_service = GmailAPIService()

    return _gmail_service
