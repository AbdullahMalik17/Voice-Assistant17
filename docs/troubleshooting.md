# Troubleshooting Guide: Voice Assistant

**Version**: 1.0.0
**Date**: 2026-01-02

## Overview

This guide helps diagnose and resolve common issues with the Voice Assistant.

---

## Quick Diagnostics

### Check System Status

```bash
# Check if assistant is running
ps aux | grep assistant

# View recent logs
tail -50 logs/assistant.log

# Check audio devices
arecord -l  # Microphones
aplay -l    # Speakers

# Check network
ping -c 3 api.openai.com

# Check Python environment
source venv/bin/activate
python -c "from src.core.config import get_config; c = get_config(); print(f'Config loaded: {c.assistant.name}')"
```

---

## Common Issues

### 1. Wake Word Not Detecting

**Symptoms:**
- Assistant doesn't respond when saying "Hey Assistant"
- No "Wake word detected" in logs

**Causes & Solutions:**

| Cause | Solution |
|-------|----------|
| Microphone not working | Check `arecord -l` shows device, test with `arecord -d 5 test.wav` |
| Microphone muted | Check system audio settings, unmute microphone |
| Wrong audio device | Set correct device in `config/assistant_config.yaml` under `audio.input_device` |
| Sensitivity too low | Increase `WAKE_WORD_SENSITIVITY` in `.env` (try 0.7) |
| Background noise | Reduce noise, speak closer to microphone |
| Model not loaded | Run `scripts/setup_wake_word.sh` to reinstall wake word model |

**Debug Commands:**
```bash
# Test microphone recording
python -c "
from src.utils.audio_utils import get_audio_utils, AudioConfig
au = get_audio_utils(AudioConfig())
print('Recording 3 seconds...')
data = au.record_audio(3.0)
print(f'Recorded {len(data)} bytes')
"
```

### 2. Speech Recognition Fails

**Symptoms:**
- "STT failed" errors in logs
- Poor transcription accuracy
- "No speech detected" messages

**Causes & Solutions:**

| Cause | Solution |
|-------|----------|
| Whisper model not loaded | First run may download model - wait or pre-download |
| Insufficient memory | Use smaller model: `STT_MODEL=whisper-tiny` |
| Network offline (API mode) | Check internet, switch to `STT_MODE=local` |
| Invalid API key | Verify `OPENAI_API_KEY` in `.env` |
| Audio quality poor | Check microphone, reduce noise, speak clearly |
| Audio too short/long | Speak for 2-5 seconds after activation |

**Debug Commands:**
```bash
# Test STT directly
python -c "
from src.services.stt import create_stt_service
from src.core.config import get_config
from src.utils.logger import get_event_logger, get_metrics_logger

config = get_config()
logger = get_event_logger('test')
metrics = get_metrics_logger(log_dir=config.log_dir)

stt = create_stt_service(config, logger, metrics, None)
print(f'STT mode: {config.stt.primary_mode}')
print(stt.test_service())
"
```

### 3. LLM Response Generation Fails

**Symptoms:**
- "LLM failed" errors
- Empty or error responses
- Long delays with timeout

**Causes & Solutions:**

| Cause | Solution |
|-------|----------|
| Invalid Gemini API key | Verify `GEMINI_API_KEY` in `.env` |
| Rate limiting | Wait and retry, or switch to local mode |
| Network offline | Check internet connection |
| Ollama not running (local) | Start Ollama: `ollama serve` |
| Model not downloaded (local) | Download: `ollama pull llama2:7b` |
| Request too long | Reduce context or query length |

**Debug Commands:**
```bash
# Test LLM directly
python -c "
from src.services.llm import create_llm_service
from src.core.config import get_config
from src.utils.logger import get_event_logger, get_metrics_logger

config = get_config()
logger = get_event_logger('test')
metrics = get_metrics_logger(log_dir=config.log_dir)

llm = create_llm_service(config, logger, metrics)
print(f'LLM mode: {config.llm.primary_mode}')
print(llm.test_service())
"

# Test Ollama directly (local mode)
curl http://localhost:11434/api/generate -d '{"model": "llama2:7b", "prompt": "Hello", "stream": false}'
```

### 4. TTS (Text-to-Speech) Fails

**Symptoms:**
- "TTS failed" errors
- No audio output
- Garbled or corrupted audio

**Causes & Solutions:**

| Cause | Solution |
|-------|----------|
| Speakers muted/disconnected | Check system audio, verify speakers work |
| Wrong output device | Set correct device in `config/assistant_config.yaml` |
| ElevenLabs API key invalid | Verify `ELEVENLABS_API_KEY` in `.env` |
| Piper not installed (local) | Install Piper: `pip install piper-tts` |
| Audio format mismatch | Check sample rate settings |

**Debug Commands:**
```bash
# Test audio output
python -c "
import numpy as np
import sounddevice as sd
t = np.linspace(0, 1, 16000)
tone = 0.3 * np.sin(2 * np.pi * 440 * t)
sd.play(tone, 16000)
sd.wait()
print('Did you hear a tone?')
"

# Test TTS service
python -c "
from src.services.tts import create_tts_service
from src.core.config import get_config
from src.utils.logger import get_event_logger, get_metrics_logger
from src.utils.audio_utils import get_audio_utils, AudioConfig

config = get_config()
logger = get_event_logger('test')
metrics = get_metrics_logger(log_dir=config.log_dir)
audio = get_audio_utils(AudioConfig())

tts = create_tts_service(config, logger, metrics, audio)
print(f'TTS mode: {config.tts.primary_mode}')
tts.synthesize('Hello, this is a test.', play_audio=True)
"
```

### 5. Network Connectivity Issues

**Symptoms:**
- "Waiting for connection" messages
- Requests being queued
- Fallback to local services

**Causes & Solutions:**

| Cause | Solution |
|-------|----------|
| No internet connection | Check `ping google.com` |
| Firewall blocking | Allow outbound HTTPS (port 443) |
| DNS issues | Try `ping 8.8.8.8` (if works, DNS is problem) |
| Proxy not configured | Set `HTTP_PROXY` and `HTTPS_PROXY` environment variables |
| API endpoint down | Check API status pages |

**Debug Commands:**
```bash
# Test network monitoring
python -c "
from src.utils.network_monitor import get_network_monitor
nm = get_network_monitor()
print(f'Connected: {nm.is_connected()}')
"

# Test specific endpoints
curl -I https://api.openai.com
curl -I https://generativelanguage.googleapis.com
curl -I https://api.elevenlabs.io
```

### 6. High Latency / Slow Responses

**Symptoms:**
- Response takes > 5 seconds
- Noticeable delay between speaking and response

**Causes & Solutions:**

| Cause | Solution |
|-------|----------|
| Large STT model | Use `STT_MODEL=whisper-tiny` or `whisper-base` |
| Network latency | Use local mode or check internet speed |
| CPU overloaded | Close other applications, check `htop` |
| Memory pressure | Check available RAM, close other apps |
| Slow disk (Pi) | Use fast microSD card (A2 rated) |

**Profiling:**
```bash
# Enable debug logging
LOG_LEVEL=DEBUG python -m src.cli.assistant

# Check metrics
cat logs/metrics.json | jq '.'
```

### 7. Context Not Maintained

**Symptoms:**
- Follow-up questions not understood
- Context resets unexpectedly

**Causes & Solutions:**

| Cause | Solution |
|-------|----------|
| 5-minute timeout | Continue conversation within 5 minutes |
| Topic shift detected | Stay on topic or start new conversation |
| 5-exchange limit | Start new conversation after 5 exchanges |
| Context interrupted | Don't use wake word during processing |

**Debug:**
```bash
# Check context stats
python -c "
from src.core.context_manager import create_context_manager
from src.core.config import get_config
from src.utils.logger import get_event_logger, get_metrics_logger
from src.storage.memory_store import MemoryStore

config = get_config()
logger = get_event_logger('test')
metrics = get_metrics_logger(log_dir=config.log_dir)
memory = MemoryStore()

cm = create_context_manager(config, logger, metrics, memory)
print(cm.get_context_stats())
"
```

### 8. Action Execution Fails

**Symptoms:**
- "Failed to open [app]" messages
- Commands not executed
- Wrong application opens

**Causes & Solutions:**

| Cause | Solution |
|-------|----------|
| App not installed | Install the requested application |
| Wrong app name | Check available apps in action executor |
| Permission denied | Run with appropriate permissions |
| Platform mismatch | Verify command for your OS |

**Check Available Actions:**
```bash
python -c "
from src.services.action_executor import create_action_executor
from src.core.config import get_config
from src.utils.logger import get_event_logger, get_metrics_logger

config = get_config()
logger = get_event_logger('test')
metrics = get_metrics_logger(log_dir=config.log_dir)

ae = create_action_executor(config, logger, metrics)
print('Registered actions:', list(ae.action_registry.keys()))
"
```

---

## Error Codes Reference

| Error Event | Meaning | Resolution |
|-------------|---------|------------|
| `AUDIO_RECORDING_FAILED` | Cannot record from microphone | Check audio input device |
| `STT_FAILED` | Speech recognition error | Check STT mode and model |
| `INTENT_CLASSIFICATION_FAILED` | Cannot classify user intent | Usually code bug - check logs |
| `LLM_FAILED` | LLM response generation error | Check API keys and network |
| `TTS_RESPONSE_FAILED` | Cannot generate speech | Check TTS mode and audio output |
| `NETWORK_LOST` | Internet connection lost | Check network, local mode continues |
| `NETWORK_RESTORED` | Internet connection restored | Queued requests will process |
| `CONTEXT_EXPIRED` | Conversation context timed out | Start new conversation |
| `ACTION_EXECUTION_FAILED` | System command failed | Check app availability |

---

## Log Analysis

### Finding Errors

```bash
# All errors
grep "ERROR" logs/assistant.log

# Errors with context
grep -B5 -A5 "ERROR" logs/assistant.log

# Count error types
grep "ERROR" logs/assistant.log | cut -d: -f4 | sort | uniq -c | sort -rn
```

### Performance Analysis

```bash
# Check latency metrics
cat logs/metrics.json | jq '.stt_latency_avg_ms, .llm_latency_avg_ms, .tts_latency_avg_ms'

# Find slow requests
grep "duration_ms" logs/assistant.log | awk -F'duration_ms=' '{print $2}' | sort -n | tail -10
```

---

## Getting Help

If issues persist:

1. **Collect Diagnostics:**
   ```bash
   # Create diagnostic report
   echo "=== System Info ===" > diagnostics.txt
   uname -a >> diagnostics.txt
   python --version >> diagnostics.txt
   echo "=== Config (redacted) ===" >> diagnostics.txt
   grep -v "KEY\|PASSWORD\|SECRET" config/.env >> diagnostics.txt
   echo "=== Recent Logs ===" >> diagnostics.txt
   tail -100 logs/assistant.log >> diagnostics.txt
   echo "=== Audio Devices ===" >> diagnostics.txt
   arecord -l >> diagnostics.txt 2>&1
   aplay -l >> diagnostics.txt 2>&1
   ```

2. **Check GitHub Issues:** Search for similar issues

3. **Open New Issue:** Include diagnostics.txt (ensure API keys are removed)

---

## Prevention Tips

1. **Keep Updated:** Regularly update dependencies
2. **Monitor Logs:** Check logs periodically for warnings
3. **Test Audio:** Verify microphone/speakers work before reporting issues
4. **Use Hybrid Mode:** Provides best reliability with fallback
5. **Backup Config:** Save working configuration before changes
