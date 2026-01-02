# Tasks: Voice Assistant Baseline

**Input**: Design documents from `/specs/001-voice-assistant-baseline/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Tests are NOT included in this baseline implementation. Tasks focus on core functionality delivery.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

Single project structure:
- `src/` - Application code
- `tests/` - Test suites
- `config/` - Configuration files
- `scripts/` - Setup and utility scripts

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create project directory structure per plan.md (src/, tests/, config/, scripts/, logs/, data/)
- [ ] T002 Initialize Python 3.10+ virtual environment and install core dependencies (FastAPI, pytest)
- [ ] T003 [P] Create .env.template file in config/ with all required environment variables
- [ ] T004 [P] Create assistant_config.yaml in config/ with default configuration
- [ ] T005 [P] Create .gitignore file excluding logs/, data/, venv/, .env
- [ ] T006 [P] Create requirements.txt with all dependencies from research.md
- [ ] T007 [P] Create README.md with project overview and quickstart link
- [ ] T008 [P] Setup pytest configuration in pytest.ini
- [ ] T009 Create scripts/install_dependencies.sh for cross-platform dependency installation
- [ ] T010 Create scripts/setup_wake_word.sh for pvporcupine model setup

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T011 [P] Implement configuration management in src/core/config.py (load .env and YAML config)
- [ ] T012 [P] Implement event logging infrastructure in src/utils/logger.py (JSON structured logging with rotation)
- [ ] T013 [P] Implement audio utilities in src/utils/audio_utils.py (PyAudio + sounddevice wrapper)
- [ ] T014 [P] Create base VoiceCommand model in src/models/voice_command.py
- [ ] T015 [P] Create Intent model in src/models/intent.py
- [ ] T016 [P] Create ConversationContext model in src/models/conversation_context.py
- [ ] T017 [P] Create EventLog model in src/models/event_log.py
- [ ] T018 [P] Implement in-memory storage in src/storage/memory_store.py
- [ ] T019 [P] Implement encrypted storage in src/storage/encrypted_store.py (Fernet + PBKDF2)
- [ ] T020 Implement network monitoring in src/utils/network_monitor.py (HTTP + DNS health checks)
- [ ] T021 Create RequestQueue model in src/models/request_queue.py with auto-retry logic

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Wake Word Activation (Priority: P1) 🎯 MVP

**Goal**: Enable hands-free assistant activation using "Hey Assistant" wake word with spoken confirmation

**Independent Test**: Speak "Hey Assistant" in quiet room and from 3 meters away; verify activation within 1 second with audio confirmation; verify normal speech doesn't trigger

### Implementation for User Story 1

- [ ] T022 [P] [US1] Install pvporcupine dependency and wake word models via scripts/setup_wake_word.sh
- [ ] T023 [P] [US1] Implement wake word detection service in src/services/wake_word.py (pvporcupine integration)
- [ ] T024 [P] [US1] Implement TTS service in src/services/tts.py (ElevenLabs API + Piper fallback)
- [ ] T025 [US1] Integrate wake word detector with audio input stream in src/services/wake_word.py
- [ ] T026 [US1] Add wake word sensitivity configuration to config/assistant_config.yaml
- [ ] T027 [US1] Implement spoken confirmation on wake word detection using TTS service
- [ ] T028 [US1] Add wake word detection event logging to EventLog
- [ ] T029 [US1] Create CLI entry point in src/cli/assistant.py (initialize services, start wake word loop)
- [ ] T030 [US1] Test wake word activation in quiet environment (manual validation)
- [ ] T031 [US1] Test wake word activation from 3 meters distance (manual validation)

**Checkpoint**: At this point, wake word activation with spoken confirmation should be fully functional

---

## Phase 4: User Story 2 - Intent Recognition and Response (Priority: P1)

**Goal**: Process user voice queries and provide spoken responses for informational, task-based, and conversational requests

**Independent Test**: After wake word activation, ask "What time is it?", "Tell me a joke", verify accurate spoken responses within 2 seconds

### Implementation for User Story 2

- [ ] T032 [P] [US2] Install Whisper and Gemini API dependencies
- [ ] T033 [P] [US2] Implement STT service in src/services/stt.py (Whisper local + OpenAI API fallback)
- [ ] T034 [P] [US2] Implement LLM service in src/services/llm.py (Gemini API + Ollama fallback)
- [ ] T035 [P] [US2] Implement intent classifier in src/services/intent_classifier.py (informational/task/conversational)
- [ ] T036 [US2] Integrate STT service with wake word activation trigger in src/cli/assistant.py
- [ ] T037 [US2] Implement audio recording after wake word detection (capture user query)
- [ ] T038 [US2] Connect STT output to intent classifier in src/cli/assistant.py
- [ ] T039 [US2] Route informational and conversational intents to LLM service
- [ ] T040 [US2] Connect LLM response to TTS service for spoken output
- [ ] T041 [US2] Add STT, LLM, and intent classification event logging
- [ ] T042 [US2] Implement error handling for speech recognition failures (FR-012)
- [ ] T043 [US2] Implement graceful degradation for network outages (FR-016)
- [ ] T044 [US2] Test informational query: "What time is it?" (manual validation)
- [ ] T045 [US2] Test conversational query: "Tell me a joke" (manual validation)
- [ ] T046 [US2] Test unclear question handling (manual validation)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work - complete voice query pipeline functional

---

## Phase 5: User Story 3 - Context-Aware Follow-Up Questions (Priority: P2)

**Goal**: Maintain 5-exchange conversation context to support follow-up questions without repeating information

**Independent Test**: Ask initial question, then follow-up without context (e.g., "weather today" then "what about tomorrow"); verify context maintained for 5 exchanges

### Implementation for User Story 3

- [ ] T047 [P] [US3] Implement context manager in src/core/context_manager.py (5-exchange FIFO queue)
- [ ] T048 [P] [US3] Implement 5-minute timeout tracking in context manager
- [ ] T049 [P] [US3] Implement topic keyword extraction in context manager
- [ ] T050 [US3] Integrate context manager with conversation flow in src/cli/assistant.py
- [ ] T051 [US3] Update LLM service to include conversation context in prompts
- [ ] T052 [US3] Implement context reset on topic shift detection
- [ ] T053 [US3] Implement context expiration on 5-minute timeout (FR-014)
- [ ] T054 [US3] Add conversation context persistence toggle (user-configurable, FR-018)
- [ ] T055 [US3] Implement encrypted context storage when persistence enabled (FR-020)
- [ ] T056 [US3] Add context management event logging
- [ ] T057 [US3] Test follow-up question: "weather today" → "what about tomorrow" (manual validation)
- [ ] T058 [US3] Test 5-exchange context limit (manual validation)
- [ ] T059 [US3] Test context timeout after 5 minutes inactivity (manual validation)

**Checkpoint**: All core voice interaction features (wake word, queries, context) should now be functional

---

## Phase 6: User Story 4 - Local Script and Action Execution (Priority: P2)

**Goal**: Execute system commands and launch applications via voice, with spoken confirmation

**Independent Test**: Say "Open Spotify" or "Check my CPU temp"; verify action executes and spoken confirmation provided

### Implementation for User Story 4

- [ ] T060 [P] [US4] Create ActionScript model in src/models/action_script.py
- [ ] T061 [P] [US4] Create SystemStatus model in src/models/system_status.py
- [ ] T062 [P] [US4] Implement action executor in src/services/action_executor.py (command parsing, validation)
- [ ] T063 [P] [US4] Implement system status retrieval in src/services/action_executor.py (CPU, memory, disk via psutil)
- [ ] T064 [P] [US4] Implement application launcher (cross-platform) in src/services/action_executor.py
- [ ] T065 [US4] Create action script registry with common commands in config/actions.yaml
- [ ] T066 [US4] Integrate action executor with task-based intent classification
- [ ] T067 [US4] Route task-based intents to action executor instead of LLM
- [ ] T068 [US4] Implement action execution confirmation via TTS (FR-008)
- [ ] T069 [US4] Implement cancellation support ("Stop" or "Cancel" commands, FR-011)
- [ ] T070 [US4] Add action execution event logging
- [ ] T071 [US4] Handle unavailable application errors (FR-009 scenario 3)
- [ ] T072 [US4] Test "Open Spotify" command (manual validation)
- [ ] T073 [US4] Test "Check CPU temp" command (manual validation)
- [ ] T074 [US4] Test cancellation with "Stop" command (manual validation)

**Checkpoint**: All user stories should now be independently functional - complete voice assistant baseline

---

## Phase 7: Cross-Cutting Concerns & Resilience

**Purpose**: Implement features that span multiple user stories

### Network Resilience (FR-025, FR-026, FR-027)

- [ ] T075 [P] Implement request queuing in src/core/request_queue.py for network outages
- [ ] T076 [P] Integrate network monitor with request queue (auto-retry on restore)
- [ ] T077 Implement "Waiting for connection" spoken notification on network loss
- [ ] T078 Add queued request processing on network restoration
- [ ] T079 Test offline mode: wake word and local commands work without internet (manual validation)
- [ ] T080 Test request queuing: ask online query while offline, verify processes when online (manual validation)

### Interruption Handling (FR-024)

- [ ] T081 Implement wake word interrupt handling during active processing
- [ ] T082 Implement task cancellation and state cleanup on interrupt
- [ ] T083 Test interruption: say wake word during LLM response, verify cancellation (manual validation)

### Configuration & Deployment

- [ ] T084 [P] Create deployment guide in docs/deployment.md
- [ ] T085 [P] Update quickstart.md with final installation and usage instructions
- [ ] T086 [P] Create troubleshooting guide in docs/troubleshooting.md
- [ ] T087 Test full quickstart.md flow on clean system (Windows, macOS, Linux validation)

---

## Phase 8: Polish & Finalization

**Purpose**: Final improvements and validation

- [ ] T088 [P] Code cleanup and refactoring for consistency
- [ ] T089 [P] Performance profiling and optimization (verify <3s wake-to-response)
- [ ] T090 [P] Security audit: verify no hardcoded secrets, proper encryption
- [ ] T091 [P] Accessibility validation: verify cross-platform audio compatibility
- [ ] T092 [P] Documentation review and updates
- [ ] T093 [P] Create example voice command reference in docs/commands.md
- [ ] T094 Validate all success criteria from spec.md (SC-001 through SC-010)
- [ ] T095 Run full system validation on Raspberry Pi 4 (performance within constraints)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - User Story 1 (P1): Can start after Foundational
  - User Story 2 (P1): Can start after Foundational
  - User Story 3 (P2): Can start after Foundational (integrates with US2 but independently testable)
  - User Story 4 (P2): Can start after Foundational (independently testable)
- **Cross-Cutting (Phase 7)**: Depends on core user stories being functional
- **Polish (Phase 8)**: Depends on all features being complete

### User Story Dependencies

- **User Story 1 (P1)**: No dependencies on other stories - pure wake word activation
- **User Story 2 (P1)**: No dependencies on other stories - uses US1 wake word but independently testable
- **User Story 3 (P2)**: Integrates with US2 LLM service but independently testable with context
- **User Story 4 (P2)**: Uses intent classification from US2 but independently testable

### Within Each User Story

- Install dependencies before implementation
- Models before services
- Services before integration
- Core implementation before error handling
- Functionality before logging

### Parallel Opportunities

**Setup Phase (Phase 1)**:
- Tasks T003, T004, T005, T006, T007, T008 can all run in parallel (different files)

**Foundational Phase (Phase 2)**:
- Tasks T011-T019 can all run in parallel (different files, no dependencies)

**After Foundational Phase Complete**:
- ALL user stories (US1, US2, US3, US4) can start in parallel if team capacity allows
- Within each user story, tasks marked [P] can run in parallel

**User Story 1 Parallel Tasks**:
- T022 (install), T023 (wake word service), T024 (TTS service) - can run in parallel

**User Story 2 Parallel Tasks**:
- T032 (install), T033 (STT service), T034 (LLM service), T035 (intent classifier) - can run in parallel

**User Story 3 Parallel Tasks**:
- T047 (context manager), T048 (timeout tracking), T049 (keyword extraction) - can run in parallel

**User Story 4 Parallel Tasks**:
- T060 (ActionScript model), T061 (SystemStatus model), T062-T064 (action executor components) - can run in parallel

**Cross-Cutting Phase**:
- T075 (request queue), T076 (network integration) can run in parallel

**Polish Phase**:
- Tasks T088-T093 can all run in parallel (different concerns)

---

## Parallel Example: User Story 2

```bash
# Launch all models and services for User Story 2 together:
Task: "Install Whisper and Gemini API dependencies"
Task: "Implement STT service in src/services/stt.py"
Task: "Implement LLM service in src/services/llm.py"
Task: "Implement intent classifier in src/services/intent_classifier.py"

# These can be developed in parallel by different developers
# Once all complete, proceed with integration tasks (T036-T040)
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (Wake Word Activation)
4. Complete Phase 4: User Story 2 (Intent Recognition and Response)
5. **STOP and VALIDATE**: Test end-to-end voice interaction independently
6. Deploy/demo basic voice assistant MVP

**MVP Deliverable**: Voice assistant that activates on "Hey Assistant" and answers questions

### Incremental Delivery

1. **Foundation** (Phases 1-2): Setup + Foundational → Infrastructure ready
2. **MVP** (Phases 3-4): User Stories 1+2 → Basic voice assistant working → Deploy/Demo
3. **Enhanced** (Phase 5): Add User Story 3 → Context-aware conversations → Deploy/Demo
4. **Complete** (Phase 6): Add User Story 4 → System control capabilities → Deploy/Demo
5. **Production** (Phases 7-8): Resilience + Polish → Production-ready → Final deployment

Each phase adds value without breaking previous functionality.

### Parallel Team Strategy

With multiple developers:

1. **Week 1**: Entire team completes Setup + Foundational together (Phases 1-2)
2. **Week 2-3**: Once Foundational done, parallelize:
   - Developer A: User Story 1 (Wake Word)
   - Developer B: User Story 2 (Intent Recognition)
   - Developer C: User Story 3 (Context Management)
   - Developer D: User Story 4 (Action Execution)
3. **Week 4**: Integrate and test all stories together
4. **Week 5**: Cross-cutting concerns and polish (Phases 7-8)

Stories complete and integrate independently.

---

## Task Summary

**Total Tasks**: 95 tasks
- **Phase 1 (Setup)**: 10 tasks
- **Phase 2 (Foundational)**: 11 tasks (BLOCKING)
- **Phase 3 (US1 - Wake Word)**: 10 tasks
- **Phase 4 (US2 - Intent Recognition)**: 15 tasks
- **Phase 5 (US3 - Context Management)**: 13 tasks
- **Phase 6 (US4 - Action Execution)**: 15 tasks
- **Phase 7 (Cross-Cutting)**: 13 tasks
- **Phase 8 (Polish)**: 8 tasks

**Parallel Opportunities**: 42 tasks marked [P] can run in parallel within their phases

**Independent Test Criteria**:
- **US1**: Wake word activates within 1s with spoken confirmation
- **US2**: Voice queries answered with spoken responses within 2s
- **US3**: Follow-up questions work without repeating context (5 exchanges)
- **US4**: System commands execute with spoken confirmation

**Suggested MVP Scope**: Phases 1-4 (User Stories 1+2) = 46 tasks

---

## Notes

- **[P] tasks**: Different files, no dependencies - can run in parallel
- **[Story] label**: Maps task to specific user story for traceability
- **Each user story**: Independently completable and testable
- **Checkpoints**: Validate story independence before moving to next
- **Commits**: Commit after each logical task or group
- **Testing**: Manual validation specified for each user story (automated tests not in baseline scope)
- **Avoid**: Cross-story dependencies that break independence, vague tasks, same-file conflicts

**Tests are NOT included** per baseline specification - focus is on core functionality delivery with manual validation.
