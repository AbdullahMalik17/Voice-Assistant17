# Implementation Tasks: Agentic AI Improvements

**Feature**: 002-agentic-ai-improvements
**Created**: 2026-01-03
**Total Tasks**: 45

## Phase 1: Audio Preprocessing & STT Robustness

### T001: Create AudioPreprocessor base module
**Status**: pending
**Priority**: P1
**File**: `src/services/audio_preprocessor.py`

- [ ] Create AudioPreprocessorConfig dataclass with noise_threshold, aec_enabled, target_level
- [ ] Create ProcessedAudio dataclass with audio_bytes, metadata, processing_stats
- [ ] Implement AudioPreprocessor class with process() method
- [ ] Add unit tests for configuration validation

**Test**: `pytest tests/unit/test_audio_preprocessor.py`

---

### T002: Implement noise reduction using noisereduce
**Status**: pending
**Priority**: P1
**File**: `src/services/audio_preprocessor.py`
**Depends**: T001

- [ ] Add noisereduce>=3.0.0 to requirements.txt
- [ ] Implement NoiseGate class with spectral gating
- [ ] Add configurable threshold (default -40dB)
- [ ] Test noise reduction on sample audio files

**Test**: Compare WER before/after noise reduction on noisy test audio

---

### T003: Implement acoustic echo cancellation
**Status**: pending
**Priority**: P2
**File**: `src/services/audio_preprocessor.py`
**Depends**: T001

- [ ] Research AEC options (webrtcvad, speexdsp bindings)
- [ ] Implement AcousticEchoCanceller class
- [ ] Add reference audio input for TTS output cancellation
- [ ] Test with simulated echo scenarios

**Test**: Verify assistant voice is filtered from input during playback

---

### T004: Add STT confidence threshold handling
**Status**: pending
**Priority**: P1
**File**: `src/services/stt.py`
**Depends**: None

- [ ] Add confidence_threshold to STT config (default 0.6)
- [ ] Modify transcribe() to check confidence score
- [ ] Return TranscriptionResult with needs_clarification flag
- [ ] Add clarification_prompt to config

**Test**: Low-confidence audio triggers clarification response

---

### T005: Integrate preprocessor with STT pipeline
**Status**: pending
**Priority**: P1
**File**: `src/services/stt.py`
**Depends**: T002, T004

- [ ] Add preprocess parameter to transcribe() method
- [ ] Chain AudioPreprocessor before STT model
- [ ] Log preprocessing latency and improvements
- [ ] Update assistant.py to use preprocessing

**Test**: End-to-end test with noisy audio shows improved accuracy

---

## Phase 2: Semantic Memory System

### T010: Set up ChromaDB integration
**Status**: pending
**Priority**: P1
**File**: `src/memory/semantic_memory.py`

- [ ] Add chromadb>=0.4.0 to requirements.txt
- [ ] Create SemanticMemoryConfig with collection_name, persist_path
- [ ] Initialize ChromaDB client and collection
- [ ] Add health check for memory service

**Test**: `pytest tests/unit/test_semantic_memory.py`

---

### T011: Implement MemoryEntry model
**Status**: pending
**Priority**: P1
**File**: `src/models/memory.py`
**Depends**: T010

- [ ] Create MemoryEntry Pydantic model
- [ ] Add fields: id, content, metadata, created_at, expires_at
- [ ] Implement serialization for ChromaDB storage
- [ ] Add TTL validation (1 day to 365 days)

**Test**: Model serialization/deserialization roundtrip

---

### T012: Implement embedding generation
**Status**: pending
**Priority**: P1
**File**: `src/memory/semantic_memory.py`
**Depends**: T010

- [ ] Add sentence-transformers>=2.2.0 to requirements
- [ ] Use all-MiniLM-L6-v2 model (fast, 384 dim)
- [ ] Implement embed() method with batching support
- [ ] Cache model to avoid repeated loading

**Test**: Embedding generation completes in <100ms for single sentence

---

### T013: Implement store() method
**Status**: pending
**Priority**: P1
**File**: `src/memory/semantic_memory.py`
**Depends**: T011, T012

- [ ] Generate UUID for new entries
- [ ] Create embedding from content
- [ ] Store in ChromaDB with metadata
- [ ] Return entry ID

**Test**: Stored entry can be retrieved by ID

---

### T014: Implement retrieve() method with semantic search
**Status**: pending
**Priority**: P1
**File**: `src/memory/semantic_memory.py`
**Depends**: T013

- [ ] Accept query string and top_k parameter
- [ ] Generate query embedding
- [ ] Search ChromaDB for similar vectors
- [ ] Return ranked MemoryEntry list with scores

**Test**: Semantically similar queries return relevant memories

---

### T015: Implement forget() and retention policies
**Status**: pending
**Priority**: P2
**File**: `src/memory/semantic_memory.py`
**Depends**: T013

- [ ] Implement forget(session_id) to clear session memories
- [ ] Implement cleanup_expired() for TTL enforcement
- [ ] Add scheduled cleanup task (daily)
- [ ] Support retention policies: session, 7d, 30d, indefinite

**Test**: Expired entries are automatically removed

---

### T016: Create DialogueState manager
**Status**: pending
**Priority**: P1
**File**: `src/core/dialogue_state.py`

- [ ] Create DialogueState dataclass with session_id, filled_slots, history
- [ ] Implement DialogueStateManager class
- [ ] Add update_state() for new user turns
- [ ] Add get_context_for_llm() to format history

**Test**: State persists across multiple turns

---

### T017: Integrate semantic memory with dialogue state
**Status**: pending
**Priority**: P1
**File**: `src/core/dialogue_state.py`
**Depends**: T014, T016

- [ ] Query semantic memory for relevant context on new turn
- [ ] Inject retrieved memories into LLM prompt
- [ ] Store important facts from assistant responses
- [ ] Add memory_enabled flag to config

**Test**: Assistant recalls information from previous session

---

## Phase 3: Enhanced NLU

### T020: Create EntityExtractor module
**Status**: pending
**Priority**: P1
**File**: `src/services/entity_extractor.py`

- [ ] Create Entity dataclass with type, value, span, confidence
- [ ] Define supported entity types enum
- [ ] Create EntityExtractor class with LLM dependency
- [ ] Implement extract() method with structured output

**Test**: Extract DATE, TIME, PERSON from sample sentences

---

### T021: Implement LLM-based entity extraction
**Status**: pending
**Priority**: P1
**File**: `src/services/entity_extractor.py`
**Depends**: T020

- [ ] Create entity extraction prompt template
- [ ] Use Gemini structured output (JSON mode)
- [ ] Parse response into Entity objects
- [ ] Handle extraction failures gracefully

**Test**: >95% accuracy on entity test dataset

---

### T022: Create SlotFiller module
**Status**: pending
**Priority**: P1
**File**: `src/services/slot_filler.py`

- [ ] Create SlotDefinition dataclass
- [ ] Create IntentSlots mapping from config
- [ ] Implement SlotFiller class
- [ ] Add check_slots() to identify missing required slots

**Test**: Missing slot detected for incomplete command

---

### T023: Configure slot definitions for common intents
**Status**: pending
**Priority**: P1
**File**: `config/slots.yaml`
**Depends**: T022

- [ ] Define slots for: set_timer, set_reminder, send_email
- [ ] Define slots for: calendar_event, search_web, get_weather
- [ ] Add prompt templates for each missing slot
- [ ] Validate slot definitions on startup

**Test**: All configured intents have valid slot definitions

---

### T024: Implement slot filling dialogue
**Status**: pending
**Priority**: P1
**File**: `src/services/slot_filler.py`
**Depends**: T022, T023

- [ ] Integrate with DialogueState for slot tracking
- [ ] Generate prompts for missing slots
- [ ] Update slots from entity extraction results
- [ ] Return action-ready params when all required slots filled

**Test**: Multi-turn slot filling completes set_timer intent

---

### T025: Upgrade IntentClassifier to LLM-based
**Status**: pending
**Priority**: P1
**File**: `src/services/intent_classifier.py`
**Depends**: T020

- [ ] Create intent classification prompt template
- [ ] Use LLM with structured output for classification
- [ ] Return top-3 candidates with confidence scores
- [ ] Keep regex patterns as fast fallback

**Test**: LLM classification matches regex for clear intents

---

### T026: Implement intent disambiguation
**Status**: pending
**Priority**: P2
**File**: `src/services/intent_classifier.py`
**Depends**: T025

- [ ] Detect when top-2 intents have similar confidence (diff < 0.15)
- [ ] Generate disambiguation question
- [ ] Present options to user via TTS
- [ ] Update intent based on user clarification

**Test**: Ambiguous "play music" prompts for Spotify vs YouTube

---

## Phase 4: Agentic Planner

### T030: Create Tool interface and registry
**Status**: pending
**Priority**: P1
**File**: `src/agents/tools.py`

- [ ] Create Tool abstract base class
- [ ] Define ToolParameter and ToolResult dataclasses
- [ ] Implement ToolRegistry with register/get/list methods
- [ ] Add tool discovery from plugins directory

**Test**: Registry correctly tracks registered tools

---

### T031: Implement built-in tools
**Status**: pending
**Priority**: P1
**File**: `src/agents/builtin_tools.py`
**Depends**: T030

- [ ] Implement SystemStatusTool (extends existing action executor)
- [ ] Implement LaunchAppTool
- [ ] Implement SetTimerTool
- [ ] Implement WebSearchTool (via DuckDuckGo API)

**Test**: Each tool executes correctly with valid parameters

---

### T032: Create Plan and PlanStep models
**Status**: pending
**Priority**: P1
**File**: `src/models/plan.py`

- [ ] Create PlanStep dataclass with id, action, parameters, status
- [ ] Create Plan dataclass with steps, current_step, status
- [ ] Implement step dependency resolution
- [ ] Add plan serialization for persistence

**Test**: Plan with dependencies executes in correct order

---

### T033: Implement AgenticPlanner
**Status**: pending
**Priority**: P1
**File**: `src/agents/planner.py`
**Depends**: T030, T032

- [ ] Create planning prompt template
- [ ] Implement create_plan() using LLM
- [ ] Validate generated plan against available tools
- [ ] Add error handling for invalid plans

**Test**: "Schedule meeting with John" generates multi-step plan

---

### T034: Implement plan execution engine
**Status**: pending
**Priority**: P1
**File**: `src/agents/planner.py`
**Depends**: T033

- [ ] Implement execute() generator for step-by-step execution
- [ ] Handle step success, failure, and retry
- [ ] Yield progress updates for TTS reporting
- [ ] Support plan cancellation via interrupt

**Test**: Plan executes all steps with progress reporting

---

### T035: Implement safety guardrails
**Status**: pending
**Priority**: P1
**File**: `src/agents/guardrails.py`

- [ ] Define sensitive action list (email, delete, financial)
- [ ] Implement confirmation prompts for sensitive actions
- [ ] Add command blocklist (rm -rf, format, etc.)
- [ ] Implement rate limiting (max 10 actions/minute)

**Test**: Sensitive action prompts for confirmation before execution

---

### T036: Integrate planner with main assistant loop
**Status**: pending
**Priority**: P1
**File**: `src/cli/assistant.py`
**Depends**: T034, T035

- [ ] Detect complex goals requiring planning
- [ ] Create and execute plans transparently
- [ ] Report progress via TTS
- [ ] Handle plan failures gracefully

**Test**: Voice command "Book a flight to Tokyo" triggers planning

---

## Phase 5: Observability

### T040: Set up Prometheus metrics
**Status**: pending
**Priority**: P2
**File**: `src/observability/metrics.py`

- [ ] Add prometheus-client to requirements
- [ ] Define core metrics (latency histograms, counters, gauges)
- [ ] Instrument STT, intent, LLM, TTS services
- [ ] Expose /metrics endpoint

**Test**: Metrics endpoint returns valid Prometheus format

---

### T041: Implement distributed tracing
**Status**: pending
**Priority**: P2
**File**: `src/observability/tracing.py`
**Depends**: T040

- [ ] Add opentelemetry packages to requirements
- [ ] Create trace context for each interaction
- [ ] Propagate trace IDs through service calls
- [ ] Export to console/Jaeger

**Test**: Full trace visible for end-to-end request

---

### T042: Add structured logging improvements
**Status**: pending
**Priority**: P2
**File**: `src/utils/logger.py`

- [ ] Add trace_id to all log entries
- [ ] Add component field (stt, intent, llm, tts)
- [ ] Implement log levels per component
- [ ] Add request/response summarization

**Test**: Logs can be filtered by trace_id

---

### T043: Create health check endpoint
**Status**: pending
**Priority**: P2
**File**: `src/api/health.py`
**Depends**: T040

- [ ] Implement /health endpoint
- [ ] Check each component status
- [ ] Return aggregated health with metrics
- [ ] Add Kubernetes-compatible liveness/readiness probes

**Test**: Health check returns 200 when all components healthy

---

## Phase 6: Testing & CI/CD

### T050: Create audio test fixtures
**Status**: pending
**Priority**: P2
**File**: `tests/fixtures/audio/`

- [ ] Record/collect clean wake word audio files
- [ ] Record/collect noisy environment samples
- [ ] Create command audio for common intents
- [ ] Document expected transcriptions

**Test**: All audio files load and play correctly

---

### T051: Implement audio integration tests
**Status**: pending
**Priority**: P2
**File**: `tests/integration/test_audio_pipeline.py`
**Depends**: T050

- [ ] Test STT accuracy on clean audio (>95% WER)
- [ ] Test STT with noise filtering improvement
- [ ] Test wake word detection latency (<1s)
- [ ] Test false positive rate (<1 per 8 hours simulated)

**Test**: `pytest tests/integration/ -m audio`

---

### T052: Create GitHub Actions CI workflow
**Status**: pending
**Priority**: P2
**File**: `.github/workflows/ci.yml`

- [ ] Set up Python 3.10 environment
- [ ] Run ruff linting
- [ ] Run mypy type checking
- [ ] Run pytest with coverage threshold (80%)

**Test**: CI passes on clean PR

---

### T053: Add security scanning
**Status**: pending
**Priority**: P2
**File**: `.github/workflows/ci.yml`
**Depends**: T052

- [ ] Add bandit for Python security analysis
- [ ] Add safety for dependency vulnerability checking
- [ ] Configure to fail on high/critical findings
- [ ] Add SAST to PR checks

**Test**: Intentional vulnerability is detected

---

## Phase 7: Documentation

### T060: Create architecture diagrams
**Status**: pending
**Priority**: P3
**File**: `docs/architecture/`

- [ ] Create system overview diagram (Mermaid or draw.io)
- [ ] Create data flow sequence diagram
- [ ] Create memory architecture diagram
- [ ] Create planner flow diagram

**Test**: Diagrams render correctly in GitHub

---

### T061: Document benchmarks
**Status**: pending
**Priority**: P3
**File**: `docs/benchmarks.md`
**Depends**: T051

- [ ] Run and document STT latency benchmarks
- [ ] Run and document intent accuracy benchmarks
- [ ] Run and document memory retrieval benchmarks
- [ ] Include methodology and hardware specs

**Test**: Benchmarks are reproducible

---

### T062: Create audio examples
**Status**: pending
**Priority**: P3
**File**: `docs/examples/`
**Depends**: T050

- [ ] Select representative audio examples
- [ ] Document expected behavior for each
- [ ] Include multi-turn conversation examples
- [ ] Add troubleshooting examples (noisy, accented)

**Test**: Examples demonstrate key capabilities

---

### T063: Update quickstart guide
**Status**: pending
**Priority**: P3
**File**: `docs/quickstart.md`

- [ ] Update installation instructions for new dependencies
- [ ] Add semantic memory setup steps
- [ ] Add tool configuration instructions
- [ ] Verify <10 minute setup time

**Test**: Fresh install following guide succeeds

---

## Summary

| Phase | Tasks | Priority | Status |
|-------|-------|----------|--------|
| 1. Audio Preprocessing | T001-T005 | P1/P2 | Pending |
| 2. Semantic Memory | T010-T017 | P1/P2 | Pending |
| 3. Enhanced NLU | T020-T026 | P1/P2 | Pending |
| 4. Agentic Planner | T030-T036 | P1 | Pending |
| 5. Observability | T040-T043 | P2 | Pending |
| 6. Testing & CI | T050-T053 | P2 | Pending |
| 7. Documentation | T060-T063 | P3 | Pending |
