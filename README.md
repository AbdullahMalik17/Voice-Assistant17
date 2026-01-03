# Voice Assistant

A privacy-first, cross-platform voice assistant with agentic AI capabilities including wake word detection, semantic memory, intelligent planning, and autonomous task execution.

## Features

### Core Capabilities
- 🎙️ **Wake Word Activation**: Hands-free activation using "Hey Assistant"
- 🗣️ **Intent Recognition**: Understand informational, task-based, and conversational queries
- 🧠 **Semantic Memory**: RAG-based context retrieval across sessions using ChromaDB
- ⚡ **Agentic Planning**: Goal decomposition and multi-step task execution
- 🔧 **Tool Integration**: Extensible tool registry for system and external actions
- 🔒 **Privacy-First**: In-memory context by default, optional encrypted persistence

### Agentic AI Features (v2.0)
- 🔊 **Audio Preprocessing**: Noise reduction, acoustic echo cancellation, VAD
- 🎯 **Entity Extraction**: LLM + rule-based extraction (dates, times, names, locations)
- 📝 **Slot Filling**: Multi-turn dialogue for parameter collection
- 🤖 **Goal Planning**: Automatic decomposition of complex requests into executable steps
- 🛡️ **Safety Guardrails**: Confirmation requirements, rate limiting, command blocklists
- 📊 **Observability**: Prometheus metrics, distributed tracing, health checks

### Platform Support
- ✅ Windows 10+
- ✅ macOS 11+
- ✅ Linux Ubuntu 20.04+
- ✅ Raspberry Pi 4/5 (Raspbian)

## Quick Start

See [Quickstart Guide](specs/001-voice-assistant-baseline/quickstart.md) for detailed setup instructions.

### Installation

```bash
# Clone repository
git clone https://github.com/your-org/voice-assistant.git
cd voice-assistant

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp config/.env.template config/.env
# Edit config/.env with your API keys
```

### Running

```bash
# Run the assistant (full mode with wake word)
python src/cli/assistant.py

# Or run test mode without wake word (keyboard trigger)
python test_assistant.py
```

### Example Commands

**Conversational**:
- "Hello, how are you?"
- "Tell me a joke"

**Informational**:
- "What time is it?"
- "What's the weather like?"

**System Control**:
- "Check my CPU usage"
- "Open Spotify"
- "Set a timer for 5 minutes"

**Multi-Step Goals** (Agentic):
- "Schedule a meeting with John for next week"
- "Search for Python tutorials and summarize them"

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      VOICE ASSISTANT                          │
│                    (Agentic AI System)                        │
└──────────────────────────┬───────────────────────────────────┘
                           │
    ┌──────────────────────┼──────────────────────────────────┐
    │                      │                                  │
    ▼                      ▼                                  ▼
┌────────────┐      ┌────────────────┐              ┌────────────────┐
│ INPUT      │      │ PROCESSING     │              │ OUTPUT         │
│            │      │                │              │                │
│ Audio      │      │ Semantic       │              │ TTS Engine     │
│ Preprocess │      │ Memory (RAG)   │              │ Action         │
│ STT Engine │      │ NLU + Slots    │              │ Executor       │
│ Wake Word  │      │ Agentic        │              │ Tool           │
│            │      │ Planner        │              │ Integrations   │
└────────────┘      └────────────────┘              └────────────────┘
                           │
    ┌──────────────────────┼──────────────────────────────────┐
    │                      │                                  │
    ▼                      ▼                                  ▼
┌────────────┐      ┌────────────┐              ┌────────────────────┐
│OBSERVABILITY│     │ STORAGE    │              │ EXTERNAL APIS      │
│            │      │            │              │                    │
│ Prometheus │      │ ChromaDB   │              │ Gemini/OpenAI LLM  │
│ Tracing    │      │ SQLite     │              │ ElevenLabs TTS     │
│ Health     │      │ Memory     │              │ Weather/Calendar   │
└────────────┘      └────────────┘              └────────────────────┘
```

### Technology Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.10+ |
| Wake Word | pvporcupine (Picovoice) |
| STT | OpenAI Whisper (local/API) |
| Audio Preprocessing | noisereduce, webrtcvad, scipy |
| LLM | Gemini API + Ollama (local) |
| TTS | ElevenLabs + Piper (local) |
| Semantic Memory | ChromaDB + sentence-transformers |
| Metrics | Prometheus |
| Automation | Playwright MCP |

### Project Structure

```
voice-assistant/
├── src/
│   ├── core/           # Configuration, context management
│   ├── services/       # STT, LLM, TTS, intent, entity extraction
│   ├── memory/         # Semantic memory, dialogue state (NEW)
│   ├── agents/         # Planner, tools, guardrails (NEW)
│   ├── observability/  # Metrics, tracing, health (NEW)
│   ├── models/         # Data models (Pydantic)
│   ├── storage/        # Memory + encrypted persistence
│   ├── api/            # FastAPI endpoints
│   ├── cli/            # CLI entry point
│   └── utils/          # Audio, logging utilities
├── tests/
│   ├── unit/           # Unit tests
│   ├── integration/    # Integration tests
│   └── fixtures/       # Test data and audio files
├── config/             # YAML config + .env template
├── specs/              # Feature specifications
│   ├── 001-voice-assistant-baseline/
│   └── 002-agentic-ai-improvements/  (NEW)
├── history/            # Prompt history records
└── .github/workflows/  # CI/CD pipelines (NEW)
```

## New Modules (v2.0)

### Semantic Memory (`src/memory/`)
- **ChromaDB integration** for vector storage
- **sentence-transformers** for embeddings
- Cross-session context retrieval (RAG)
- Configurable retention policies

### Agentic Planner (`src/agents/`)
- **Tool Registry**: Register and discover tools
- **Goal Decomposition**: LLM-based plan generation
- **Plan Execution**: Step-by-step with progress
- **Safety Guardrails**: Confirmations, rate limits, blocklists

### Audio Preprocessing (`src/services/audio_preprocessor.py`)
- Spectral noise gating (noisereduce)
- Acoustic echo cancellation
- Voice activity detection (webrtcvad)
- Audio normalization

### Entity Extraction (`src/services/entity_extractor.py`)
- DATE, TIME, DATETIME, DURATION
- PERSON, LOCATION, ORGANIZATION
- NUMBER, MONEY, EMAIL, URL, PHONE
- APP_NAME, FILE_PATH

### Observability (`src/observability/`)
- **Prometheus metrics**: Latency histograms, counters, gauges
- **Distributed tracing**: Request tracking with spans
- **Health checks**: Component status, K8s probes

## Configuration

### Environment Variables

```bash
# API Keys
OPENAI_API_KEY=your-key
GEMINI_API_KEY=your-key
ELEVENLABS_API_KEY=your-key
PICOVOICE_ACCESS_KEY=your-key

# Service Modes (local, api, hybrid)
STT_MODE=hybrid
LLM_MODE=api
TTS_MODE=api

# Features
ENABLE_CONVERSATION_PERSISTENCE=false
```

### Config File (`config/assistant_config.yaml`)

```yaml
audio_preprocessor:
  enabled: true
  noise_reduction_enabled: true
  noise_reduction_method: spectral_gating
  aec_enabled: false

stt:
  primary_mode: hybrid
  confidence_threshold: 0.6

context:
  max_exchanges: 5
  timeout_seconds: 300
```

## Performance Targets

| Metric | Target |
|--------|--------|
| Wake word activation | <1 second |
| STT processing | <500ms |
| Intent + Entity extraction | <200ms |
| LLM response | <2 seconds |
| End-to-end | <3 seconds |
| Speech recognition (WER) | >95% |

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific suites
pytest tests/unit/           # Unit tests
pytest tests/integration/    # Integration tests
```

## CI/CD

GitHub Actions workflow includes:
- **Lint**: Ruff linting and formatting
- **Type Check**: MyPy static analysis
- **Test**: pytest with 80% coverage threshold
- **Security**: Bandit + pip-audit vulnerability scanning

## Documentation

- [Quickstart Guide](specs/001-voice-assistant-baseline/quickstart.md)
- [Baseline Specification](specs/001-voice-assistant-baseline/spec.md)
- [Agentic AI Specification](specs/002-agentic-ai-improvements/spec.md) (NEW)
- [Implementation Plan](specs/002-agentic-ai-improvements/plan.md) (NEW)
- [Task Breakdown](specs/002-agentic-ai-improvements/tasks.md) (NEW)

## Development Status

**Current Version**: 2.0.0 (Agentic AI)

### Completed Features
- [x] Voice pipeline (STT → Intent → LLM → TTS)
- [x] Context management with topic detection
- [x] System status queries and app launching
- [x] Audio preprocessing with noise reduction
- [x] Semantic memory (RAG) with ChromaDB
- [x] Entity extraction and slot filling
- [x] Agentic planner with tool registry
- [x] Safety guardrails
- [x] Observability infrastructure
- [x] CI/CD pipeline

### Roadmap
- [ ] Integration tests with real audio files
- [ ] External API integrations (Calendar, Email, Weather)
- [ ] Voice personalization (speaker ID)
- [ ] Multilingual support
- [ ] Continuous learning from interactions

## Contributing

See [CLAUDE.md](CLAUDE.md) for development guidelines.

## License

[Your License Here]

## Support

1. Check the [Quickstart Guide](specs/001-voice-assistant-baseline/quickstart.md)
2. Review [Troubleshooting](specs/001-voice-assistant-baseline/quickstart.md#troubleshooting)
3. Open a GitHub issue
