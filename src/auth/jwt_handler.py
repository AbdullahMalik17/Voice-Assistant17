"""
JWT Token Handler for authenticating WebSocket and API requests.
Validates JWT tokens from NextAuth.js frontend.
"""
import jwt
import os
from typing import Optional, Dict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Get JWT secret from environment (same as NEXTAUTH_SECRET in frontend)
JWT_SECRET = os.getenv('NEXTAUTH_SECRET', '')
SUPABASE_JWT_SECRET = os.getenv('SUPABASE_JWT_SECRET', '')

class JWTHandler:
    """Handles JWT token validation and user extraction."""

    def __init__(self, secret: Optional[str] = None):
        self.secret = secret or JWT_SECRET or SUPABASE_JWT_SECRET
        if not self.secret:
            logger.warning("⚠️  No JWT secret configured. Authentication will be disabled!")

    def validate_token(self, token: str) -> Optional[Dict]:
        """
        Validate JWT token and extract user information.

        Args:
            token: JWT token string

        Returns:
            Dict with user info if valid, None if invalid
        """
        if not self.secret:
            logger.warning("JWT validation skipped - no secret configured")
            return None

        try:
            # Try NextAuth JWT format first
            payload = jwt.decode(
                token,
                self.secret,
                algorithms=["HS256", "HS512"],
                options={"verify_exp": True}
            )

            # Extract user info from NextAuth JWT
            user_info = {
                "user_id": payload.get("id") or payload.get("sub"),
                "email": payload.get("email"),
                "name": payload.get("name"),
                "token_type": "nextauth"
            }

            logger.info(f"✅ Validated NextAuth JWT for user: {user_info['email']}")
            return user_info

        except jwt.ExpiredSignatureError:
            logger.error("❌ Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.error(f"❌ Invalid token: {e}")

            # Try Supabase JWT format as fallback
            if SUPABASE_JWT_SECRET and SUPABASE_JWT_SECRET != self.secret:
                try:
                    payload = jwt.decode(
                        token,
                        SUPABASE_JWT_SECRET,
                        algorithms=["HS256"],
                        options={"verify_exp": True}
                    )

                    user_info = {
                        "user_id": payload.get("sub"),
                        "email": payload.get("email"),
                        "token_type": "supabase"
                    }

                    logger.info(f"✅ Validated Supabase JWT for user: {user_info['email']}")
                    return user_info
                except Exception as e:
                    logger.error(f"❌ Supabase JWT validation failed: {e}")

            return None

    def extract_token_from_query(self, query_string: str) -> Optional[str]:
        """
        Extract JWT token from WebSocket query string.
        Supports: ?token=xxx or ?auth=xxx

        Args:
            query_string: URL query string

        Returns:
            Token string if found, None otherwise
        """
        if not query_string:
            return None

        # Parse query string manually (simple implementation)
        params = {}
        for param in query_string.split('&'):
            if '=' in param:
                key, value = param.split('=', 1)
                params[key] = value

        return params.get('token') or params.get('auth')

    def extract_token_from_header(self, auth_header: str) -> Optional[str]:
        """
        Extract JWT token from Authorization header.
        Supports: Bearer <token>

        Args:
            auth_header: Authorization header value

        Returns:
            Token string if found, None otherwise
        """
        if not auth_header:
            return None

        if auth_header.startswith('Bearer '):
            return auth_header[7:]  # Remove "Bearer " prefix

        return auth_header

# Global JWT handler instance
jwt_handler = JWTHandler()
