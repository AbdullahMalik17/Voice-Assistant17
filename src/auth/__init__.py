"""
Authentication module for Voice Assistant.
Handles JWT token validation for WebSocket and HTTP requests.
"""
from .jwt_handler import JWTHandler, jwt_handler
from .middleware import (
    authenticate_websocket,
    authenticate_http,
    get_user_id_from_auth,
    AuthenticationError
)

__all__ = [
    'JWTHandler',
    'jwt_handler',
    'authenticate_websocket',
    'authenticate_http',
    'get_user_id_from_auth',
    'AuthenticationError'
]
