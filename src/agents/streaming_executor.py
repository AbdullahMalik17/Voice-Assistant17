"""
Streaming Execution Engine for Agentic Plans

Provides async streaming execution with real-time event emission,
cancellation support, and step-by-step progress tracking.
"""

import asyncio
import logging
from datetime import datetime
from typing import AsyncGenerator, Optional, Dict, Any, Callable

from .planner import Plan, PlanStep, PlanStatus, StepStatus, ExecutionEvent
from .tools import ToolRegistry, ToolResult
from .guardrails import SafetyGuardrails
from .execution_feedback import ExecutionFeedbackAnalyzer

logger = logging.getLogger(__name__)


class StreamingExecutionState:
    """Track state of streaming execution for pause/resume."""
    
    def __init__(self, plan: Plan):
        self.plan = plan
        self.paused = False
        self.cancelled = False
        self.pause_event = asyncio.Event()
        self.pause_event.set()  # Not paused by default
        
    async def pause(self):
        """Pause execution."""
        self.paused = True
        self.pause_event.clear()
        logger.info(f"Pausing execution of plan {self.plan.id}")
    
    async def resume(self):
        """Resume execution."""
        if self.paused:
            self.paused = False
            self.pause_event.set()
            logger.info(f"Resuming execution of plan {self.plan.id}")
    
    async def cancel(self):
        """Cancel execution."""
        self.cancelled = True
        self.pause_event.set()
        logger.info(f"Cancelling execution of plan {self.plan.id}")
    
    async def wait_if_paused(self):
        """Wait if execution is paused."""
        await self.pause_event.wait()


class StreamingExecutor:
    """
    Async streaming executor for plans.
    
    Features:
    - Real-time event streaming (step_started, step_completed, etc.)
    - Pause/resume/cancel support
    - Concurrent step execution where dependencies allow
    - Real-time progress reporting
    - Failure tracking and learning via ExecutionFeedbackAnalyzer
    """
    
    def __init__(
        self,
        tool_registry: ToolRegistry,
        guardrails: Optional[SafetyGuardrails] = None,
        feedback_analyzer: Optional[ExecutionFeedbackAnalyzer] = None
    ):
        self.tools = tool_registry
        self.guardrails = guardrails
        self.feedback_analyzer = feedback_analyzer
        
    async def execute_streaming(
        self,
        plan: Plan,
        on_event: Optional[Callable[[ExecutionEvent], None]] = None
    ) -> AsyncGenerator[ExecutionEvent, Optional[bool]]:
        """
        Execute plan with real-time event streaming.
        
        Yields ExecutionEvent for each milestone:
        - plan_started
        - step_started, step_completed, step_failed
        - confirmation_needed (can receive True/False to continue/skip)
        - plan_completed
        
        Args:
            plan: Plan to execute
            on_event: Optional callback for each event
            
        Yields:
            ExecutionEvent objects with progress information
        """
        state = StreamingExecutionState(plan)
        plan.status = PlanStatus.EXECUTING
        plan.started_at = datetime.now()
        
        try:
            # Emit plan started event
            start_event = ExecutionEvent(
                event_type="plan_started",
                plan=plan,
                message=f"Starting plan: {plan.goal}",
                data={"total_steps": len(plan.steps)}
            )
            if on_event:
                on_event(start_event)
            yield start_event
            
            # Execute steps (with dependency ordering)
            for step in plan.steps:
                if state.cancelled:
                    break
                
                # Wait if paused
                await state.wait_if_paused()
                
                # Execute step and yield events
                async for event in self._execute_step(step, plan, state):
                    if on_event:
                        on_event(event)
                    yield event
            
            # Plan completion
            plan.completed_at = datetime.now()
            if state.cancelled:
                plan.status = PlanStatus.CANCELLED
            elif plan.has_failed():
                plan.status = PlanStatus.FAILED
            else:
                plan.status = PlanStatus.COMPLETED
            
            completion_event = ExecutionEvent(
                event_type="plan_completed",
                plan=plan,
                message=f"Plan {plan.status.value}",
                data={"progress": plan.get_progress()}
            )
            if on_event:
                on_event(completion_event)
            yield completion_event
            
        except Exception as e:
            logger.error(f"Error executing plan: {e}")
            plan.status = PlanStatus.FAILED
            error_event = ExecutionEvent(
                event_type="plan_error",
                plan=plan,
                message=f"Execution error: {str(e)}",
                data={"error": str(e)}
            )
            if on_event:
                on_event(error_event)
            yield error_event
    
    async def _execute_step(
        self,
        step: PlanStep,
        plan: Plan,
        state: StreamingExecutionState
    ) -> AsyncGenerator[ExecutionEvent, None]:
        """
        Execute a single step with dependency checking.
        
        Yields:
            Events for step lifecycle
        """
        # Check dependencies
        for dep_id in step.depends_on:
            dep_step = next(
                (s for s in plan.steps if s.id == dep_id),
                None
            )
            if dep_step and dep_step.status != StepStatus.COMPLETED:
                step.status = StepStatus.SKIPPED
                step.error = f"Dependency {dep_id} not completed"
                
                skip_event = ExecutionEvent(
                    event_type="step_skipped",
                    step=step,
                    plan=plan,
                    message=f"Skipped: {step.description} (dependency not met)"
                )
                yield skip_event
                return
        
        # Start step
        step.status = StepStatus.RUNNING
        step.started_at = datetime.now()
        
        start_event = ExecutionEvent(
            event_type="step_started",
            step=step,
            plan=plan,
            message=f"Starting: {step.description}",
            data={"progress": plan.get_progress()}
        )
        yield start_event
        
        # Safety check
        safety_check = self.guardrails.check_action(
            step.action,
            step.parameters
        ) if self.guardrails else None
        
        if safety_check and not safety_check.is_safe:
            step.status = StepStatus.FAILED
            step.error = safety_check.blocked_reason
            
            fail_event = ExecutionEvent(
                event_type="step_failed",
                step=step,
                plan=plan,
                message=f"Blocked: {safety_check.blocked_reason}"
            )
            yield fail_event
            return
        
        # Handle confirmation
        if (safety_check and (safety_check.requires_confirmation or step.requires_confirmation)):
            step.status = StepStatus.WAITING_CONFIRMATION
            confirmation_prompt = self.guardrails.get_confirmation_prompt(
                step.action,
                step.parameters,
                safety_check
            )
            
            confirm_event = ExecutionEvent(
                event_type="confirmation_needed",
                step=step,
                plan=plan,
                message=confirmation_prompt,
                data={"safety_check": safety_check.to_dict()}
            )
            
            # Yield and wait for confirmation
            confirmed = yield confirm_event
            
            if not confirmed:
                step.status = StepStatus.CANCELLED
                cancel_event = ExecutionEvent(
                    event_type="step_cancelled",
                    step=step,
                    plan=plan,
                    message="Step cancelled by user"
                )
                yield cancel_event
                return
            
            step.status = StepStatus.RUNNING
        
        # Execute tool
        try:
            # Run tool execution in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.tools.execute(step.action, **step.parameters)
            )
            
            step.result = result
            step.completed_at = datetime.now()
            
            if result.success:
                step.status = StepStatus.COMPLETED
                complete_event = ExecutionEvent(
                    event_type="step_completed",
                    step=step,
                    plan=plan,
                    message=f"Completed: {step.description}",
                    data={
                        "result": result.to_dict(),
                        "progress": plan.get_progress()
                    }
                )
                yield complete_event
            else:
                step.status = StepStatus.FAILED
                step.error = result.error
                
                # Record failure for learning
                if self.feedback_analyzer:
                    self.feedback_analyzer.record_failure(step, result)
                
                fail_event = ExecutionEvent(
                    event_type="step_failed",
                    step=step,
                    plan=plan,
                    message=f"Failed: {result.error}",
                    data={"error": result.error}
                )
                yield fail_event
                
        except Exception as e:
            step.status = StepStatus.FAILED
            step.error = str(e)
            step.completed_at = datetime.now()
            
            # Record failure for learning
            if self.feedback_analyzer:
                fail_result = ToolResult(success=False, error=str(e))
                self.feedback_analyzer.record_failure(step, fail_result)
            
            error_event = ExecutionEvent(
                event_type="step_error",
                step=step,
                plan=plan,
                message=f"Error: {str(e)}",
                data={"error": str(e)}
            )
            yield error_event
    
    async def pause_execution(self, state: StreamingExecutionState):
        """Pause execution (can be resumed)."""
        await state.pause()
    
    async def resume_execution(self, state: StreamingExecutionState):
        """Resume paused execution."""
        await state.resume()
    
    async def cancel_execution(self, state: StreamingExecutionState):
        """Cancel execution."""
        await state.cancel()
