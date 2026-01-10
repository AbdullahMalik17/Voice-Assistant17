"""Pydantic models for conversation sessions and turns"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID


class ConversationSession(BaseModel):
    """Model for conversation session stored in Supabase"""

    session_id: UUID
    user_id: UUID
    title: Optional[str] = None
    created_at: datetime
    last_updated: datetime
    state: str = "active"
    current_intent: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "title": "Morning Conversation",
                "created_at": "2026-01-10T10:00:00Z",
                "last_updated": "2026-01-10T10:15:00Z",
                "state": "active",
                "current_intent": "general_query",
                "metadata": {
                    "device": "web",
                    "ip": "192.168.1.1"
                }
            }
        }


class ConversationTurn(BaseModel):
    """Model for individual conversation turn (user message + assistant response)"""

    turn_id: UUID
    session_id: UUID
    user_input: str
    assistant_response: str
    intent: Optional[str] = None
    intent_confidence: float = 0.0
    entities: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "turn_id": "660e8400-e29b-41d4-a716-446655440000",
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "user_input": "What's the weather like?",
                "assistant_response": "I can help you check the weather. Where are you located?",
                "intent": "weather_query",
                "intent_confidence": 0.95,
                "entities": {
                    "query_type": "weather",
                    "requires_location": True
                },
                "timestamp": "2026-01-10T10:05:00Z"
            }
        }


class ConversationTurnCreate(BaseModel):
    """Model for creating a new conversation turn (without turn_id and timestamp)"""

    session_id: UUID
    user_input: str
    assistant_response: str
    intent: Optional[str] = None
    intent_confidence: float = 0.0
    entities: Dict[str, Any] = Field(default_factory=dict)


class ConversationSessionCreate(BaseModel):
    """Model for creating a new conversation session (without session_id and timestamps)"""

    user_id: UUID
    title: Optional[str] = None
    state: str = "active"
    current_intent: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
