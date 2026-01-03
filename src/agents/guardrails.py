"""
Safety Guardrails Module
Provides safety checks and confirmation requirements for agentic actions.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class ActionRisk(str, Enum):
    """Risk levels for actions"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ConfirmationType(str, Enum):
    """Types of confirmation required"""
    NONE = "none"
    SIMPLE = "simple"  # Yes/No confirmation
    DETAILED = "detailed"  # Show details and confirm
    EXPLICIT = "explicit"  # Require specific phrase


@dataclass
class SafetyCheck:
    """Result of a safety check"""
    is_safe: bool
    risk_level: ActionRisk
    requires_confirmation: bool
    confirmation_type: ConfirmationType
    warnings: List[str] = field(default_factory=list)
    blocked_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_safe": self.is_safe,
            "risk_level": self.risk_level.value,
            "requires_confirmation": self.requires_confirmation,
            "confirmation_type": self.confirmation_type.value,
            "warnings": self.warnings,
            "blocked_reason": self.blocked_reason
        }


@dataclass
class RateLimitState:
    """Track rate limiting for actions"""
    action_counts: Dict[str, int] = field(default_factory=dict)
    window_start: datetime = field(default_factory=datetime.now)
    window_duration: timedelta = field(default=timedelta(minutes=1))

    def increment(self, action: str) -> None:
        """Increment action count"""
        self.action_counts[action] = self.action_counts.get(action, 0) + 1

    def get_count(self, action: str) -> int:
        """Get count for an action"""
        return self.action_counts.get(action, 0)

    def reset_if_expired(self) -> None:
        """Reset counts if window has expired"""
        if datetime.now() - self.window_start > self.window_duration:
            self.action_counts.clear()
            self.window_start = datetime.now()


class SafetyGuardrails:
    """
    Safety guardrails for agentic actions.

    Provides:
    - Action classification by risk level
    - Confirmation requirements for sensitive actions
    - Command blocklist for dangerous operations
    - Rate limiting to prevent abuse
    - Scope validation for allowed operations
    """

    def __init__(
        self,
        blocked_patterns: Optional[List[str]] = None,
        sensitive_actions: Optional[Set[str]] = None,
        max_actions_per_minute: int = 10,
        require_confirmation_for_high_risk: bool = True
    ):
        # Default blocked command patterns (dangerous operations)
        self.blocked_patterns = blocked_patterns or [
            r"rm\s+-rf",
            r"rm\s+-r\s+/",
            r"del\s+/[fqs]",
            r"format\s+[a-z]:",
            r"mkfs\.",
            r"dd\s+if=",
            r":(){.*};:",  # Fork bomb
            r">\s*/dev/sd",
            r"chmod\s+-R\s+777\s+/",
            r"shutdown",
            r"reboot",
            r"halt",
            r"poweroff",
            r"init\s+0",
            r"curl.*\|\s*(ba)?sh",  # Pipe to shell
            r"wget.*\|\s*(ba)?sh",
        ]

        # Actions that are considered sensitive
        self.sensitive_actions = sensitive_actions or {
            "send_email",
            "send_message",
            "delete_file",
            "delete_folder",
            "move_file",
            "make_purchase",
            "transfer_money",
            "share_file",
            "post_social",
            "calendar_delete",
            "uninstall_app",
            "change_password",
            "grant_permission",
        }

        # Actions that are always blocked
        self.blocked_actions = {
            "execute_arbitrary_code",
            "modify_system_files",
            "access_other_users",
            "disable_security",
        }

        # Rate limiting
        self.max_actions_per_minute = max_actions_per_minute
        self.rate_limit_state = RateLimitState()

        self.require_confirmation_for_high_risk = require_confirmation_for_high_risk

    def check_action(
        self,
        action: str,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None
    ) -> SafetyCheck:
        """
        Check if an action is safe to execute.

        Args:
            action: The action/tool name
            params: Parameters for the action
            context: Additional context (user confirmation, etc.)

        Returns:
            SafetyCheck with safety assessment
        """
        warnings = []

        # Check if action is blocked
        if action in self.blocked_actions:
            return SafetyCheck(
                is_safe=False,
                risk_level=ActionRisk.CRITICAL,
                requires_confirmation=False,
                confirmation_type=ConfirmationType.NONE,
                blocked_reason=f"Action '{action}' is not allowed"
            )

        # Check rate limiting
        self.rate_limit_state.reset_if_expired()
        if self.rate_limit_state.get_count(action) >= self.max_actions_per_minute:
            return SafetyCheck(
                is_safe=False,
                risk_level=ActionRisk.HIGH,
                requires_confirmation=False,
                confirmation_type=ConfirmationType.NONE,
                blocked_reason=f"Rate limit exceeded for '{action}'"
            )

        # Check for blocked patterns in parameters
        blocked_pattern = self._check_blocked_patterns(params)
        if blocked_pattern:
            return SafetyCheck(
                is_safe=False,
                risk_level=ActionRisk.CRITICAL,
                requires_confirmation=False,
                confirmation_type=ConfirmationType.NONE,
                blocked_reason=f"Dangerous pattern detected: {blocked_pattern}"
            )

        # Determine risk level
        risk_level = self._assess_risk_level(action, params)

        # Determine confirmation requirements
        requires_confirmation = False
        confirmation_type = ConfirmationType.NONE

        if action in self.sensitive_actions:
            requires_confirmation = True
            confirmation_type = ConfirmationType.DETAILED
            warnings.append(f"'{action}' is a sensitive action and requires confirmation")

        if risk_level == ActionRisk.HIGH and self.require_confirmation_for_high_risk:
            requires_confirmation = True
            confirmation_type = ConfirmationType.DETAILED

        if risk_level == ActionRisk.CRITICAL:
            requires_confirmation = True
            confirmation_type = ConfirmationType.EXPLICIT

        # Check if user has already confirmed (from context)
        if context and context.get("user_confirmed"):
            requires_confirmation = False

        # Increment rate limit counter
        self.rate_limit_state.increment(action)

        return SafetyCheck(
            is_safe=True,
            risk_level=risk_level,
            requires_confirmation=requires_confirmation,
            confirmation_type=confirmation_type,
            warnings=warnings
        )

    def _check_blocked_patterns(self, params: Dict[str, Any]) -> Optional[str]:
        """Check if any parameter contains blocked patterns"""
        for key, value in params.items():
            if isinstance(value, str):
                for pattern in self.blocked_patterns:
                    if re.search(pattern, value, re.IGNORECASE):
                        return pattern
        return None

    def _assess_risk_level(
        self,
        action: str,
        params: Dict[str, Any]
    ) -> ActionRisk:
        """Assess the risk level of an action"""

        # Critical risk actions
        critical_actions = {
            "delete_all", "format", "wipe", "uninstall",
            "transfer_money", "make_payment"
        }

        # High risk actions
        high_risk_actions = {
            "send_email", "delete_file", "delete_folder",
            "share_file", "post_social", "move_file"
        }

        # Medium risk actions
        medium_risk_actions = {
            "create_file", "modify_file", "calendar_event",
            "set_reminder", "download_file"
        }

        if action in critical_actions:
            return ActionRisk.CRITICAL

        if action in high_risk_actions:
            return ActionRisk.HIGH

        if action in medium_risk_actions:
            return ActionRisk.MEDIUM

        # Check for risky patterns in action name
        if any(word in action.lower() for word in ["delete", "remove", "send", "share"]):
            return ActionRisk.HIGH

        return ActionRisk.LOW

    def get_confirmation_prompt(
        self,
        action: str,
        params: Dict[str, Any],
        check: SafetyCheck
    ) -> str:
        """Generate a confirmation prompt for the user"""

        if check.confirmation_type == ConfirmationType.SIMPLE:
            return f"Do you want to {action.replace('_', ' ')}? (yes/no)"

        elif check.confirmation_type == ConfirmationType.DETAILED:
            details = ", ".join(f"{k}={v}" for k, v in params.items())
            prompt = f"I'm about to {action.replace('_', ' ')}"
            if details:
                prompt += f" with: {details}"
            prompt += ". Is that okay?"
            return prompt

        elif check.confirmation_type == ConfirmationType.EXPLICIT:
            return f"This is a sensitive action. To proceed with {action}, please say 'confirm {action}'"

        return ""

    def validate_confirmation(
        self,
        user_response: str,
        action: str,
        check: SafetyCheck
    ) -> bool:
        """Validate user confirmation response"""

        response_lower = user_response.lower().strip()

        if check.confirmation_type == ConfirmationType.SIMPLE:
            return response_lower in ["yes", "yeah", "yep", "ok", "okay", "sure", "do it"]

        elif check.confirmation_type == ConfirmationType.DETAILED:
            return response_lower in ["yes", "yeah", "yep", "ok", "okay", "that's okay", "go ahead", "proceed"]

        elif check.confirmation_type == ConfirmationType.EXPLICIT:
            expected = f"confirm {action}"
            return expected.lower() in response_lower

        return True

    def add_blocked_pattern(self, pattern: str) -> None:
        """Add a new blocked pattern"""
        self.blocked_patterns.append(pattern)

    def add_sensitive_action(self, action: str) -> None:
        """Add a new sensitive action"""
        self.sensitive_actions.add(action)

    def reset_rate_limit(self) -> None:
        """Reset rate limiting state"""
        self.rate_limit_state = RateLimitState()


def create_safety_guardrails(
    max_actions_per_minute: int = 10,
    require_confirmation: bool = True
) -> SafetyGuardrails:
    """Factory function to create SafetyGuardrails"""
    return SafetyGuardrails(
        max_actions_per_minute=max_actions_per_minute,
        require_confirmation_for_high_risk=require_confirmation
    )
