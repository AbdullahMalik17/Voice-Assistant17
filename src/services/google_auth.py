"""
Google OAuth2 Authentication Service
Handles OAuth2 authentication flow for Gmail and Google Drive APIs.
Manages token storage, refresh, and credential lifecycle.
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class GoogleAuthService:
    """
    Google OAuth2 authentication service.
    Manages credentials for Gmail and Google Drive APIs.
    """

    # OAuth2 scopes for Gmail and Drive
    GMAIL_SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/gmail.modify'
    ]

    DRIVE_SCOPES = [
        'https://www.googleapis.com/auth/drive.readonly',
        'https://www.googleapis.com/auth/drive.file',
        'https://www.googleapis.com/auth/drive.metadata.readonly'
    ]

    def __init__(
        self,
        credentials_file: str = "config/google_credentials.json",
        token_file: str = "config/google_token.json"
    ):
        """
        Initialize Google Auth service.

        Args:
            credentials_file: Path to OAuth2 client credentials JSON
            token_file: Path to store user tokens
        """
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.credentials = None

        logger.info("GoogleAuthService initialized")

    def get_credentials(self, scopes: Optional[List[str]] = None) -> Any:
        """
        Get or create OAuth2 credentials.

        Args:
            scopes: List of OAuth2 scopes (defaults to Gmail + Drive)

        Returns:
            google.oauth2.credentials.Credentials object
        """
        if scopes is None:
            scopes = self.GMAIL_SCOPES + self.DRIVE_SCOPES

        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request
            from google_auth_oauthlib.flow import InstalledAppFlow

            creds = None

            # Load existing token if available
            if os.path.exists(self.token_file):
                creds = Credentials.from_authorized_user_file(self.token_file, scopes)
                logger.info("Loaded existing credentials from token file")

            # If no valid credentials, perform OAuth flow
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    # Refresh expired token
                    logger.info("Refreshing expired token...")
                    creds.refresh(Request())
                    logger.info("Token refreshed successfully")
                else:
                    # Perform OAuth2 flow
                    logger.info("Starting OAuth2 flow...")

                    if not os.path.exists(self.credentials_file):
                        raise FileNotFoundError(
                            f"Credentials file not found: {self.credentials_file}\n"
                            "Please download OAuth2 credentials from Google Cloud Console."
                        )

                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_file,
                        scopes
                    )

                    # Run local server for OAuth callback
                    creds = flow.run_local_server(
                        port=8080,
                        prompt='consent',
                        success_message='Authentication successful! You can close this window.'
                    )

                    logger.info("OAuth2 flow completed successfully")

                # Save credentials for next run
                token_dir = os.path.dirname(self.token_file)
                if token_dir and not os.path.exists(token_dir):
                    os.makedirs(token_dir)

                with open(self.token_file, 'w') as token:
                    token.write(creds.to_json())
                    logger.info(f"Credentials saved to {self.token_file}")

            self.credentials = creds
            return creds

        except ImportError as e:
            logger.error(f"Required Google Auth libraries not installed: {e}")
            raise RuntimeError(
                "Google Auth libraries not installed. "
                "Install with: pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client"
            )
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise

    def revoke_credentials(self) -> Dict[str, Any]:
        """
        Revoke current OAuth2 credentials.

        Returns:
            Dict with revocation status
        """
        try:
            if os.path.exists(self.token_file):
                os.remove(self.token_file)
                logger.info("Credentials revoked and token file deleted")

                return {
                    "success": True,
                    "message": "Credentials revoked successfully"
                }
            else:
                return {
                    "success": False,
                    "message": "No credentials found to revoke"
                }
        except Exception as e:
            logger.error(f"Failed to revoke credentials: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_credentials_status(self) -> Dict[str, Any]:
        """
        Get current credentials status.

        Returns:
            Dict with credentials info
        """
        try:
            if not os.path.exists(self.token_file):
                return {
                    "authenticated": False,
                    "message": "No credentials found"
                }

            from google.oauth2.credentials import Credentials

            creds = Credentials.from_authorized_user_file(
                self.token_file,
                self.GMAIL_SCOPES + self.DRIVE_SCOPES
            )

            status = {
                "authenticated": True,
                "valid": creds.valid,
                "expired": creds.expired if hasattr(creds, 'expired') else None,
                "has_refresh_token": bool(creds.refresh_token),
                "scopes": creds.scopes if hasattr(creds, 'scopes') else []
            }

            if creds.expiry:
                status["expiry"] = creds.expiry.isoformat()
                status["expires_in_seconds"] = (creds.expiry - datetime.utcnow()).total_seconds()

            return status

        except Exception as e:
            logger.error(f"Failed to get credentials status: {e}")
            return {
                "authenticated": False,
                "error": str(e)
            }

    def is_authenticated(self) -> bool:
        """
        Check if user is authenticated.

        Returns:
            True if valid credentials exist
        """
        try:
            status = self.get_credentials_status()
            return status.get("authenticated", False) and status.get("valid", False)
        except Exception:
            return False


# Singleton instance
_google_auth: Optional[GoogleAuthService] = None


def get_google_auth(
    credentials_file: str = "config/google_credentials.json",
    token_file: str = "config/google_token.json"
) -> GoogleAuthService:
    """
    Get or create Google Auth service instance.

    Args:
        credentials_file: Path to OAuth2 credentials
        token_file: Path to token storage

    Returns:
        GoogleAuthService instance
    """
    global _google_auth

    if _google_auth is None:
        _google_auth = GoogleAuthService(
            credentials_file=credentials_file,
            token_file=token_file
        )

    return _google_auth
