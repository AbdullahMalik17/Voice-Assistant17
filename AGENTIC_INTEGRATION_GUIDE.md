# Agentic System Integration Guide

Quick start guide for integrating the new agentic components.

## Quick Start

### Initialize Components

```python
from src.agents import (
    ReasoningPlanner,
    StreamingExecutor,
    AutonomousDecisionMaker,
    ExecutionFeedbackAnalyzer,
    AgentStatePersistence,
    AgentMetrics
)
from src.memory.semantic_memory import SemanticMemory

# Initialize all services
memory = SemanticMemory()
planner = ReasoningPlanner(
    tool_registry=tools,
    guardrails=guardrails,
    llm_service=llm,
    memory_service=memory
)
decision_maker = AutonomousDecisionMaker(user_id="user123")
feedback = ExecutionFeedbackAnalyzer(user_id="user123")
executor = StreamingExecutor(
    tool_registry=tools,
    feedback_analyzer=feedback
)
persistence = AgentStatePersistence()
metrics = AgentMetrics()
```

## WebSocket Integration

Update your WebSocket handler to stream execution events:

```python
async def handle_plan_execution(websocket, plan):
    async for event in executor.execute_streaming(plan):
        await websocket.send_json({
            "type": "execution_event",
            "event_type": event.event_type,
            "message": event.message
        })
        
        # Record metrics
        if event.event_type == "step_completed":
            metrics.record_step_execution(
                tool_name=event.step.action,
                success=True,
                latency_seconds=...
            )
    
    # Save state when done
    persistence.save_plan_state(plan)
    metrics.record_plan_completion(plan)
```

## Memory Integration

Memory is auto-enabled if memory_service is provided to planner:

```python
# Store user actions
memory.store(
    content="User opened Slack and sent message",
    user_id="user123",
    intent="slack_communication"
)

# Planner automatically retrieves context for better planning
plan, reasoning = planner.create_plan_with_reasoning(
    goal="Send message to team",
    user_id="user123"
)
```

## Metrics API Endpoint

Add to your API server:

```python
@app.get("/api/metrics")
async def get_metrics():
    return metrics.get_dashboard_summary()

@app.get("/api/metrics/export")
async def export_metrics():
    return metrics.export_metrics()
```

## Frontend Components

Create execution visualizer in React:

```typescript
export function ExecutionVisualizer({ planId }) {
  const [events, setEvents] = useState([]);
  
  useEffect(() => {
    subscribe(`plan:${planId}`, (event) => {
      setEvents(prev => [...prev, event]);
    });
  }, [planId]);
  
  return (
    <div>
      {events.map(e => (
        <div key={e.id}>{e.type}: {e.message}</div>
      ))}
    </div>
  );
}
```

## Testing

See test_agent_integration.py for complete examples:

```bash
pytest test_agent_integration.py -v
```

## Configuration

Set trust thresholds for autonomy decisions in AutonomousDecisionMaker:

```python
decision_maker.daily_action_limits = {
    "critical": 3,
    "high": 10,
    "medium": 50,
    "low": 999
}
```

## Checklist

- [ ] Import agentic modules
- [ ] Initialize all components
- [ ] Update WebSocket to stream events
- [ ] Add metrics endpoint
- [ ] Create ExecutionVisualizer component
- [ ] Store user actions in memory
- [ ] Test end-to-end flow
