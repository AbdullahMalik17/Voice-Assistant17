"""
Reasoning Planner with Transparent Decision-Making

An enhanced planner that explains its reasoning when creating plans.
Provides step-by-step justification for the plan structure and action selection.
"""

import json
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple

from .planner import AgenticPlanner, Plan, PlanStep
from .tools import ToolRegistry
from .guardrails import SafetyGuardrails
from ..memory.semantic_memory import SemanticMemory

logger = logging.getLogger(__name__)


@dataclass
class PlanReasoning:
    """Reasoning explanation for a generated plan"""
    goal_interpretation: str
    identified_needs: List[str]
    preconditions: List[str]
    potential_issues: List[str]
    approach_explanation: str
    alternatives_considered: List[str]
    confidence: float  # 0.0 to 1.0


# Enhanced planning prompt with reasoning
REASONING_PLANNING_PROMPT = '''You are an intelligent assistant that creates plans with clear reasoning.

Given a user's goal and available tools, you will:
1. Interpret what the user is trying to accomplish
2. Identify preconditions and dependencies
3. Consider potential issues
4. Explain your approach
5. Create a detailed step-by-step plan

{tools}

User's goal: {goal}

Current context:
{context}

{memory_context}

Think through the following BEFORE creating the plan:

**Goal Interpretation:**
What is the user trying to accomplish? What is the real intent?

**Preconditions & Dependencies:**
What needs to be true before we can proceed?
What dependencies exist between actions?

**Potential Issues:**
What could go wrong? What are the failure modes?
How should we handle them?

**Approach:**
How will we accomplish this goal?
Why did we choose this approach over alternatives?
What are the key steps?

Then create a JSON response with this structure:
{{
  "reasoning": {{
    "goal_interpretation": "What we understand the user wants",
    "identified_needs": ["need1", "need2"],
    "preconditions": ["precond1", "precond2"],
    "potential_issues": ["issue1", "issue2"],
    "approach_explanation": "Why we chose this approach",
    "alternatives_considered": ["alt1", "alt2"]
  }},
  "steps": [
    {{
      "id": "step_1",
      "action": "tool_name",
      "description": "What this step does and why",
      "parameters": {{"param1": "value1"}},
      "depends_on": [],
      "rationale": "Why this step is necessary"
    }}
  ]
}}

Rules:
1. Use only the available tools listed above
2. Break complex goals into simple, atomic steps
3. Set depends_on to step IDs that must complete first
4. Include all required parameters for each tool
5. Order steps logically
6. Explain the reasoning for each step
7. Consider the user's history and patterns

Return ONLY valid JSON:'''


class ReasoningPlanner(AgenticPlanner):
    """
    Enhanced planner that explains its reasoning.
    
    Extends AgenticPlanner with:
    - Transparent decision-making explanations
    - Reasoning about goal interpretation
    - Alternative approach consideration
    - Confidence scoring
    """
    
    def __init__(
        self,
        tool_registry: ToolRegistry,
        guardrails: Optional[SafetyGuardrails] = None,
        llm_service=None,
        memory_service: Optional[SemanticMemory] = None
    ):
        """Initialize reasoning planner"""
        super().__init__(
            tool_registry=tool_registry,
            guardrails=guardrails,
            llm_service=llm_service,
            memory_service=memory_service
        )
    
    def create_plan_with_reasoning(
        self,
        goal: str,
        context: Optional[str] = None,
        user_id: str = "default"
    ) -> Tuple[Plan, PlanReasoning]:
        """
        Create a plan with reasoning explanations.
        
        Args:
            goal: The user's goal in natural language
            context: Optional conversation context
            user_id: User identifier for memory context retrieval
            
        Returns:
            Tuple of (Plan, PlanReasoning)
        """
        if not self.llm_service:
            # Fallback to regular planning without reasoning
            plan = self.create_plan(goal, context, user_id)
            reasoning = PlanReasoning(
                goal_interpretation=goal,
                identified_needs=[],
                preconditions=[],
                potential_issues=[],
                approach_explanation="Rule-based planning (LLM not available)",
                alternatives_considered=[],
                confidence=0.6
            )
            return plan, reasoning
        
        try:
            return self._create_plan_with_llm_reasoning(goal, context, user_id)
        except Exception as e:
            logger.error(f"Error creating reasoning plan: {e}")
            # Fallback
            plan = self.create_plan(goal, context, user_id)
            reasoning = PlanReasoning(
                goal_interpretation=goal,
                identified_needs=[],
                preconditions=[],
                potential_issues=[],
                approach_explanation=f"Fallback planning (error: {str(e)})",
                alternatives_considered=[],
                confidence=0.5
            )
            return plan, reasoning
    
    def _create_plan_with_llm_reasoning(
        self,
        goal: str,
        context: Optional[str],
        user_id: str
    ) -> Tuple[Plan, PlanReasoning]:
        """
        Generate plan with reasoning using LLM with reasoning prompt.
        
        Returns tuple of (Plan, PlanReasoning)
        """
        import uuid
        import re
        
        tools_prompt = self.tools.get_tools_for_prompt()
        memory_context = self._get_memory_context(goal, user_id)
        
        prompt = REASONING_PLANNING_PROMPT.format(
            tools=tools_prompt,
            goal=goal,
            context=context or "No additional context",
            memory_context=memory_context
        )
        
        response = self.llm_service.generate(
            prompt=prompt,
            max_tokens=2000,
            temperature=0.3
        )
        
        # Parse JSON from response
        json_match = re.search(r'\{[\s\S]*\}', response)
        if not json_match:
            raise ValueError("No valid JSON in response")
        
        data = json.loads(json_match.group())
        
        # Extract reasoning
        reasoning_data = data.get("reasoning", {})
        reasoning = PlanReasoning(
            goal_interpretation=reasoning_data.get(
                "goal_interpretation",
                goal
            ),
            identified_needs=reasoning_data.get("identified_needs", []),
            preconditions=reasoning_data.get("preconditions", []),
            potential_issues=reasoning_data.get("potential_issues", []),
            approach_explanation=reasoning_data.get(
                "approach_explanation",
                "LLM-based planning"
            ),
            alternatives_considered=reasoning_data.get(
                "alternatives_considered",
                []
            ),
            confidence=min(
                1.0,
                max(0.0, len(reasoning_data.get("identified_needs", [])) / 5.0)
            )
        )
        
        # Extract and create plan steps
        steps = []
        for i, step_data in enumerate(data.get("steps", [])):
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
        
        # Create plan
        plan = Plan(
            id=str(uuid.uuid4()),
            goal=goal,
            steps=steps
        )
        
        self._active_plans[plan.id] = plan
        
        return plan, reasoning
    
    def get_plan_reasoning_summary(
        self,
        plan: Plan,
        reasoning: PlanReasoning
    ) -> str:
        """
        Get a human-readable summary of plan and reasoning.
        
        Args:
            plan: The generated plan
            reasoning: The reasoning behind the plan
            
        Returns:
            Formatted string explanation
        """
        lines = [
            "=== PLAN WITH REASONING ===",
            f"\nGoal: {plan.goal}",
            f"\nInterpretation: {reasoning.goal_interpretation}",
            f"\nConfidence: {reasoning.confidence:.0%}",
            f"\nNeeds Identified: {', '.join(reasoning.identified_needs) or 'None'}",
            f"\nPreconditions: {', '.join(reasoning.preconditions) or 'None'}",
            f"\nPotential Issues: {', '.join(reasoning.potential_issues) or 'None'}",
            f"\nApproach: {reasoning.approach_explanation}",
            f"\nAlternatives Considered: {', '.join(reasoning.alternatives_considered) or 'None'}",
            f"\n--- EXECUTION STEPS ({len(plan.steps)} steps) ---"
        ]
        
        for step in plan.steps:
            lines.append(f"\n{step.id}: {step.action}")
            lines.append(f"  Description: {step.description}")
            if step.parameters:
                lines.append(f"  Parameters: {step.parameters}")
            if step.depends_on:
                lines.append(f"  Depends on: {', '.join(step.depends_on)}")
        
        return "\n".join(lines)
