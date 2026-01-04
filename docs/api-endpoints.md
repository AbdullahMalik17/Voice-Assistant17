# API Endpoints Documentation

## Overview

The voice assistant provides REST API endpoints for programmatic access to its features, including chat functionality, voice processing, and memory operations.

## Base URL

```
http://localhost:8000
```

## Endpoints

### Chat API

#### POST `/api/chat`

Send a text message and receive a response from the voice assistant.

**Request:**
```json
{
    "text": "Hello, how are you?",
    "user_id": "optional_user_identifier"
}
```

**Parameters:**
- `text` (string, required): The message text to send
- `user_id` (string, optional): User identifier for persistent memory across sessions

**Response:**
```json
{
    "text": "Response from the assistant",
    "intent": "unknown|informational|task|conversational",
    "confidence": 0.85,
    "audio": "base64_encoded_audio_data" // Present if TTS is enabled
}
```

**Example Request:**
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"text":"What time is it?", "user_id":"user_123"}'
```

**Example Response:**
```json
{
    "text": "The current time is 2:30 PM.",
    "intent": "informational",
    "confidence": 0.92,
    "audio": "UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoAAAAA..."
}
```

### Health Check

#### GET `/health`

Check the health status of the voice assistant API.

**Response:**
```json
{
    "status": "healthy",
    "timestamp": "2026-01-03T15:30:00Z",
    "services": {
        "stt": true,
        "llm": true,
        "tts": true,
        "memory": true,
        "agents": true
    }
}
```

### Audio Processing (Future)

#### POST `/api/transcribe` (Coming Soon)

Transcribe audio data to text.

**Request:**
```json
{
    "audio": "base64_encoded_audio_data",
    "format": "mp3|wav|pcm"
}
```

### Memory Operations (Coming Soon)

#### GET `/api/memory/{user_id}`

Retrieve user's memory history.

**Response:**
```json
{
    "memories": [
        {
            "id": "memory_id",
            "user_message": "User message",
            "assistant_response": "Assistant response",
            "timestamp": "2026-01-03T15:30:00Z",
            "metadata": {
                "intent": "informational",
                "confidence": 0.85
            }
        }
    ]
}
```

## WebSocket Endpoints

### Voice Chat WebSocket

#### WebSocket `/ws/voice`

Real-time voice communication with the assistant.

**Connection:**
```
ws://localhost:8000/ws/voice
```

**Message Format:**
- **Text Messages:** JSON objects for text input/output
- **Binary Messages:** Audio data for voice input/output

**Text Message Types:**
1. **Input:** `{ "type": "text", "content": "Hello" }`
2. **Response:** `{ "type": "response", "content": { "text": "Hi there", "intent": "greeting", "confidence": 0.95 } }`
3. **Audio Response:** `{ "type": "audio_response", "content": { "text": "Hi there", "audio": "base64_data", "intent": "greeting", "confidence": 0.95 } }`
4. **System:** `{ "type": "system", "content": { "message": "Connected" } }`
5. **Error:** `{ "type": "error", "content": { "error": "Error message" } }`

## Authentication

The API endpoints do not require authentication for basic usage. For production deployments, authentication can be added through middleware.

## Rate Limiting

The API is subject to rate limits from external services:
- Gemini API: 20 requests per day for free tier
- ElevenLabs TTS: API-specific limits
- Mem0: Rate limits based on plan

## Error Handling

### Common Error Responses

**400 Bad Request:**
```json
{
    "detail": "Text is required"
}
```

**429 Too Many Requests:**
```json
{
    "detail": "Rate limit exceeded for external service"
}
```

**500 Internal Server Error:**
```json
{
    "detail": "Internal server error occurred"
}
```

## Headers

- **Content-Type**: `application/json` for JSON requests
- **Accept**: `application/json` for JSON responses

## Web Interface Integration

The web interface uses these endpoints to communicate with the backend:
- `/api/chat` for text-based conversations
- `/ws/voice` for real-time voice communication
- `/health` for connection status checking

## Session Management

- Each WebSocket connection creates a unique session ID
- REST API endpoints can use provided `user_id` for persistent memory
- Session data is maintained for the duration of the connection
- Memory persistence across sessions requires consistent `user_id`

## Examples

### Simple Chat
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello, world!"}'
```

### Chat with Memory
```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"text":"Remember my favorite color is blue", "user_id":"john_doe_123"}'

curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"text":"What did I tell you about my favorite color?", "user_id":"john_doe_123"}'
```

### Health Check
```bash
curl http://localhost:8000/health
```