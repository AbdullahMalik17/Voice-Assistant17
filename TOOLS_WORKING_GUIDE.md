# Tools Module - Complete Working Guide

**Location**: `src/agents/tools.py`  
**Purpose**: Atomic actions that the agentic system can execute  
**Status**: Production-ready with 15+ built-in tools

---

## 🏗️ Architecture Overview

### Component Hierarchy

```
Tool (Abstract Base Class)
├── Built-in Tools (15+)
│   ├── SystemStatusTool
│   ├── SetTimerTool
│   ├── WebSearchTool
│   ├── LaunchAppTool
│   ├── SendEmailTool
│   ├── SendSlackMessage
│   ├── OpenBrowserTool
│   ├── ReadFileContent
│   ├── WriteFileTool
│   ├── ListDirectoryTool
│   ├── CreateGmailDraft
│   ├── CreateNotion
│   └── [Others...]
│
└── Custom Tools (User-defined)
    ├── Your Custom Tool 1
    └── Your Custom Tool 2

ToolRegistry (Management Layer)
├── Register/Unregister tools
├── Discovery & lookup
├── Category filtering
└── Safe execution with validation
```

---

## 📚 Core Classes

### 1. **ToolParameter** - Defines What Tool Expects

```python
class ToolParameter:
    """Describes a single parameter for a tool"""
    name: str                    # "duration_seconds"
    type: str                    # "string" | "number" | "boolean" | "array" | "object"
    description: str             # Human-readable description
    required: bool               # True/False
    default: Optional[Any]       # Default value if not provided
    enum: Optional[List[Any]]    # Valid values to restrict input
    items_type: Optional[str]    # Type of items in array
```

**Example**:
```python
ToolParameter(
    name="duration_seconds",
    type="number",
    description="Duration in seconds",
    required=True
)

ToolParameter(
    name="info_type",
    type="string",
    description="Type of information to get",
    required=False,
    default="all",
    enum=["cpu", "memory", "disk", "battery", "all"]
)
```

---

### 2. **ToolResult** - What Tool Returns

```python
@dataclass
class ToolResult:
    """Result of tool execution"""
    success: bool                # True if succeeded
    data: Optional[Any]          # Result data
    message: Optional[str]       # Human-readable message
    error: Optional[str]         # Error message if failed
    execution_time_ms: float     # How long it took
    metadata: Dict[str, Any]     # Additional metadata
```

**Example**:
```python
# Success result
ToolResult(
    success=True,
    data={
        "timer_id": "timer_123",
        "duration_seconds": 300,
        "end_time": 1234567890
    },
    message="Timer set successfully",
    execution_time_ms=12.5
)

# Failure result
ToolResult(
    success=False,
    error="Missing required parameter: duration_seconds",
    execution_time_ms=2.1
)
```

---

### 3. **ToolDescription** - Metadata for Planning

```python
@dataclass
class ToolDescription:
    """How the planner knows about a tool"""
    name: str                           # "set_timer"
    description: str                    # What it does
    category: ToolCategory              # SYSTEM, COMMUNICATION, etc.
    parameters: List[ToolParameter]     # What it needs
    requires_confirmation: bool         # Needs user approval?
    examples: List[str]                 # Usage examples
```

**Used by LLM to plan**:
```
Available tools:
- set_timer(duration_seconds: number, label?: string): Set a countdown timer
- web_search(query: string, max_results?: number): Search the web
- system_status(info_type?: string): Get system information
```

---

### 4. **Tool** - Abstract Base Class

All tools inherit from this:

```python
class Tool(ABC):
    # Class-level metadata
    name: str = "base_tool"
    description: str = "Base tool"
    category: ToolCategory = ToolCategory.CUSTOM
    requires_confirmation: bool = False
    
    def _setup_parameters(self) -> None:
        """Override to define parameters"""
        pass
    
    @abstractmethod
    def execute(self, **params: Any) -> ToolResult:
        """Override to implement tool logic"""
        pass
    
    def validate_params(self, params: Dict) -> Optional[str]:
        """Checks parameters are valid"""
        pass
    
    def safe_execute(self, **params: Any) -> ToolResult:
        """Execute with validation + error handling"""
        pass
    
    def get_description(self) -> ToolDescription:
        """Get metadata for planner"""
        pass
```

---

### 5. **ToolRegistry** - Manages All Tools

```python
class ToolRegistry:
    """Central registry for all available tools"""
    
    def register(self, tool: Tool) -> None:
        """Register a new tool"""
        
    def unregister(self, tool_name: str) -> bool:
        """Unregister a tool"""
        
    def get(self, tool_name: str) -> Optional[Tool]:
        """Get a specific tool"""
        
    def list_available(self) -> List[ToolDescription]:
        """List all tools with descriptions"""
        
    def list_by_category(self, category: ToolCategory) -> List[ToolDescription]:
        """Get tools in a category"""
        
    def get_tools_for_prompt(self) -> str:
        """Format all tools for LLM prompts"""
        
    def execute(self, tool_name: str, **params: Any) -> ToolResult:
        """Execute a tool by name"""
        
    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics"""
```

---

## 🔧 How It Works - Step by Step

### Flow 1: Simple Execution

```
User: "Set a timer for 5 minutes"
  ↓
NLU → Intent: set_timer
  ↓
Planner retrieves tool description from Registry
  ├─ Name: set_timer
  ├─ Params: [duration_seconds: number, label?: string]
  ├─ Requires confirmation: false
  └─ Examples: ["Set a timer for 5 minutes", ...]
  ↓
Planner creates step: set_timer(duration_seconds=300, label="Timer")
  ↓
StreamingExecutor calls:
  registry.execute("set_timer", duration_seconds=300, label="Timer")
  ↓
Registry gets the SetTimerTool and calls: tool.safe_execute(...)
  ├─ Validates parameters
  │  └─ "duration_seconds" is required ✓
  │  └─ "label" is string ✓
  ├─ Measures execution time
  ├─ Calls: tool.execute(duration_seconds=300, label="Timer")
  └─ Returns: ToolResult(success=True, data={...})
  ↓
StreamingExecutor emits: step_completed event
  ↓
Metrics collector records success
  ↓
"Timer set for 5 minutes" (audio + text)
```

---

### Flow 2: Complex Multi-Tool Plan

```
User: "Search for Python tutorials and send results to my email"
  ↓
Planner creates 3-step plan:
  Step 1: web_search(query="Python tutorials", max_results=5)
  Step 2: create_gmail_draft(to="user@gmail.com", subject="Python Tutorials", body="{results from step 1}")
  Step 3: send_email(draft_id="{draft_id from step 2}")
  ↓
Executor runs sequentially:
  
  Step 1: web_search
  ├─ Registry gets WebSearchTool
  ├─ Validates: query="Python tutorials" ✓, max_results=5 ✓
  ├─ Tool tries Tavily API (if key exists)
  ├─ Falls back to DuckDuckGo if needed
  └─ Returns: ToolResult with [{"title": "...", "link": "...", "snippet": "..."}, ...]
  
  Step 2: create_gmail_draft (depends on Step 1)
  ├─ Registry gets CreateGmailDraftTool
  ├─ Validates: to, subject, body ✓
  ├─ Uses Google Gmail API
  └─ Returns: ToolResult with draft_id and preview
  
  Step 3: send_email (depends on Step 2)
  ├─ Registry gets SendEmailTool
  ├─ Validates: draft_id ✓
  ├─ Calls Gmail API to send
  └─ Returns: ToolResult with message_id and confirmation
  ↓
"Found 5 tutorials and sent them to your email"
```

---

### Flow 3: Tool with Confirmation

```
User: "Delete the file important.txt"
  ↓
Planner creates: delete_file(path="/path/to/important.txt")
  ↓
Registry gets DeleteFileTool (requires_confirmation=True)
  ↓
Safety Guardrails check:
  ├─ Action: delete_file
  ├─ Risk level: CRITICAL
  ├─ Requires confirmation: YES
  └─ Reason: Destructive operation on system file
  ↓
StreamingExecutor emits: confirmation_needed event
  ↓
WebSocket sends to UI: "Please confirm: Delete file important.txt?"
  ↓
User clicks "Confirm" or "Cancel"
  ├─ If Confirm:
  │  └─ ExecutionFeedbackAnalyzer records:
  │     - Action: delete_file
  │     - Result: success
  │     - Confirmation: approved
  │     - AutonomousDecisionMaker updates trust score
  │
  └─ If Cancel:
     └─ Step marked CANCELLED, plan continues (if possible)
```

---

## 📋 Built-in Tools Reference

### System Tools (ToolCategory.SYSTEM)

```python
# 1. SystemStatusTool
get_system_info(info_type: "cpu" | "memory" | "disk" | "battery" | "all")
→ ToolResult: {cpu_percent, memory_percent, disk_free_gb, battery_percent, ...}

# 2. LaunchAppTool
launch_app(app_name: str, wait: bool?)
→ ToolResult: {success, message, process_id}

# 3. GetCurrentTimeTool
get_current_time()
→ ToolResult: {timestamp, formatted_time, date, day_of_week}
```

### Productivity Tools (ToolCategory.PRODUCTIVITY)

```python
# 1. SetTimerTool
set_timer(duration_seconds: number, label: string?)
→ ToolResult: {message, duration_seconds, end_time}

# 2. ReadFileContentTool
read_file(path: str, encoding: "utf-8"?)
→ ToolResult: {content, size_bytes, last_modified}

# 3. WriteFileTool
write_file(path: str, content: str, append: bool?)
→ ToolResult: {success, bytes_written, file_path}

# 4. ListDirectoryTool
list_directory(path: str, recursive: bool?)
→ ToolResult: {files, directories, total_items}
```

### Communication Tools (ToolCategory.COMMUNICATION)

```python
# 1. SendEmailTool
send_email(to: str, subject: str, body: str, cc?: str, bcc?: str)
→ ToolResult: {message_id, timestamp, status}

# 2. SendSlackMessageTool
send_slack_message(channel: str, message: str, thread_ts?: str)
→ ToolResult: {timestamp, channel, message_text}

# 3. SendDiscordMessageTool
send_discord_message(channel_id: str, message: str)
→ ToolResult: {message_id, channel_id, timestamp}
```

### Information Tools (ToolCategory.INFORMATION)

```python
# 1. WebSearchTool
web_search(query: str, max_results: number?)
→ ToolResult: {results: [{title, link, snippet}, ...], source: "tavily" | "duckduckgo"}

# 2. WeatherTool
get_weather(location: str, units: "C" | "F"?)
→ ToolResult: {temperature, description, humidity, wind_speed}

# 3. GetCurrentWeatherTool
get_current_weather(location: str, units?: string)
→ ToolResult: {current_weather_data}
```

---

## 💻 Creating Custom Tools

### Example: Custom "AnalyzeSentiment" Tool

```python
from src.agents.tools import Tool, ToolCategory, ToolParameter, ToolResult

class AnalyzeSentimentTool(Tool):
    """Analyze sentiment of text"""
    name = "analyze_sentiment"
    description = "Analyze the sentiment (positive, negative, neutral) of text"
    category = ToolCategory.INFORMATION
    requires_confirmation = False
    
    def _setup_parameters(self) -> None:
        """Define what parameters this tool needs"""
        self._parameters = [
            ToolParameter(
                name="text",
                type="string",
                description="Text to analyze",
                required=True
            ),
            ToolParameter(
                name="language",
                type="string",
                description="Language of text",
                required=False,
                default="en",
                enum=["en", "es", "fr", "de"]
            )
        ]
        self._examples = [
            "Analyze sentiment of: I love this product!",
            "What's the sentiment of this review?",
            "Is this negative feedback?"
        ]
    
    def execute(self, text: str, language: str = "en", **params) -> ToolResult:
        """Implement the tool logic"""
        try:
            # Use TextBlob for sentiment analysis
            from textblob import TextBlob
            
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity  # -1 to 1
            subjectivity = blob.sentiment.subjectivity  # 0 to 1
            
            # Classify sentiment
            if polarity > 0.1:
                sentiment = "positive"
            elif polarity < -0.1:
                sentiment = "negative"
            else:
                sentiment = "neutral"
            
            return ToolResult(
                success=True,
                data={
                    "text": text[:100],  # First 100 chars
                    "sentiment": sentiment,
                    "polarity": round(polarity, 3),
                    "subjectivity": round(subjectivity, 3),
                    "language": language
                },
                message=f"Text sentiment: {sentiment}"
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Failed to analyze sentiment: {str(e)}"
            )


# Register the custom tool
from src.agents.tools import ToolRegistry

registry = ToolRegistry()
registry.register(AnalyzeSentimentTool())

# Now it's available for the agent to use!
result = registry.execute(
    "analyze_sentiment",
    text="I absolutely love this amazing product!",
    language="en"
)
print(result.data)
# Output: {
#   "text": "I absolutely love this amazing product!",
#   "sentiment": "positive",
#   "polarity": 0.875,
#   "subjectivity": 0.75,
#   "language": "en"
# }
```

---

## 🔄 Integration with Agentic System

### How Registry Integrates

```python
# 1. In AgenticPlanner
planner = AgenticPlanner(tool_registry=registry)

# 2. When creating plans, planner calls:
tools_prompt = registry.get_tools_for_prompt()
# Returns:
# Available tools:
# - set_timer(duration_seconds: number, label?: string): Set a countdown timer
# - web_search(query: string, max_results?: number): Search the web
# ...

# 3. LLM sees available tools and includes in plan

# 4. During execution, StreamingExecutor calls:
result = registry.execute(tool_name, **params)

# 5. ExecutionFeedbackAnalyzer tracks:
feedback.record_failure(step, result)  # If failed
metrics.record_step_execution(tool_name, success, latency)
```

---

## 📊 Tool Lifecycle

```
1. DEFINITION (Build time)
   └─ Extend Tool class
   └─ Define name, category, requires_confirmation
   └─ Implement _setup_parameters()
   └─ Implement execute() method

2. REGISTRATION (Startup time)
   └─ registry.register(MyTool())
   └─ Tool added to registry
   └─ Indexed by category

3. DISCOVERY (Plan generation time)
   └─ registry.list_available()
   └─ registry.list_by_category(COMMUNICATION)
   └─ registry.get_tools_for_prompt()
   └─ LLM sees available tools

4. EXECUTION (Runtime)
   └─ Planner includes tool in plan
   └─ Executor calls registry.execute(tool_name, **params)
   └─ Tool.safe_execute() validates, measures time, handles errors
   └─ Returns ToolResult

5. LEARNING (Post-execution)
   └─ ExecutionFeedbackAnalyzer tracks failure patterns
   └─ AgentMetrics records tool reliability
   └─ AutonomousDecisionMaker builds trust score
   └─ Next time, system is smarter
```

---

## 🎯 Tool Execution Statistics

### Tracked per Tool

```python
metrics.get_tool_metrics("send_email")
# Returns:
{
    "tool": "send_email",
    "executions": 45,
    "successes": 42,
    "failures": 3,
    "success_rate": "93.3%",
    "avg_latency_ms": "1245.3",
    "p95_latency_ms": "2500.1",
    "top_errors": [
        "SMTP connection timeout (2 times)",
        "Invalid recipient address (1 time)"
    ]
}
```

### Top Failing Tools

```python
metrics.get_top_failing_tools(top_n=5)
# Returns tools sorted by failure rate:
[
    {"tool": "open_slack", "failures": 12, "failure_rate": "18%"},
    {"tool": "browser_automation", "failures": 8, "failure_rate": "15%"},
    {"tool": "send_teams_message", "failures": 5, "failure_rate": "12%"},
    ...
]
```

---

## 🧪 Testing & Debugging

### Test a Tool

```python
from src.agents.tools import ToolRegistry, SetTimerTool

# Create and register
registry = ToolRegistry()
registry.register(SetTimerTool())

# Test execution
result = registry.execute(
    "set_timer",
    duration_seconds=300,
    label="Work Break"
)

# Check result
print(f"Success: {result.success}")
print(f"Data: {result.data}")
print(f"Time taken: {result.execution_time_ms}ms")

assert result.success == True
assert result.data["duration_seconds"] == 300
assert result.execution_time_ms < 50  # Should be instant
```

### Validate Parameters

```python
tool = SetTimerTool()

# Test validation
error = tool.validate_params({
    "duration_seconds": 300
})
print(error)  # None (valid)

error = tool.validate_params({
    "label": "Test"
    # Missing duration_seconds!
})
print(error)  # "Missing required parameter: duration_seconds"
```

---

## 🚀 Performance Considerations

### Execution Time Tracking
```python
# Each tool tracks own execution time
result.execution_time_ms  # How long tool took

# Metrics aggregate by tool
metrics.get_tool_metrics("web_search")
# "avg_latency_ms": "2145.3"
# "p95_latency_ms": "5342.1"  # 95th percentile
```

### Best Practices

1. **Keep tools focused** - One thing per tool
2. **Validate early** - Fail fast with good errors
3. **Handle timeouts** - Don't hang forever
4. **Log errors** - Help with debugging
5. **Return metadata** - Include timing, IDs, etc.

---

## 📖 Summary

```
┌─────────────────────────────────────────┐
│         Tools Architecture              │
├─────────────────────────────────────────┤
│                                         │
│  Tool (ABC)                             │
│  ├─ 15+ Built-in Tools                 │
│  └─ Unlimited Custom Tools              │
│                                         │
│  ToolParameter (defines inputs)         │
│  ToolResult (defines outputs)           │
│  ToolDescription (for planner)          │
│                                         │
│  ToolRegistry (central management)      │
│  ├─ register(tool)                      │
│  ├─ execute(name, **params)             │
│  ├─ list_available()                    │
│  └─ get_stats()                         │
│                                         │
│  Integration Points:                    │
│  ├─ Planner (gets tool descriptions)    │
│  ├─ Executor (executes tools)           │
│  ├─ Feedback (tracks failures)          │
│  └─ Metrics (measures performance)      │
│                                         │
└─────────────────────────────────────────┘
```

**Everything is production-ready and extensible!**
