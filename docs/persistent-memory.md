# Persistent Memory System

## Overview

The voice assistant includes a persistent memory system powered by Mem0 that stores and retrieves user conversation history across sessions. This enables the assistant to remember user preferences, past interactions, and provide personalized responses.

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   User Input    │───▶│ Memory Service  │───▶│  Mem0 Cloud     │
│                 │    │                 │    │                 │
│ - User message  │    │ - Add            │    │ - Store         │
│ - Assistant     │    │ - Search         │    │ - Retrieve      │
│   response      │    │ - Context        │    │ - Semantic      │
└─────────────────┘    │   injection      │    │   search        │
                       └──────────────────┘    └─────────────────┘
```

## Components

### PersistentMemoryService (`src/services/persistent_memory.py`)

The main memory service that handles all persistent memory operations:

- **Initialization**: Connects to Mem0 cloud API using API key
- **Storage**: Stores user/assistant conversation pairs
- **Retrieval**: Semantic search for relevant memories
- **Context Injection**: Formats memories for LLM context

### Memory Storage

Each conversation is stored as a pair of messages:
```python
messages = [
    {"role": "user", "content": user_message},
    {"role": "assistant", "content": assistant_response}
]
```

Additional metadata includes:
- Intent type and confidence scores
- Timestamps
- Session information

### Memory Retrieval

Uses semantic search to find relevant memories:
- **Query-based**: Searches based on current user query
- **User-scoped**: Filters by user_id for privacy
- **Context-aware**: Returns most relevant memories for current conversation

## API Integration

### Chat Endpoint Enhancement

The `/api/chat` endpoint now accepts an optional `user_id` parameter:

```json
{
    "text": "Hello, how are you?",
    "user_id": "user_12345"
}
```

- If `user_id` provided: Uses persistent memory across sessions
- If no `user_id`: Falls back to session-based memory

### Context Injection Process

1. Retrieve relevant memories based on current query
2. Format memories into context string
3. Inject context into LLM prompt
4. Generate response considering past context
5. Store new conversation in persistent memory

## Configuration

### Environment Variables

Add to `.env`:
```
MEM0_API_KEY=your-mem0-api-key
```

### Memory Service Configuration

The service automatically uses the API key from environment variables:

```python
# In persistent_memory.py
api_key = os.getenv("MEM0_API_KEY")
```

## Usage Examples

### With Persistent Memory
```bash
# First conversation - stores user information
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"text":"My name is Alice and I love hiking", "user_id":"alice_123"}'

# Later conversation - retrieves context
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"text":"What did I tell you about myself?", "user_id":"alice_123"}'
```

### Without Persistent Memory
```bash
# Uses session-based memory only
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"text":"Hello there"}'
```

## Web Interface Integration

The web interface automatically passes a consistent session ID for WebSocket connections, enabling memory persistence within a browser session. For cross-session persistence, the web interface can be enhanced to use user authentication.

## Benefits

- **Personalization**: Assistant remembers user preferences and history
- **Context Awareness**: Conversations build on previous interactions
- **Scalability**: Cloud-based storage handles large volumes
- **Privacy**: Memories are scoped to individual users
- **Flexibility**: Optional feature that doesn't break existing functionality

## Error Handling

- Graceful degradation if Mem0 API unavailable
- Fallback to semantic memory if persistent memory fails
- Proper logging for debugging memory operations
- Rate limiting awareness for API quotas

## Best Practices

1. **User ID Consistency**: Use consistent user_id across sessions
2. **Memory Limits**: Configure appropriate memory limits to avoid context bloat
3. **Privacy**: Ensure user consent for memory storage
4. **Testing**: Test with both persistent and non-persistent scenarios