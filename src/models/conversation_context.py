"""
ConversationContext Model
Short-term memory of the last 5 exchanges for follow-up question resolution
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class ContextStatus(str, Enum):
    """Context lifecycle states"""
    ACTIVE = "ACTIVE"  # Context is valid and accepting updates
    EXPIRED = "EXPIRED"  # Timeout exceeded
    INTERRUPTED = "INTERRUPTED"  # Wake word during processing
    RESET = "RESET"  # Topic shift detected


class Exchange(BaseModel):
    """Single user-assistant exchange"""

    user_input: str = Field(..., description="Transcribed user speech")
    user_intent_id: UUID = Field(..., description="Reference to Intent object")
    assistant_response: str = Field(..., description="Generated response text")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall exchange confidence")


class ConversationContext(BaseModel):
    """
    Conversation context entity
    Maintains short-term memory for contextual follow-up questions
    """

    id: UUID = Field(default_factory=uuid4)
    session_id: UUID = Field(default_factory=uuid4)
    exchanges: List[Exchange] = Field(default_factory=list, max_length=5)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    timeout_seconds: int = Field(300, gt=0, description="Inactivity timeout (default: 5 minutes)")
    is_active: bool = Field(True)
    topic_keywords: List[str] = Field(default_factory=list, description="Extracted topics")
    status: ContextStatus = Field(default=ContextStatus.ACTIVE)

    @field_validator('exchanges')
    @classmethod
    def validate_exchanges_limit(cls, v: List[Exchange]) -> List[Exchange]:
        """Enforce maximum 5 exchanges (FIFO queue)"""
        if len(v) > 5:
            # Keep only the most recent 5
            return v[-5:]
        return v

    def add_exchange(
        self,
        user_input: str,
        user_intent_id: UUID,
        assistant_response: str,
        confidence: float
    ) -> None:
        """Add new exchange to context (FIFO queue)"""
        if not self.is_active:
            raise ValueError("Cannot add exchange to inactive context")

        exchange = Exchange(
            user_input=user_input,
            user_intent_id=user_intent_id,
            assistant_response=assistant_response,
            confidence=confidence
        )

        self.exchanges.append(exchange)

        # Enforce max 5 exchanges (FIFO)
        if len(self.exchanges) > 5:
            self.exchanges = self.exchanges[-5:]

        self.last_activity = datetime.utcnow()

    def is_expired(self) -> bool:
        """Check if context has expired due to inactivity"""
        if not self.is_active:
            return True

        time_since_activity = datetime.utcnow() - self.last_activity
        return time_since_activity.total_seconds() > self.timeout_seconds

    def expire(self) -> None:
        """Mark context as expired"""
        self.is_active = False
        self.status = ContextStatus.EXPIRED

    def interrupt(self) -> None:
        """Mark context as interrupted (wake word during processing)"""
        self.is_active = False
        self.status = ContextStatus.INTERRUPTED

    def reset(self) -> None:
        """Reset context (topic shift detected)"""
        self.exchanges.clear()
        self.topic_keywords.clear()
        self.last_activity = datetime.utcnow()
        self.status = ContextStatus.RESET
        self.is_active = True

    def get_recent_exchanges(self, count: int = 5) -> List[Exchange]:
        """Get the N most recent exchanges"""
        return self.exchanges[-count:]

    def get_context_summary(self) -> str:
        """Generate summary of conversation context for LLM prompt"""
        if not self.exchanges:
            return ""

        summary_parts = []
        for i, exchange in enumerate(self.exchanges, 1):
            summary_parts.append(f"Exchange {i}:")
            summary_parts.append(f"  User: {exchange.user_input}")
            summary_parts.append(f"  Assistant: {exchange.assistant_response}")

        return "\n".join(summary_parts)

    def update_topic_keywords(self, keywords: List[str]) -> None:
        """Update topic keywords for context matching"""
        self.topic_keywords = keywords
        self.last_activity = datetime.utcnow()

    def has_topic_shift(self, new_keywords: List[str], threshold: float = 0.7) -> bool:
        """
        Detect topic shift based on keyword overlap
        Returns True if overlap is below threshold
        """
        if not self.topic_keywords or not new_keywords:
            return False

        # Calculate Jaccard similarity
        set_current = set(self.topic_keywords)
        set_new = set(new_keywords)

        intersection = len(set_current & set_new)
        union = len(set_current | set_new)

        if union == 0:
            return False

        similarity = intersection / union
        return similarity < threshold
