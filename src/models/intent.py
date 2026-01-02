"""
Intent Model
Classified request type with extracted entities and parameters
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class IntentType(str, Enum):
    """Classification categories for user requests"""
    INFORMATIONAL = "INFORMATIONAL"  # Query requiring external data
    TASK_BASED = "TASK_BASED"  # System action
    CONVERSATIONAL = "CONVERSATIONAL"  # Social interaction


class ActionType(str, Enum):
    """Specific action types for task-based intents"""
    LAUNCH_APP = "LAUNCH_APP"  # Open application
    SYSTEM_STATUS = "SYSTEM_STATUS"  # Check CPU/memory/disk
    BROWSER_AUTOMATION = "BROWSER_AUTOMATION"  # Playwright MCP automation
    FILE_OPERATION = "FILE_OPERATION"  # File management
    CUSTOM_SCRIPT = "CUSTOM_SCRIPT"  # User-defined script


class Intent(BaseModel):
    """
    Intent entity
    Represents classified user request with extracted parameters
    """

    id: UUID = Field(default_factory=uuid4)
    voice_command_id: UUID = Field(..., description="Source voice command")
    intent_type: IntentType = Field(..., description="Classification category")
    entities: Dict[str, Any] = Field(default_factory=dict, description="Extracted entities")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Classification confidence")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    requires_network: bool = Field(False, description="Whether needs internet")
    action_type: Optional[ActionType] = Field(None, description="Specific action if task-based")

    @field_validator('action_type')
    @classmethod
    def validate_action_type(cls, v: Optional[ActionType], info) -> Optional[ActionType]:
        """action_type required if intent_type is TASK_BASED"""
        intent_type = info.data.get('intent_type')
        if intent_type == IntentType.TASK_BASED and v is None:
            raise ValueError("action_type required when intent_type is TASK_BASED")
        if intent_type != IntentType.TASK_BASED and v is not None:
            raise ValueError("action_type only valid when intent_type is TASK_BASED")
        return v

    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v: datetime) -> datetime:
        if v > datetime.utcnow():
            raise ValueError("timestamp must not be in the future")
        return v

    def is_actionable(self, confidence_threshold: float = 0.6) -> bool:
        """Check if intent has sufficient confidence to act upon"""
        return self.confidence_score >= confidence_threshold

    def get_entity(self, key: str, default: Any = None) -> Any:
        """Get entity value by key"""
        return self.entities.get(key, default)
