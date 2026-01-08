# Voice Assistant

A privacy-first, cross-platform voice assistant with agentic AI capabilities including persistent memory, web interface, and intelligent planning with autonomous task execution.

## Features

### Core Capabilities
- 🎙️ **Wake Word Activation**: Hands-free activation using "Hey Assistant"
- 🗣️ **Intent Recognition**: Understand informational, task-based, and conversational queries
- 🧠 **Persistent Memory**: Cloud-based memory with Mem0 for cross-session context using semantic search
- ⚡ **Agentic Planning**: Goal decomposition and multi-step task execution
- 🔧 **Tool Integration**: Extensible tool registry for system and external actions
- 🔒 **Privacy-First**: In-memory context by default, optional encrypted persistence

### Web Interface Features
- 🌐 **Real-time Chat**: WebSocket-based communication with live updates
- 🎤 **Voice Input**: Push-to-talk recording with space bar activation
- 🔊 **Voice Output**: Automatic TTS playback with manual speaker buttons
- 📱 **Cross-Platform**: Next.js web interface accessible from any device
- 🔄 **Auto-reconnection**: Robust WebSocket connection management

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
- ✅ Web Browsers (Chrome, Firefox, Safari, Edge)

## Quick Start

See [Quickstart Guide](specs/001-voice-assistant-baseline/quickstart.md) for detailed setup instructions.

### Prerequisites

- **Python 3.10+** (Required for sentence-transformers)
- **Node.js 18+** (For web interface)
- **npm** or **yarn** (For web dependencies)
- **Audio Input Device** (Microphone)
- **Audio Output Device** (Speakers/Headphones)

### Installation

```bash
# Clone repository
git clone https://github.com/your-org/voice-assistant.git
cd voice-assistant

# Create virtual environment (Python 3.10+ required)
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# OR use UV for faster installation (10-100x faster!)
# Install UV first: irm https://astral.sh/uv/install.ps1 | iex
# Then: uv pip install -r requirements.txt

# Configure environment
cp config/.env.template config/.env
# Edit config/.env with your API keys:
#   - GEMINI_API_KEY (required for LLM)
#   - OPENAI_API_KEY (optional, for STT)
#   - ELEVENLABS_API_KEY (optional, for TTS)
#   - PICOVOICE_ACCESS_KEY (required for wake word)
```

### Running the Project

#### 🚀 Quick Start (Recommended for Testing)

**Step 1: Install Core Dependencies**
```bash
# Install essential backend packages (if not using venv)
python -m pip install fastapi uvicorn[standard] pydantic pydantic-settings python-dotenv pyyaml numpy google-genai ollama
```

**Step 2: Start Backend Server**
```bash
# From project root directory
python -m uvicorn src.api.websocket_server:app --host 0.0.0.0 --port 8000

# You should see:
# INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**Step 3: Start Web Interface** (In a new terminal)
```bash
cd web
npm install  # First time only
npm run dev

# You should see:
# ▲ Next.js 14.1.0
# - Local: http://localhost:3000
```

**Step 4: Access the Application**
- Open browser: http://localhost:3000
- You should see the Voice Assistant chat interface
- Backend API: http://localhost:8000
- Health check: http://localhost:8000/health

---

#### 📋 Detailed Setup Options

**Option 1: Web Interface (Full Stack) - Complete Setup**

**Terminal 1 - Backend Server:**
```bash
# Navigate to project root
cd D:\Voice_Assistant

# Option A: Using virtual environment (recommended)
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
python -m uvicorn src.api.websocket_server:app --host 0.0.0.0 --port 8000

# Option B: Using system Python (if venv issues)
python -m pip install --user fastapi uvicorn[standard] pydantic pydantic-settings python-dotenv pyyaml numpy google-genai ollama
python -m uvicorn src.api.websocket_server:app --host 0.0.0.0 --port 8000

# Backend will start on: http://0.0.0.0:8000
# WebSocket endpoint: ws://localhost:8000/ws/voice
```

**Terminal 2 - Frontend Server:**
```bash
# Navigate to web directory
cd D:\Voice_Assistant\web

# Install Node.js dependencies (first time only)
npm install

# Start development server
npm run dev

# Or use yarn
yarn install  # first time
yarn dev

# Frontend will start on: http://localhost:3000
# If port 3000 is busy, Next.js will use port 3001
```

**Verify Both Services:**
```bash
# Check backend health
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","version":"2.0.0","services":{...},"active_sessions":0}

# Check frontend (in browser)
# Open: http://localhost:3000
```

---

**Option 2: Test Mode (Voice-only, No Wake Word)**

For quick testing without the web interface:

```bash
# Activate virtual environment
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # macOS/Linux

# Run test mode (press ENTER to record)
python test_assistant.py

# Press ENTER when you see:
# "Press ENTER to record..."
# Speak for up to 20 seconds
# The assistant will transcribe and respond
```

---

**Option 3: Full CLI Mode (With Wake Word Detection)**

For hands-free voice activation:

```bash
# Activate virtual environment
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # macOS/Linux

# Ensure wake word model is available
# PICOVOICE_ACCESS_KEY must be set in config/.env

# Run full assistant
python -m src.cli.assistant

# Say "Hey Assistant" to activate
# Speak your command
# Wait for response
```

---

#### 🛑 Stopping the Services

**Stop Backend Server:**
```bash
# In the terminal running backend, press:
Ctrl + C

# Or find and kill the process:
# Windows:
tasklist | findstr python
taskkill /PID <process_id> /F

# Linux/macOS:
ps aux | grep uvicorn
kill <process_id>
```

**Stop Frontend Server:**
```bash
# In the terminal running frontend, press:
Ctrl + C

# Or kill the Node.js process:
# Windows:
tasklist | findstr node
taskkill /PID <process_id> /F

# Linux/macOS:
ps aux | grep node
kill <process_id>
```

---

#### 🔍 Port Management

**Default Ports:**
- Backend API: `8000`
- Frontend UI: `3000`
- WebSocket: `8000/ws/voice`

**Check if Ports are in Use:**
```bash
# Windows:
netstat -ano | findstr "8000"
netstat -ano | findstr "3000"

# Linux/macOS:
lsof -i :8000
lsof -i :3000
```

**Change Default Ports:**
```bash
# Backend - use different port:
python -m uvicorn src.api.websocket_server:app --host 0.0.0.0 --port 8080

# Frontend - Next.js will auto-assign if 3000 is busy
# Or manually specify:
npm run dev -- -p 3001
```

---

### Web Interface Usage

1. Open browser to `http://localhost:3000`
2. **Text Input**: Type messages directly in the input field
3. **Voice Input**: Hold SPACEBAR to record voice messages (or click microphone button)
4. **Audio Playback**: Click speaker icons to replay voice responses
5. **Conversation History**: View full chat history with audio playback controls

**Connection Status:**
- 🟢 Green dot: Connected to backend
- 🔴 Red dot: Disconnected (check backend server)
- WebSocket auto-reconnects if connection drops

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
┌─────────────────────────────────────────────────────────────────────────────┐
│                        VOICE ASSISTANT                                    │
│                   (Agentic AI System)                                     │
└──────────────────────────┬─────────────────────────────────────────────────┘
                           │
    ┌──────────────────────┼─────────────────────────────────────────────────┐
    │                      │                                                 │
    ▼                      ▼                                                 ▼
┌────────────┐      ┌────────────────┐                              ┌────────────────┐
│ WEB UI     │      │ BACKEND API    │                              │ INPUT/OUTPUT   │
│            │      │                │                              │                │
│ Next.js    │◄────►│ WebSocket      │◄────────────────────────────►│ Audio          │
│ React      │      │ FastAPI        │                              │ Preprocess     │
│ Chat UI    │      │ Memory         │                              │ STT/TTS        │
└────────────┘      │ Services       │                              │ Wake Word      │
                    └────────────────┘                              └────────────────┘
                           │
    ┌──────────────────────┼─────────────────────────────────────────────────┐
    │                      │                                                 │
    ▼                      ▼                                                 ▼
┌────────────┐      ┌────────────────┐                              ┌────────────────────┐
│PERSISTENT  │      │ AGENTIC        │                              │ EXTERNAL APIS      │
│MEMORY      │      │ AI             │                              │                    │
│            │      │                │                              │ Gemini/OpenAI LLM  │
│ Mem0 Cloud │      │ Semantic       │                              │ ElevenLabs TTS     │
│ Semantic   │      │ Memory (RAG)   │                              │ ChromaDB           │
│ Search     │      │ NLU + Slots    │                              │ Weather/Calendar   │
└────────────┘      │ Agentic        │                              │ APIs               │
                    │ Planner        │                              └────────────────────┘
                    │ Tools          │
                    └────────────────┘
                           │
                    ┌────────────┐
                    │OBSERVABILITY│
                    │            │
                    │ Prometheus │
                    │ Tracing    │
                    │ Health     │
                    └────────────┘
```

### Technology Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.10+ |
| Web Framework | Next.js 14, React 18 |
| Backend API | FastAPI, WebSockets |
| Wake Word | pvporcupine (Picovoice) |
| STT | OpenAI Whisper (local/API) |
| Audio Preprocessing | noisereduce, webrtcvad, scipy |
| LLM | OpenAI GPT-3.5/4 + Gemini + Ollama (local) |
| TTS | ElevenLabs + Piper (local) |
| Persistent Memory | Mem0 Cloud (semantic search) |
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
│   ├── api/            # FastAPI endpoints, WebSocket server
│   ├── cli/            # CLI entry point
│   └── utils/          # Audio, logging utilities
├── web/                # Next.js web interface
│   ├── src/
│   │   ├── components/ # React components (chat, voice input)
│   │   ├── hooks/      # Custom hooks (WebSocket, audio)
│   │   ├── pages/      # Next.js pages
│   │   └── types/      # TypeScript type definitions
│   ├── public/         # Static assets
│   ├── package.json    # Node.js dependencies
│   └── next.config.js  # Next.js configuration
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

### Persistent Memory (`src/services/persistent_memory.py`)
- **Mem0 Cloud Integration**: Cloud-based persistent memory with semantic search
- **Cross-Session Context**: User-specific memory across conversations
- **Conversation Storage**: Full user/assistant conversation history
- **Context Injection**: Automatic memory context in LLM prompts

### Web Interface (`web/`)
- **Next.js 14**: Modern React framework with App Router
- **Real-time Chat**: WebSocket-based communication with live updates
- **Voice Input**: Push-to-talk recording with space bar activation
- **Audio Playback**: Automatic TTS with manual speaker controls
- **Responsive Design**: Cross-platform web interface

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

### WebSocket Server (`src/api/websocket_server.py`)
- **Real-time Communication**: WebSocket-based bidirectional messaging
- **Audio Streaming**: Direct audio transmission for voice features
- **Session Management**: Persistent connection handling
- **Memory Integration**: Persistent memory context for conversations

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
MEM0_API_KEY=your-mem0-key  # For persistent memory
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
# Activate virtual environment first
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # macOS/Linux

# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific suites
pytest tests/unit/           # Unit tests
pytest tests/integration/    # Integration tests
```

## Troubleshooting

### Virtual Environment Issues

**Problem**: `uvicorn` or other modules not found
```bash
# Solution: Ensure virtual environment is activated
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # macOS/Linux

# Verify activation (you should see (.venv) in prompt)
# Then reinstall dependencies if needed:
pip install -r requirements.txt
```

### API Key Issues

**Problem**: Services failing with authentication errors
```bash
# Solution: Check .env file in config/ directory
# Required keys:
#   GEMINI_API_KEY=your-key-here
#   PICOVOICE_ACCESS_KEY=your-key-here
# Optional keys:
#   OPENAI_API_KEY=your-key-here
#   ELEVENLABS_API_KEY=your-key-here
```

### Audio Device Issues

**Problem**: No audio input/output detected
```bash
# Solution 1: List available audio devices
python -c "import sounddevice; print(sounddevice.query_devices())"

# Solution 2: Update config/assistant_config.yaml
# Set input_device and output_device to correct device index
```

### Web Interface Not Loading

**Problem**: Cannot connect to `localhost:3000`
```bash
# Solution: Ensure both backend and frontend are running
# Backend should be on port 8000
# Frontend should be on port 3000
# Check for port conflicts: netstat -ano | findstr "8000\|3000"
```

### Import Errors

**Problem**: `ModuleNotFoundError` for project modules
```bash
# Solution: Run from project root directory
cd D:\Voice_Assistant
python test_assistant.py  # Not from subdirectories
```

For more help, see:
- [Quickstart Guide](specs/001-voice-assistant-baseline/quickstart.md)
- [Troubleshooting Guide](docs/troubleshooting.md)
- Open a GitHub issue

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
- [Persistent Memory](docs/persistent-memory.md)
- [API Endpoints](docs/api-endpoints.md)
- [Web Interface](docs/web-interface.md)

## Development Status

**Current Version**: 2.1.0 (Agentic AI with Web Interface)

### Completed Features
- [x] Voice pipeline (STT → Intent → LLM → TTS)
- [x] Context management with topic detection
- [x] System status queries and app launching
- [x] Audio preprocessing with noise reduction
- [x] Semantic memory (RAG) with ChromaDB
- [x] Persistent memory with Mem0 cloud storage
- [x] Entity extraction and slot filling
- [x] Agentic planner with tool registry
- [x] Safety guardrails
- [x] Observability infrastructure
- [x] CI/CD pipeline
- [x] Web interface with Next.js
- [x] Real-time WebSocket communication
- [x] Voice input/output in web browser
- [x] Audio playback with auto-play controls

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
