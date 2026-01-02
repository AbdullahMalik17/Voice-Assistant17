# Data Model: Voice Assistant Baseline

**Feature**: 001-voice-assistant-baseline
**Date**: 2026-01-01
**Status**: Completed

## Overview

This document defines the core data entities, their attributes, relationships, validation rules, and state transitions for the Voice Assistant Baseline feature.

---

## Entity Definitions

### 1. VoiceCommand

**Description**: Represents a user's spoken input captured after wake word detection.

**Attributes**:
- `id`: string (UUID) - Unique identifier
- `audio_data`: bytes - Raw audio buffer from microphone
- `transcribed_text`: string | null - Speech-to-text output
- `timestamp`: datetime - When command was captured
- `duration_ms`: integer - Audio duration in milliseconds
- `confidence_score`: float (0.0-1.0) - STT confidence level
- `status`: enum - Processing status

**States**:
- `CAPTURED` → Audio recorded, awaiting transcription
- `TRANSCRIBING` → STT service processing
- `TRANSCRIBED` → Text available, ready for intent classification
- `FAILED` → STT failed or audio invalid
- `CANCELLED` → Interrupted by new wake word

**Validation Rules**:
- `audio_data` must not be empty
- `duration_ms` must be >0 and <60000 (max 1 minute)
- `confidence_score` must be between 0.0 and 1.0
- `timestamp` must not be in the future

**Relationships**:
- One-to-one with `Intent` (after classification)
- Referenced by `ConversationContext`

---

### 2. Intent

**Description**: Classified request type with extracted entities and parameters.

**Attributes**:
- `id`: string (UUID) - Unique identifier
- `voice_command_id`: string (UUID, FK) - Source command
- `intent_type`: enum - Classification category
- `entities`: dict - Extracted entities (e.g., {"app": "Spotify"})
- `confidence_score`: float (0.0-1.0) - Classification confidence
- `timestamp`: datetime - When classified
- `requires_network`: boolean - Whether needs internet
- `action_type`: enum | null - Specific action if task-based

**Intent Types**:
- `INFORMATIONAL` - Query requiring external data (weather, time, facts)
- `TASK_BASED` - System action (open app, check status)
- `CONVERSATIONAL` - Social interaction (joke, greeting)

**Action Types** (for TASK_BASED):
- `LAUNCH_APP` - Open application
- `SYSTEM_STATUS` - Check CPU/memory/disk
- `BROWSER_AUTOMATION` - Playwright MCP automation
- `FILE_OPERATION` - File management
- `CUSTOM_SCRIPT` - User-defined script

**Validation Rules**:
- `voice_command_id` must reference valid VoiceCommand
- `intent_type` must be one of the defined enum values
- `confidence_score` must be between 0.0 and 1.0
- `entities` must be valid JSON dict
- `action_type` required if `intent_type` is TASK_BASED

**Relationships**:
- Many-to-one with `VoiceCommand`
- Referenced by `ConversationContext`
- May trigger `ActionScript` execution

---

### 3. ConversationContext

**Description**: Short-term memory of the last 5 exchanges for follow-up question resolution.

**Attributes**:
- `id`: string (UUID) - Unique identifier
- `session_id`: string (UUID) - Current session identifier
- `exchanges`: list[Exchange] - Last 5 user-assistant exchanges
- `last_activity`: datetime - Most recent interaction timestamp
- `timeout_seconds`: integer - Inactivity timeout (default: 300)
- `is_active`: boolean - Whether context is still valid
- `topic_keywords`: list[string] - Extracted topics for context matching

**Exchange Structure**:
```python
{
    "user_input": str,           # Transcribed user speech
    "user_intent": Intent,        # Classified intent object
    "assistant_response": str,    # Generated response text
    "timestamp": datetime,        # When exchange occurred
    "confidence": float          # Overall exchange confidence
}
```

**State Transitions**:
```
ACTIVE → timeout after 5 minutes → EXPIRED
ACTIVE → wake word during processing → INTERRUPTED → RESET → ACTIVE (new)
ACTIVE → topic shift detected → RESET → ACTIVE (new topic)
```

**Validation Rules**:
- `exchanges` list max length: 5 (FIFO queue)
- `last_activity` updated on every interaction
- `timeout_seconds` must be >0
- Auto-expire if `datetime.now() - last_activity > timeout_seconds`

**Relationships**:
- References multiple `VoiceCommand` and `Intent` objects
- One active context per user session

---

### 4. ActionScript

**Description**: Mapped system command or script for task-based intents.

**Attributes**:
- `id`: string (UUID) - Unique identifier
- `name`: string - Human-readable action name
- `command_template`: string - Command with placeholders
- `platform`: enum - Target OS (WINDOWS, MACOS, LINUX, ALL)
- `requires_confirmation`: boolean - Ask user before executing
- `timeout_seconds`: integer - Max execution time
- `parameters`: list[Parameter] - Expected parameters
- `category`: enum - Action category

**Parameter Structure**:
```python
{
    "name": str,                  # Parameter name
    "type": str,                  # Data type (string, int, bool)
    "required": bool,             # Whether mandatory
    "default": any,               # Default value if not provided
    "validation_regex": str       # Validation pattern
}
```

**Categories**:
- `APPLICATION` - Launch/manage applications
- `SYSTEM_INFO` - Retrieve system status
- `FILE_MGMT` - File operations
- `BROWSER` - Web automation via Playwright
- `CUSTOM` - User-defined scripts

**Examples**:
```python
# Launch Spotify
{
    "name": "Launch Spotify",
    "command_template": "spotify" if platform == MACOS else "start spotify",
    "platform": "ALL",
    "requires_confirmation": False,
    "timeout_seconds": 10,
    "parameters": [],
    "category": "APPLICATION"
}

# Check CPU temperature
{
    "name": "Check CPU Temp",
    "command_template": "sensors | grep 'Package id 0'",  # Linux example
    "platform": "LINUX",
    "requires_confirmation": False,
    "timeout_seconds": 5,
    "parameters": [],
    "category": "SYSTEM_INFO"
}
```

**Validation Rules**:
- `name` must be unique per platform
- `command_template` must not contain unsanitized user input
- `timeout_seconds` must be >0 and <300 (5 minutes max)
- Parameters must match those referenced in command_template

**Relationships**:
- Triggered by `Intent` with `action_type`
- Execution logged in `EventLog`

---

### 5. SystemStatus

**Description**: Current system state information accessible for informational queries.

**Attributes**:
- `timestamp`: datetime - When status was captured
- `cpu_percent`: float - CPU usage percentage
- `cpu_temp_celsius`: float | null - CPU temperature (if available)
- `memory_percent`: float - RAM usage percentage
- `memory_available_mb`: integer - Available RAM in MB
- `disk_percent`: float - Disk usage percentage
- `disk_available_gb`: float - Available disk space in GB
- `running_processes`: integer - Number of processes
- `uptime_seconds`: integer - System uptime
- `network_connected`: boolean - Internet connectivity status

**Validation Rules**:
- All percentage values must be between 0.0 and 100.0
- `memory_available_mb` must be >=0
- `disk_available_gb` must be >=0
- `timestamp` must not be in the future

**Refresh Policy**:
- Cached for 5 seconds to avoid excessive system calls
- Refreshed on demand when user requests status

**Relationships**:
- No persistent relationships; ephemeral data
- Retrieved by `ActionScript` for SYSTEM_INFO category

---

### 6. EventLog

**Description**: Structured record of system events and performance metrics.

**Attributes**:
- `id`: string (UUID) - Unique identifier
- `timestamp`: datetime - When event occurred
- `event_type`: enum - Category of event
- `severity`: enum - Log level
- `message`: string - Human-readable description
- `metadata`: dict - Additional structured data
- `duration_ms`: integer | null - Event duration if applicable
- `success`: boolean - Whether operation succeeded

**Event Types**:
- `WAKE_WORD_DETECTED` - Wake word activation
- `STT_PROCESSED` - Speech transcription completed
- `INTENT_CLASSIFIED` - Intent classification completed
- `LLM_QUERY` - LLM response generation
- `TTS_SPOKEN` - Text-to-speech playback
- `ACTION_EXECUTED` - System command executed
- `ERROR_OCCURRED` - Error or exception
- `NETWORK_STATUS_CHANGED` - Connectivity change

**Severity Levels**:
- `DEBUG` - Detailed diagnostic information
- `INFO` - General informational events
- `WARNING` - Warning conditions
- `ERROR` - Error conditions
- `CRITICAL` - Critical failures

**Example Metadata**:
```python
# Wake word detection
{
    "event_type": "WAKE_WORD_DETECTED",
    "metadata": {
        "confidence": 0.95,
        "audio_duration_ms": 150,
        "keyword": "Hey Assistant"
    }
}

# STT processing
{
    "event_type": "STT_PROCESSED",
    "metadata": {
        "transcribed_text": "What's the weather?",
        "confidence": 0.97,
        "model": "whisper-base",
        "fallback_used": False
    },
    "duration_ms": 1200
}
```

**Validation Rules**:
- `timestamp` must not be in the future
- `event_type` must be valid enum value
- `metadata` must be valid JSON dict
- `duration_ms` must be >=0 if provided

**Storage**:
- Persisted to local JSON files in `logs/` directory
- Log rotation: max 10MB per file, 5 backup files
- Retention: auto-delete logs older than 30 days

**Relationships**:
- References `VoiceCommand`, `Intent`, `ActionScript` via UUIDs in metadata
- No direct FK relationships (optimized for append-only writes)

---

### 7. RequestQueue

**Description**: Temporary storage for voice commands requiring network that were received during offline periods.

**Attributes**:
- `id`: string (UUID) - Unique identifier
- `voice_command_id`: string (UUID, FK) - Queued command
- `intent_id`: string (UUID, FK) - Classified intent
- `queued_at`: datetime - When added to queue
- `retry_count`: integer - Number of retry attempts
- `max_retries`: integer - Maximum retry attempts (default: 3)
- `status`: enum - Queue item status
- `error_message`: string | null - Last error if retries failed

**States**:
- `QUEUED` → Waiting for network restoration
- `RETRYING` → Attempting to process
- `COMPLETED` → Successfully processed
- `FAILED` → Max retries exceeded
- `EXPIRED` → Timed out (>1 hour in queue)

**Validation Rules**:
- `voice_command_id` and `intent_id` must reference valid objects
- `retry_count` must be <=`max_retries`
- `queued_at` must not be in the future
- Auto-expire items older than 1 hour

**Processing Policy**:
- Network connectivity monitor triggers queue processing
- Items processed in FIFO order
- 30-second delay between retry attempts
- User notified when queue item processed or failed

**Relationships**:
- Many-to-one with `VoiceCommand` and `Intent`
- Processed items logged in `EventLog`

---

## Entity Relationship Diagram

```
┌─────────────────┐
│  VoiceCommand   │
│  - id           │
│  - audio_data   │
│  - transcribed  │
│  - timestamp    │
└────────┬────────┘
         │
         │ 1:1
         ▼
    ┌────────────┐
    │   Intent   │
    │  - id      │
    │  - type    │
    │  - entities│
    └──┬─────┬───┘
       │     │
    1:N│     │triggers
       │     │
       ▼     ▼
┌──────────────┐  ┌──────────────┐
│Conversation  │  │ ActionScript │
│  Context     │  │  - command   │
│  - exchanges │  │  - platform  │
│  - topic     │  │  - params    │
└──────────────┘  └──────────────┘
                          │
                       logs to
                          ▼
                   ┌──────────────┐
                   │  EventLog    │
                   │  - event_type│
                   │  - metadata  │
                   └──────────────┘

┌──────────────┐
│RequestQueue  │
│  - queued_at │
│  - status    │
└──────┬───────┘
       │
   references
       │
       ▼
  VoiceCommand
  & Intent
```

---

## State Machines

### VoiceCommand Lifecycle

```
                  ┌─────────┐
     audio input  │CAPTURED │
    ──────────────►         │
                  └────┬────┘
                       │
                  STT process
                       │
                  ┌────▼────────┐
                  │TRANSCRIBING │
                  └────┬────────┘
                       │
              ┌────────┴────────┐
              │                 │
         success            failure/timeout
              │                 │
         ┌────▼─────┐      ┌───▼───┐
         │TRANSCRIBED│      │FAILED │
         └───────────┘      └───────┘
              │
       wake word interrupt
              │
         ┌────▼────┐
         │CANCELLED│
         └─────────┘
```

### ConversationContext Lifecycle

```
         ┌──────┐
    ─────►ACTIVE│
         └──┬───┘
            │
    ┌───────┼───────┬─────────┐
    │       │       │         │
  timeout  wake  topic     exchange
  (5 min)  word  shift     added (5)
    │       │       │         │
    ▼       ▼       ▼         │
 ┌────┐  ┌────┐  ┌────┐      │
 │EXP │  │INT │  │RESET─────►│
 │IRED│  │ERRU│  │           │
 └────┘  │PTED│  │           │
         └──┬─┘  └───────────┘
            │
          reset
            │
         ┌──▼───┐
         │ACTIVE│
         │ (new)│
         └──────┘
```

### RequestQueue Item Lifecycle

```
   network      ┌──────┐
  offline ──────►QUEUED│
                └──┬───┘
                   │
            network restored
                   │
              ┌────▼───────┐
              │  RETRYING  │
              └────┬───────┘
                   │
         ┌─────────┼─────────┐
         │                   │
      success            failure
         │                   │
    ┌────▼────┐         retry++
    │COMPLETED│              │
    └─────────┘      ┌───────▼────────┐
                     │ retry < max?   │
                     └───┬────────┬───┘
                        yes       no
                         │        │
                    back to    ┌──▼───┐
                    RETRYING   │FAILED│
                               └──────┘

       timeout (1 hour)
            │
         ┌──▼────┐
         │EXPIRED│
         └───────┘
```

---

## Validation Summary

All entities include:
- **Type validation**: All fields have strict type constraints
- **Range validation**: Numeric values have min/max bounds
- **Format validation**: UUIDs, timestamps, enums validated against standards
- **Referential integrity**: Foreign keys reference valid parent entities
- **Business rules**: Domain-specific constraints (e.g., max 5 exchanges, 5-minute timeout)

---

**Data model complete. Ready for API contract generation.**

**Next Step**: Generate OpenAPI specifications in `contracts/` directory
