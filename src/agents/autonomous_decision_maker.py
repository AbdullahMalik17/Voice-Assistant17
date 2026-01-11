"""
Autonomous Decision-Making Layer

Determines which actions can be executed autonomously based on:
- User history and trust patterns
- Action risk level
- Context confidence
- Recent interaction patterns
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class TrustLevel(str, Enum):
    """User trust level for an action."""
    UNKNOWN = "unknown"       # Never seen before
    LOW = "low"               # Few attempts, mixed results
    MEDIUM = "medium"         # Several successful attempts
    HIGH = "high"             # Many successful attempts
    EXPERT = "expert"         # User always approves/succeeds


@dataclass
class ActionHistory:
    """Track history of an action."""
    action_name: str
    total_attempts: int = 0
    successful_attempts: int = 0
    user_approved: int = 0       # Times user approved confirmation
    user_rejected: int = 0       # Times user rejected confirmation
    last_executed: Optional[datetime] = None
    failures: List[str] = field(default_factory=list)  # Recent failure reasons
    
    def get_success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_attempts == 0:
            return 0.0
        return self.successful_attempts / self.total_attempts
    
    def get_approval_rate(self) -> float:
        """Calculate user approval rate."""
        total_confirmations = self.user_approved + self.user_rejected
        if total_confirmations == 0:
            return 0.0
        return self.user_approved / total_confirmations
    
    def get_trust_level(self) -> TrustLevel:
        """Determine trust level."""
        if self.total_attempts == 0:
            return TrustLevel.UNKNOWN
        
        approval_rate = self.get_approval_rate()
        success_rate = self.get_success_rate()
        
        if self.total_attempts >= 10 and approval_rate >= 0.9 and success_rate >= 0.9:
            return TrustLevel.EXPERT
        elif self.total_attempts >= 5 and approval_rate >= 0.8 and success_rate >= 0.7:
            return TrustLevel.HIGH
        elif self.total_attempts >= 3 and success_rate >= 0.6:
            return TrustLevel.MEDIUM
        else:
            return TrustLevel.LOW


@dataclass
class UserContext:
    """Current user context for decision-making."""
    user_id: str
    current_time: datetime = field(default_factory=datetime.now)
    recent_actions: List[str] = field(default_factory=list)
    current_topic: str = ""
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    active_sessions: int = 0
    is_interactive: bool = True  # Is user actively interacting?
    context_confidence: float = 0.5  # How well do we understand current context?


@dataclass
class AutonomyDecision:
    """Result of autonomy decision."""
    should_auto_execute: bool
    trust_score: float  # 0.0 to 1.0
    trust_level: TrustLevel
    reasoning: str
    confidence: float  # How confident is the decision?
    fallback_action: Optional[str] = None  # Alternative if this fails


class AutonomousDecisionMaker:
    """
    Decides which actions can execute autonomously based on user patterns.
    
    The core idea: as users approve and succeed with actions, trust builds,
    and fewer confirmations are required.
    """
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.action_history: Dict[str, ActionHistory] = {}
        self.daily_action_limits: Dict[str, int] = {
            "critical": 3,      # Delete, format disk, etc.
            "high": 10,         # Send email, post on social
            "medium": 50,       # Open apps, set timers
            "low": 999          # Read system info
        }
        self.today_action_counts: Dict[str, int] = {}
        self.last_reset = datetime.now()
        self._reset_daily_limits_if_needed()
    
    def _reset_daily_limits_if_needed(self):
        """Reset daily limits if it's a new day."""
        if (datetime.now() - self.last_reset).days >= 1:
            self.today_action_counts.clear()
            self.last_reset = datetime.now()
    
    def record_execution(
        self,
        action: str,
        success: bool,
        user_approved_confirmation: bool = False,
        user_rejected_confirmation: bool = False,
        failure_reason: Optional[str] = None
    ):
        """
        Record the outcome of an action execution.
        
        This is how trust is built.
        """
        if action not in self.action_history:
            self.action_history[action] = ActionHistory(action_name=action)
        
        history = self.action_history[action]
        history.total_attempts += 1
        history.last_executed = datetime.now()
        
        if success:
            history.successful_attempts += 1
        
        if user_approved_confirmation:
            history.user_approved += 1
        if user_rejected_confirmation:
            history.user_rejected += 1
        
        if failure_reason:
            history.failures.append(failure_reason)
            # Keep last 10 failures
            history.failures = history.failures[-10:]
        
        logger.info(
            f"Recorded {action}: "
            f"success={success}, "
            f"trust_level={history.get_trust_level().value}"
        )
    
    def decide_autonomy(
        self,
        action: str,
        parameters: Dict[str, Any],
        risk_level: str,  # "low", "medium", "high", "critical"
        context: UserContext
    ) -> AutonomyDecision:
        """
        Decide if an action should execute autonomously.
        
        Returns AutonomyDecision with reasoning.
        """
        self._reset_daily_limits_if_needed()
        
        # Get action history
        history = self.action_history.get(action, ActionHistory(action_name=action))
        trust_level = history.get_trust_level()
        
        # Calculate scores
        success_score = history.get_success_rate()  # 0-1
        approval_score = history.get_approval_rate()  # 0-1
        context_score = context.context_confidence  # 0-1
        
        # Risk-based thresholds
        thresholds = {
            "low": {"min_score": 0.4, "min_success": 0.5},
            "medium": {"min_score": 0.6, "min_success": 0.7},
            "high": {"min_score": 0.75, "min_success": 0.85},
            "critical": {"min_score": 0.9, "min_success": 0.95}
        }
        
        threshold = thresholds.get(risk_level, thresholds["medium"])
        
        # Compute trust score
        # Weight: 40% success, 40% approval, 20% context
        trust_score = (
            success_score * 0.4 +
            approval_score * 0.4 +
            context_score * 0.2
        )
        
        # Decision logic
        should_auto = (
            trust_score >= threshold["min_score"] and
            success_score >= threshold["min_success"] and
            history.total_attempts > 0  # Must have precedent
        )
        
        # Additional checks
        if should_auto:
            # Check daily limits
            limit = self.daily_action_limits.get(risk_level, 50)
            today_count = self.today_action_counts.get(action, 0)
            if today_count >= limit:
                should_auto = False
                reasoning = f"Daily limit reached for {action} ({today_count}/{limit})"
                confidence = 0.95
            else:
                reasoning = (
                    f"User has {history.total_attempts} successful experiences with this action. "
                    f"Success rate: {success_score:.0%}, Approval rate: {approval_score:.0%}. "
                    f"Trust score: {trust_score:.2f} (threshold: {threshold['min_score']})"
                )
                confidence = min(trust_score, success_score)
        else:
            reasoning = (
                f"Insufficient trust for autonomous execution. "
                f"Trust score: {trust_score:.2f} (need {threshold['min_score']}). "
                f"Success rate: {success_score:.0%} (need {threshold['min_success']:.0%}). "
                f"Attempts: {history.total_attempts}"
            )
            confidence = 1.0 - trust_score
        
        if should_auto:
            self.today_action_counts[action] = self.today_action_counts.get(action, 0) + 1
        
        return AutonomyDecision(
            should_auto_execute=should_auto,
            trust_score=trust_score,
            trust_level=trust_level,
            reasoning=reasoning,
            confidence=confidence
        )
    
    def get_action_stats(self, action: str) -> Dict[str, Any]:
        """Get statistics for an action."""
        if action not in self.action_history:
            return {"status": "no_history"}
        
        history = self.action_history[action]
        return {
            "action": action,
            "trust_level": history.get_trust_level().value,
            "total_attempts": history.total_attempts,
            "success_rate": f"{history.get_success_rate():.0%}",
            "approval_rate": f"{history.get_approval_rate():.0%}",
            "last_executed": history.last_executed.isoformat() if history.last_executed else None,
            "recent_failures": history.failures[-3:]
        }
    
    def get_user_profile(self) -> Dict[str, Any]:
        """Get overall user profile for autonomy."""
        all_attempts = sum(h.total_attempts for h in self.action_history.values())
        all_successes = sum(h.successful_attempts for h in self.action_history.values())
        all_approved = sum(h.user_approved for h in self.action_history.values())
        all_rejected = sum(h.user_rejected for h in self.action_history.values())
        
        return {
            "user_id": self.user_id,
            "total_experiences": all_attempts,
            "overall_success_rate": f"{all_successes/all_attempts:.0%}" if all_attempts > 0 else "unknown",
            "overall_approval_rate": f"{all_approved/(all_approved+all_rejected):.0%}" if (all_approved+all_rejected) > 0 else "unknown",
            "actions_with_high_trust": [
                h.action_name for h in self.action_history.values()
                if h.get_trust_level() in [TrustLevel.HIGH, TrustLevel.EXPERT]
            ],
            "actions_to_avoid": [
                h.action_name for h in self.action_history.values()
                if h.get_approval_rate() < 0.3
            ]
        }


# Global decision makers per user (in production, use database)
_decision_makers: Dict[str, AutonomousDecisionMaker] = {}


def get_decision_maker(user_id: str) -> AutonomousDecisionMaker:
    """Get or create decision maker for user."""
    if user_id not in _decision_makers:
        _decision_makers[user_id] = AutonomousDecisionMaker(user_id)
    return _decision_makers[user_id]
