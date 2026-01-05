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
    from src.services.stt import STTService
    from src.services.llm import LLMService
    from src.services.tts import TTSService
    from src.services.intent_classifier import IntentClassifier
    from src.core.config import get_config
    SERVICES_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Some services not available: {e}")
    SERVICES_AVAILABLE = False

# Optional imports for enhanced features
try:
    from src.memory.semantic_memory import SemanticMemory
    from src.memory.dialogue_state import DialogueStateManager
    MEMORY_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Memory services not available: {e}")
    MEMORY_AVAILABLE = False

try:
    from src.agents.planner import AgenticPlanner
    from src.agents.guardrails import SafetyGuardrails
    AGENTS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Agent services not available: {e}")
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


class SimpleEventLogger:
    """Simple event logger wrapper for services."""
    def __init__(self, logger):
        self._logger = logger

    def info(self, event=None, message=None, **kwargs):
        self._logger.info(f"{event}: {message}" if event else str(message))

    def warning(self, event=None, message=None, **kwargs):
        self._logger.warning(f"{event}: {message}" if event else str(message))

    def error(self, event=None, message=None, **kwargs):
        self._logger.error(f"{event}: {message}" if event else str(message))

    def tts_completed(self, **kwargs):
        """Log TTS completion event."""
        self._logger.info(f"TTS_COMPLETED: {kwargs}")

    def stt_completed(self, **kwargs):
        """Log STT completion event."""
        self._logger.info(f"STT_COMPLETED: {kwargs}")


class SimpleMetricsLogger:
    """Simple metrics logger wrapper."""
    def record_metric(self, name, value):
        pass  # No-op for now


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
            # Create loggers for services
            base_logger = logging.getLogger("services")
            service_logger = SimpleEventLogger(base_logger)
            metrics_logger = SimpleMetricsLogger()

            # Initialize LLM service (required for text chat)
            try:
                self.llm = LLMService(config, service_logger, metrics_logger)
                logger.info("LLM service initialized")
            except Exception as e:
                logger.error(f"Failed to initialize LLM service: {e}")

            # Initialize other services (optional for text-only mode)
            try:
                self.intent = IntentClassifier(config, service_logger, metrics_logger)
                logger.info("Intent classifier initialized")
            except Exception as e:
                logger.warning(f"Intent classifier not available: {e}")

            # Initialize audio utils for TTS and STT
            try:
                from src.utils.audio_utils import AudioUtils
                self.audio_utils = AudioUtils()
            except Exception as e:
                logger.warning(f"Audio utils not available: {e}")
                self.audio_utils = None

            # Initialize TTS for voice output
            try:
                if self.audio_utils:
                    self.tts = TTSService(config, service_logger, metrics_logger, self.audio_utils)
                    logger.info("TTS service initialized")
            except Exception as e:
                logger.warning(f"TTS service not available: {e}")

            # STT for voice input (web interface uses browser's MediaRecorder)
            try:
                if self.audio_utils:
                    self.stt = STTService(config, service_logger, metrics_logger, self.audio_utils)
                    logger.info("STT service initialized")
            except Exception as e:
                logger.warning(f"STT service not available: {e}")

        # Initialize persistent memory (mem0)
        try:
            from src.services.persistent_memory import PersistentMemoryService
            self.persistent_memory = PersistentMemoryService()
            logger.info("Persistent memory service initialized")
        except Exception as e:
            logger.warning(f"Persistent memory not available: {e}")
            self.persistent_memory = None

        # Initialize semantic memory (optional, legacy)
        if MEMORY_AVAILABLE:
            try:
                from src.memory.semantic_memory import MemoryConfig
                memory_config = MemoryConfig()
                self.memory = SemanticMemory(memory_config)
                self.dialogue = DialogueStateManager(self.memory)
                logger.info("Semantic memory services initialized")
            except Exception as e:
                logger.warning(f"Semantic memory services not available: {e}")

        if AGENTS_AVAILABLE and self.llm:
            try:
                # Create tool registry with all available tools
                from ..agents.tools import create_default_registry
                tool_registry = create_default_registry()

                # Create guardrails
                self.guardrails = SafetyGuardrails()

                # Initialize planner with tool registry and LLM service
                self.planner = AgenticPlanner(
                    tool_registry=tool_registry,
                    guardrails=self.guardrails,
                    llm_service=self.llm
                )
                logger.info("Agent services initialized")
            except Exception as e:
                logger.warning(f"Agent services not available: {e}")
                logger.error(f"Error details: {e}")

    async def process_text(self, text: str, user_id: str, context: List[dict] = None) -> dict:
        """Process text input and return response."""
        try:
            # Check if this is a complex request that could benefit from tools
            should_use_agent = False
            if self.planner:
                # Determine if the request might require tools (contains action words, complex requests, etc.)
                text_lower = text.lower()
                tool_indicators = [
                    "open", "launch", "start", "find", "search", "timer", "weather",
                    "gmail", "drive", "email", "screenshot", "status", "system",
                    "file", "folder", "list", "show", "check", "get", "take"
                ]
                should_use_agent = any(indicator in text_lower for indicator in tool_indicators)

            # If agent is available and the request might benefit from tools, try using it first
            if self.planner and should_use_agent:
                try:
                    # Create a plan for the request
                    # Build context string for the planner
                    context_str = ""
                    persistent_context = ""
                    if self.persistent_memory:
                        persistent_context = self.persistent_memory.get_memory_context(
                            query=text,
                            user_id=user_id,
                            limit=5
                        )

                    if persistent_context:
                        context_str = persistent_context + "\n\n"
                    # Get context from semantic memory if available (legacy)
                    memory_context = None
                    if self.dialogue:
                        memory_context = self.dialogue.retrieve_context(user_id, text)

                    if context:
                        context_str += "\n".join([
                            f"{msg['role']}: {msg['content']}"
                            for msg in context[-5:]
                        ])
                    if memory_context:
                        context_str += "\n" + str(memory_context)

                    plan = self.planner.create_plan(text, context_str if context_str else None)
                    is_valid, errors = self.planner.validate_plan(plan)

                    if is_valid and plan.steps:
                        # Execute the plan
                        success, results = self.planner.execute_simple(plan)

                        # Check if any steps were successfully executed
                        executed_steps = [r for r in results if r['type'] == 'step_completed']
                        if executed_steps:
                            # Get the last step result
                            last_result = executed_steps[-1]
                            tool_result = last_result['data'].get('result', {})

                            if tool_result.get('success'):
                                # Format the tool result as the response
                                tool_data = tool_result.get('data', {})
                                response_text = self._format_tool_response(tool_data, text)

                                result = {
                                    "text": response_text,
                                    "intent": "tool_execution",
                                    "confidence": 1.0,
                                    "tool_results": tool_data,
                                    "tool_execution": True
                                }

                                # Store tool execution in persistent memory
                                if self.persistent_memory:
                                    self.persistent_memory.add_conversation(
                                        user_message=text,
                                        assistant_message=response_text,
                                        user_id=user_id,
                                        metadata={
                                            "intent": "tool_execution",
                                            "confidence": 1.0,
                                            "tool_data": tool_data
                                        }
                                    )

                                # Generate TTS audio for tool response
                                if self.tts:
                                    try:
                                        audio_response = await asyncio.to_thread(
                                            self.tts.synthesize, response_text
                                        )
                                        if audio_response:
                                            result["audio"] = base64.b64encode(audio_response).decode()
                                            logger.info("TTS audio generated for tool response")
                                    except Exception as e:
                                        logger.warning(f"TTS generation failed: {e}")

                                return result
                except Exception as e:
                    logger.warning(f"Agent tool execution failed: {e}")
                    # Fall back to regular processing if agent fails

            # Skip intent classification for web interface (requires voice_command_id)
            intent_result = None

            # Retrieve relevant memories from persistent memory (mem0)
            persistent_context = ""
            if self.persistent_memory:
                persistent_context = self.persistent_memory.get_memory_context(
                    query=text,
                    user_id=user_id,
                    limit=5
                )

            # Get context from semantic memory if available (legacy)
            memory_context = None
            if self.dialogue:
                memory_context = self.dialogue.retrieve_context(user_id, text)

            # Build context string with memories
            context_str = ""
            if persistent_context:
                context_str = persistent_context + "\n\n"
            if context:
                context_str += "\n".join([
                    f"{msg['role']}: {msg['content']}"
                    for msg in context[-5:]
                ])
            if memory_context:
                context_str += "\n" + str(memory_context)

            # Generate response with memory context
            if self.llm:
                # If we have persistent context, include it in the query
                query_with_context = text
                if persistent_context:
                    query_with_context = f"{persistent_context}\n\nUser query: {text}"

                response = await asyncio.to_thread(
                    self.llm.generate_response,
                    query=query_with_context,
                    intent=intent_result,
                    context=None  # Context handling simplified for web interface
                )
            else:
                response = f"Echo: {text} (LLM service not available)"

            # Store conversation in persistent memory
            if self.persistent_memory:
                self.persistent_memory.add_conversation(
                    user_message=text,
                    assistant_message=response,
                    user_id=user_id,
                    metadata={
                        "intent": intent_result.intent_type if intent_result else "unknown",
                        "confidence": intent_result.confidence if intent_result else 0.0
                    }
                )

            # Update dialogue state if available (legacy)
            if self.dialogue:
                self.dialogue.update_session(user_id, text, response)

            result = {
                "text": response,
                "intent": intent_result.intent_type if intent_result else "unknown",
                "confidence": intent_result.confidence if intent_result else 0.0
            }

            # Generate TTS audio for text responses (web interface voice output)
            if self.tts:
                try:
                    audio_response = await asyncio.to_thread(
                        self.tts.synthesize, response
                    )
                    if audio_response:
                        result["audio"] = base64.b64encode(audio_response).decode()
                        logger.info("TTS audio generated for text response")
                except Exception as e:
                    logger.warning(f"TTS generation failed: {e}")

            return result

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

            # Calculate audio duration in milliseconds
            duration_ms = 0
            if self.audio_utils:
                duration_seconds = self.audio_utils.get_duration(audio_bytes)
                duration_ms = int(duration_seconds * 1000)

            # Transcribe audio
            transcription = await asyncio.to_thread(
                self.stt.transcribe_with_result, audio_bytes, duration_ms
            )

            if not transcription.text:
                return {
                    "error": "Could not transcribe audio",
                    "text": "",
                    "transcription": ""
                }

            # Process as text - for WebSocket, use session_id as user_id
            response = await self.process_text(transcription.text, session_id, context)
            response["transcription"] = transcription.text
            response["stt_confidence"] = transcription.confidence

            # Generate TTS if available (always enabled for web interface)
            if self.tts:
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

    def _format_tool_response(self, tool_data: dict, original_request: str) -> str:
        """Format tool execution results into a natural language response."""
        if not tool_data:
            return "I processed your request but didn't get specific results."

        # Handle different types of tool results
        if "message" in tool_data:
            return tool_data["message"]

        if "emails" in tool_data:
            # Gmail tool response
            count = tool_data.get("total_count", len(tool_data.get("emails", [])))
            return f"I found {count} emails for you."

        if "files" in tool_data:
            # Drive tool response
            count = tool_data.get("count", len(tool_data.get("files", [])))
            return f"I found {count} files in your Drive."

        if "processes" in tool_data:
            # System processes tool
            count = tool_data.get("count", len(tool_data.get("processes", [])))
            return f"I found {count} running processes."

        if "results" in tool_data:
            # File search results
            count = tool_data.get("count", len(tool_data.get("results", [])))
            return f"I found {count} files matching your search."

        if "path" in tool_data and "screenshot" in tool_data:
            # Screenshot tool
            return "I've taken a screenshot and saved it successfully."

        # Generic response for other tool types
        if "success" in tool_data:
            if tool_data.get("success"):
                return "I've completed the requested action successfully."
            else:
                return "I tried to complete the action but encountered an issue."

        # Default fallback
        return f"I've processed your request: {original_request}"


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
            config = get_config()
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
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000,http://127.0.0.1:3000,http://127.0.0.1:8000").split(",")
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
    user_id = request.get("user_id", session_id)  # Use provided user_id or fall back to session_id

    if not text:
        raise HTTPException(status_code=400, detail="Text is required")

    response = await handler.process_text(text, user_id)  # Use user_id instead of session_id for memory
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
