# API Contracts: Voice Assistant Baseline

This directory contains OpenAPI specifications for the internal service interfaces of the Voice Assistant system.

## Service Contracts

### 1. Wake Word Service (`wake-word-service.yaml`)
- **Purpose**: Continuous audio monitoring for wake word detection
- **Input**: Audio stream from microphone
- **Output**: Wake word detection events
- **Key Operations**:
  - `POST /detect` - Submit audio chunk for wake word detection
  - `GET /status` - Check service health and sensitivity settings
  - `PUT /sensitivity` - Adjust detection sensitivity

### 2. Speech-to-Text Service (`stt-service.yaml`)
- **Purpose**: Convert speech audio to text
- **Input**: Audio buffer (WAV format)
- **Output**: Transcribed text with confidence score
- **Key Operations**:
  - `POST /transcribe` - Transcribe audio to text
  - `POST /transcribe/stream` - Streaming transcription
  - `GET /models` - List available STT models (local vs API)

### 3. Intent Classification Service (`intent-service.yaml`)
- **Purpose**: Classify user requests and extract entities
- **Input**: Transcribed text
- **Output**: Intent type, entities, confidence
- **Key Operations**:
  - `POST /classify` - Classify intent from text
  - `POST /extract-entities` - Extract entities from text
  - `GET /intent-types` - List supported intent types

### 4. LLM Service (`llm-service.yaml`)
- **Purpose**: Generate responses to queries
- **Input**: Intent + conversation context
- **Output**: Response text
- **Key Operations**:
  - `POST /query` - Generate response for query
  - `POST /query/streaming` - Streaming response generation
  - `GET /models` - List available LLM models (Gemini API vs Ollama)

### 5. Text-to-Speech Service (`tts-service.yaml`)
- **Purpose**: Convert text to spoken audio
- **Input**: Response text
- **Output**: Audio stream (MP3/WAV)
- **Key Operations**:
  - `POST /synthesize` - Convert text to speech
  - `POST /synthesize/stream` - Streaming audio output
  - `GET /voices` - List available voices

### 6. Action Executor Service (`action-executor-service.yaml`)
- **Purpose**: Execute system commands and scripts
- **Input**: Action type + parameters
- **Output**: Execution result + status
- **Key Operations**:
  - `POST /execute` - Execute action script
  - `GET /actions` - List available actions
  - `GET /system-status` - Retrieve system status

## Contract Standards

All contracts follow these conventions:

**Common Headers**:
```yaml
X-Request-ID: UUID for tracing
X-Correlation-ID: Session identifier
Authorization: Bearer token (if required)
```

**Standard Error Format**:
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable description",
    "details": {},
    "timestamp": "2026-01-01T12:00:00Z"
  }
}
```

**Standard Success Format**:
```json
{
  "data": { ... },
  "metadata": {
    "request_id": "uuid",
    "processing_time_ms": 123,
    "model_used": "model-name"
  }
}
```

## Service Communication

Services communicate via:
1. **HTTP/REST** - For request/response patterns
2. **Event Bus** (future) - For asynchronous events
3. **Shared Memory** - For low-latency audio streaming (local only)

## Testing

Contract tests validate:
- Request/response schema compliance
- Error handling behavior
- Performance SLAs (latency, throughput)
- Fallback behavior (cloud to local)

Run contract tests:
```bash
pytest tests/contract/
```

## OpenAPI Specification Generation

Full OpenAPI 3.0 specifications will be generated for each service during implementation phase. These contracts serve as the interface definition for service development and testing.
