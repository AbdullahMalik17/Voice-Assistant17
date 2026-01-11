# Tools System - Visual Architecture & Data Flow

## 1. COMPONENT ARCHITECTURE

```
┌──────────────────────────────────────────────────────────────────────┐
│                         TOOL REGISTRY                                │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │ Internal Storage                                           │    │
│  │ _tools: Dict[str, Tool]                                   │    │
│  │ _categories: Dict[Category, List[str]]                    │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Public API                                                  │   │
│  │ register(tool) → Add tool                                  │   │
│  │ get(name) → Get specific tool                             │   │
│  │ list_available() → All tools                              │   │
│  │ list_by_category(cat) → Filtered tools                    │   │
│  │ execute(name, **params) → Run tool                        │   │
│  │ get_tools_for_prompt() → LLM format                       │   │
│  └─────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
         ↑                    ↑                    ↑
         │                    │                    │
    ┌────────┐            ┌────────┐          ┌────────┐
    │ Planner│            │Executor│          │Discovery
    │(reads) │            │(exec)  │          │(inspect)
    └────────┘            └────────┘          └────────┘
```

---

## 2. TOOL CLASS HIERARCHY

```
┌──────────────────────────────┐
│   Tool (ABC)                 │
│ ────────────────────────────│
│ + name: str                 │
│ + description: str          │
│ + category: ToolCategory    │
│ + requires_confirmation: bool
│                            │
│ + _setup_parameters()       │
│ + execute() [ABSTRACT]      │
│ + validate_params()         │
│ + safe_execute()            │
│ + get_description()         │
└──────────────────────────────┘
         △
         │ inherits
         │
    ┌────┴─────────────────────────────────┐
    │                                       │
    │ Built-in Tools (15+)                 │
    │                                       │
┌───┴──────┐  ┌──────────────┐  ┌────────────────┐
│SystemTools│  │Communication │  │Productivity    │
├───────────┤  ├──────────────┤  ├────────────────┤
│System     │  │SendEmail     │  │SetTimer        │
│Status     │  │SendSlack     │  │ReadFile        │
│LaunchApp  │  │SendDiscord   │  │WriteFile       │
│Get        │  │              │  │List            │
│Time       │  │              │  │Directory       │
└───────────┘  └──────────────┘  └────────────────┘

┌──────────────┐  ┌─────────────┐
│Information   │  │Custom Tools │
├──────────────┤  ├─────────────┤
│WebSearch     │  │User-defined │
│Weather       │  │Extensions   │
│...           │  │...          │
└──────────────┘  └─────────────┘
```

---

## 3. EXECUTION FLOW

### Simple Tool Execution

```
User Request
     │
     ▼
NLU (Extract intent + params)
     │
     ├─ Intent: "set_timer"
     ├─ Params: duration=300
     └─ Lang: "natural_language"
     │
     ▼
Planner (LLM + Tool Descriptions)
     │
     ├─ Queries Registry: list_available()
     ├─ Gets Tool Descriptions
     ├─ LLM generates plan
     └─ Plan: [set_timer(duration_seconds=300, label="Timer")]
     │
     ▼
Streaming Executor
     │
     ├─ For each step in plan:
     │  └─ Call: executor.execute_step(step)
     │
     ▼
Registry.execute("set_timer", duration_seconds=300, label="Timer")
     │
     ├─ Get tool: SetTimerTool
     ├─ Call: tool.safe_execute(duration_seconds=300, label="Timer")
     │
     ▼
Tool.safe_execute()
     │
     ├─ [1] START TIMER: start_time = time.now()
     │
     ├─ [2] VALIDATE: validate_params(duration_seconds=300, label="Timer")
     │  ├─ duration_seconds in params? YES ✓
     │  ├─ Required? YES ✓
     │  └─ Type=number? YES ✓
     │
     ├─ [3] EXECUTE: result = execute(duration_seconds=300, label="Timer")
     │  └─ Returns: ToolResult(success=True, data={...})
     │
     ├─ [4] MEASURE: execution_time = time.now() - start_time
     │
     ▼
ExecutionFeedbackAnalyzer (if any failure)
     │
     ├─ Record failure pattern
     ├─ Classify error type
     └─ Track for learning
     │
     ▼
AgentMetrics
     │
     ├─ Record execution
     ├─ Track latency
     ├─ Update tool stats
     └─ Calculate health
     │
     ▼
Response to User
```

---

## 4. TOOL PARAMETER VALIDATION

```
Input Parameters
    │
    ▼
Validator Loop
    │
    ├─ For each ToolParameter in tool._parameters:
    │  │
    │  ├─ REQUIRED CHECK
    │  │  └─ If required=True and param not in input:
    │  │     └─ FAIL: "Missing required parameter: X"
    │  │
    │  ├─ TYPE CHECK
    │  │  └─ If param type is "number" and value is "abc":
    │  │     └─ FAIL: "Invalid type for X"
    │  │
    │  ├─ ENUM CHECK
    │  │  └─ If enum=["a", "b", "c"] and value="d":
    │  │     └─ FAIL: "Invalid value for X. Must be one of: a,b,c"
    │  │
    │  └─ DEFAULT
    │     └─ If not provided and default exists:
    │        └─ Use default value
    │
    ▼
VALID or ERROR
```

---

## 5. DATA FLOW: From Planning to Execution

```
PLANNING PHASE
═════════════════════════════════════════════════════════════

Registry
   │
   ├─ get_tools_for_prompt()
   │  └─ Formats all tools as:
   │     "- set_timer(duration_seconds: number, label?: string): ..."
   │     "- web_search(query: string, max_results?: number): ..."
   │     └─ Returns: String for LLM
   │
   ▼
LLM (Claude/Gemini)
   │
   ├─ Reads available tools
   ├─ Reads user goal
   ├─ Generates plan:
   │  {
   │    "steps": [
   │      {
   │        "action": "set_timer",
   │        "parameters": {"duration_seconds": 300, "label": "Break"}
   │      },
   │      {
   │        "action": "open_browser",
   │        "parameters": {"url": "https://example.com"}
   │      }
   │    ]
   │  }
   │
   └─ Returns JSON to Planner


EXECUTION PHASE
═════════════════════════════════════════════════════════════

Plan with Steps
   │
   ▼
StreamingExecutor.execute_streaming(plan)
   │
   ├─ For step 1: action="set_timer", params={duration_seconds: 300}
   │  │
   │  ├─ EMIT: step_started
   │  │
   │  ├─ Registry.execute("set_timer", duration_seconds=300)
   │  │  │
   │  │  ├─ Get: SetTimerTool
   │  │  ├─ Validate parameters ✓
   │  │  ├─ Execute: return ToolResult(success=True, data={...})
   │  │  │
   │  │  └─ Returns: ToolResult
   │  │
   │  ├─ EMIT: step_completed + result
   │  │
   │  ├─ ExecutionFeedbackAnalyzer.record_execution(success=True)
   │  │
   │  └─ AgentMetrics.record_step_execution(...)
   │
   ├─ For step 2: action="open_browser", params={url: "..."}
   │  │
   │  └─ ... (same flow)
   │
   ▼
Completion
   │
   ├─ Emit: plan_completed
   ├─ AgentStatePersistence.save_plan_state()
   └─ AgentMetrics.record_plan_completion()
```

---

## 6. TOOL CATEGORIES & ORGANIZATION

```
                    ToolRegistry
                         │
        ┌────────────────┼────────────────┐
        │                │                │
    SYSTEM            COMMUNICATION    PRODUCTIVITY
        │                │                │
   ┌────┴────┐      ┌────┴────┐     ┌────┴────┐
   │ System   │      │ Send     │     │ Set     │
   │ Status   │      │ Email    │     │ Timer   │
   │          │      │          │     │         │
   │ Launch   │      │ Send     │     │ Read    │
   │ App      │      │ Slack    │     │ File    │
   │          │      │          │     │         │
   │ Get      │      │ Send     │     │ Write   │
   │ Time     │      │ Discord  │     │ File    │
   └──────────┘      └──────────┘     └─────────┘

    INFORMATION        AUTOMATION      CUSTOM
        │                  │              │
   ┌────┴────┐        ┌────┴────┐   ┌────┴────┐
   │ Web      │        │ Browser  │   │ Your    │
   │ Search   │        │ Automate │   │ Tool 1  │
   │          │        │          │   │         │
   │ Weather  │        │ Keyboard │   │ Your    │
   │          │        │ Type     │   │ Tool 2  │
   │ Get Data │        │          │   │         │
   └──────────┘        └──────────┘   └─────────┘
```

---

## 7. LIFECYCLE: Tool Definition to Execution

```
TIME →

DEVELOPMENT TIME (Once per tool)
════════════════════════════════════
  Create class → Extend Tool
       │
       ├─ Set class attributes:
       │  ├─ name = "my_tool"
       │  ├─ description = "..."
       │  ├─ category = COMMUNICATION
       │  └─ requires_confirmation = True
       │
       ├─ Implement _setup_parameters()
       │  └─ Define: ToolParameter(name, type, required, ...)
       │
       └─ Implement execute(**params) -> ToolResult
          └─ Logic to do the work

STARTUP TIME (Once per server startup)
════════════════════════════════════════
  Create Registry → Register all tools
       │
       ├─ registry = ToolRegistry()
       ├─ registry.register(SetTimerTool())
       ├─ registry.register(WebSearchTool())
       ├─ registry.register(SendEmailTool())
       └─ ... (15+ more tools)

PLAN GENERATION TIME (Per user request)
════════════════════════════════════════
  LLM gets tool list
       │
       ├─ registry.get_tools_for_prompt()
       ├─ → "- set_timer(...): ..."
       ├─ → "- web_search(...): ..."
       └─ LLM generates plan

EXECUTION TIME (Per step in plan)
════════════════════════════════════
  Execute tool
       │
       ├─ registry.execute(tool_name, **params)
       ├─ → Validates parameters
       ├─ → Calls tool.execute()
       ├─ → Measures time
       └─ → Returns ToolResult

POST-EXECUTION (Learning)
════════════════════════════════════
  Track and learn
       │
       ├─ ExecutionFeedbackAnalyzer records patterns
       ├─ AgentMetrics updates KPIs
       ├─ AutonomousDecisionMaker updates trust
       └─ Next time: system is smarter!
```

---

## 8. TOOL EXECUTION: Detailed Step-by-Step

```
┌─────────────────────────────────────────────────────┐
│ registry.execute("set_timer",                        │
│                  duration_seconds=300,               │
│                  label="Break")                       │
└──────────────────────────┬──────────────────────────┘
                           │
         ┌─────────────────┴─────────────────┐
         │                                   │
         ▼                                   ▼
    ┌────────────────┐            ┌──────────────────────┐
    │ STEP 1: LOOKUP │            │ STEP 2: SAFE EXECUTE │
    ├────────────────┤            ├──────────────────────┤
    │ Get tool from  │            │ Tool.safe_execute()  │
    │ self._tools    │            │                      │
    │ by name        │────────────┤ START: t0 = now()    │
    │                │            │                      │
    │ Found:         │            │ VALIDATE:            │
    │ SetTimerTool   │            │ - Check required ✓   │
    │                │            │ - Check types ✓      │
    │                │            │ - Check enums ✓      │
    │                │            │                      │
    │ If not found:  │            │ EXECUTE:             │
    │ return error   │            │ result =             │
    └────────────────┘            │   tool.execute(...)  │
                                  │                      │
                                  │ MEASURE:             │
                                  │ dt = now() - t0      │
                                  │ result.exec_time = dt│
                                  │                      │
                                  │ RETURN: ToolResult   │
                                  └──────────────────────┘
                                           │
                    ┌──────────────────────┴──────────────────┐
                    │                                         │
                    ▼                                         ▼
            ┌─────────────────┐                    ┌──────────────────┐
            │ SUCCESS CASE    │                    │ ERROR CASE       │
            ├─────────────────┤                    ├──────────────────┤
            │ ToolResult:     │                    │ ToolResult:      │
            │ - success: True │                    │ - success: False │
            │ - data: {...}   │                    │ - error: "msg"   │
            │ - message: "OK" │                    │ - exec_time: ms  │
            │ - exec_time: ms │                    │                  │
            │ - error: None   │                    │ Caught by:       │
            │                 │                    │ ExecutionFeedback
            │ Processed by:   │                    │ ExecutorAnalyzer │
            │ - Executor      │                    │ - Metrics        │
            │ - Metrics       │                    │ - Planner        │
            │ - Feedback      │                    │                  │
            └─────────────────┘                    └──────────────────┘
```

---

## 9. INTEGRATION WITH AGENTIC COMPONENTS

```
                        TOOL REGISTRY
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
          ▼                  ▼                  ▼
      PLANNER          STREAMING             GUARDRAILS
                       EXECUTOR
          │                  │                  │
          ├─ Gets tools  ├─ Executes      ├─ Checks safety
          │  descriptions    tools            for actions
          │                  │                │
          ├─ Formats for ├─ Measures       ├─ Gets confirmation
          │  LLM prompt      time           │  status
          │                  │                │
          └─ Uses for    └─ Records in   └─ Maps to risk
             planning         metrics         levels

          │                  │                  │
          └──────────────────┼──────────────────┘
                             │
                    EXECUTION FEEDBACK
                   ANALYZER & METRICS
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
          ▼                  ▼                  ▼
      FAILURE           TOOL STATS         AUTONOMY
      PATTERNS          BY TOOL            DECISION
          │                  │                │
          ├─ Classify    ├─ Success rate    ├─ Track trust
          │  error types     per tool         │  scores
          │                  │                │
          ├─ Record       ├─ Latency %ile    ├─ Build user
          │  patterns        (p50,p95,p99)   │  profiles
          │                  │                │
          └─ Suggest      └─ Top failing   └─ Auto-approve
             improvements     tools            future actions
```

---

## 10. PERFORMANCE & MONITORING

```
Tool Execution Metrics Collection
═══════════════════════════════════════════

For each tool execution:

START → VALIDATE → EXECUTE → MEASURE → STORE
                                  │
                                  ├─ execution_time_ms
                                  ├─ success/failure
                                  ├─ error type
                                  ├─ parameters used
                                  └─ result data

Aggregation (per tool):
═══════════════════════════════════════════

Collected data:
└─ Last 1000 executions per tool

Calculated:
├─ executions: 1000
├─ successes: 950
├─ failures: 50
├─ success_rate: 95%
├─ avg_latency: 1234ms
├─ p50_latency: 800ms
├─ p95_latency: 2500ms
├─ p99_latency: 4100ms
├─ top_errors: [(error_type, count), ...]
└─ health: 🟢 GOOD / 🟡 FAIR / 🔴 POOR

Dashboard Display:
═══════════════════════════════════════════

Top Failing Tools          | Tool Reliability
─────────────────────────────────────────────
browser_automation: 18%    | set_timer: 99%
slack_message: 15%         | web_search: 95%
send_email: 12%            | system_status: 100%
open_app: 10%              | read_file: 98%
keyboard_type: 8%          | write_file: 97%
```

---

## Summary

The Tools system is:
- ✅ **Centralized** - All tools managed by ToolRegistry
- ✅ **Type-safe** - Parameters validated before execution
- ✅ **Measurable** - Every execution tracked for metrics
- ✅ **Learnable** - Failures analyzed for improvement
- ✅ **Extensible** - Easy to add custom tools
- ✅ **Production-ready** - Error handling, timeouts, logging

**The tools are the atomic actions that power the entire agentic system!**
