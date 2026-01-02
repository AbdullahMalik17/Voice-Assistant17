"""
VoiceCommand Model
Represents a user's spoken input captured after wake word detection
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, field_serializer


class VoiceCommandStatus(str, Enum):
    """Processing status for voice commands"""
    CAPTURED = "CAPTURED"  # Audio recorded, awaiting transcription
    TRANSCRIBING = "TRANSCRIBING"  # STT service processing
    TRANSCRIBED = "TRANSCRIBED"  # Text available, ready for intent classification
    FAILED = "FAILED"  # STT failed or audio invalid
    CANCELLED = "CANCELLED"  # Interrupted by new wake word


class VoiceCommand(BaseModel):
    """
    Voice command entity
    Represents captured audio and transcription state
    """

    id: UUID = Field(default_factory=uuid4)
    audio_data: bytes = Field(..., description="Raw audio buffer from microphone")
    transcribed_text: Optional[str] = Field(None, description="Speech-to-text output")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    duration_ms: int = Field(..., gt=0, le=60000, description="Audio duration in milliseconds")
    confidence_score: float = Field(0.0, ge=0.0, le=1.0, description="STT confidence level")
    status: VoiceCommandStatus = Field(default=VoiceCommandStatus.CAPTURED)

    @field_validator('audio_data')
    @classmethod
    def validate_audio_data(cls, v: bytes) -> bytes:
        if len(v) == 0:
            raise ValueError("audio_data must not be empty")
        return v

    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v: datetime) -> datetime:
        if v > datetime.utcnow():
            raise ValueError("timestamp must not be in the future")
        return v

    @field_serializer('audio_data')
    def serialize_audio_data(self, v: bytes, _info) -> str:
        return f"<{len(v)} bytes>"

    def to_transcribing(self) -> None:
        """Transition to TRANSCRIBING state"""
        if self.status != VoiceCommandStatus.CAPTURED:
            raise ValueError(f"Cannot transition to TRANSCRIBING from {self.status}")
        self.status = VoiceCommandStatus.TRANSCRIBING

    def to_transcribed(self, text: str, confidence: float) -> None:
        """Transition to TRANSCRIBED state"""
        if self.status != VoiceCommandStatus.TRANSCRIBING:
            raise ValueError(f"Cannot transition to TRANSCRIBED from {self.status}")
        self.transcribed_text = text
        self.confidence_score = confidence
        self.status = VoiceCommandStatus.TRANSCRIBED

    def to_failed(self) -> None:
        """Transition to FAILED state"""
        if self.status in [VoiceCommandStatus.TRANSCRIBED, VoiceCommandStatus.CANCELLED]:
            raise ValueError(f"Cannot transition to FAILED from {self.status}")
        self.status = VoiceCommandStatus.FAILED

    def to_cancelled(self) -> None:
        """Transition to CANCELLED state"""
        if self.status in [VoiceCommandStatus.TRANSCRIBED, VoiceCommandStatus.FAILED]:
            raise ValueError(f"Cannot transition to CANCELLED from {self.status}")
        self.status = VoiceCommandStatus.CANCELLED