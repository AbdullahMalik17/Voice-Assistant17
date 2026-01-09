"""
Authentication Middleware for FastAPI
Validates JWT tokens for WebSocket and HTTP endpoints.
"""
from fastapi import WebSocket, HTTPException, status, Header
from typing import Optional, Dict
import logging

from .jwt_handler import jwt_handler

logger = logging.getLogger(__name__)


class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


async def authenticate_websocket(websocket: WebSocket) -> Optional[Dict]:
    """
    Authenticate WebSocket connection using JWT token.

    Token can be provided via:
    1. Query parameter: ?token=xxx
    2. Query parameter: ?auth=xxx

    Args:
        websocket: FastAPI WebSocket instance

    Returns:
        User info dict if authenticated, None if authentication disabled

    Raises:
        AuthenticationError if token is invalid
    """
    # Extract query string
    query_string = websocket.scope.get('query_string', b'').decode('utf-8')

    # Try to extract token
    token = jwt_handler.extract_token_from_query(query_string)

    if not token:
        # If no JWT secret is configured, allow unauthenticated access
        if not jwt_handler.secret:
            logger.warning("⚠️  No JWT secret configured - WebSocket auth disabled")
            return {"user_id": "anonymous", "email": "anonymous@example.com", "authenticated": False}

        raise AuthenticationError("Missing authentication token. Provide token in query: ?token=YOUR_JWT_TOKEN")

    # Validate token
    user_info = jwt_handler.validate_token(token)

    if not user_info:
        raise AuthenticationError("Invalid or expired authentication token")

    user_info["authenticated"] = True
    return user_info


async def authenticate_http(authorization: Optional[str] = Header(None)) -> Optional[Dict]:
    """
    Authenticate HTTP request using JWT token from Authorization header.

    Args:
        authorization: Authorization header value (Bearer token)

    Returns:
        User info dict if authenticated, None if authentication disabled

    Raises:
        HTTPException if token is invalid
    """
    # If no JWT secret is configured, allow unauthenticated access
    if not jwt_handler.secret:
        logger.warning("⚠️  No JWT secret configured - HTTP auth disabled")
        return {"user_id": "anonymous", "email": "anonymous@example.com", "authenticated": False}

    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract token
    token = jwt_handler.extract_token_from_header(authorization)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Use: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate token
    user_info = jwt_handler.validate_token(token)

    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_info["authenticated"] = True
    return user_info


def get_user_id_from_auth(user_info: Optional[Dict]) -> str:
    """
    Extract user ID from authentication info.
    Falls back to "anonymous" if not authenticated.

    Args:
        user_info: User info dict from authentication

    Returns:
        User ID string
    """
    if not user_info:
        return "anonymous"

    return user_info.get("user_id", "anonymous")
