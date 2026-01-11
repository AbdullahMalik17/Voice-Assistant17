# Agentic System - Quick Reference Card

## 🚀 30-Second Start

```python
from src.agents import (
    ReasoningPlanner, StreamingExecutor, AutonomousDecisionMaker,
    ExecutionFeedbackAnalyzer, AgentStatePersistence, AgentMetrics
)
from src.memory.semantic_memory import SemanticMemory

# Initialize
memory = SemanticMemory()
planner = ReasoningPlanner(tools, guardrails, llm, memory)
decision_maker = AutonomousDecisionMaker(user_id="user1")
feedback = ExecutionFeedbackAnalyzer(user_id="user1")
executor = StreamingExecutor(tools, guardrails, feedback)
persistence = AgentStatePersistence()
metrics = AgentMetrics()

# Execute
plan, reasoning = planner.create_plan_with_reasoning(goal="Send email")
async for event in executor.execute_streaming(plan):
    print(f"{event.event_type}: {event.message}")
```

---

## 📚 Core Classes

### ReasoningPlanner
```python
plan, reasoning = planner.create_plan_with_reasoning(goal, context, user_id)
summary = planner.get_plan_reasoning_summary(plan, reasoning)
```

### AutonomousDecisionMaker
```python
decision = decision_maker.decide_autonomy(action, params, risk_level, context)
decision_maker.record_execution(action, success, approved, rejected)
stats = decision_maker.get_action_stats(action)
profile = decision_maker.get_user_profile()
```

### StreamingExecutor
```python
async for event in executor.execute_streaming(plan, on_event=callback):
    # event.event_type: plan_started, step_started, step_completed, etc.
    # event.step: PlanStep object
    # event.message: Human readable message
    # event.data: Additional context
    pass
```

### ExecutionFeedbackAnalyzer
```python
feedback.record_failure(step, result, context_info)
refinements = feedback.get_step_refinements(action, params)
reliability = feedback.get_action_reliability(action)
report = feedback.export_feedback_report()
```

### AgentStatePersistence
```python
persistence.save_plan_state(plan, context, checkpoint_name)
plan = persistence.resume_plan(plan_id)
suggestions = persistence.get_recovery_suggestions(plan_id)
saved_plans = persistence.list_saved_plans()
```

### AgentMetrics
```python
metrics.record_plan_created(plan)
metrics.record_step_execution(tool, success, latency, requires_confirmation)
metrics.record_plan_completion(plan)

dashboard = metrics.get_dashboard_summary()
tool_metrics = metrics.get_tool_metrics(tool_name)
failing_tools = metrics.get_top_failing_tools(top_n=5)
```

---

## 🎯 Trust Levels

| Level | Threshold | Attempts | Success | Approval |
|-------|-----------|----------|---------|----------|
| UNKNOWN | N/A | 0 | - | - |
| LOW | 0.3 | <3 | <60% | - |
| MEDIUM | 0.5 | 3+ | 60%+ | - |
| HIGH | 0.75 | 5+ | 70%+ | 80%+ |
| EXPERT | 0.95 | 10+ | 90%+ | 90%+ |

---

## ⚠️ Risk Levels

```
"critical"  → min_score: 0.90, min_success: 0.95  (Delete, format, etc.)
"high"      → min_score: 0.75, min_success: 0.85  (Send email, post)
"medium"    → min_score: 0.60, min_success: 0.70  (Open apps, timers)
"low"       → min_score: 0.40, min_success: 0.50  (Read system)
```

---

## 🔴 Error Types

```
not_available    → App/tool not installed
permission_error → Authorization failed
timeout          → Execution too slow
connectivity     → Network problem
invalid_input    → Bad parameters
state_conflict   → Conflicting state
unknown          → Other
```

---

## 📊 Metrics Dictionary

```python
dashboard = {
    "plans": {
        "plans_created": int,
        "plans_completed": int,
        "plans_failed": int,
        "completion_rate": "88.1%",
        "success_rate": "83.3%"
    },
    "steps": {
        "steps_executed": int,
        "steps_succeeded": int,
        "success_rate": "92.9%",
        "failure_rate": "5.1%"
    },
    "tools": {
        "tool_name": {
            "executions": int,
            "successes": int,
            "failures": int,
            "success_rate": "91.3%",
            "avg_latency_ms": "1245.3",
            "p95_latency_ms": "2134.5"
        }
    },
    "autonomy": {
        "confirmations_required": int,
        "confirmations_approved": int,
        "confirmations_rejected": int,
        "acceptance_rate": "83.3%",
        "autonomy_score": "92.3%"
    },
    "latency": {
        "avg_latency_s": "2.34",
        "p50_latency_s": "1.45",
        "p95_latency_s": "4.23",
        "p99_latency_s": "6.78"
    },
    "health": {
        "plan_success": "🟢 Excellent",
        "step_success": "🟢 Excellent",
        "tool_reliability": "🟢 Good",
        "user_trust": "🟢 High"
    }
}
```

---

## 🔗 Integration Checklist

- [ ] Import agentic modules
- [ ] Initialize all components
- [ ] Update WebSocket handler to stream events
- [ ] Create ExecutionVisualizer React component
- [ ] Create MetricsDashboard React component
- [ ] Add /api/metrics endpoint
- [ ] Connect memory service to planner
- [ ] Record plan metrics after execution
- [ ] Save plan state to persistence
- [ ] Test end-to-end flow
- [ ] Load test with concurrent users

---

## 🧪 Quick Tests

```python
# Test autonomy
decision_maker.record_execution("timer", True, True)
decision = decision_maker.decide_autonomy("timer", {}, "low", ctx)
assert decision.should_auto_execute == True

# Test feedback
feedback.record_failure(step, result)
refs = feedback.get_step_refinements("slack", {})
assert len(refs) > 0

# Test persistence
persistence.save_plan_state(plan)
restored = persistence.resume_plan(plan.id)
assert restored.id == plan.id

# Test metrics
metrics.record_step_execution("email", True, 1.5)
dash = metrics.get_dashboard_summary()
assert "plans" in dash
```

---

## 📖 Documentation Map

| Document | Purpose | Audience |
|----------|---------|----------|
| [AGENTIC_IMPLEMENTATION.md](AGENTIC_IMPLEMENTATION.md) | Complete guide | Developers |
| [AGENTIC_INTEGRATION_GUIDE.md](AGENTIC_INTEGRATION_GUIDE.md) | Quick start | Integration team |
| [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) | Project overview | Project managers |
| This file | Quick reference | All |

---

## 🎓 Key Concepts

### Trust Score
```
(success_rate × 0.4) + (approval_rate × 0.4) + (context_confidence × 0.2)
```

### Autonomy Decision
```
should_auto = (
    trust_score >= threshold AND
    success_rate >= min_success AND
    total_attempts > 0 AND
    daily_count < limit
)
```

### Event Streaming
```
plan_started
  → step_started
    → step_completed (success) OR step_failed OR step_skipped
  → [next steps...]
plan_completed
```

---

## 🆘 Common Issues

| Issue | Solution |
|-------|----------|
| Memory not injecting | Ensure memory_service passed to planner |
| Metrics not collecting | Call record_step_execution() during execution |
| State not persisting | Call save_plan_state() after completion |
| No events streaming | Ensure executor.execute_streaming() is async/await |
| Trust not building | Call record_execution() after each action |

---

## 🎯 Example Flows

### Simple Action
```
set_timer(5min) → Auto-execute → Done (high trust)
```

### Complex Goal
```
Find flights + email → Plan with reasoning → 
Confirm step 1 → Execute step 2 → Save state →
Success or learn from failure
```

### Recovery
```
Plan interrupted → Resume from persistence →
Get recovery suggestions → Re-execute → Done
```

---

## 📞 Support

- Full docs: [AGENTIC_IMPLEMENTATION.md](AGENTIC_IMPLEMENTATION.md)
- Integration: [AGENTIC_INTEGRATION_GUIDE.md](AGENTIC_INTEGRATION_GUIDE.md)
- Summary: [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)

---

**Last Updated**: January 11, 2026  
**Status**: ✅ Production Ready
