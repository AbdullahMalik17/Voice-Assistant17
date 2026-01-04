# Web Interface Documentation

## Overview

The voice assistant includes a modern web interface built with Next.js 14 that provides real-time chat functionality with both text and voice capabilities. The interface connects to the backend via WebSocket for real-time communication and REST API for additional functionality.

## Architecture

```
┌─────────────────┐    WebSocket     ┌──────────────────┐
│   Web UI       │◄────────────────►│  Backend API    │
│                │                  │                 │
│ - Next.js 14   │    REST API      │ - FastAPI       │
│ - React 18     │◄────────────────►│ - WebSockets    │
│ - TypeScript   │                  │ - Memory Service│
│ - Tailwind CSS │                  │ - STT/TTS/LLM   │
└─────────────────┘                  └──────────────────┘
```

## Features

### Real-time Chat
- WebSocket-based bidirectional communication
- Live message updates with connection status indicators
- Message history with timestamps

### Voice Capabilities
- Push-to-talk voice recording (space bar)
- Real-time voice transmission to backend
- Automatic TTS playback of responses
- Manual speaker buttons for replaying audio

### User Interface
- Responsive design for desktop and mobile
- Clean, modern chat interface
- Visual feedback for recording state
- Connection status indicators
- Error handling and user feedback

## Components

### Core Components

#### ChatContainer (`web/src/components/chat/ChatContainer.tsx`)
- Main chat interface component
- Manages WebSocket connection
- Handles message state and UI updates
- Integrates with voice recording

#### MessageList (`web/src/components/chat/MessageList.tsx`)
- Displays message history
- Auto-scrolls to latest message
- Handles processing indicators

#### MessageBubble (`web/src/components/chat/MessageBubble.tsx`)
- Individual message display
- Audio playback controls
- Speaker/listen buttons
- Timestamps and metadata

#### ChatInput (`web/src/components/chat/ChatInput.tsx`)
- Text input field with send button
- Handles text message submission

#### PushToTalk (`web/src/components/voice/PushToTalk.tsx`)
- Voice recording interface
- Space bar activation
- Visual recording feedback
- Audio transmission to backend

### Hooks

#### useWebSocket (`web/src/hooks/useWebSocket.ts`)
- WebSocket connection management
- Automatic reconnection handling
- Message handling and state management
- Connection status tracking

## API Integration

### WebSocket Connection

The web interface connects to the backend via WebSocket:

```
ws://localhost:8000/ws/voice
```

### Message Types

#### Client to Server
- **Text Messages:** `{ "type": "text", "content": "message text" }`
- **Audio Messages:** Binary data (audio chunks)

#### Server to Client
- **Response:** `{ "type": "response", "content": { "text": "...", "intent": "...", "confidence": ... } }`
- **Audio Response:** `{ "type": "audio_response", "content": { "text": "...", "audio": "base64...", ... } }`
- **System Messages:** `{ "type": "system", "content": { ... } }`
- **Errors:** `{ "type": "error", "content": { ... } }`

### REST API Usage

The interface may also use REST endpoints for:
- Health checks: `GET /health`
- Chat: `POST /api/chat`
- Future features as needed

## User Experience

### Text Chat
1. Type message in input field
2. Press Enter or click Send button
3. Message appears in chat history
4. Response appears from assistant
5. Audio response automatically plays (if TTS enabled)

### Voice Chat
1. Hold Space bar to start recording
2. Speak your message
3. Release Space bar to send
4. Audio is transmitted to backend
5. Response appears in text and audio
6. Audio response automatically plays

### Audio Playback
1. Assistant responses include audio by default
2. Auto-play when received
3. Manual replay with speaker button
4. Visual feedback during playback

## Configuration

### Environment Variables

The web interface uses environment variables from `.env.local`:

```
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/voice
```

### WebSocket URL

Default WebSocket URL is `ws://localhost:8000/ws/voice` but can be configured via environment variable.

## Error Handling

### Connection Issues
- Visual connection status indicators
- Automatic reconnection attempts
- User feedback for connection problems
- Graceful degradation when disconnected

### Audio Issues
- Fallback to text-only when audio fails
- Error messages for audio playback issues
- Manual retry options

### API Errors
- Display error messages to user
- Maintain chat history during errors
- Allow retry of failed operations

## Performance

### Optimizations
- Efficient WebSocket message handling
- Lazy loading of chat history
- Optimized audio playback
- Minimal re-renders with React hooks

### Responsive Design
- Mobile-friendly layout
- Touch-friendly controls
- Adaptive sizing for different screens

## Development

### Running the Web Interface

```bash
cd web
npm install
npm run dev
```

Interface will be available at `http://localhost:3000` (or 3001 if 3000 is busy).

### Building for Production

```bash
npm run build
npm start
```

## Integration with Backend

### Memory Persistence
- WebSocket sessions maintain connection-based memory
- REST API calls can use user_id for cross-session persistence
- Automatic context injection for personalized responses

### Voice Processing
- Audio captured via browser MediaRecorder API
- Transmitted via WebSocket to backend
- Processed by STT → LLM → TTS pipeline
- Response audio played back in browser

## Security Considerations

- No sensitive data stored in browser
- WebSocket connections secured in production
- Audio data processed server-side
- Input validation on backend

## Future Enhancements

- User authentication
- Persistent chat history
- Multiple conversation threads
- Enhanced voice controls
- Accessibility improvements