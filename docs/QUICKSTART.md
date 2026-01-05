# Voice Assistant - Quick Start Guide

Get up and running with the Voice Assistant in under 10 minutes!

## Prerequisites

- **Python 3.10+** (Required for latest libraries)
- **Operating System**: Windows 10+, macOS 11+, or Ubuntu 20.04+
- **RAM**: 4GB minimum, 8GB recommended
- **Microphone**: Built-in or external
- **Internet**: Required for API modes (optional for local-only)

## Installation

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/voice-assistant.git
cd voice-assistant
```

### Step 2: Create Virtual Environment

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS/Linux
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install Dependencies

```bash
# Install all dependencies
pip install -r requirements.txt

# Install browser automation (optional)
# Windows
scripts\install_browser_automation.bat

# Linux/macOS
bash scripts/install_browser_automation.sh

# Install Google APIs (optional)
# Windows
scripts\install_google_apis.bat

# Linux/macOS
bash scripts/install_google_apis.sh
```

### Step 4: Configure Environment

```bash
# Copy template
cp .env.template .env

# Edit .env and add your API keys
# Required for API mode:
#  - OPENAI_API_KEY
#  - GOOGLE_API_KEY (Gemini)
#  - ELEVENLABS_API_KEY
#  - MEM0_API_KEY

# Optional for local-only mode:
#  - Leave API keys empty
```

### Step 5: First Run

```bash
# Run the assistant
python src/cli/assistant.py

# Or use the provided script
# Windows
python voice.py

# Linux/macOS
python3 voice.py
```

## Quick Configuration Modes

### Mode 1: Fully Local (Privacy-First, No API Costs)

**Best for**: Privacy-focused users, offline environments

**Edit** `.env`:
```bash
# STT
STT_PRIMARY_MODE=local

# LLM
LLM_PRIMARY_MODE=local  # Uses Ollama

# TTS
TTS_PRIMARY_MODE=local  # Uses Piper

# No API keys needed
```

**Performance**: 4-8s latency depending on hardware

**Setup Ollama** (for local LLM):
```bash
# Install Ollama from https://ollama.ai
# Pull a model
ollama pull phi-2  # Fast 2.7B model
# or
ollama pull mistral  # Better 7B model
```

### Mode 2: Hybrid (Balanced Performance & Cost)

**Best for**: Most users, good balance

**Edit** `.env`:
```bash
# STT (local is fast and free)
STT_PRIMARY_MODE=local

# LLM (cloud for quality)
LLM_PRIMARY_MODE=api
GOOGLE_API_KEY=your_gemini_api_key

# TTS (local is fast)
TTS_PRIMARY_MODE=local
```

**Performance**: ~2.1s latency

**Cost**: ~$0.50 per 1,000 requests

### Mode 3: Full Cloud (Best Quality)

**Best for**: Production, best accuracy

**Edit** `.env`:
```bash
# All cloud services
STT_PRIMARY_MODE=api
OPENAI_API_KEY=your_openai_key

LLM_PRIMARY_MODE=api
GOOGLE_API_KEY=your_gemini_key

TTS_PRIMARY_MODE=api
ELEVENLABS_API_KEY=your_elevenlabs_key

MEM0_API_KEY=your_mem0_key
```

**Performance**: ~2.5s latency

**Cost**: ~$5.80 per 1,000 requests

## Web Interface

The Voice Assistant includes a modern web interface!

### Start the Web Server

```bash
# Start backend API
python src/api/websocket_server.py

# In another terminal, start frontend
cd web
npm install
npm run dev
```

### Access the Interface

Open your browser to: `http://localhost:3000`

Features:
- Real-time voice interaction
- Text chat fallback
- Visual feedback
- Conversation history

## Basic Usage

### 1. Wake Word Activation

Say: **"Hey Assistant"** or **"OK Assistant"**

Wait for the confirmation beep, then speak your command.

### 2. Simple Commands

```
"What time is it?"
"Set a timer for 5 minutes"
"Open Spotify"
"Check my CPU usage"
```

### 3. Complex Commands

```
"Search for Python tutorials and email me the results"
"Check my system status and open Task Manager"
"Navigate to github.com and take a screenshot"
```

### 4. Multi-Turn Conversations

```
You: "Send an email"
Assistant: "Who should I send this email to?"
You: "john@example.com"
Assistant: "What should the subject be?"
You: "Meeting notes"
...
```

## Testing the Installation

Run the validation tests:

```bash
# Quick test
python test_assistant.py

# Comprehensive test
python test_manual_validation.py

# Run specific tests
pytest tests/integration/test_audio_pipeline.py -v
```

## Troubleshooting

### "ModuleNotFoundError" errors

```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

### Microphone not detected

```bash
# List available devices
python -c "import sounddevice as sd; print(sd.query_devices())"

# Update config/assistant_config.yaml with correct device index
```

### Wake word not working

1. Ensure microphone is working
2. Speak clearly within 1-3 meters
3. Reduce background noise
4. Check wake word sensitivity in config

### High latency

**For local mode**:
- Use Whisper "tiny" or "base" model (faster)
- Use Ollama phi-2 (faster than mistral)
- Close other applications

**For API mode**:
- Check internet connection
- Verify API keys are correct
- Check API service status

### "API key not found" errors

1. Verify `.env` file exists
2. Check API keys are set correctly
3. Restart the assistant after editing `.env`

## Next Steps

### Enable Browser Automation

```bash
# Install Playwright browsers
playwright install chromium

# Test browser tools
python -c "from src.agents.browser_tools import BrowserNavigateTool; \
           tool = BrowserNavigateTool(); \
           print(tool.execute(url='https://google.com'))"
```

### Set Up Google Services

1. **Create Google Cloud Project**
   - Visit: https://console.cloud.google.com
   - Create new project
   - Enable Gmail API, Google Calendar API, and Google Drive API

2. **Create OAuth2 Credentials**
   - Go to "APIs & Services" > "Credentials"
   - Create OAuth 2.0 Client ID (Desktop app)
   - Download JSON and save as `config/google_credentials.json`

3. **Test Gmail Integration**
   ```bash
   python -c "from src.services.gmail_api import get_gmail_service; \
              service = get_gmail_service(); \
              print(service.list_messages())"
   ```

4. **Test Calendar Integration**
   ```bash
   python -c "from src.services.calendar_service import create_calendar_service; \
              from src.utils.logger import EventLogger, MetricsLogger; \
              service = create_calendar_service('config/google_credentials.json', 'data/calendar_token.pickle', EventLogger(), MetricsLogger()); \
              print(service.list_events())"
   ```

5. **Test Email Scheduler** (requires both Gmail and Calendar)
   ```bash
   python -c "from src.services.email_scheduler import create_email_scheduler_service; \
              from src.services.calendar_service import create_calendar_service; \
              from src.services.gmail_api import get_gmail_service; \
              from src.utils.logger import EventLogger, MetricsLogger; \
              from datetime import datetime, timedelta; \
              gmail = get_gmail_service(); \
              calendar = create_calendar_service('config/google_credentials.json', 'data/calendar_token.pickle', EventLogger(), MetricsLogger()); \
              scheduler = create_email_scheduler_service(calendar, gmail, EventLogger(), MetricsLogger()); \
              result = scheduler.schedule_email('test@example.com', 'Test', 'Test body', datetime.utcnow() + timedelta(hours=1)); \
              print('Scheduled:', result.id if result else 'Failed')"
   ```

### Configure Advanced Features

Edit `config/assistant_config.yaml`:

```yaml
# Audio preprocessing
audio_preprocessor:
  noise_reduction_enabled: true
  aec_enabled: true  # Acoustic echo cancellation

# Semantic memory
memory:
  retention_policy: "30d"  # 7d, 30d, 90d, forever
  max_entries: 10000

# Safety guardrails
guardrails:
  max_actions_per_minute: 10
  require_confirmation_for_high_risk: true
```

## Performance Optimization

### For Desktop (High-End)

```yaml
# config/assistant_config.yaml
stt:
  primary_mode: local
  local_model: whisper-base  # or whisper-small
  use_gpu: true

llm:
  primary_mode: api  # Use Gemini for quality

tts:
  primary_mode: local  # Piper is fast
```

**Expected Latency**: ~2.1s

### For Raspberry Pi

```yaml
stt:
  primary_mode: api  # OpenAI API (local too slow)
  local_model: whisper-tiny  # Fallback

llm:
  primary_mode: api  # Gemini API

tts:
  primary_mode: local  # Piper works well
  piper:
    voice_model: en_US-lessac-low  # Faster model
```

**Expected Latency**: ~2.8s

### For Server Deployment

```yaml
# Use all cloud services for consistency
stt:
  primary_mode: api

llm:
  primary_mode: api

tts:
  primary_mode: api
```

## Usage Examples

See [audio_examples.md](audio_examples.md) for comprehensive command examples.

### Quick Reference

| Task | Command |
|------|---------|
| **Open app** | "Open [Spotify/Chrome/Word/etc.]" |
| **System info** | "Check my [CPU/memory/disk/battery]" |
| **Timer** | "Set a timer for [5 minutes]" |
| **Email** | "Check my email", "Send email to [address]" |
| **Schedule Email** | "Schedule email to [address] for [time]" |
| **Calendar** | "Add event [title] at [time]", "Show my calendar" |
| **Browse** | "Navigate to [url]", "Search for [query]" |
| **Weather** | "What's the weather in [location]?" |

## Learning More

- **Architecture**: [docs/architecture.md](architecture.md)
- **Benchmarks**: [docs/benchmarks.md](benchmarks.md)
- **Audio Examples**: [docs/audio_examples.md](audio_examples.md)
- **Troubleshooting**: [docs/troubleshooting.md](troubleshooting.md)
- **API Documentation**: [docs/api-endpoints.md](api-endpoints.md)

## Deployment

### Docker Deployment

```bash
# Build image
docker build -t voice-assistant .

# Run container
docker run -p 8000:8000 \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  voice-assistant
```

### Kubernetes Deployment

```bash
# Apply manifests
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml

# Check status
kubectl get pods
```

### Systemd Service (Linux)

```bash
# Copy service file
sudo cp scripts/voice-assistant.service /etc/systemd/system/

# Enable and start
sudo systemctl enable voice-assistant
sudo systemctl start voice-assistant

# Check status
sudo systemctl status voice-assistant
```

## Support & Community

- **Issues**: [GitHub Issues](https://github.com/yourusername/voice-assistant/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/voice-assistant/discussions)
- **Documentation**: [docs/](docs/)

## What's New

### Version 2.1.0

✅ **Agentic AI Improvements**
- LLM-based intent classification with disambiguation
- Entity extraction (14 types) with slot filling
- Multi-step planning and tool orchestration
- Safety guardrails (rate limiting, confirmations)
- 20+ tools (system, browser, email, drive)

✅ **Latest Libraries** (January 2026)
- ChromaDB 1.4.0 (vector memory)
- sentence-transformers 5.2.0 (embeddings)
- FastAPI 0.128.0 (web framework)
- OpenAI SDK 2.14.0 (STT/LLM APIs)
- Pydantic 2.12.5 (validation)

✅ **Enhanced Pipeline**
- Audio preprocessing (noise reduction, AEC)
- Semantic memory with RAG
- Multi-turn dialogue support
- Real-time web interface

## License

MIT License - see [LICENSE](../LICENSE)

---

**Happy Voice Assisting!** 🎤🤖

For questions or issues, please check the [troubleshooting guide](troubleshooting.md) or [open an issue](https://github.com/yourusername/voice-assistant/issues).
