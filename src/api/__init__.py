"""
Voice Assistant API module.
Provides WebSocket and REST endpoints for web interface.
"""

from .websocket_server import app, session_manager, VoiceAssistantHandler

__all__ = ["app", "session_manager", "VoiceAssistantHandler"]

