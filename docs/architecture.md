# Voice Assistant Architecture

## System Overview

The Voice Assistant is a production-grade, privacy-first AI-powered voice assistant with agentic capabilities. It follows a modular, layered architecture designed for extensibility, testability, and offline-first operation.

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
├─────────────────────────────────────────────────────────────────┤
│  CLI Interface          │       Web Interface (Next.js)         │
│  (voice.py)             │       WebSocket + REST API            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      AUDIO INPUT PIPELINE                       │
├─────────────────────────────────────────────────────────────────┤
│  Wake Word Detection    →    Audio Preprocessing                │
│  (Porcupine)                 (Noise Reduction, AEC, VAD)        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   SPEECH-TO-TEXT (STT)                          │
├─────────────────────────────────────────────────────────────────┤
│  Primary: Whisper (Local)                                        │
│  Fallback: OpenAI Whisper API                                    │
│  Features: Preprocessing, Confidence Scoring                     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      NLU PIPELINE                               │
├─────────────────────────────────────────────────────────────────┤
│  Intent Classification  →  Entity Extraction  →  Slot Filling   │
│  (LLM + Rule-based)       (LLM + Regex)         (Multi-turn)    │
│                                                                  │
│  • 3 Intent Types: Task, Informational, Conversational          │
│  • 14 Entity Types: Date, Time, Person, Location, etc.          │
│  • Auto-disambiguation when confidence is low                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    SEMANTIC MEMORY                              │
├─────────────────────────────────────────────────────────────────┤
│  ChromaDB 1.4.0 (Vector Storage)                                │
│  sentence-transformers 5.2.0 (Embeddings)                       │
│  Dialogue State Manager (Multi-turn context)                    │
│  Retention Policies: 7d, 30d, 90d, forever                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AGENTIC PLANNING                             │
├─────────────────────────────────────────────────────────────────┤
│  AgenticPlanner (Goal Decomposition)                            │
│  │                                                               │
│  ├─ LLM-based Planning (Primary)                                │
│  ├─ Rule-based Fallback                                         │
│  ├─ Safety Guardrails (Rate limiting, Confirmations)            │
│  └─ Tool Registry (20+ tools)                                   │
│                                                                  │
│  Tool Categories:                                                │
│  • System (launch_app, system_status, set_timer)                │
│  • Browser (navigate, search, screenshot, click, type)          │
│  • Communication (email, drive operations)                       │
│  • Information (web_search, get_weather)                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LLM GENERATION                               │
├─────────────────────────────────────────────────────────────────┤
│  Primary: Google Gemini API                                      │
│  Fallback: Ollama (Local)                                        │
│  Context: Semantic memory + Dialogue state                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  TEXT-TO-SPEECH (TTS)                           │
├─────────────────────────────────────────────────────────────────┤
│  Primary: ElevenLabs API                                         │
│  Fallback: Piper TTS (Local)                                     │
│  Features: Voice selection, Speed control                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     AUDIO OUTPUT                                │
├─────────────────────────────────────────────────────────────────┤
│  PyAudio / sounddevice                                           │
│  Sample Rate: 16kHz, Channels: 1 (Mono)                         │
└─────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Audio Preprocessing Pipeline

**Purpose**: Improve STT accuracy by cleaning audio input

**Components**:
- **Noise Reduction**: Spectral gating method using `noisereduce`
- **Acoustic Echo Cancellation (AEC)**: Removes TTS playback echo
- **Voice Activity Detection (VAD)**: `webrtcvad` for speech detection
- **Normalization**: Adjusts audio levels to optimal range

**Flow**:
```
Raw Audio → Noise Reduction → AEC → VAD → Normalization → Clean Audio
```

### 2. Intent Classification System

**Architecture**: Hybrid LLM + Rule-based with disambiguation

**Intent Types**:
1. **TASK_BASED**: Execute specific action (e.g., "open Spotify")
2. **INFORMATIONAL**: Request information (e.g., "what's the weather?")
3. **CONVERSATIONAL**: General chat (e.g., "how are you?")

**Action Types** (for TASK_BASED):
- LAUNCH_APP, SYSTEM_STATUS, EMAIL_ACCESS, DRIVE_ACCESS
- BROWSER_AUTOMATION, SYSTEM_CONTROL, FILE_OPERATION

**Disambiguation**: Triggers when top 2 candidates within 0.15 confidence

### 3. Agentic Planning System

**Components**:

1. **Tool Registry**:
   ```python
   ToolRegistry → {
       Tool Interface (name, params, execute),
       5 Built-in Tools,
       7 Browser Tools,
       7 System Tools,
       8 Gmail/Drive Tools
   }
   ```

2. **AgenticPlanner**:
   ```python
   Goal → Plan Generation (LLM/Rules) → Validation →
   Step Execution → Safety Checks → Tool Execution
   ```

3. **Safety Guardrails**:
   - **Blocked Patterns**: `rm -rf`, `format`, shell pipes, etc.
   - **Sensitive Actions**: send_email, delete_file, share_file
   - **Rate Limiting**: 10 actions/minute default
   - **Confirmation Levels**: SIMPLE, DETAILED, EXPLICIT

**Execution Model**: Generator-based with progress events

```python
for event in planner.execute(plan):
    if event.type == "confirmation_needed":
        confirmed = ask_user(event.message)
        executor.send(confirmed)
```

### 4. Semantic Memory Architecture

**Storage**: ChromaDB 1.4.0 (PersistentClient)

**Embedding Model**: sentence-transformers/all-MiniLM-L6-v2

**Memory Entry Structure**:
```python
MemoryEntry {
    id: UUID,
    content: str,
    embedding: np.ndarray (384-dim),
    metadata: {
        timestamp, source, intent_type,
        entities, confidence
    },
    memory_type: EPISODIC | SEMANTIC | PROCEDURAL
}
```

**Retrieval**: RAG-based semantic search with k-NN (k=5 default)

**Retention Policies**:
- `7d`: Delete after 7 days
- `30d`: Delete after 30 days
- `90d`: Delete after 90 days
- `forever`: Never delete

### 5. Observability Stack

**Metrics** (Prometheus):
- `stt_transcription_latency_ms`, `llm_generation_latency_ms`
- `intent_classification_confidence`, `memory_retrieval_latency_ms`
- `tool_execution_duration_ms`, `plan_completion_rate`

**Tracing** (OpenTelemetry):
- End-to-end request tracing
- Component-level spans

**Logging**:
- Structured JSON logging (`python-json-logger`)
- Event-based logging with context

**Health Checks**:
- `/health` endpoint (API readiness)
- Service availability monitoring

## Data Flow

### Typical Voice Interaction

```
1. User speaks wake word
   └─> Porcupine detects → System activated

2. User speaks command
   └─> Audio captured → Preprocessed → Whisper STT
       └─> Text: "Set a timer for 5 minutes"

3. NLU Pipeline
   └─> Intent: TASK_BASED / set_timer
   └─> Entities: [{type: DURATION, value: "5 minutes", normalized: 300}]
   └─> Slots: {duration_seconds: 300, label: "Timer"}
   └─> Status: COMPLETE (no missing slots)

4. Semantic Memory
   └─> Store interaction
   └─> Retrieve similar past interactions
   └─> Update dialogue state

5. Action Execution
   └─> Safety check (LOW risk, no confirmation needed)
   └─> Execute set_timer tool
   └─> Result: Timer started for 300 seconds

6. Response Generation
   └─> LLM generates: "I've set a 5 minute timer"
   └─> ElevenLabs TTS synthesis
   └─> Audio playback

7. Memory Update
   └─> Store response
   └─> Update context for next turn
```

### Complex Multi-Step Task

```
1. User: "Find information about Python and send it to my email"

2. Intent: TASK_BASED (multi-step)

3. Agentic Planning
   └─> Plan created:
       Step 1: web_search(query="Python programming")
       Step 2: send_email(recipient=user_email, body=search_results)

4. Safety Check
   └─> Step 1: LOW risk, proceed
   └─> Step 2: HIGH risk (send_email), needs confirmation
       └─> Prompt: "I'll send an email to you@example.com with: [results]. Is that okay?"

5. User confirms → Execution
   └─> Execute step 1 → Search complete
   └─> Execute step 2 → Email sent

6. Result: "I've sent the information to your email"
```

## Technology Stack

### Core Dependencies (Latest Versions)

| Component | Library | Version |
|-----------|---------|---------|
| Web Framework | FastAPI | 0.128.0 |
| Data Validation | Pydantic | 2.12.5 |
| Vector DB | ChromaDB | 1.4.0 |
| Embeddings | sentence-transformers | 5.2.0 |
| STT | openai-whisper | latest |
| LLM API | OpenAI SDK | 2.14.0 |
| Browser | Playwright | 1.51.0 |
| Metrics | prometheus-client | 0.21.1 |
| Tracing | OpenTelemetry | 1.29.0 |

### Python Version

**Required**: Python 3.10+ (for sentence-transformers 5.2.0)

## Deployment Architecture

### Local Development
```
Python Process → FastAPI + Uvicorn → WebSocket Server
                 ↓
              Local Services (Whisper, Piper, Ollama)
                 ↓
              ChromaDB (PersistentClient)
```

### Production (Cloud)
```
Load Balancer
   ↓
FastAPI Instances (Kubernetes)
   ↓
External Services (OpenAI, ElevenLabs, Google APIs)
   ↓
ChromaDB Server (Dedicated)
   ↓
Prometheus + Grafana
```

### Raspberry Pi (Edge)
```
Single Process (Optimized)
   ↓
Local Models Only (Whisper base, Piper TTS, Ollama)
   ↓
SQLite-backed ChromaDB
   ↓
Minimal metrics collection
```

## Performance Targets

| Metric | Target | Current |
|--------|--------|---------|
| Wake Word Detection | <1s | ~0.8s |
| STT Transcription | <500ms | ~400ms |
| Intent Classification | <200ms | ~150ms |
| LLM Response | <2s | ~1.5s |
| End-to-End Latency | <3s | ~2.5s |
| Memory Retrieval | <100ms | ~80ms |

## Security & Privacy

### Privacy-First Design
- **Local-first**: All models can run locally
- **No telemetry**: Anonymous telemetry disabled by default
- **Encrypted storage**: Sensitive data encrypted at rest
- **API keys**: Stored in environment variables, never logged

### Safety Guardrails
- **Command blocklist**: Dangerous patterns blocked (rm -rf, format, etc.)
- **Rate limiting**: 10 actions/minute per action type
- **Confirmation prompts**: Required for sensitive actions
- **Audit logging**: All actions logged with timestamps

## Extensibility

### Adding New Tools
```python
class MyTool(Tool):
    name = "my_tool"
    description = "Does something cool"
    category = ToolCategory.CUSTOM

    def execute(self, **params) -> ToolResult:
        # Implementation
        return ToolResult(success=True, data=result)

# Register
registry.register(MyTool())
```

### Adding New Entity Types
```python
class EntityType(str, Enum):
    # Existing types...
    MY_ENTITY = "MY_ENTITY"

# Add extraction pattern
patterns = {
    EntityType.MY_ENTITY: re.compile(r'pattern')
}
```

### Adding Custom Memory Types
```python
class MemoryType(str, Enum):
    # Existing types...
    CUSTOM = "custom"

# Store with custom type
memory.store(content, memory_type=MemoryType.CUSTOM)
```

## Monitoring & Observability

### Key Metrics Dashboard

1. **Performance**:
   - Request latency (p50, p95, p99)
   - Component processing times
   - Memory retrieval performance

2. **Accuracy**:
   - STT confidence scores
   - Intent classification accuracy
   - Plan completion rates

3. **Reliability**:
   - Error rates by component
   - Fallback activation frequency
   - API availability

4. **Usage**:
   - Requests per minute
   - Tool usage distribution
   - Memory growth rate

### Health Endpoints

- `GET /health` - Service health status
- `GET /metrics` - Prometheus metrics
- `GET /ready` - Readiness probe
- `GET /live` - Liveness probe

## Future Enhancements

1. **Multi-modal Support**: Vision (image understanding), Document processing
2. **Continuous Learning**: User feedback loop, Preference learning
3. **Advanced Planning**: Hierarchical planning, Plan optimization
4. **Multi-language**: Translation, Language detection
5. **Voice Cloning**: Custom TTS voices
6. **Distributed Deployment**: Multi-region, Load balancing
