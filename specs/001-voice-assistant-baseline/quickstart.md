# Quickstart Guide: Voice Assistant Baseline

**Feature**: 001-voice-assistant-baseline
**Date**: 2026-01-01

## Overview

This guide provides setup, configuration, and usage instructions for the Voice Assistant Baseline implementation.

---

## Prerequisites

### System Requirements

**Minimum**:
- **OS**: Windows 10+, macOS 11+, Ubuntu 20.04+, or Raspbian (Raspberry Pi 4/5)
- **CPU**: Dual-core 1.5GHz (quad-core recommended for Raspberry Pi)
- **RAM**: 2GB (4GB recommended)
- **Disk**: 2GB free space
- **Microphone**: Working audio input device
- **Speakers**: Working audio output device

**Recommended**:
- **Internet**: Broadband connection for cloud services (optional for local-only mode)
- **Python**: 3.10 or higher

---

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/your-org/voice-assistant.git
cd voice-assistant
git checkout 001-voice-assistant-baseline
```

### 2. Install Dependencies

#### Option A: Automated Installation (Recommended)

```bash
# Run installation script
chmod +x scripts/install_dependencies.sh
./scripts/install_dependencies.sh
```

#### Option B: Manual Installation

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python packages
pip install -r requirements.txt

# Install system dependencies (Linux/Mac)
# For wake word detection
sudo apt-get install portaudio19-dev  # Ubuntu/Debian
brew install portaudio  # macOS

# For Playwright (optional, for browser automation)
playwright install chromium
```

### 3. Configure Environment

```bash
# Copy environment template
cp config/.env.template config/.env

# Edit configuration
nano config/.env
```

**Environment Variables**:
```bash
# API Keys (optional - for cloud services)
OPENAI_API_KEY=your_openai_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here

# Service Configuration
STT_MODE=hybrid  # local, api, or hybrid
LLM_MODE=hybrid  # local, api, or hybrid
TTS_MODE=hybrid  # local, api, or hybrid

# Privacy Settings
ENABLE_CONVERSATION_PERSISTENCE=false  # true to enable encrypted storage
CONVERSATION_RETENTION_DAYS=7

# Performance Tuning
WAKE_WORD_SENSITIVITY=0.5  # 0.0 (low) to 1.0 (high)
STT_MODEL=whisper-base  # whisper-tiny, whisper-base, whisper-small
LLM_MODEL=gemini-pro  # For API mode
OLLAMA_MODEL=llama2:7b  # For local mode

# Logging
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
LOG_DIR=logs
METRICS_ENABLED=true
```

### 4. Initialize Wake Word Model

```bash
# Download and setup wake word model
chmod +x scripts/setup_wake_word.sh
./scripts/setup_wake_word.sh
```

---

## Configuration

### Assistant Configuration (`config/assistant_config.yaml`)

```yaml
assistant:
  name: "Assistant"
  wake_word: "Hey Assistant"

audio:
  sample_rate: 16000
  channels: 1
  chunk_size: 1024

context:
  max_exchanges: 5
  timeout_seconds: 300  # 5 minutes

network:
  check_interval_seconds: 5
  retry_delay_seconds: 30
  max_queue_items: 10

actions:
  require_confirmation: false  # Set true for destructive actions
  timeout_seconds: 30

logging:
  event_log_max_size_mb: 10
  event_log_backup_count: 5
  metrics_export_interval_seconds: 60
```

---

## Running the Assistant

### Start the Assistant

```bash
# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Run the assistant
python src/cli/assistant.py

# Or use the convenience script
./run_assistant.sh
```

**Expected Output**:
```
[2026-01-01 12:00:00] INFO: Initializing Voice Assistant...
[2026-01-01 12:00:01] INFO: Wake word detector loaded (sensitivity: 0.5)
[2026-01-01 12:00:02] INFO: STT service ready (mode: hybrid, model: whisper-base)
[2026-01-01 12:00:03] INFO: LLM service ready (mode: hybrid, model: gemini-pro)
[2026-01-01 12:00:04] INFO: TTS service ready (mode: hybrid)
[2026-01-01 12:00:05] INFO: Assistant ready. Listening for "Hey Assistant"...
```

### Using the Assistant

1. **Activate**: Say "Hey Assistant"
2. **Confirm**: Listen for spoken confirmation ("I'm listening")
3. **Speak**: Ask your question or give a command
4. **Response**: Assistant processes and responds with speech

**Example Interactions**:

```
User: "Hey Assistant"
Assistant: "I'm listening"

User: "What's the weather today?"
Assistant: "The weather today is sunny with a high of 75°F"

User: "Open Spotify"
Assistant: "Opening Spotify" (launches Spotify application)

User: "Hey Assistant"
Assistant: "I'm listening"

User: "Check my CPU temperature"
Assistant: "Your CPU temperature is 45 degrees Celsius"
```

---

## Testing

### Run Unit Tests

```bash
pytest tests/unit/ -v
```

### Run Integration Tests

```bash
pytest tests/integration/ -v
```

### Run Contract Tests

```bash
pytest tests/contract/ -v
```

### Test Coverage

```bash
pytest --cov=src --cov-report=html
open htmlcov/index.html  # View coverage report
```

---

## Troubleshooting

### Wake Word Not Detecting

**Symptoms**: Assistant doesn't activate when saying wake word

**Solutions**:
1. Check microphone is working and set as default input
2. Adjust `WAKE_WORD_SENSITIVITY` in `.env` (try 0.7 for more sensitivity)
3. Reduce background noise
4. Check logs: `tail -f logs/assistant.log`

### STT Transcription Errors

**Symptoms**: Poor transcription accuracy or "STT failed" errors

**Solutions**:
1. Speak clearly and at moderate pace
2. Reduce background noise
3. Check internet connection (for API fallback)
4. Try larger model: `STT_MODEL=whisper-small` in `.env`

### Network Connectivity Issues

**Symptoms**: "Waiting for connection" messages

**Solutions**:
1. Check internet connection
2. Verify API keys are correct in `.env`
3. Try local-only mode: Set all `*_MODE=local` in `.env`
4. Check queued requests: View `logs/assistant.log` for queue status

### High Latency / Slow Responses

**Symptoms**: Responses take >5 seconds

**Solutions**:
1. Use smaller STT model: `STT_MODEL=whisper-tiny`
2. Enable API mode for faster processing: `STT_MODE=api`
3. Check system resources: `htop` or Task Manager
4. On Raspberry Pi: Close background applications

### Audio Playback Issues

**Symptoms**: No audio output or garbled speech

**Solutions**:
1. Check speakers/headphones are connected and working
2. Verify default audio output device
3. Try different TTS mode: `TTS_MODE=local` or `TTS_MODE=api`
4. Check audio permissions (especially on macOS)

---

## Advanced Configuration

### Local-Only Mode (Maximum Privacy)

```bash
# In .env file
STT_MODE=local
LLM_MODE=local
TTS_MODE=local

# Comment out API keys
# OPENAI_API_KEY=
# GEMINI_API_KEY=
# ELEVENLABS_API_KEY=
```

**Note**: Local-only mode has higher latency and may not meet all performance targets.

### Cloud-Only Mode (Minimum Latency)

```bash
# In .env file
STT_MODE=api
LLM_MODE=api
TTS_MODE=api

# Ensure API keys are set
OPENAI_API_KEY=your_key
GEMINI_API_KEY=your_key
ELEVENLABS_API_KEY=your_key
```

**Note**: Cloud-only mode requires constant internet and sends data to external services.

### Enable Conversation Persistence

```bash
# In .env file
ENABLE_CONVERSATION_PERSISTENCE=true

# Set encryption password (prompted on first run)
# Or set via environment:
CONVERSATION_ENCRYPTION_KEY=your_secure_password_here
```

**Warning**: Store encryption password securely. Lost passwords cannot be recovered.

---

## Monitoring & Logs

### View Logs

```bash
# Real-time log monitoring
tail -f logs/assistant.log

# Search logs
grep "ERROR" logs/assistant.log

# View metrics
cat logs/metrics.log | jq '.'
```

### Log Format

```json
{
  "timestamp": "2026-01-01T12:00:00.000Z",
  "level": "INFO",
  "event": "WAKE_WORD_DETECTED",
  "module": "wake_word",
  "extra": {
    "confidence": 0.95,
    "audio_duration_ms": 150
  }
}
```

### Performance Metrics

Key metrics tracked:
- Wake word detection latency
- STT processing time
- Intent classification accuracy
- LLM response generation time
- TTS synthesis time
- End-to-end interaction time

---

## Updating

### Update Dependencies

```bash
git pull origin 001-voice-assistant-baseline
pip install -r requirements.txt --upgrade
```

### Database Migrations

(Not applicable for baseline - in-memory storage)

---

## Uninstallation

```bash
# Deactivate virtual environment
deactivate

# Remove virtual environment
rm -rf venv

# Remove logs and data
rm -rf logs data

# Optionally remove wake word models
rm -rf models
```

---

## Additional Resources

- **Full Documentation**: See `specs/001-voice-assistant-baseline/`
- **API Contracts**: See `specs/001-voice-assistant-baseline/contracts/`
- **Data Model**: See `specs/001-voice-assistant-baseline/data-model.md`
- **Research Decisions**: See `specs/001-voice-assistant-baseline/research.md`

---

## Support

For issues or questions:
1. Check logs: `logs/assistant.log`
2. Review troubleshooting section above
3. Open an issue on GitHub
4. Check project documentation in `specs/`

---

**Voice Assistant Baseline is now ready to use!**

**Next Steps**: Run `/sp.tasks` to generate implementation tasks
