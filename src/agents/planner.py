"""
Agentic Planner Module
Provides goal decomposition and multi-step plan execution for the Voice Assistant.
"""

import json
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Generator, List, Optional, Tuple

from .tools import ToolRegistry, ToolResult, ToolDescription
from .guardrails import SafetyGuardrails, SafetyCheck, ActionRisk


class StepStatus(str, Enum):
    """Status of a plan step"""
    PENDING = "pending"
    WAITING_CONFIRMATION = "waiting_confirmation"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"


class PlanStatus(str, Enum):
    """Status of a plan"""
    DRAFT = "draft"
    READY = "ready"
    EXECUTING = "executing"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class PlanStep:
    """A single step in an execution plan"""
    id: str
    action: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    requires_confirmation: bool = False
    status: StepStatus = StepStatus.PENDING
    result: Optional[ToolResult] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "action": self.action,
            "description": self.description,
            "parameters": self.parameters,
            "depends_on": self.depends_on,
            "requires_confirmation": self.requires_confirmation,
            "status": self.status.value,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


@dataclass
class Plan:
    """A complete execution plan"""
    id: str
    goal: str
    steps: List[PlanStep] = field(default_factory=list)
    status: PlanStatus = PlanStatus.DRAFT
    current_step_index: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_step(self, step: PlanStep) -> None:
        """Add a step to the plan"""
        self.steps.append(step)

    def get_current_step(self) -> Optional[PlanStep]:
        """Get the current step"""
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    def advance(self) -> bool:
        """Advance to the next step"""
        if self.current_step_index < len(self.steps) - 1:
            self.current_step_index += 1
            return True
        return False

    def is_complete(self) -> bool:
        """Check if all steps are complete"""
        return all(
            s.status in [StepStatus.COMPLETED, StepStatus.SKIPPED]
            for s in self.steps
        )

    def has_failed(self) -> bool:
        """Check if any step has failed"""
        return any(s.status == StepStatus.FAILED for s in self.steps)

    def get_progress(self) -> Tuple[int, int]:
        """Get progress as (completed, total)"""
        completed = sum(
            1 for s in self.steps
            if s.status in [StepStatus.COMPLETED, StepStatus.SKIPPED]
        )
        return completed, len(self.steps)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "goal": self.goal,
            "steps": [s.to_dict() for s in self.steps],
            "status": self.status.value,
            "current_step_index": self.current_step_index,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata
        }


@dataclass
class ExecutionEvent:
    """Event emitted during plan execution"""
    event_type: str  # step_started, step_completed, step_failed, confirmation_needed, plan_completed
    step: Optional[PlanStep] = None
    plan: Optional[Plan] = None
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)


# Planning prompt template
PLANNING_PROMPT = '''You are an AI assistant that creates step-by-step plans to accomplish goals.

Given a user's goal and available tools, create a JSON plan with ordered steps.

{tools}

User's goal: {goal}

Current context:
{context}

Create a plan as JSON with this structure:
{{
  "steps": [
    {{
      "id": "step_1",
      "action": "tool_name",
      "description": "What this step does",
      "parameters": {{"param1": "value1"}},
      "depends_on": []
    }}
  ]
}}

Rules:
1. Use only the available tools listed above
2. Break complex goals into simple, atomic steps
3. Set depends_on to step IDs that must complete first
4. Include all required parameters for each tool
5. Order steps logically

Return ONLY valid JSON:'''


class AgenticPlanner:
    """
    Agentic planner that decomposes complex goals into executable plans.

    Provides:
    - Goal decomposition using LLM
    - Plan validation against available tools
    - Step-by-step execution with progress reporting
    - Safety checks and confirmation handling
    - Plan persistence and resumption
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        guardrails: Optional[SafetyGuardrails] = None,
        llm_service=None
    ):
        """
        Initialize the planner.

        Args:
            tool_registry: Registry of available tools
            guardrails: Safety guardrails for action checking
            llm_service: LLM service for plan generation
        """
        self.tools = tool_registry
        self.guardrails = guardrails or SafetyGuardrails()
        self.llm_service = llm_service

        # Active plans
        self._active_plans: Dict[str, Plan] = {}

    def create_plan(
        self,
        goal: str,
        context: Optional[str] = None
    ) -> Plan:
        """
        Create an execution plan for a goal.

        Args:
            goal: The user's goal in natural language
            context: Optional conversation context

        Returns:
            A Plan object with steps to execute
        """
        plan_id = str(uuid.uuid4())

        # Try LLM-based planning
        if self.llm_service:
            try:
                steps = self._generate_plan_with_llm(goal, context)
                plan = Plan(
                    id=plan_id,
                    goal=goal,
                    steps=steps,
                    status=PlanStatus.READY
                )
                self._active_plans[plan_id] = plan
                return plan
            except Exception:
                pass

        # Fallback to rule-based planning
        steps = self._generate_plan_rule_based(goal)
        plan = Plan(
            id=plan_id,
            goal=goal,
            steps=steps,
            status=PlanStatus.READY
        )
        self._active_plans[plan_id] = plan
        return plan

    def _generate_plan_with_llm(
        self,
        goal: str,
        context: Optional[str]
    ) -> List[PlanStep]:
        """Generate plan using LLM"""
        tools_prompt = self.tools.get_tools_for_prompt()

        prompt = PLANNING_PROMPT.format(
            tools=tools_prompt,
            goal=goal,
            context=context or "No additional context"
        )

        response = self.llm_service.generate(
            prompt=prompt,
            max_tokens=1000,
            temperature=0.2
        )

        # Parse JSON from response
        json_match = re.search(r'\{[\s\S]*\}', response)
        if not json_match:
            raise ValueError("No valid JSON in response")

        data = json.loads(json_match.group())
        steps = []

        for i, step_data in enumerate(data.get("steps", [])):
            # Validate tool exists
            tool = self.tools.get(step_data.get("action", ""))
            requires_confirmation = False
            if tool:
                requires_confirmation = tool.requires_confirmation

            step = PlanStep(
                id=step_data.get("id", f"step_{i+1}"),
                action=step_data.get("action", "unknown"),
                description=step_data.get("description", ""),
                parameters=step_data.get("parameters", {}),
                depends_on=step_data.get("depends_on", []),
                requires_confirmation=requires_confirmation
            )
            steps.append(step)

        return steps

    def _generate_plan_rule_based(self, goal: str) -> List[PlanStep]:
        """Generate plan using rule-based approach"""
        goal_lower = goal.lower()
        steps = []

        # Pattern matching for common goals
        if any(word in goal_lower for word in ["timer", "countdown"]):
            # Extract duration
            duration = 300  # Default 5 minutes
            duration_match = re.search(r'(\d+)\s*(second|minute|hour)', goal_lower)
            if duration_match:
                amount = int(duration_match.group(1))
                unit = duration_match.group(2)
                if "minute" in unit:
                    duration = amount * 60
                elif "hour" in unit:
                    duration = amount * 3600
                else:
                    duration = amount

            steps.append(PlanStep(
                id="step_1",
                action="set_timer",
                description=f"Set a timer",
                parameters={"duration_seconds": duration, "label": "Timer"}
            ))

        elif any(word in goal_lower for word in ["open", "launch", "start"]):
            # Extract app name
            app_patterns = [
                r"(?:open|launch|start)\s+(\w+)",
                r"(\w+)\s+app"
            ]
            app_name = "application"
            for pattern in app_patterns:
                match = re.search(pattern, goal_lower)
                if match:
                    app_name = match.group(1)
                    break

            steps.append(PlanStep(
                id="step_1",
                action="launch_app",
                description=f"Launch {app_name}",
                parameters={"app_name": app_name}
            ))

        elif any(word in goal_lower for word in ["cpu", "memory", "disk", "battery", "status"]):
            steps.append(PlanStep(
                id="step_1",
                action="system_status",
                description="Check system status",
                parameters={"info_type": "all"}
            ))

        elif any(word in goal_lower for word in ["weather"]):
            location = "current location"
            location_match = re.search(r"(?:in|for|at)\s+(.+)", goal_lower)
            if location_match:
                location = location_match.group(1).strip()

            steps.append(PlanStep(
                id="step_1",
                action="get_weather",
                description=f"Get weather for {location}",
                parameters={"location": location}
            ))

        elif any(word in goal_lower for word in ["search", "look up", "find"]):
            query = goal_lower
            for prefix in ["search for", "search", "look up", "find"]:
                if prefix in goal_lower:
                    query = goal_lower.split(prefix, 1)[-1].strip()
                    break

            steps.append(PlanStep(
                id="step_1",
                action="web_search",
                description=f"Search for: {query}",
                parameters={"query": query}
            ))

        else:
            # Generic single-step plan
            steps.append(PlanStep(
                id="step_1",
                action="unknown",
                description="Unable to determine action",
                parameters={}
            ))

        return steps

    def validate_plan(self, plan: Plan) -> Tuple[bool, List[str]]:
        """
        Validate a plan before execution.

        Returns:
            (is_valid, list_of_errors)
        """
        errors = []

        for step in plan.steps:
            # Check if tool exists
            tool = self.tools.get(step.action)
            if not tool:
                errors.append(f"Step {step.id}: Unknown tool '{step.action}'")
                continue

            # Check required parameters
            validation_error = tool.validate_params(step.parameters)
            if validation_error:
                errors.append(f"Step {step.id}: {validation_error}")

            # Check dependencies exist
            step_ids = {s.id for s in plan.steps}
            for dep in step.depends_on:
                if dep not in step_ids:
                    errors.append(f"Step {step.id}: Unknown dependency '{dep}'")

        return len(errors) == 0, errors

    def execute(
        self,
        plan: Plan,
        confirm_callback=None
    ) -> Generator[ExecutionEvent, Optional[bool], None]:
        """
        Execute a plan step by step.

        This is a generator that yields events and can receive confirmations.

        Args:
            plan: The plan to execute
            confirm_callback: Optional callback for confirmations

        Yields:
            ExecutionEvent for each step and milestone

        Usage:
            executor = planner.execute(plan)
            for event in executor:
                if event.event_type == "confirmation_needed":
                    confirmed = ask_user(event.message)
                    executor.send(confirmed)
        """
        plan.status = PlanStatus.EXECUTING
        plan.started_at = datetime.now()

        for step in plan.steps:
            # Check dependencies
            for dep_id in step.depends_on:
                dep_step = next((s for s in plan.steps if s.id == dep_id), None)
                if dep_step and dep_step.status != StepStatus.COMPLETED:
                    step.status = StepStatus.SKIPPED
                    step.error = f"Dependency {dep_id} not completed"
                    continue

            # Start step
            step.status = StepStatus.RUNNING
            step.started_at = datetime.now()

            yield ExecutionEvent(
                event_type="step_started",
                step=step,
                plan=plan,
                message=f"Starting: {step.description}"
            )

            # Safety check
            safety_check = self.guardrails.check_action(
                step.action,
                step.parameters
            )

            if not safety_check.is_safe:
                step.status = StepStatus.FAILED
                step.error = safety_check.blocked_reason
                yield ExecutionEvent(
                    event_type="step_failed",
                    step=step,
                    plan=plan,
                    message=f"Blocked: {safety_check.blocked_reason}"
                )
                continue

            # Handle confirmation
            if safety_check.requires_confirmation or step.requires_confirmation:
                step.status = StepStatus.WAITING_CONFIRMATION
                confirmation_prompt = self.guardrails.get_confirmation_prompt(
                    step.action,
                    step.parameters,
                    safety_check
                )

                confirmed = yield ExecutionEvent(
                    event_type="confirmation_needed",
                    step=step,
                    plan=plan,
                    message=confirmation_prompt,
                    data={"safety_check": safety_check.to_dict()}
                )

                if not confirmed:
                    step.status = StepStatus.CANCELLED
                    yield ExecutionEvent(
                        event_type="step_cancelled",
                        step=step,
                        plan=plan,
                        message="Step cancelled by user"
                    )
                    continue

                step.status = StepStatus.RUNNING

            # Execute the step
            try:
                result = self.tools.execute(step.action, **step.parameters)
                step.result = result
                step.completed_at = datetime.now()

                if result.success:
                    step.status = StepStatus.COMPLETED
                    yield ExecutionEvent(
                        event_type="step_completed",
                        step=step,
                        plan=plan,
                        message=f"Completed: {step.description}",
                        data={"result": result.to_dict()}
                    )
                else:
                    step.status = StepStatus.FAILED
                    step.error = result.error
                    yield ExecutionEvent(
                        event_type="step_failed",
                        step=step,
                        plan=plan,
                        message=f"Failed: {result.error}"
                    )

            except Exception as e:
                step.status = StepStatus.FAILED
                step.error = str(e)
                step.completed_at = datetime.now()
                yield ExecutionEvent(
                    event_type="step_failed",
                    step=step,
                    plan=plan,
                    message=f"Error: {str(e)}"
                )

        # Complete plan
        plan.completed_at = datetime.now()
        if plan.is_complete():
            plan.status = PlanStatus.COMPLETED
        elif plan.has_failed():
            plan.status = PlanStatus.FAILED
        else:
            plan.status = PlanStatus.COMPLETED

        yield ExecutionEvent(
            event_type="plan_completed",
            plan=plan,
            message=f"Plan {'completed' if plan.is_complete() else 'finished with errors'}",
            data={"progress": plan.get_progress()}
        )

    def execute_simple(self, plan: Plan) -> Tuple[bool, List[Dict]]:
        """
        Execute a plan without generator (blocking).

        Returns:
            (success, list_of_step_results)
        """
        results = []

        for event in self.execute(plan):
            results.append({
                "type": event.event_type,
                "message": event.message,
                "data": event.data
            })

        return plan.is_complete(), results

    def cancel_plan(self, plan_id: str) -> bool:
        """Cancel an active plan"""
        plan = self._active_plans.get(plan_id)
        if plan:
            plan.status = PlanStatus.CANCELLED
            for step in plan.steps:
                if step.status == StepStatus.PENDING:
                    step.status = StepStatus.CANCELLED
            return True
        return False

    def get_plan(self, plan_id: str) -> Optional[Plan]:
        """Get a plan by ID"""
        return self._active_plans.get(plan_id)

    def list_active_plans(self) -> List[Plan]:
        """List all active plans"""
        return [
            p for p in self._active_plans.values()
            if p.status in [PlanStatus.READY, PlanStatus.EXECUTING, PlanStatus.PAUSED]
        ]


def create_agentic_planner(
    tool_registry: Optional[ToolRegistry] = None,
    llm_service=None
) -> AgenticPlanner:
    """Factory function to create AgenticPlanner"""
    from .tools import create_default_registry
    from .guardrails import create_safety_guardrails

    registry = tool_registry or create_default_registry()
    guardrails = create_safety_guardrails()

    return AgenticPlanner(
        tool_registry=registry,
        guardrails=guardrails,
        llm_service=llm_service
    )
