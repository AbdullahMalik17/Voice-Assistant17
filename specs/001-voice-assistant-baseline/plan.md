# Implementation Plan: Voice Assistant Baseline

**Branch**: `001-voice-assistant-baseline` | **Date**: 2026-01-01 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-voice-assistant-baseline/spec.md`

## Summary

Build a privacy-centric voice assistant with wake word detection ("Hey Assistant"), natural language understanding for informational/task-based/conversational queries, 5-exchange context management, and local action execution capabilities. The system uses modular architecture with separate STT, LLM, and TTS components, prioritizes local execution for privacy, and degrades gracefully during network outages. Cross-platform support includes Windows, macOS, Linux, and Raspberry Pi 4/5.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**:
- FastAPI (backend service layer)
- OpenAI Whisper (STT - local/API hybrid)
- Gemini API (google-genai) / Ollama (LLM - cloud/local fallback)
- ElevenLabs API / Piper (TTS - cloud/local hybrid)
- pvporcupine (wake word detection)
- Playwright (system automation via MCP)

**Storage**:
- In-memory: Conversation context (default, 5 exchanges, 5-minute timeout)
- Optional local encrypted storage: Conversation history (user-configurable, 7-day retention default)
- Local files: Event logs and performance metrics

**Testing**: pytest (unit, integration, contract tests)

**Target Platform**: Cross-platform (Windows 10+, macOS 11+, Linux Ubuntu 20.04+, Raspberry Pi 4/5 with Raspbian)

**Project Type**: Single application with modular service architecture

**Performance Goals**:
- Wake word detection: <1 second activation time
- Speech-to-text: >95% WER accuracy in quiet environments
- Query processing: <2 seconds from speech end to spoken response
- Total interaction: <3 seconds wake-to-response
- Memory footprint: <500MB on Raspberry Pi

**Constraints**:
- Privacy: No persistent storage without user consent; local-first processing
- Latency: Sub-500ms response generation target (constitution requirement)
- Accuracy: >90% wake word accuracy at 3 meters; >95% STT WER
- Offline capability: Wake word detection and basic commands work without internet
- Cross-platform: No platform-specific degradation

**Scale/Scope**:
- Single-user system (baseline)
- 5-exchange conversation context window
- Support for ~20-30 common system commands
- Event logging with local file rotation
- Request queue for offline scenarios

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### ✅ Privacy First
- **Compliance**: Conversation history persistence is OPT-IN (disabled by default)
- **Compliance**: In-memory context storage by default (no persistent data without consent)
- **Compliance**: When persistence enabled, local encryption required (FR-020)
- **Compliance**: Wake word detection and basic commands run locally (FR-015)

### ✅ Latency Optimization
- **Compliance**: <3 second total wake-to-response target (SC-003)
- **Compliance**: <2 second query processing after speech (FR-005)
- **Compliance**: <1 second wake word activation (FR-002)
- **Note**: Sub-500ms constitution target applies to response generation; total includes wake word + STT processing

### ✅ Modular Architecture
- **Compliance**: Separate STT, LLM, and TTS service layers
- **Compliance**: Hybrid cloud/local support for each component
- **Compliance**: FastAPI service layer orchestrates decoupled components

### ✅ Reliability / Edge-First
- **Compliance**: Offline operation for wake word and basic commands (FR-015)
- **Compliance**: Graceful degradation with user notification (FR-016)
- **Compliance**: Request queuing during network outages with auto-retry (FR-025, FR-026)
- **Compliance**: Network connectivity monitoring (FR-027)

### ✅ System-Wide Control & Automation
- **Compliance**: Playwright MCP integration for browser automation
- **Compliance**: Local script/command execution (FR-007, FR-009, FR-010)
- **Compliance**: Voice-triggered automation workflows

**Gate Status**: ✅ PASSED - All constitutional principles satisfied

## Project Structure

### Documentation (this feature)

```text
specs/001-voice-assistant-baseline/
├── spec.md              # Feature specification (completed)
├── plan.md              # This file (/sp.plan command output)
├── research.md          # Phase 0 output (technology decisions)
├── data-model.md        # Phase 1 output (entities & state)
├── quickstart.md        # Phase 1 output (setup & usage)
├── contracts/           # Phase 1 output (API specs)
│   ├── stt-service.yaml
│   ├── llm-service.yaml
│   ├── tts-service.yaml
│   └── wake-word-service.yaml
├── checklists/
│   └── requirements.md  # Quality validation checklist
└── tasks.md             # Phase 2 output (/sp.tasks command - NOT created yet)
```

### Source Code (repository root)

```text
src/
├── core/
│   ├── __init__.py
│   ├── config.py              # Configuration management
│   ├── context_manager.py     # Conversation context (5 exchanges)
│   └── request_queue.py       # Network outage request queuing
├── services/
│   ├── __init__.py
│   ├── wake_word.py           # pvporcupine wake word detection
│   ├── stt.py                 # Whisper STT (local/API hybrid)
│   ├── llm.py                 # Gemini/Ollama LLM (cloud/local)
│   ├── tts.py                 # ElevenLabs/Piper TTS (cloud/local)
│   ├── intent_classifier.py  # Intent recognition (informational/task/conversational)
│   ├── action_executor.py    # Local script/command execution
│   └── playwright_mcp.py     # Playwright automation integration
├── models/
│   ├── __init__.py
│   ├── voice_command.py       # Voice command entity
│   ├── intent.py              # Intent entity
│   ├── conversation_context.py # Context entity
│   └── event_log.py           # Event logging entity
├── storage/
│   ├── __init__.py
│   ├── memory_store.py        # In-memory context storage
│   └── encrypted_store.py     # Optional encrypted persistence
├── api/
│   ├── __init__.py
│   ├── main.py                # FastAPI application entry
│   ├── routes.py              # API endpoints
│   └── middleware.py          # Logging, error handling
├── cli/
│   ├── __init__.py
│   └── assistant.py           # CLI interface for assistant
└── utils/
    ├── __init__.py
    ├── logger.py              # Event logging & metrics
    ├── audio_utils.py         # Audio I/O utilities
    └── network_monitor.py     # Connectivity monitoring

tests/
├── unit/
│   ├── test_wake_word.py
│   ├── test_stt.py
│   ├── test_llm.py
│   ├── test_tts.py
│   ├── test_intent_classifier.py
│   ├── test_action_executor.py
│   └── test_context_manager.py
├── integration/
│   ├── test_voice_pipeline.py
│   ├── test_offline_mode.py
│   └── test_network_recovery.py
└── contract/
    ├── test_stt_contract.py
    ├── test_llm_contract.py
    └── test_tts_contract.py

config/
├── .env.template              # Environment configuration template
└── assistant_config.yaml      # Assistant configuration

scripts/
├── install_dependencies.sh    # Cross-platform dependency installer
└── setup_wake_word.sh         # Wake word model setup

logs/                          # Event logs and metrics (gitignored)
data/                          # Optional encrypted conversation storage (gitignored)
```

**Structure Decision**: Single application with modular service architecture. This matches the constitution's requirement for decoupled STT/LLM/TTS layers while maintaining simplicity for a baseline voice assistant. Services are organized by function, with clear separation between core logic, service implementations, data models, and storage mechanisms.

## Complexity Tracking

> No constitutional violations - this section intentionally left empty.

## Phase 0: Research & Technology Decisions

See [research.md](./research.md) for detailed technology evaluations and decisions.

**Key Research Areas**:
1. Wake word detection library selection (pvporcupine vs. snowboy vs. custom)
2. STT hybrid architecture (Whisper local vs. API tradeoffs)
3. LLM selection (Gemini API vs. Ollama performance/latency)
4. TTS fast synthesis (ElevenLabs vs. Piper quality/latency)
5. Context management persistence strategy
6. Playwright MCP integration patterns
7. Cross-platform audio I/O libraries
8. Network connectivity monitoring best practices
9. Encrypted local storage implementation
10. Event logging and metrics collection

## Phase 1: Data Model & API Contracts

### Data Model

See [data-model.md](./data-model.md) for complete entity definitions, relationships, and state transitions.

**Core Entities**:
- **VoiceCommand**: User spoken input after wake word
- **Intent**: Classified request type with extracted entities
- **ConversationContext**: 5-exchange short-term memory
- **ActionScript**: Mapped system commands
- **SystemStatus**: System state information
- **EventLog**: Structured event/metric records
- **RequestQueue**: Queued requests during network outages

### API Contracts

See [contracts/](./contracts/) for OpenAPI specifications of internal service interfaces.

**Service Contracts**:
- `wake-word-service.yaml`: Wake word detection API
- `stt-service.yaml`: Speech-to-text service API
- `llm-service.yaml`: Language model service API
- `tts-service.yaml`: Text-to-speech service API
- `action-executor-service.yaml`: Action execution API

### Quickstart

See [quickstart.md](./quickstart.md) for setup, configuration, and basic usage instructions.

## Skills Required for This Project

Based on the architecture and requirements, the following skills need to be developed:

### 1. Wake Word Detection Skill
**Purpose**: Listen for "Hey Assistant" wake word and activate the assistant
**Key Capabilities**:
- Continuous audio stream monitoring
- pvporcupine library integration
- Sensitivity adjustment (false positive/negative tradeoff)
- Cross-platform audio input handling
**Integration**: Triggers STT service on detection

### 2. Speech-to-Text (STT) Skill
**Purpose**: Convert user speech to text with >95% WER accuracy
**Key Capabilities**:
- Whisper model integration (local/API hybrid)
- Audio preprocessing and normalization
- Streaming vs. batch processing decision
- Fallback to cloud API when local performance insufficient
**Integration**: Feeds text to intent classifier

### 3. Intent Classification Skill
**Purpose**: Classify user requests into informational/task-based/conversational
**Key Capabilities**:
- Natural language understanding
- Entity extraction from text
- Intent type determination
- Confidence scoring
**Integration**: Routes to appropriate handler (LLM query vs. action execution)

### 4. Context Management Skill
**Purpose**: Maintain 5-exchange conversation memory for follow-up questions
**Key Capabilities**:
- In-memory conversation context storage
- 5-minute timeout tracking
- Context resolution for pronouns/references
- Context reset on topic shift detection
**Integration**: Provides context to LLM for coherent responses

### 5. LLM Query Skill
**Purpose**: Generate responses for informational and conversational queries
**Key Capabilities**:
- Gemini API / Ollama integration
- Cloud/local fallback logic
- Prompt construction with conversation context
- Response generation within latency constraints
**Integration**: Returns response text to TTS

### 6. Text-to-Speech (TTS) Skill
**Purpose**: Convert text responses to natural-sounding speech
**Key Capabilities**:
- ElevenLabs API / Piper integration
- Voice quality vs. latency tradeoff
- Audio output streaming
- Cross-platform audio playback
**Integration**: Speaks responses to user

### 7. Action Execution Skill
**Purpose**: Execute local scripts and system commands via voice
**Key Capabilities**:
- Command parsing and validation
- Application launcher (cross-platform)
- System status retrieval (CPU, memory, disk)
- Script execution with safety constraints
**Integration**: Returns execution status to TTS for confirmation

### 8. Playwright Automation Skill
**Purpose**: Execute browser automation tasks via voice commands
**Key Capabilities**:
- Playwright MCP integration
- Natural language to automation workflow translation
- Browser navigation and interaction
- Visual feedback capture and analysis
**Integration**: Executes complex multi-step automation from voice commands

### 9. Network Resilience Skill
**Purpose**: Handle network disconnection gracefully with request queuing
**Key Capabilities**:
- Network connectivity monitoring
- Request queue management
- Auto-retry logic on connection restore
- User notification of network status
**Integration**: Ensures offline wake word/local commands work; queues online requests

### 10. Event Logging & Metrics Skill
**Purpose**: Log events and track performance metrics for debugging/monitoring
**Key Capabilities**:
- Structured event logging (wake word, intents, actions, errors)
- Performance metric tracking (latency, accuracy)
- Local file persistence with rotation
- Log analysis and reporting
**Integration**: Captures telemetry from all services

### 11. Privacy & Storage Management Skill
**Purpose**: Manage conversation data storage with user privacy controls
**Key Capabilities**:
- User preference management (opt-in/out)
- Encrypted local storage (when enabled)
- Automatic data retention/deletion
- In-memory default operation
**Integration**: Stores/retrieves conversation history based on user settings

### 12. Interruption Handling Skill
**Purpose**: Handle wake word during active processing (immediate interruption)
**Key Capabilities**:
- Task cancellation on wake word detection
- State cleanup for interrupted operations
- New request activation
- Graceful termination of in-flight tasks
**Integration**: Cancels current operation and restarts pipeline

---

**Next Steps**:
1. Complete Phase 0 research.md with detailed technology decisions
2. Complete Phase 1 data-model.md with entity specifications
3. Generate API contracts in contracts/ directory
4. Create quickstart.md for setup and usage
5. Run /sp.tasks to generate actionable implementation tasks
