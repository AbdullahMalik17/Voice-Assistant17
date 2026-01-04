# Backend API Implementation

Complete FastAPI backend with WebSocket support for the Voice Assistant web interface.

## Table of Contents
1. [WebSocket Server](#websocket-server)
2. [Audio Processing](#audio-processing)
3. [REST Endpoints](#rest-endpoints)
4. [Integration with Voice Assistant](#integration)

## WebSocket Server

### Full Implementation: `src/api/websocket_server.py`

```python
"""
WebSocket server for Voice Assistant web interface.
Handles real-time audio streaming and text chat.
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import asyncio
import json
import base64
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from enum import Enum

# Import Voice Assistant services
from services.stt import STTService
from services.llm import LLMService
from services.tts import TTSService
from services.intent import IntentClassifier
from memory.semantic_memory import SemanticMemory
from memory.dialogue_state import DialogueStateManager
from agents.planner import AgenticPlanner
from agents.guardrails import SafetyGuardrails
from core.config import load_config

class MessageType(str, Enum):
    TEXT = "text"
    AUDIO = "audio"
    AUDIO_STREAM = "audio_stream"
    SYSTEM = "system"
    ERROR = "error"
    RESPONSE = "response"
    AUDIO_RESPONSE = "audio_response"
    STATUS = "status"

@dataclass
class WebSocketMessage:
    type: MessageType
    content: Any
    session_id: str
    timestamp: str = None
    metadata: Optional[Dict] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> dict:
        return asdict(self)

class SessionManager:
    """Manages WebSocket sessions and their state."""

    def __init__(self):
        self.sessions: Dict[str, dict] = {}
        self.connections: Dict[str, WebSocket] = {}

    def create_session(self, websocket: WebSocket) -> str:
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "created_at": datetime.utcnow(),
            "messages": [],
            "context": {}
        }
        self.connections[session_id] = websocket
        return session_id

    def get_session(self, session_id: str) -> Optional[dict]:
        return self.sessions.get(session_id)

    def remove_session(self, session_id: str):
        self.sessions.pop(session_id, None)
        self.connections.pop(session_id, None)

    async def send_to_session(self, session_id: str, message: WebSocketMessage):
        if websocket := self.connections.get(session_id):
            await websocket.send_json(message.to_dict())

class VoiceAssistantHandler:
    """Handles Voice Assistant processing for WebSocket requests."""

    def __init__(self, config):
        self.config = config
        self.stt = STTService(config)
        self.llm = LLMService(config)
        self.tts = TTSService(config)
        self.intent = IntentClassifier(config)
        self.memory = SemanticMemory(config)
        self.dialogue = DialogueStateManager(self.memory)
        self.planner = AgenticPlanner(self.llm)
        self.guardrails = SafetyGuardrails(config)

    async def process_text(self, text: str, session_id: str) -> dict:
        """Process text input and return response."""
        # Classify intent
        intent_result = await asyncio.to_thread(
            self.intent.classify, text
        )

        # Get context from memory
        context = self.dialogue.retrieve_context(session_id, text)

        # Generate response
        response = await asyncio.to_thread(
            self.llm.generate,
            text,
            context=context,
            intent=intent_result
        )

        # Update dialogue state
        self.dialogue.update_session(session_id, text, response)

        return {
            "text": response,
            "intent": intent_result.intent_type if intent_result else "unknown",
            "confidence": intent_result.confidence if intent_result else 0.0
        }

    async def process_audio(self, audio_bytes: bytes, session_id: str) -> dict:
        """Process audio input and return response with optional TTS."""
        # Transcribe audio
        transcription = await asyncio.to_thread(
            self.stt.transcribe_with_result, audio_bytes
        )

        if not transcription.text:
            return {"error": "Could not transcribe audio", "text": ""}

        # Process as text
        response = await self.process_text(transcription.text, session_id)
        response["transcription"] = transcription.text
        response["stt_confidence"] = transcription.confidence

        # Generate TTS if enabled
        if self.config.tts.enabled:
            audio_response = await asyncio.to_thread(
                self.tts.synthesize, response["text"]
            )
            response["audio"] = base64.b64encode(audio_response).decode()

        return response

# Global instances
session_manager = SessionManager()
handler: Optional[VoiceAssistantHandler] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup."""
    global handler
    config = load_config()
    handler = VoiceAssistantHandler(config)
    yield
    # Cleanup on shutdown

app = FastAPI(
    title="Voice Assistant API",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws/voice")
async def websocket_voice_endpoint(websocket: WebSocket):
    """WebSocket endpoint for voice/text communication."""
    await websocket.accept()
    session_id = session_manager.create_session(websocket)

    # Send session info
    await websocket.send_json(
        WebSocketMessage(
            type=MessageType.SYSTEM,
            content={"message": "Connected", "session_id": session_id},
            session_id=session_id
        ).to_dict()
    )

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "text")
            content = data.get("content", "")

            if msg_type == "text":
                response = await handler.process_text(content, session_id)
                await websocket.send_json(
                    WebSocketMessage(
                        type=MessageType.RESPONSE,
                        content=response,
                        session_id=session_id
                    ).to_dict()
                )

            elif msg_type == "audio":
                # Decode base64 audio
                audio_bytes = base64.b64decode(content)
                response = await handler.process_audio(audio_bytes, session_id)

                msg_type = MessageType.AUDIO_RESPONSE if "audio" in response else MessageType.RESPONSE
                await websocket.send_json(
                    WebSocketMessage(
                        type=msg_type,
                        content=response,
                        session_id=session_id
                    ).to_dict()
                )

            elif msg_type == "ping":
                await websocket.send_json(
                    WebSocketMessage(
                        type=MessageType.STATUS,
                        content={"status": "pong"},
                        session_id=session_id
                    ).to_dict()
                )

    except WebSocketDisconnect:
        session_manager.remove_session(session_id)
    except Exception as e:
        await websocket.send_json(
            WebSocketMessage(
                type=MessageType.ERROR,
                content={"error": str(e)},
                session_id=session_id
            ).to_dict()
        )
        session_manager.remove_session(session_id)

# REST Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "2.0.0"}

@app.post("/api/chat")
async def chat_endpoint(request: dict):
    """REST endpoint for text chat (non-WebSocket)."""
    text = request.get("text", "")
    session_id = request.get("session_id", str(uuid.uuid4()))

    if not text:
        raise HTTPException(status_code=400, detail="Text is required")

    response = await handler.process_text(text, session_id)
    return JSONResponse(content=response)

@app.post("/api/transcribe")
async def transcribe_endpoint(request: dict):
    """Transcribe audio to text."""
    audio_b64 = request.get("audio", "")

    if not audio_b64:
        raise HTTPException(status_code=400, detail="Audio is required")

    audio_bytes = base64.b64decode(audio_b64)
    result = await asyncio.to_thread(handler.stt.transcribe_with_result, audio_bytes)

    return {
        "text": result.text,
        "confidence": result.confidence
    }
```

## Running the Server

```bash
# Development
uvicorn src.api.websocket_server:app --reload --host 0.0.0.0 --port 8000

# Production
gunicorn src.api.websocket_server:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## Environment Variables

```bash
# Required for production
CORS_ORIGINS=https://yourdomain.com
API_HOST=0.0.0.0
API_PORT=8000
```
