"""
Agent State Persistence & Resume

Enables saving and restoring agent execution state to recover from crashes
and resume multi-step plans from where they left off.
"""

import json
import logging
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

from .planner import Plan, PlanStep, PlanStatus, StepStatus

logger = logging.getLogger(__name__)


class AgentStatePersistence:
    """
    Manages persistence and restoration of agent execution state.
    
    Provides:
    - Save execution state to disk
    - Load and resume plans from saved state
    - Automatic state snapshots during execution
    - Plan history and recovery
    """
    
    def __init__(self, storage_dir: str = "data/agent_state"):
        """
        Initialize state persistence.
        
        Args:
            storage_dir: Directory to store state files
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        self.plans_dir = self.storage_dir / "plans"
        self.plans_dir.mkdir(exist_ok=True)
        
        self.checkpoints_dir = self.storage_dir / "checkpoints"
        self.checkpoints_dir.mkdir(exist_ok=True)
    
    def save_plan_state(
        self,
        plan: Plan,
        context: Optional[Dict[str, Any]] = None,
        checkpoint_name: Optional[str] = None
    ) -> str:
        """
        Save plan execution state to disk.
        
        Args:
            plan: The plan to save
            context: Optional execution context (user info, system state, etc.)
            checkpoint_name: Optional name for this checkpoint
            
        Returns:
            Path to saved state file
        """
        # Prepare state dictionary
        state = {
            "plan_id": plan.id,
            "goal": plan.goal,
            "status": plan.status.value,
            "current_step_index": plan.current_step_index,
            "steps": [],
            "created_at": plan.created_at.isoformat(),
            "started_at": plan.started_at.isoformat() if plan.started_at else None,
            "completed_at": plan.completed_at.isoformat() if plan.completed_at else None,
            "saved_at": datetime.now().isoformat(),
            "context": context or {},
            "metadata": plan.metadata
        }
        
        # Serialize steps with their current state
        for step in plan.steps:
            step_dict = {
                "id": step.id,
                "action": step.action,
                "description": step.description,
                "parameters": step.parameters,
                "depends_on": step.depends_on,
                "requires_confirmation": step.requires_confirmation,
                "status": step.status.value,
                "error": step.error,
                "started_at": step.started_at.isoformat() if step.started_at else None,
                "completed_at": step.completed_at.isoformat() if step.completed_at else None,
            }
            
            # Include tool result if available
            if step.result:
                step_dict["result"] = {
                    "success": step.result.success,
                    "output": step.result.output,
                    "error": step.result.error
                }
            
            state["steps"].append(step_dict)
        
        # Determine filename
        if checkpoint_name:
            filename = f"{plan.id}_{checkpoint_name}.json"
        else:
            filename = f"{plan.id}_latest.json"
        
        filepath = self.plans_dir / filename
        
        # Write to file
        try:
            with open(filepath, 'w') as f:
                json.dump(state, f, indent=2)
            
            logger.info(f"Saved plan state to {filepath}")
            return str(filepath)
        
        except Exception as e:
            logger.error(f"Failed to save plan state: {e}")
            raise
    
    def load_plan_state(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """
        Load the latest plan state from disk.
        
        Args:
            plan_id: The plan ID to load
            
        Returns:
            State dictionary or None if not found
        """
        filepath = self.plans_dir / f"{plan_id}_latest.json"
        
        if not filepath.exists():
            logger.warning(f"No saved state found for plan {plan_id}")
            return None
        
        try:
            with open(filepath, 'r') as f:
                state = json.load(f)
            
            logger.info(f"Loaded plan state from {filepath}")
            return state
        
        except Exception as e:
            logger.error(f"Failed to load plan state: {e}")
            return None
    
    def restore_plan_from_state(self, state: Dict[str, Any]) -> Plan:
        """
        Reconstruct a Plan object from saved state.
        
        Args:
            state: The state dictionary from load_plan_state
            
        Returns:
            Restored Plan object
        """
        from .planner import Plan as PlanClass, PlanStep as PlanStepClass
        from .tools import ToolResult
        
        plan = PlanClass(
            id=state["plan_id"],
            goal=state["goal"],
            status=PlanStatus(state["status"]),
            current_step_index=state["current_step_index"],
            created_at=datetime.fromisoformat(state["created_at"]),
            metadata=state.get("metadata", {})
        )
        
        # Restore started/completed times if available
        if state.get("started_at"):
            plan.started_at = datetime.fromisoformat(state["started_at"])
        if state.get("completed_at"):
            plan.completed_at = datetime.fromisoformat(state["completed_at"])
        
        # Restore steps
        for step_dict in state.get("steps", []):
            step = PlanStepClass(
                id=step_dict["id"],
                action=step_dict["action"],
                description=step_dict["description"],
                parameters=step_dict["parameters"],
                depends_on=step_dict.get("depends_on", []),
                requires_confirmation=step_dict.get("requires_confirmation", False),
                status=StepStatus(step_dict["status"]),
                error=step_dict.get("error")
            )
            
            # Restore timing
            if step_dict.get("started_at"):
                step.started_at = datetime.fromisoformat(step_dict["started_at"])
            if step_dict.get("completed_at"):
                step.completed_at = datetime.fromisoformat(step_dict["completed_at"])
            
            # Restore result if available
            if step_dict.get("result"):
                result_dict = step_dict["result"]
                step.result = ToolResult(
                    success=result_dict["success"],
                    output=result_dict.get("output"),
                    error=result_dict.get("error")
                )
            
            plan.add_step(step)
        
        return plan
    
    def resume_plan(self, plan_id: str) -> Optional[Plan]:
        """
        Load a saved plan and prepare it for resumption.
        
        Args:
            plan_id: The plan ID to resume
            
        Returns:
            Restored Plan ready to continue, or None if not found
        """
        state = self.load_plan_state(plan_id)
        if not state:
            return None
        
        plan = self.restore_plan_from_state(state)
        
        logger.info(
            f"Resuming plan {plan_id} at step {plan.current_step_index + 1}/"
            f"{len(plan.steps)}"
        )
        
        return plan
    
    def get_recovery_suggestions(self, plan_id: str) -> List[str]:
        """
        Analyze a saved plan state and suggest recovery actions.
        
        Args:
            plan_id: The plan ID to analyze
            
        Returns:
            List of recovery suggestion strings
        """
        state = self.load_plan_state(plan_id)
        if not state:
            return []
        
        suggestions = []
        
        # Analyze plan status
        if state["status"] == PlanStatus.EXECUTING.value:
            suggestions.append(
                f"Plan was interrupted at step {state['current_step_index'] + 1}. "
                f"Resume execution to continue."
            )
        
        # Check for failed steps
        failed_steps = [
            s for s in state["steps"]
            if s["status"] == StepStatus.FAILED.value
        ]
        
        if failed_steps:
            for step in failed_steps[:3]:  # Show first 3 failures
                suggestions.append(
                    f"Step '{step['id']}' ({step['action']}) failed: {step.get('error', 'Unknown error')}. "
                    f"Consider alternative approach or check dependencies."
                )
        
        # Check for pending steps
        pending_steps = [
            s for s in state["steps"]
            if s["status"] == StepStatus.PENDING.value
        ]
        
        if pending_steps:
            suggestions.append(
                f"{len(pending_steps)} steps are still pending. "
                f"Resume to execute them."
            )
        
        return suggestions
    
    def list_saved_plans(self) -> List[Dict[str, Any]]:
        """
        List all saved plan states.
        
        Returns:
            List of plan summaries with ID, status, and last saved time
        """
        plans = []
        
        for filepath in self.plans_dir.glob("*_latest.json"):
            try:
                with open(filepath, 'r') as f:
                    state = json.load(f)
                
                plans.append({
                    "plan_id": state["plan_id"],
                    "goal": state["goal"],
                    "status": state["status"],
                    "progress": (
                        sum(1 for s in state["steps"] if s["status"] != StepStatus.PENDING.value),
                        len(state["steps"])
                    ),
                    "saved_at": state.get("saved_at"),
                    "filepath": str(filepath)
                })
            
            except Exception as e:
                logger.warning(f"Failed to read plan file {filepath}: {e}")
        
        return sorted(plans, key=lambda x: x["saved_at"], reverse=True)
    
    def cleanup_old_states(self, keep_days: int = 7) -> int:
        """
        Remove saved states older than keep_days.
        
        Args:
            keep_days: Number of days of states to keep
            
        Returns:
            Number of files deleted
        """
        from datetime import timedelta
        
        cutoff = datetime.now() - timedelta(days=keep_days)
        deleted_count = 0
        
        for filepath in self.plans_dir.glob("*.json"):
            try:
                with open(filepath, 'r') as f:
                    state = json.load(f)
                
                saved_at = datetime.fromisoformat(state.get("saved_at", ""))
                
                if saved_at < cutoff:
                    filepath.unlink()
                    deleted_count += 1
            
            except Exception as e:
                logger.warning(f"Failed to cleanup {filepath}: {e}")
        
        logger.info(f"Cleaned up {deleted_count} old state files")
        return deleted_count
