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
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict, field
from enum import Enum
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import Voice Assistant services
try:
    from services.stt import STTService
    from services.llm import LLMService
    from services.tts import TTSService
    from services.intent import IntentClassifier
    from core.config import load_config
    SERVICES_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Some services not available: {e}")
    SERVICES_AVAILABLE = False

# Optional imports for enhanced features
try:
    from memory.semantic_memory import SemanticMemory
    from memory.dialogue_state import DialogueStateManager
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False

try:
    from agents.planner import AgenticPlanner
    from agents.guardrails import SafetyGuardrails
    AGENTS_AVAILABLE = True
except ImportError:
    AGENTS_AVAILABLE = False


class MessageType(str, Enum):
    """Types of WebSocket messages."""
    TEXT = "text"
    AUDIO = "audio"
    AUDIO_STREAM = "audio_stream"
    SYSTEM = "system"
    ERROR = "error"
    RESPONSE = "response"
    AUDIO_RESPONSE = "audio_response"
    STATUS = "status"
    TYPING = "typing"


@dataclass
class WebSocketMessage:
    """Structured WebSocket message."""
    type: MessageType
    content: Any
    session_id: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Optional[Dict] = None

    def to_dict(self) -> dict:
        return {
            "type": self.type.value if isinstance(self.type, MessageType) else self.type,
            "content": self.content,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }


class SessionManager:
    """Manages WebSocket sessions and their state."""

    def __init__(self):
        self.sessions: Dict[str, dict] = {}
        self.connections: Dict[str, WebSocket] = {}

    def create_session(self, websocket: WebSocket) -> str:
        """Create a new session for a WebSocket connection."""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "created_at": datetime.utcnow(),
            "messages": [],
            "context": {},
            "last_activity": datetime.utcnow()
        }
        self.connections[session_id] = websocket
        logger.info(f"Created session: {session_id}")
        return session_id

    def get_session(self, session_id: str) -> Optional[dict]:
        """Get session data by ID."""
        return self.sessions.get(session_id)

    def update_activity(self, session_id: str):
        """Update last activity timestamp for a session."""
        if session_id in self.sessions:
            self.sessions[session_id]["last_activity"] = datetime.utcnow()

    def add_message(self, session_id: str, role: str, content: str):
        """Add a message to session history."""
        if session_id in self.sessions:
            self.sessions[session_id]["messages"].append({
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow().isoformat()
            })

    def get_context(self, session_id: str, max_messages: int = 10) -> List[dict]:
        """Get recent conversation context for a session."""
        if session_id in self.sessions:
            return self.sessions[session_id]["messages"][-max_messages:]
        return []

    def remove_session(self, session_id: str):
        """Remove a session and its connection."""
        self.sessions.pop(session_id, None)
        self.connections.pop(session_id, None)
        logger.info(f"Removed session: {session_id}")

    async def send_to_session(self, session_id: str, message: WebSocketMessage):
        """Send a message to a specific session."""
        if websocket := self.connections.get(session_id):
            try:
                await websocket.send_json(message.to_dict())
            except Exception as e:
                logger.error(f"Failed to send message to session {session_id}: {e}")

    def get_active_sessions_count(self) -> int:
        """Get the count of active sessions."""
        return len(self.connections)


class VoiceAssistantHandler:
    """Handles Voice Assistant processing for WebSocket requests."""

    def __init__(self, config):
        self.config = config
        self.stt = None
        self.llm = None
        self.tts = None
        self.intent = None
        self.memory = None
        self.dialogue = None
        self.planner = None
        self.guardrails = None

        # Initialize available services
        if SERVICES_AVAILABLE:
            try:
                self.stt = STTService(config)
                self.llm = LLMService(config)
                self.tts = TTSService(config)
                self.intent = IntentClassifier(config)
                logger.info("Core services initialized")
            except Exception as e:
                logger.error(f"Failed to initialize core services: {e}")

        if MEMORY_AVAILABLE:
            try:
                self.memory = SemanticMemory(config)
                self.dialogue = DialogueStateManager(self.memory)
                logger.info("Memory services initialized")
            except Exception as e:
                logger.warning(f"Memory services not available: {e}")

        if AGENTS_AVAILABLE and self.llm:
            try:
                self.planner = AgenticPlanner(self.llm)
                self.guardrails = SafetyGuardrails(config)
                logger.info("Agent services initialized")
            except Exception as e:
                logger.warning(f"Agent services not available: {e}")

    async def process_text(self, text: str, session_id: str, context: List[dict] = None) -> dict:
        """Process text input and return response."""
        try:
            # Classify intent if available
            intent_result = None
            if self.intent:
                intent_result = await asyncio.to_thread(
                    self.intent.classify, text
                )

            # Get context from memory if available
            memory_context = None
            if self.dialogue:
                memory_context = self.dialogue.retrieve_context(session_id, text)

            # Build context string
            context_str = ""
            if context:
                context_str = "\n".join([
                    f"{msg['role']}: {msg['content']}"
                    for msg in context[-5:]
                ])
            if memory_context:
                context_str += "\n" + str(memory_context)

            # Generate response
            if self.llm:
                response = await asyncio.to_thread(
                    self.llm.generate,
                    text,
                    context=context_str if context_str else None
                )
            else:
                response = f"Echo: {text} (LLM service not available)"

            # Update dialogue state if available
            if self.dialogue:
                self.dialogue.update_session(session_id, text, response)

            return {
                "text": response,
                "intent": intent_result.intent_type if intent_result else "unknown",
                "confidence": intent_result.confidence if intent_result else 0.0
            }

        except Exception as e:
            logger.error(f"Error processing text: {e}")
            return {
                "text": f"I apologize, but I encountered an error: {str(e)}",
                "intent": "error",
                "confidence": 0.0,
                "error": str(e)
            }

    async def process_audio(self, audio_bytes: bytes, session_id: str, context: List[dict] = None) -> dict:
        """Process audio input and return response with optional TTS."""
        try:
            if not self.stt:
                return {"error": "STT service not available", "text": ""}

            # Transcribe audio
            transcription = await asyncio.to_thread(
                self.stt.transcribe_with_result, audio_bytes
            )

            if not transcription.text:
                return {
                    "error": "Could not transcribe audio",
                    "text": "",
                    "transcription": ""
                }

            # Process as text
            response = await self.process_text(transcription.text, session_id, context)
            response["transcription"] = transcription.text
            response["stt_confidence"] = transcription.confidence

            # Generate TTS if available and enabled
            if self.tts and hasattr(self.config, 'tts') and self.config.tts.enabled:
                try:
                    audio_response = await asyncio.to_thread(
                        self.tts.synthesize, response["text"]
                    )
                    if audio_response:
                        response["audio"] = base64.b64encode(audio_response).decode()
                except Exception as e:
                    logger.warning(f"TTS synthesis failed: {e}")

            return response

        except Exception as e:
            logger.error(f"Error processing audio: {e}")
            return {
                "error": str(e),
                "text": "I apologize, but I couldn't process your audio.",
                "transcription": ""
            }


# Global instances
session_manager = SessionManager()
handler: Optional[VoiceAssistantHandler] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup, cleanup on shutdown."""
    global handler

    logger.info("Starting Voice Assistant API server...")

    # Load configuration
    try:
        if SERVICES_AVAILABLE:
            config = load_config()
        else:
            config = None
        handler = VoiceAssistantHandler(config)
        logger.info("Voice Assistant handler initialized")
    except Exception as e:
        logger.error(f"Failed to initialize handler: {e}")
        handler = VoiceAssistantHandler(None)

    yield

    # Cleanup on shutdown
    logger.info("Shutting down Voice Assistant API server...")


# Create FastAPI app
app = FastAPI(
    title="Voice Assistant API",
    description="WebSocket and REST API for Voice Assistant",
    version="2.0.0",
    lifespan=lifespan
)

# Configure CORS
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.websocket("/ws/voice")
async def websocket_voice_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time voice/text communication."""
    await websocket.accept()
    session_id = session_manager.create_session(websocket)

    try:
        # Send session info
        await websocket.send_json(
            WebSocketMessage(
                type=MessageType.SYSTEM,
                content={"message": "Connected", "session_id": session_id},
                session_id=session_id
            ).to_dict()
        )
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type", "text")
            content = data.get("content", "")

            session_manager.update_activity(session_id)

            # Send typing indicator
            await websocket.send_json(
                WebSocketMessage(
                    type=MessageType.TYPING,
                    content={"status": "processing"},
                    session_id=session_id
                ).to_dict()
            )

            if msg_type == "text":
                # Get conversation context
                context = session_manager.get_context(session_id)

                # Process text
                response = await handler.process_text(content, session_id, context)

                # Store messages
                session_manager.add_message(session_id, "user", content)
                session_manager.add_message(session_id, "assistant", response["text"])

                await websocket.send_json(
                    WebSocketMessage(
                        type=MessageType.RESPONSE,
                        content=response,
                        session_id=session_id
                    ).to_dict()
                )

            elif msg_type == "audio":
                # Decode base64 audio
                try:
                    audio_bytes = base64.b64decode(content)
                except Exception as e:
                    await websocket.send_json(
                        WebSocketMessage(
                            type=MessageType.ERROR,
                            content={"error": f"Invalid audio data: {e}"},
                            session_id=session_id
                        ).to_dict()
                    )
                    continue

                # Get conversation context
                context = session_manager.get_context(session_id)

                # Process audio
                response = await handler.process_audio(audio_bytes, session_id, context)

                # Store messages if transcription available
                if response.get("transcription"):
                    session_manager.add_message(session_id, "user", response["transcription"])
                    session_manager.add_message(session_id, "assistant", response.get("text", ""))

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
        logger.info(f"Client disconnected: {session_id}")
        session_manager.remove_session(session_id)
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
        try:
            await websocket.send_json(
                WebSocketMessage(
                    type=MessageType.ERROR,
                    content={"error": str(e)},
                    session_id=session_id
                ).to_dict()
            )
        except:
            pass
        session_manager.remove_session(session_id)


# REST Endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers and monitoring."""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "services": {
            "stt": handler.stt is not None if handler else False,
            "llm": handler.llm is not None if handler else False,
            "tts": handler.tts is not None if handler else False,
            "memory": handler.memory is not None if handler else False,
            "agents": handler.planner is not None if handler else False
        },
        "active_sessions": session_manager.get_active_sessions_count()
    }


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Voice Assistant API",
        "version": "2.0.0",
        "endpoints": {
            "websocket": "/ws/voice",
            "health": "/health",
            "chat": "/api/chat",
            "transcribe": "/api/transcribe"
        }
    }


@app.post("/api/chat")
async def chat_endpoint(request: dict):
    """REST endpoint for text chat (non-WebSocket alternative)."""
    text = request.get("text", "")
    session_id = request.get("session_id", str(uuid.uuid4()))

    if not text:
        raise HTTPException(status_code=400, detail="Text is required")

    response = await handler.process_text(text, session_id)
    return JSONResponse(content=response)


@app.post("/api/transcribe")
async def transcribe_endpoint(request: dict):
    """Transcribe audio to text (REST endpoint)."""
    audio_b64 = request.get("audio", "")

    if not audio_b64:
        raise HTTPException(status_code=400, detail="Audio is required")

    if not handler or not handler.stt:
        raise HTTPException(status_code=503, detail="STT service not available")

    try:
        audio_bytes = base64.b64decode(audio_b64)
        result = await asyncio.to_thread(handler.stt.transcribe_with_result, audio_bytes)
        return {
            "text": result.text,
            "confidence": result.confidence
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.websocket_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
