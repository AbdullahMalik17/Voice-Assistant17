"""
Execution Feedback Loop & Refinement

Analyzes plan execution failures and learns from them to improve future planning.
Captures failure patterns and suggests refinements for similar future tasks.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from .planner import PlanStep, StepStatus
from .tools import ToolResult

logger = logging.getLogger(__name__)


@dataclass
class FailurePattern:
    """A recorded execution failure pattern"""
    action_name: str
    parameters: Dict[str, Any]
    error_message: str
    error_type: str
    timestamp: datetime = field(default_factory=datetime.now)
    context_info: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "action": self.action_name,
            "parameters": self.parameters,
            "error": self.error_message,
            "error_type": self.error_type,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context_info
        }


@dataclass
class StepRefinement:
    """Suggested refinement for a step based on past failures"""
    step_id: str
    action: str
    suggestion: str
    reason: str
    confidence: float  # 0.0 to 1.0


class ExecutionFeedbackAnalyzer:
    """
    Analyzes execution failures and learns patterns to improve future planning.
    
    Features:
    - Records failure patterns for each action
    - Suggests refinements based on past failures
    - Identifies systemic issues (e.g., "app not installed")
    - Provides context for plan regeneration
    """
    
    def __init__(self, user_id: str = "default", retention_days: int = 30):
        """
        Initialize feedback analyzer.
        
        Args:
            user_id: User identifier for tracking personal patterns
            retention_days: How long to retain failure patterns
        """
        self.user_id = user_id
        self.retention_days = retention_days
        
        # Track failures by action
        self.failures: Dict[str, List[FailurePattern]] = {}
        self.last_cleanup = datetime.now()
    
    def record_failure(
        self,
        step: PlanStep,
        result: ToolResult,
        context_info: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record a step failure for learning.
        
        Args:
            step: The plan step that failed
            result: The tool result with error information
            context_info: Optional context about the failure (system state, etc.)
        """
        if result.success:
            return  # Only record failures
        
        action = step.action
        if action not in self.failures:
            self.failures[action] = []
        
        pattern = FailurePattern(
            action_name=action,
            parameters=step.parameters,
            error_message=result.error or "Unknown error",
            error_type=self._classify_error(result.error or ""),
            context_info=context_info or {}
        )
        
        self.failures[action].append(pattern)
        
        # Keep only recent failures
        self.failures[action] = self.failures[action][-20:]
        
        logger.info(
            f"Recorded failure for {action}: {result.error} "
            f"({len(self.failures[action])} total failures)"
        )
        
        self._cleanup_expired_failures()
    
    def _classify_error(self, error_message: str) -> str:
        """Classify error type from message"""
        error_lower = error_message.lower()
        
        if "not found" in error_lower or "not installed" in error_lower:
            return "not_available"
        elif "permission" in error_lower or "denied" in error_lower:
            return "permission_error"
        elif "timeout" in error_lower:
            return "timeout"
        elif "connection" in error_lower or "network" in error_lower:
            return "connectivity"
        elif "invalid" in error_lower or "malformed" in error_lower:
            return "invalid_input"
        elif "already" in error_lower:
            return "state_conflict"
        else:
            return "unknown"
    
    def get_step_refinements(
        self,
        action: str,
        parameters: Dict[str, Any]
    ) -> List[StepRefinement]:
        """
        Get suggested refinements for a step based on past failures.
        
        Args:
            action: The action name
            parameters: The action parameters
            
        Returns:
            List of suggested refinements
        """
        if action not in self.failures or not self.failures[action]:
            return []
        
        refinements = []
        patterns = self.failures[action]
        
        # Analyze failure patterns
        error_types: Dict[str, int] = {}
        for pattern in patterns:
            error_types[pattern.error_type] = error_types.get(pattern.error_type, 0) + 1
        
        # Generate suggestions based on error types
        total_failures = len(patterns)
        
        for error_type, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
            confidence = min(count / max(total_failures, 1), 1.0)
            
            if error_type == "not_available":
                refinement = StepRefinement(
                    step_id="",
                    action=action,
                    suggestion=f"Add precondition check: verify {action} availability before execution",
                    reason=f"{count} past attempts failed due to unavailability",
                    confidence=confidence
                )
                refinements.append(refinement)
            
            elif error_type == "permission_error":
                refinement = StepRefinement(
                    step_id="",
                    action=action,
                    suggestion="Ensure proper permissions/authentication before executing this action",
                    reason=f"{count} past attempts failed due to permission errors",
                    confidence=confidence
                )
                refinements.append(refinement)
            
            elif error_type == "timeout":
                refinement = StepRefinement(
                    step_id="",
                    action=action,
                    suggestion="Increase timeout or break into smaller parallel steps",
                    reason=f"{count} past attempts timed out",
                    confidence=confidence
                )
                refinements.append(refinement)
            
            elif error_type == "invalid_input":
                refinement = StepRefinement(
                    step_id="",
                    action=action,
                    suggestion="Validate input parameters before execution",
                    reason=f"{count} past attempts had invalid parameters",
                    confidence=confidence
                )
                refinements.append(refinement)
        
        return refinements
    
    def get_action_reliability(self, action: str) -> Dict[str, Any]:
        """Get reliability metrics for an action"""
        if action not in self.failures or not self.failures[action]:
            return {"action": action, "status": "no_failures_recorded"}
        
        patterns = self.failures[action]
        error_types: Dict[str, int] = {}
        
        for pattern in patterns:
            error_types[pattern.error_type] = error_types.get(pattern.error_type, 0) + 1
        
        return {
            "action": action,
            "total_failures": len(patterns),
            "failure_rate": "high" if len(patterns) > 5 else "medium" if len(patterns) > 2 else "low",
            "most_common_errors": sorted(
                error_types.items(),
                key=lambda x: x[1],
                reverse=True
            )[:3],
            "last_failure": patterns[-1].timestamp.isoformat() if patterns else None
        }
    
    def should_use_alternative_tool(self, action: str) -> bool:
        """Determine if we should try an alternative tool"""
        if action not in self.failures:
            return False
        
        patterns = self.failures[action]
        # If more than 50% of recent attempts failed, suggest alternative
        return len(patterns) > 3 and len([p for p in patterns[-5:] if p.error_type == "not_available"]) > 2
    
    def _cleanup_expired_failures(self) -> None:
        """Remove old failure patterns"""
        # Only cleanup periodically (not every call)
        if (datetime.now() - self.last_cleanup).seconds < 3600:
            return
        
        cutoff_date = datetime.now() - timedelta(days=self.retention_days)
        
        for action in self.failures:
            self.failures[action] = [
                p for p in self.failures[action]
                if p.timestamp > cutoff_date
            ]
        
        self.last_cleanup = datetime.now()
    
    def export_feedback_report(self) -> Dict[str, Any]:
        """Export a comprehensive feedback report"""
        report = {
            "user_id": self.user_id,
            "timestamp": datetime.now().isoformat(),
            "total_actions_with_failures": len(self.failures),
            "actions": {}
        }
        
        for action, patterns in self.failures.items():
            if patterns:
                report["actions"][action] = self.get_action_reliability(action)
        
        return report
