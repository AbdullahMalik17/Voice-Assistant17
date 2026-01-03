# Implementation Plan: Agentic AI Improvements

**Feature**: 002-agentic-ai-improvements
**Created**: 2026-01-03
**Status**: Draft

## Architecture Overview

```
                    ┌──────────────────────────────────────────────────────────┐
                    │                     VOICE ASSISTANT                       │
                    │                   (Agentic AI System)                     │
                    └──────────────────────────┬───────────────────────────────┘
                                               │
    ┌──────────────────────────────────────────┼──────────────────────────────────────────┐
    │                                          │                                          │
    ▼                                          ▼                                          ▼
┌────────────────┐                    ┌────────────────┐                    ┌────────────────┐
│ INPUT LAYER    │                    │ PROCESSING     │                    │ OUTPUT LAYER   │
│                │                    │ LAYER          │                    │                │
│ ┌────────────┐ │                    │ ┌────────────┐ │                    │ ┌────────────┐ │
│ │Audio       │ │                    │ │Semantic    │ │                    │ │TTS Engine  │ │
│ │Preprocessor│ │                    │ │Memory (RAG)│ │                    │ │            │ │
│ │- AEC       │ │                    │ │- ChromaDB  │ │                    │ │- ElevenLabs│ │
│ │- Noise Gate│ │                    │ │- Embeddings│ │                    │ │- Piper     │ │
│ └────────────┘ │                    │ └────────────┘ │                    │ └────────────┘ │
│ ┌────────────┐ │                    │ ┌────────────┐ │                    │ ┌────────────┐ │
│ │STT Engine  │ │                    │ │NLU Engine  │ │                    │ │Action      │ │
│ │- Whisper   │ │                    │ │- Entities  │ │                    │ │Executor    │ │
│ │- Vosk      │ │                    │ │- Slots     │ │                    │ │- Local     │ │
│ │- Kaldi     │ │                    │ │- Intents   │ │                    │ │- Remote    │ │
│ └────────────┘ │                    │ └────────────┘ │                    │ └────────────┘ │
│ ┌────────────┐ │                    │ ┌────────────┐ │                    │ ┌────────────┐ │
│ │Wake Word   │ │                    │ │Agentic     │ │                    │ │Tool        │ │
│ │Detector    │ │                    │ │Planner     │ │                    │ │Integrations│ │
│ │- Porcupine │ │                    │ │- Goals     │ │                    │ │- Calendar  │ │
│ └────────────┘ │                    │ │- Plans     │ │                    │ │- Email     │ │
└────────────────┘                    │ │- Steps     │ │                    │ │- Weather   │ │
                                      │ └────────────┘ │                    │ │- Web       │ │
                                      │ ┌────────────┐ │                    │ └────────────┘ │
                                      │ │Dialogue    │ │                    └────────────────┘
                                      │ │State Mgr   │ │
                                      │ │- Context   │ │
                                      │ │- History   │ │
                                      │ └────────────┘ │
                                      └────────────────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────────┐
                    │                          │                              │
                    ▼                          ▼                              ▼
            ┌────────────────┐        ┌────────────────┐        ┌────────────────┐
            │ OBSERVABILITY  │        │ STORAGE        │        │ EXTERNAL APIS  │
            │                │        │                │        │                │
            │ - Prometheus   │        │ - SQLite       │        │ - Gemini LLM   │
            │ - Grafana      │        │ - ChromaDB     │        │ - OpenAI       │
            │ - Tracing      │        │ - Encrypted    │        │ - Weather      │
            │ - Alerting     │        │ - Memory       │        │ - Calendar     │
            └────────────────┘        └────────────────┘        └────────────────┘
```

## Phase 1: Audio Preprocessing & STT Robustness

### 1.1 Audio Preprocessor Module

**Location**: `src/services/audio_preprocessor.py`

**Components**:
- **NoiseGate**: Spectral gating using `noisereduce` library
- **AcousticEchoCanceller**: WebRTC AEC or `speexdsp` bindings
- **Normalizer**: Audio level normalization for consistent STT input

**Dependencies**:
```
noisereduce>=3.0.0      # Spectral noise reduction
webrtcvad>=2.0.10       # Voice activity detection
numpy>=1.24.0           # Array operations
scipy>=1.10.0           # Signal processing
```

**Interface**:
```python
class AudioPreprocessor:
    def __init__(self, config: AudioPreprocessorConfig):
        self.noise_gate = NoiseGate(threshold_db=config.noise_threshold)
        self.aec = AcousticEchoCanceller(enabled=config.aec_enabled)
        self.normalizer = Normalizer(target_db=config.target_level)

    def process(self, audio: bytes, reference: Optional[bytes] = None) -> ProcessedAudio:
        """Process raw audio through noise reduction and AEC."""
        pass
```

### 1.2 STT Confidence Handling

**Modifications to**: `src/services/stt.py`

- Add confidence threshold check (default 0.6)
- Implement clarification request when confidence low
- Add alternative STT engines (Vosk, Kaldi) as fallback options

**Configuration**:
```yaml
stt:
  confidence_threshold: 0.6
  clarification_prompt: "I didn't catch that. Could you repeat?"
  fallback_engines:
    - whisper
    - vosk
    - api
```

---

## Phase 2: Semantic Memory System

### 2.1 Vector Store Integration

**Location**: `src/memory/semantic_memory.py`

**Technology**: ChromaDB (embedded, no external service needed)

**Dependencies**:
```
chromadb>=0.4.0         # Vector database
sentence-transformers>=2.2.0  # Embeddings
```

**Schema**:
```python
@dataclass
class MemoryEntry:
    id: str
    content: str                    # Original text
    embedding: List[float]          # 384-dim vector
    metadata: Dict[str, Any]        # session_id, timestamp, entities
    created_at: datetime
    expires_at: Optional[datetime]  # Retention policy
```

**Interface**:
```python
class SemanticMemory:
    def store(self, content: str, metadata: Dict) -> str:
        """Store content with auto-generated embedding."""
        pass

    def retrieve(self, query: str, top_k: int = 5) -> List[MemoryEntry]:
        """Retrieve similar memories using semantic search."""
        pass

    def forget(self, session_id: Optional[str] = None) -> int:
        """Delete memories by session or expired."""
        pass
```

### 2.2 Dialogue State Manager

**Location**: `src/core/dialogue_state.py`

**Replaces**: Fixed 5-exchange FIFO in `context_manager.py`

**Features**:
- Dynamic conversation tracking (no fixed window)
- Slot tracking for multi-turn tasks
- Goal/subgoal tracking for planning
- Automatic summarization for long conversations

**Schema**:
```python
@dataclass
class DialogueState:
    session_id: str
    current_intent: Optional[Intent]
    filled_slots: Dict[str, Any]
    pending_slots: List[str]
    active_plan: Optional[Plan]
    history: List[Turn]            # Full history
    summary: Optional[str]         # Compressed for long conversations
    last_update: datetime
```

---

## Phase 3: Enhanced NLU

### 3.1 Entity Extraction

**Location**: `src/services/entity_extractor.py`

**Approach**: LLM-based extraction with structured output

**Supported Entities**:
- DATE, TIME, DATETIME
- PERSON, ORGANIZATION
- LOCATION
- NUMBER, MONEY, DURATION
- APP_NAME, URL, EMAIL

**Implementation**:
```python
class EntityExtractor:
    def __init__(self, llm: LLMService):
        self.llm = llm
        self.prompt = ENTITY_EXTRACTION_PROMPT

    def extract(self, text: str) -> List[Entity]:
        """Extract entities using LLM with structured output."""
        response = self.llm.generate(
            prompt=self.prompt.format(text=text),
            response_format={"type": "json_object"}
        )
        return self._parse_entities(response)
```

### 3.2 Slot Filler

**Location**: `src/services/slot_filler.py`

**Purpose**: Track required parameters for task-based intents

**Schema**:
```python
@dataclass
class SlotDefinition:
    name: str
    entity_type: str
    required: bool
    prompt: str          # Question to ask if missing
    default: Optional[Any]

@dataclass
class IntentSlots:
    intent: str
    slots: List[SlotDefinition]
```

**Slot Definitions** (config-driven):
```yaml
slots:
  set_timer:
    - name: duration
      entity_type: DURATION
      required: true
      prompt: "How long should I set the timer for?"

  send_email:
    - name: recipient
      entity_type: EMAIL
      required: true
      prompt: "Who should I send this to?"
    - name: subject
      entity_type: TEXT
      required: false
      default: "(No subject)"
```

### 3.3 LLM-Based Intent Classification

**Modifications to**: `src/services/intent_classifier.py`

**Changes**:
- Use LLM for primary classification
- Keep regex patterns as fast fallback
- Return multiple candidates with confidence scores

---

## Phase 4: Agentic Planner

### 4.1 Planner Module

**Location**: `src/agents/planner.py`

**Purpose**: Decompose complex goals into executable steps

**Architecture**:
```
User Goal → Planner → Plan → Executor → Results
               │
               ├── Tool Discovery
               ├── Step Generation
               ├── Dependency Resolution
               └── Safety Validation
```

**Schema**:
```python
@dataclass
class PlanStep:
    id: str
    action: str                  # Tool to invoke
    parameters: Dict[str, Any]   # Filled from slots/context
    depends_on: List[str]        # Step IDs that must complete first
    requires_confirmation: bool  # Sensitive action flag
    status: StepStatus          # pending, running, completed, failed

@dataclass
class Plan:
    id: str
    goal: str                    # Original user request
    steps: List[PlanStep]
    current_step: int
    status: PlanStatus
    created_at: datetime
```

**Implementation**:
```python
class AgenticPlanner:
    def __init__(self, llm: LLMService, tools: ToolRegistry):
        self.llm = llm
        self.tools = tools

    def create_plan(self, goal: str, context: DialogueState) -> Plan:
        """Generate execution plan from natural language goal."""
        available_tools = self.tools.list_available()
        prompt = PLANNING_PROMPT.format(
            goal=goal,
            tools=available_tools,
            context=context.summary
        )
        plan_json = self.llm.generate(prompt, response_format={"type": "json_object"})
        return self._parse_and_validate(plan_json)

    def execute(self, plan: Plan) -> Generator[StepResult, None, None]:
        """Execute plan steps, yielding results for progress reporting."""
        pass
```

### 4.2 Tool Registry

**Location**: `src/agents/tools.py`

**Purpose**: Manage available tools for the planner

**Built-in Tools**:
- `system_status`: CPU, memory, disk, battery
- `launch_app`: Open applications
- `web_search`: Search the web
- `calendar_read`: Read calendar events
- `calendar_write`: Create calendar events
- `send_email`: Compose and send email
- `get_weather`: Current weather and forecast
- `set_timer`: Set countdown timer
- `set_reminder`: Set future reminder

**Interface**:
```python
class Tool(ABC):
    name: str
    description: str
    parameters: List[ToolParameter]
    requires_confirmation: bool

    @abstractmethod
    def execute(self, params: Dict[str, Any]) -> ToolResult:
        pass

class ToolRegistry:
    def register(self, tool: Tool) -> None: ...
    def get(self, name: str) -> Tool: ...
    def list_available(self) -> List[ToolDescription]: ...
```

### 4.3 Safety Guardrails

**Location**: `src/agents/guardrails.py`

**Safety Checks**:
- Confirmation required for: email, delete, financial, system modification
- Command blocklist: rm -rf, format, shutdown (unless explicit)
- Rate limiting: Max 10 actions per minute
- Scope validation: Only approved tools can be invoked

---

## Phase 5: Observability

### 5.1 Metrics

**Location**: `src/observability/metrics.py`

**Prometheus Metrics**:
```python
# Latency histograms
stt_latency = Histogram('stt_latency_seconds', 'STT processing time')
intent_latency = Histogram('intent_latency_seconds', 'Intent classification time')
plan_latency = Histogram('plan_latency_seconds', 'Plan generation time')
e2e_latency = Histogram('e2e_latency_seconds', 'End-to-end response time')

# Counters
requests_total = Counter('requests_total', 'Total requests', ['intent_type'])
errors_total = Counter('errors_total', 'Total errors', ['error_type'])
tool_calls_total = Counter('tool_calls_total', 'Tool invocations', ['tool_name'])

# Gauges
active_sessions = Gauge('active_sessions', 'Active conversation sessions')
memory_entries = Gauge('memory_entries', 'Semantic memory entries')
```

### 5.2 Distributed Tracing

**Location**: `src/observability/tracing.py`

**Implementation**: OpenTelemetry with Jaeger export

**Trace Context**:
```python
@dataclass
class TraceContext:
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    attributes: Dict[str, Any]
```

### 5.3 Health Check

**Location**: `src/api/health.py`

**Endpoint**: `GET /health`

**Response**:
```json
{
  "status": "healthy",
  "version": "2.0.0",
  "uptime_seconds": 3600,
  "components": {
    "stt": "healthy",
    "llm": "healthy",
    "tts": "healthy",
    "memory": "healthy"
  },
  "metrics": {
    "requests_last_hour": 150,
    "avg_latency_ms": 450,
    "error_rate": 0.02
  }
}
```

---

## Phase 6: Testing & CI/CD

### 6.1 Audio Integration Tests

**Location**: `tests/integration/test_audio_pipeline.py`

**Test Assets**: `tests/fixtures/audio/`
- `wake_word_clean.wav` - Clear wake word
- `wake_word_noisy.wav` - Wake word with background noise
- `command_set_timer.wav` - "Set a timer for 5 minutes"
- `command_weather.wav` - "What's the weather today"
- `multi_turn_1.wav`, `multi_turn_2.wav` - Follow-up conversation

**Test Cases**:
```python
@pytest.mark.integration
async def test_stt_accuracy_clean_audio():
    """Validate >95% WER on clean audio."""
    audio = load_audio("tests/fixtures/audio/command_set_timer.wav")
    result = await stt.transcribe(audio)
    assert wer(result.text, "Set a timer for 5 minutes") < 0.05

@pytest.mark.integration
async def test_stt_with_noise_filtering():
    """Validate noise filtering improves accuracy."""
    audio = load_audio("tests/fixtures/audio/wake_word_noisy.wav")
    result_raw = await stt.transcribe(audio, preprocess=False)
    result_filtered = await stt.transcribe(audio, preprocess=True)
    assert result_filtered.confidence > result_raw.confidence
```

### 6.2 GitHub Actions Workflow

**Location**: `.github/workflows/ci.yml`

```yaml
name: CI Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      - run: pip install ruff mypy
      - run: ruff check src/
      - run: mypy src/

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      - run: pip install -e .[dev]
      - run: pytest --cov=src --cov-fail-under=80

  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install bandit safety
      - run: bandit -r src/
      - run: safety check
```

---

## Phase 7: Documentation

### 7.1 Architecture Diagrams

**Location**: `docs/architecture/`

- `system-overview.png` - High-level component diagram
- `data-flow.png` - Request processing sequence
- `memory-architecture.png` - Semantic memory design
- `planner-flow.png` - Agentic planning sequence

### 7.2 Benchmark Documentation

**Location**: `docs/benchmarks.md`

**Metrics to Document**:
- STT latency by model (whisper-base, -small, -medium)
- Intent classification accuracy on test set
- Memory retrieval precision/recall
- End-to-end response time percentiles

---

## Implementation Order

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| 1. Audio Preprocessing | Week 1 | None |
| 2. Semantic Memory | Week 2 | None |
| 3. Enhanced NLU | Week 2-3 | Phase 2 |
| 4. Agentic Planner | Week 3-4 | Phase 2, 3 |
| 5. Observability | Week 4 | None |
| 6. Testing & CI | Week 5 | All phases |
| 7. Documentation | Week 5-6 | All phases |

## Key Decisions

1. **Vector DB**: ChromaDB (embedded) over Pinecone (cloud) for privacy
2. **Embeddings**: sentence-transformers (local) for offline capability
3. **Tracing**: OpenTelemetry for vendor-neutral observability
4. **Testing**: Real audio files over mocked inputs for accuracy
5. **Safety**: Explicit confirmation for destructive actions

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| ChromaDB performance at scale | Implement pagination, add TTL-based cleanup |
| LLM latency for entity extraction | Cache common patterns, use local model fallback |
| Tool API failures | Implement circuit breaker, graceful degradation |
| Memory growth | Configurable retention, automatic summarization |
