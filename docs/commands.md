# Voice Command Reference

**Version**: 1.0.0
**Date**: 2026-01-02

## Overview

This document lists all voice commands supported by the Voice Assistant.

---

## Activation

### Wake Word
Say **"Hey Assistant"** to activate the assistant.

The assistant will respond with "I'm listening" and begin recording your query.

---

## Query Types

### Informational Queries

Ask questions to get information:

| Example Command | Description |
|-----------------|-------------|
| "What time is it?" | Get current time |
| "What's the weather today?" | Weather information (requires internet) |
| "What is the capital of France?" | General knowledge queries |
| "How do I bake a cake?" | How-to questions |
| "Tell me about quantum physics" | Explanatory queries |

### Conversational Queries

Have a conversation with the assistant:

| Example Command | Description |
|-----------------|-------------|
| "Tell me a joke" | Entertainment requests |
| "How are you?" | Social interaction |
| "What do you think about AI?" | Opinion questions |
| "Let's chat" | Open conversation |

### Follow-up Questions

The assistant maintains context for up to 5 exchanges:

```
User: "What's the weather today?"
Assistant: "It's sunny with a high of 75°F"

User: "What about tomorrow?"
Assistant: "Tomorrow will be partly cloudy with a high of 72°F"

User: "Should I bring an umbrella?"
Assistant: "Based on tomorrow's forecast, you might want one just in case"
```

**Note**: Context resets after 5 minutes of inactivity or when the topic changes significantly.

---

## System Commands (Task-Based)

### System Status

Check your computer's status:

| Command | Description |
|---------|-------------|
| "Check my CPU usage" | CPU utilization percentage |
| "What's my CPU temperature?" | CPU temperature (if available) |
| "Check memory usage" | RAM utilization |
| "How much disk space do I have?" | Disk usage and available space |
| "Check battery status" | Battery level and charging status |
| "What's my system status?" | Full system overview |

### Application Control

Launch applications:

| Command | Description |
|---------|-------------|
| "Open Spotify" | Launch Spotify |
| "Open Notepad" | Launch Notepad (Windows) |
| "Open browser" | Launch default browser |

**Note**: Available applications vary by operating system.

---

## Control Commands

### Cancellation

Interrupt the assistant:

| Command | Description |
|---------|-------------|
| Say wake word during response | Interrupts current processing |
| "Stop" | Cancel current action |
| "Cancel" | Cancel current action |
| "Never mind" | Cancel and return to listening |

### Session Control

| Action | Description |
|--------|-------------|
| Press Ctrl+C | Gracefully shutdown assistant |

---

## Error Handling

### Speech Recognition Issues

If the assistant doesn't understand:
- Speak more clearly
- Reduce background noise
- Move closer to the microphone
- Try rephrasing your question

The assistant will say "I'm not sure I understood that. Could you repeat?"

### Network Issues

When offline:
- Local commands (system status, app launching) still work
- Cloud-dependent queries are queued for later
- Assistant announces "Waiting for network connection"

When connection restores:
- Queued requests are processed automatically
- Assistant announces "Network connection restored"

---

## Tips for Best Results

1. **Speak naturally** - No need for robotic speech
2. **Wait for confirmation** - After wake word, wait for "I'm listening"
3. **Be specific** - Clear questions get better answers
4. **Use follow-ups** - The assistant remembers recent context
5. **One request at a time** - Complete one interaction before starting another

---

## Supported Languages

Currently supported: **English (en)**

The assistant uses Whisper for speech recognition, which supports multiple languages, but responses are generated in English.

---

## Privacy Notes

- **Local processing**: Wake word detection and STT can run locally
- **Cloud APIs**: LLM and TTS may use cloud services (configurable)
- **No storage**: By default, no conversation data is stored
- **Optional persistence**: Enable encrypted local storage in config

---

## Customization

### Adjust Wake Word Sensitivity

Edit `config/.env`:
```bash
WAKE_WORD_SENSITIVITY=0.7  # Higher = more sensitive (0.0-1.0)
```

### Change STT/LLM/TTS Modes

```bash
# Local-only (maximum privacy)
STT_MODE=local
LLM_MODE=local
TTS_MODE=local

# API-only (minimum latency)
STT_MODE=api
LLM_MODE=api
TTS_MODE=api

# Hybrid (recommended - fallback on failure)
STT_MODE=hybrid
LLM_MODE=hybrid
TTS_MODE=hybrid
```

---

## Adding Custom Commands

Custom commands can be added to `config/actions.yaml` (future feature).

For now, the assistant handles:
- **Informational**: General questions answered by LLM
- **Conversational**: Casual interaction answered by LLM
- **Task-based**: System commands handled by Action Executor
