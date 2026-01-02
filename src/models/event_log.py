"""
EventLog Model
Structured record of system events and performance metrics
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class EventType(str, Enum):
    """Categories of system events"""
    WAKE_WORD_DETECTED = "WAKE_WORD_DETECTED"
    STT_PROCESSED = "STT_PROCESSED"
    INTENT_CLASSIFIED = "INTENT_CLASSIFIED"
    LLM_QUERY = "LLM_QUERY"
    TTS_GENERATED = "TTS_GENERATED"
    ACTION_EXECUTED = "ACTION_EXECUTED"
    CONTEXT_UPDATED = "CONTEXT_UPDATED"
    NETWORK_STATUS_CHANGED = "NETWORK_STATUS_CHANGED"
    REQUEST_QUEUED = "REQUEST_QUEUED"
    ERROR_OCCURRED = "ERROR_OCCURRED"
    SYSTEM_STARTUP = "SYSTEM_STARTUP"
    SYSTEM_SHUTDOWN = "SYSTEM_SHUTDOWN"


class Severity(str, Enum):
    """Log level severity"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class EventLog(BaseModel):
    """
    Event log entity
    Structured record of system events with metadata and metrics
    """

    id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_type: EventType = Field(..., description="Category of event")
    severity: Severity = Field(..., description="Log level")
    message: str = Field(..., description="Human-readable description")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional structured data")
    duration_ms: Optional[int] = Field(None, ge=0, description="Event duration if applicable")
    success: bool = Field(True, description="Whether operation succeeded")
    component: str = Field(..., description="System component that generated event")

    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v: datetime) -> datetime:
        if v > datetime.utcnow():
            raise ValueError("timestamp must not be in the future")
        return v

    @field_validator('message')
    @classmethod
    def validate_message(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError("message must not be empty")
        return v

    @classmethod
    def wake_word_detected(cls, confidence: float, duration_ms: int) -> "EventLog":
        """Factory: Create wake word detection event"""
        return cls(
            event_type=EventType.WAKE_WORD_DETECTED,
            severity=Severity.INFO,
            message="Wake word detected",
            component="wake_word",
            metadata={"confidence": confidence},
            duration_ms=duration_ms,
            success=True
        )

    @classmethod
    def stt_processed(
        cls,
        text: str,
        confidence: float,
        duration_ms: int,
        mode: str,
        success: bool = True
    ) -> "EventLog":
        """Factory: Create STT processing event"""
        return cls(
            event_type=EventType.STT_PROCESSED,
            severity=Severity.INFO if success else Severity.ERROR,
            message=f"Speech-to-text {'completed' if success else 'failed'}",
            component="stt",
            metadata={"transcribed_text": text, "confidence": confidence, "mode": mode},
            duration_ms=duration_ms,
            success=success
        )

    @classmethod
    def intent_classified(
        cls,
        intent_type: str,
        confidence: float,
        entities: Dict[str, Any]
    ) -> "EventLog":
        """Factory: Create intent classification event"""
        return cls(
            event_type=EventType.INTENT_CLASSIFIED,
            severity=Severity.INFO,
            message="Intent classified",
            component="intent_classifier",
            metadata={"intent_type": intent_type, "confidence": confidence, "entities": entities},
            success=True
        )

    @classmethod
    def llm_query(
        cls,
        response_length: int,
        duration_ms: int,
        mode: str,
        success: bool = True
    ) -> "EventLog":
        """Factory: Create LLM query event"""
        return cls(
            event_type=EventType.LLM_QUERY,
            severity=Severity.INFO if success else Severity.ERROR,
            message=f"LLM response {'generated' if success else 'failed'}",
            component="llm",
            metadata={"response_length": response_length, "mode": mode},
            duration_ms=duration_ms,
            success=success
        )

    @classmethod
    def tts_generated(
        cls,
        text_length: int,
        audio_duration_ms: int,
        mode: str,
        success: bool = True
    ) -> "EventLog":
        """Factory: Create TTS generation event"""
        return cls(
            event_type=EventType.TTS_GENERATED,
            severity=Severity.INFO if success else Severity.ERROR,
            message=f"Text-to-speech {'completed' if success else 'failed'}",
            component="tts",
            metadata={"text_length": text_length, "audio_duration_ms": audio_duration_ms, "mode": mode},
            success=success
        )

    @classmethod
    def action_executed(
        cls,
        action_type: str,
        duration_ms: int,
        success: bool = True
    ) -> "EventLog":
        """Factory: Create action execution event"""
        return cls(
            event_type=EventType.ACTION_EXECUTED,
            severity=Severity.INFO if success else Severity.WARNING,
            message=f"Action '{action_type}' {'executed successfully' if success else 'failed'}",
            component="action_executor",
            metadata={"action_type": action_type},
            duration_ms=duration_ms,
            success=success
        )

    @classmethod
    def context_updated(cls, exchanges_count: int, timeout_seconds: int) -> "EventLog":
        """Factory: Create context update event"""
        return cls(
            event_type=EventType.CONTEXT_UPDATED,
            severity=Severity.DEBUG,
            message="Conversation context updated",
            component="context_manager",
            metadata={"exchanges_count": exchanges_count, "timeout_seconds": timeout_seconds},
            success=True
        )

    @classmethod
    def network_status_changed(cls, is_online: bool) -> "EventLog":
        """Factory: Create network status change event"""
        return cls(
            event_type=EventType.NETWORK_STATUS_CHANGED,
            severity=Severity.WARNING,
            message=f"Network status changed to {'online' if is_online else 'offline'}",
            component="network_monitor",
            metadata={"is_online": is_online},
            success=True
        )

    @classmethod
    def request_queued(cls, request_type: str, queue_size: int) -> "EventLog":
        """Factory: Create request queuing event"""
        return cls(
            event_type=EventType.REQUEST_QUEUED,
            severity=Severity.WARNING,
            message="Request queued due to network outage",
            component="request_queue",
            metadata={"request_type": request_type, "queue_size": queue_size},
            success=True
        )

    @classmethod
    def error_occurred(
        cls,
        error_type: str,
        error_message: str,
        component: str
    ) -> "EventLog":
        """Factory: Create error event"""
        return cls(
            event_type=EventType.ERROR_OCCURRED,
            severity=Severity.ERROR,
            message=error_message,
            component=component,
            metadata={"error_type": error_type},
            success=False
        )
