"""
ActionScript Model
Mapped system command or script for task-based intents
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class Platform(str, Enum):
    """Target operating system"""
    WINDOWS = "WINDOWS"
    MACOS = "MACOS"
    LINUX = "LINUX"
    ALL = "ALL"  # Cross-platform


class ActionCategory(str, Enum):
    """Action categories"""
    APPLICATION = "APPLICATION"  # Launch/manage applications
    SYSTEM_INFO = "SYSTEM_INFO"  # Retrieve system status
    FILE_MGMT = "FILE_MGMT"  # File operations
    BROWSER = "BROWSER"  # Web automation via Playwright
    CUSTOM = "CUSTOM"  # User-defined scripts


class Parameter(BaseModel):
    """Command parameter definition"""

    name: str = Field(..., description="Parameter name")
    type: str = Field(..., description="Data type (string, int, bool)")
    required: bool = Field(True, description="Whether mandatory")
    default: Optional[Any] = Field(None, description="Default value if not provided")
    validation_regex: Optional[str] = Field(None, description="Validation pattern")

    @field_validator('type')
    @classmethod
    def validate_type(cls, v: str) -> str:
        valid_types = ['string', 'int', 'bool', 'float']
        if v not in valid_types:
            raise ValueError(f"type must be one of: {valid_types}")
        return v


class ActionScript(BaseModel):
    """
    Action script entity
    Mapped system command for task-based intent execution
    """

    id: UUID = Field(default_factory=uuid4)
    name: str = Field(..., description="Human-readable action name")
    command_template: str = Field(..., description="Command with placeholders")
    platform: Platform = Field(..., description="Target OS")
    requires_confirmation: bool = Field(False, description="Ask user before executing")
    timeout_seconds: int = Field(..., gt=0, le=300, description="Max execution time")
    parameters: List[Parameter] = Field(default_factory=list, description="Expected parameters")
    category: ActionCategory = Field(..., description="Action category")
    description: Optional[str] = Field(None, description="Action description")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError("name must not be empty")
        return v.strip()

    @field_validator('command_template')
    @classmethod
    def validate_command_template(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError("command_template must not be empty")
        # Check for potential command injection patterns
        dangerous_patterns = [';', '&&', '||', '|', '>', '<', '$(', '`']
        for pattern in dangerous_patterns:
            if pattern in v and '{' not in v:  # Allow in templates
                raise ValueError(f"Potentially unsafe pattern '{pattern}' in command_template")
        return v

    def format_command(self, params: Dict[str, Any]) -> str:
        """Format command template with provided parameters"""
        # Validate all required parameters are provided
        for param in self.parameters:
            if param.required and param.name not in params:
                if param.default is not None:
                    params[param.name] = param.default
                else:
                    raise ValueError(f"Required parameter '{param.name}' not provided")

        # Sanitize parameter values
        sanitized_params = {}
        for key, value in params.items():
            # Basic sanitization - remove shell metacharacters
            if isinstance(value, str):
                dangerous_chars = [';', '&', '|', '>', '<', '$', '`', '\\']
                sanitized = value
                for char in dangerous_chars:
                    sanitized = sanitized.replace(char, '')
                sanitized_params[key] = sanitized
            else:
                sanitized_params[key] = value

        # Format command
        try:
            command = self.command_template.format(**sanitized_params)
        except KeyError as e:
            raise ValueError(f"Missing parameter in template: {e}")

        return command

    def is_platform_compatible(self, current_platform: str) -> bool:
        """Check if action is compatible with current platform"""
        if self.platform == Platform.ALL:
            return True
        return self.platform.value.lower() == current_platform.lower()
