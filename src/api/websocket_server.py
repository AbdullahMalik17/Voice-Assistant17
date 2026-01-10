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
    from src.storage.sqlite_store import SqliteStore
    MEMORY_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Memory services not available: {e}")
    MEMORY_AVAILABLE = False

# Supabase conversation persistence
try:
    from src.services.supabase_conversation import SupabaseConversationService
    SUPABASE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Supabase service not available: {e}")
    SUPABASE_AVAILABLE = False

# Authentication imports
try:
    from src.auth import authenticate_websocket, get_user_id_from_auth, AuthenticationError
    AUTH_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Authentication not available: {e}")
    AUTH_AVAILABLE = False

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

    def debug(self, event=None, message=None, **kwargs):
        self._logger.debug(f"{event}: {message}" if event else str(message))

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
        self.persistent_memory = None
        self.supabase_conversation = None
        self.sqlite_store = None
        self.audio_utils = None

        # Initialize available services
        if SERVICES_AVAILABLE:
            # Create loggers for services
            base_logger = logging.getLogger("services")
            service_logger = SimpleEventLogger(base_logger)
            metrics_logger = SimpleMetricsLogger()

            # Initialize LLM service (required for text chat)
            try:
                self.llm = LLMService(config, service_logger, metrics_logger)
                if not self.llm.is_ready():
                    logger.warning("LLM service initialized but NOT ready (check API key)")
                else:
                    logger.info("LLM service initialized and ready")
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

        # Initialize SQLite store FIRST (critical for persistence)
        try:
            self.sqlite_store = SqliteStore()
            logger.info("SQLite store initialized for conversation persistence")
        except Exception as e:
            logger.warning(f"SQLite store not available: {e}")
            self.sqlite_store = None

        # Initialize persistent memory (mem0) - OPTIONAL
        try:
            from src.services.persistent_memory import PersistentMemoryService
            self.persistent_memory = PersistentMemoryService()
            logger.info("Persistent memory service initialized")
        except Exception as e:
            logger.debug(f"Persistent memory not available (optional): {e}")
            self.persistent_memory = None

        # Initialize Supabase conversation persistence (OPTIONAL)
        if SUPABASE_AVAILABLE:
            try:
                self.supabase_conversation = SupabaseConversationService()
                if self.supabase_conversation.is_available():
                    logger.info("Supabase conversation service initialized")
                else:
                    logger.debug("Supabase conversation service created but not available (optional)")
                    self.supabase_conversation = None
            except Exception as e:
                logger.debug(f"Supabase conversation service not available (optional): {e}")
                self.supabase_conversation = None
        else:
            self.supabase_conversation = None

        # Initialize semantic memory (optional, legacy)
        if MEMORY_AVAILABLE:
            try:
                from src.memory.semantic_memory import MemoryConfig
                memory_config = MemoryConfig()
                self.memory = SemanticMemory(memory_config)

                # Initialize DialogueStateManager with SQLite store
                if self.sqlite_store:
                    self.dialogue = DialogueStateManager(self.memory, sqlite_store=self.sqlite_store)
                    logger.info("Semantic and persistent session memory services initialized")
                else:
                    logger.warning("DialogueStateManager not initialized (SQLite store unavailable)")
            except Exception as e:
                logger.warning(f"Semantic memory services not available: {e}")

        if AGENTS_AVAILABLE and self.llm:
            try:
                # Create tool registry with all available tools
                from ..agents.tools import create_default_registry
                # Pass sqlite_store to enable conversation history tools
                tool_registry = create_default_registry(
                    sqlite_store=self.sqlite_store if hasattr(self, 'sqlite_store') else None
                )

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
                                
                                # Generate natural language response using LLM
                                if self.llm:
                                    response_text = await asyncio.to_thread(
                                        self.llm.generate_summarized_response,
                                        query=text,
                                        tool_name=last_result['message'], # Contains the tool/step description
                                        tool_result=tool_data
                                    )
                                else:
                                    response_text = self._format_tool_response(tool_data, text)

                                result = {
                                    "text": response_text,
                                    "intent": "tool_execution",
                                    "confidence": 1.0,
                                    "tool_results": tool_data,
                                    "tool_execution": True
                                }

                                # Store tool execution in SQLite (PRIMARY)
                                if self.dialogue:
                                    try:
                                        self.dialogue.update_session(
                                            session_id=user_id,
                                            user_input=text,
                                            assistant_response=response_text,
                                            intent="tool_execution",
                                            intent_confidence=1.0,
                                            entities={"tool_data": tool_data}
                                        )
                                    except Exception as e:
                                        logger.warning(f"Failed to store tool execution: {e}")
                                elif self.sqlite_store:
                                    # Fallback: directly use sqlite_store
                                    try:
                                        self.sqlite_store.add_turn(
                                            session_id=user_id,
                                            user_input=text,
                                            assistant_response=response_text,
                                            intent="tool_execution",
                                            intent_confidence=1.0
                                        )
                                    except Exception as e:
                                        logger.warning(f"Failed to store tool execution in SQLite: {e}")

                                # Store tool execution in persistent memory (OPTIONAL)
                                if self.persistent_memory:
                                    try:
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
                                    except Exception as e:
                                        logger.debug(f"Failed to store in persistent memory: {e}")

                                # Store tool execution in Supabase (OPTIONAL, non-blocking)
                                if self.supabase_conversation:
                                    try:
                                        asyncio.create_task(
                                            self.supabase_conversation.add_turn(
                                                session_id=user_id,
                                                user_input=text,
                                                assistant_response=response_text,
                                                intent="tool_execution",
                                                intent_confidence=1.0,
                                                entities={"tool_data": tool_data}
                                            )
                                        )
                                    except Exception as e:
                                        logger.debug(f"Failed to queue Supabase storage: {e}")

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
                            else:
                                # Handle failure with LLM if possible
                                error_msg = tool_result.get('error', 'Unknown error')
                                if self.llm:
                                    response_text = await asyncio.to_thread(
                                        self.llm.generate_summarized_response,
                                        query=text,
                                        tool_name=last_result['message'],
                                        tool_result={"error": error_msg}
                                    )
                                else:
                                    response_text = f"I encountered an error while trying to help you: {error_msg}"
                                
                                return {
                                    "text": response_text,
                                    "intent": "error",
                                    "confidence": 0.0,
                                    "error": error_msg
                                }
                except Exception as e:
                    logger.warning(f"Agent tool execution failed: {e}")
                    # Fall back to regular processing if agent fails

            # Skip intent classification for web interface (requires voice_command_id)
            intent_result = None

            # Load user profile first (critical for memory)
            user_profile = None
            if self.sqlite_store:
                try:
                    user_profile = self.sqlite_store.get_user_profile(user_id)
                except Exception as e:
                    logger.debug(f"Failed to load user profile: {e}")

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

            # Add user profile information at the top (name, preferences, etc.)
            if user_profile:
                context_str += "User Information:\n"
                for key, value in user_profile.items():
                    context_str += f"- {key}: {value}\n"
                context_str += "\n"

            if persistent_context:
                context_str += f"Additional Context:\n{persistent_context}\n\n"

            # Add SQLite conversation history for better context
            if self.dialogue:
                dialogue_state = self.dialogue.get_session(user_id)
                if dialogue_state and dialogue_state.turns:
                    history_context = dialogue_state.get_context_for_llm(max_turns=10)
                    if history_context:
                        context_str += f"Previous Conversation:\n{history_context}\n\n"

            if context:
                context_str += "Current Session:\n"
                context_str += "\n".join([
                    f"{msg['role']}: {msg['content']}"
                    for msg in context[-5:]
                ])
                context_str += "\n"

            if memory_context:
                context_str += f"Semantic Memory:\n{str(memory_context)}\n"

            # Generate response with memory context
            if self.llm:
                # Build complete context string with user information and history
                context_str = ""

                # Include persistent memory context (user name, preferences, etc.)
                if persistent_context:
                    context_str += f"User Information:\n{persistent_context}\n\n"

                # Include recent conversation history from SQLite
                if self.dialogue:
                    dialogue_state = self.dialogue.get_session(user_id)
                    if dialogue_state and dialogue_state.turns:
                        history_context = dialogue_state.get_context_for_llm(max_turns=5)
                        if history_context:
                            context_str += f"Recent Conversation:\n{history_context}\n\n"

                # Include session context
                if context and isinstance(context, list):
                    context_str += "Conversation Context:\n"
                    for msg in context[-3:]:  # Last 3 messages
                        context_str += f"{msg['role'].title()}: {msg['content']}\n"
                    context_str += "\n"

                # Build final query with context
                query_with_context = f"{context_str}Current User Query: {text}"

                response = await asyncio.to_thread(
                    self.llm.generate_response,
                    query=query_with_context,
                    intent=intent_result,
                    context=context  # Pass context object for additional processing
                )
            else:
                response = f"Echo: {text} (LLM service not available)"

            # Store conversation in SQLite (PRIMARY - always try this first)
            if self.dialogue:
                try:
                    self.dialogue.update_session(
                        session_id=user_id,
                        user_input=text,
                        assistant_response=response,
                        intent=intent_result.intent_type if intent_result else "unknown",
                        intent_confidence=intent_result.confidence if intent_result else 0.0,
                        entities={}
                    )
                    logger.debug(f"Conversation stored in SQLite for session {user_id}")
                except Exception as e:
                    logger.warning(f"Failed to store in dialogue state: {e}")
            elif self.sqlite_store:
                # Fallback: directly use sqlite_store if dialogue is not available
                try:
                    self.sqlite_store.add_turn(
                        session_id=user_id,
                        user_input=text,
                        assistant_response=response,
                        intent=intent_result.intent_type if intent_result else "unknown",
                        intent_confidence=intent_result.confidence if intent_result else 0.0
                    )
                    logger.debug(f"Conversation stored directly in SQLite for session {user_id}")
                except Exception as e:
                    logger.warning(f"Failed to store in SQLite: {e}")

            # Store conversation in persistent memory (OPTIONAL - mem0)
            if self.persistent_memory:
                try:
                    self.persistent_memory.add_conversation(
                        user_message=text,
                        assistant_message=response,
                        user_id=user_id,
                        metadata={
                            "intent": intent_result.intent_type if intent_result else "unknown",
                            "confidence": intent_result.confidence if intent_result else 0.0
                        }
                    )
                except Exception as e:
                    logger.debug(f"Failed to store in persistent memory (optional): {e}")

            # Store conversation in Supabase (OPTIONAL - non-blocking)
            if self.supabase_conversation:
                try:
                    asyncio.create_task(
                        self.supabase_conversation.add_turn(
                            session_id=user_id,
                            user_input=text,
                            assistant_response=response,
                            intent=intent_result.intent_type if intent_result else "unknown",
                            intent_confidence=intent_result.confidence if intent_result else 0.0,
                            entities={}
                        )
                    )
                except Exception as e:
                    logger.debug(f"Failed to queue Supabase storage (optional): {e}")

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
    try:
        await websocket.accept()
    except Exception as e:
        logger.error(f"❌ Failed to accept WebSocket connection: {e}")
        return

    # Authenticate user (optional)
    user_info = None
    user_id = "anonymous"

    if AUTH_AVAILABLE:
        try:
            user_info = await authenticate_websocket(websocket)
            user_id = get_user_id_from_auth(user_info)
            logger.info(f"✅ Authenticated user: {user_info.get('email', 'unknown')} (ID: {user_id})")
        except AuthenticationError as e:
            logger.warning(f"⚠️  Authentication optional: {e}")
            # Allow connection as anonymous if auth fails
            user_id = "anonymous"
        except Exception as e:
            logger.warning(f"⚠️  Auth error (allowing anonymous): {e}")
            # Allow connection as anonymous
            user_id = "anonymous"

    # Always create a session (anonymous or authenticated)
    session_id = session_manager.create_session(websocket)

    # Store user info if authenticated
    if user_info:
        session_manager.sessions[session_id]["user_info"] = user_info
        session_manager.sessions[session_id]["user_id"] = user_id

    try:
        # Send session info with user context
        await websocket.send_json(
            WebSocketMessage(
                type=MessageType.SYSTEM,
                content={
                    "message": "Connected",
                    "session_id": session_id,
                    "user_id": user_id,
                    "authenticated": user_info.get("authenticated", False) if user_info else False
                },
                session_id=session_id
            ).to_dict()
        )

        # Load conversation history from SQLite if available
        if handler and handler.dialogue and handler.sqlite_store:
            try:
                dialogue_state = handler.dialogue.get_session(session_id)
                if dialogue_state and dialogue_state.turns:
                    recent_turns = dialogue_state.get_recent_turns(10)
                    if recent_turns:
                        await websocket.send_json(
                            WebSocketMessage(
                                type=MessageType.SYSTEM,
                                content={
                                    "message": "Conversation history loaded",
                                    "turns": [t.to_dict() for t in recent_turns],
                                    "history_loaded": True
                                },
                                session_id=session_id
                            ).to_dict()
                        )
            except Exception as e:
                logger.warning(f"Failed to load conversation history: {e}")
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
    llm_ready = False
    if handler and handler.llm:
        llm_ready = handler.llm.is_ready()

    return {
        "status": "healthy",
        "version": "2.0.0",
        "services": {
            "stt": handler.stt is not None if handler else False,
            "llm": llm_ready,
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


# Conversation History Endpoints
@app.get("/api/conversations")
async def get_all_conversations(user_id: str = "default", limit: int = 20):
    """
    Get user's recent conversation sessions.
    Query params:
        - user_id: User identifier (default: "default")
        - limit: Maximum number of sessions to return (default: 20)
    """
    if not handler or not handler.dialogue or not handler.dialogue.sqlite_store:
        raise HTTPException(status_code=503, detail="Storage not available")

    try:
        sessions = handler.dialogue.sqlite_store.get_user_sessions(user_id, limit)
        return JSONResponse(content={"sessions": sessions, "count": len(sessions)})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/conversations/{session_id}")
async def get_conversation_details(session_id: str, user_id: str = "default"):
    """
    Get full conversation details for a specific session.
    Returns all turns with timestamps, intents, and entities.
    """
    if not handler or not handler.dialogue or not handler.dialogue.sqlite_store:
        raise HTTPException(status_code=503, detail="Storage not available")

    try:
        session_data = handler.dialogue.sqlite_store.get_session(session_id)

        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")

        # Verify user owns this session
        if session_data.get('user_id') != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        return JSONResponse(content={"session": session_data})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/conversations/{session_id}")
async def delete_conversation(session_id: str, user_id: str = "default"):
    """
    Delete a conversation session and all its turns.
    """
    if not handler or not handler.dialogue or not handler.dialogue.sqlite_store:
        raise HTTPException(status_code=503, detail="Storage not available")

    try:
        # Verify session exists and user owns it
        session_data = handler.dialogue.sqlite_store.get_session(session_id)

        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")

        if session_data.get('user_id') != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        # Delete the session
        handler.dialogue.sqlite_store.delete_session(session_id)

        return JSONResponse(content={
            "success": True,
            "message": f"Session {session_id} deleted successfully"
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/conversations/search")
async def search_conversations(
    query: str,
    user_id: str = "default",
    limit: int = 10
):
    """
    Search through conversation history for specific terms.
    Query params:
        - query: Search term
        - user_id: User identifier
        - limit: Maximum number of results
    """
    if not handler or not handler.dialogue or not handler.dialogue.sqlite_store:
        raise HTTPException(status_code=503, detail="Storage not available")

    if not query:
        raise HTTPException(status_code=400, detail="Query parameter is required")

    try:
        # Get user's sessions
        sessions = handler.dialogue.sqlite_store.get_user_sessions(user_id, limit=100)

        # Search through turns for matching content
        results = []
        for session in sessions:
            session_data = handler.dialogue.sqlite_store.get_session(session['session_id'])
            if session_data and 'turns' in session_data:
                for turn in session_data['turns']:
                    # Case-insensitive search in user input and assistant response
                    if (query.lower() in turn['user_input'].lower() or
                        query.lower() in turn['assistant_response'].lower()):
                        results.append({
                            "session_id": session['session_id'],
                            "turn_id": turn['turn_id'],
                            "user_input": turn['user_input'],
                            "assistant_response": turn['assistant_response'],
                            "timestamp": turn['timestamp'],
                            "intent": turn.get('intent')
                        })

                        if len(results) >= limit:
                            break

            if len(results) >= limit:
                break

        return JSONResponse(content={
            "results": results,
            "count": len(results),
            "query": query
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/conversations/export/{session_id}")
async def export_conversation(session_id: str, user_id: str = "default", format: str = "json"):
    """
    Export a conversation session to JSON or text format.
    Query params:
        - format: "json" or "text" (default: "json")
    """
    if not handler or not handler.dialogue or not handler.dialogue.sqlite_store:
        raise HTTPException(status_code=503, detail="Storage not available")

    try:
        session_data = handler.dialogue.sqlite_store.get_session(session_id)

        if not session_data:
            raise HTTPException(status_code=404, detail="Session not found")

        if session_data.get('user_id') != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        if format == "text":
            # Generate text format
            text_export = f"Conversation Export - Session: {session_id}\n"
            text_export += f"Created: {session_data.get('created_at', 'Unknown')}\n"
            text_export += f"Last Updated: {session_data.get('last_updated', 'Unknown')}\n"
            text_export += "="*80 + "\n\n"

            for turn in session_data.get('turns', []):
                text_export += f"[{turn.get('timestamp', '')}]\n"
                text_export += f"User: {turn['user_input']}\n"
                text_export += f"Assistant: {turn['assistant_response']}\n"
                if turn.get('intent'):
                    text_export += f"Intent: {turn['intent']} (confidence: {turn.get('intent_confidence', 0):.2f})\n"
                text_export += "\n" + "-"*80 + "\n\n"

            return JSONResponse(content={
                "format": "text",
                "content": text_export
            })
        else:
            # Return JSON format
            return JSONResponse(content={
                "format": "json",
                "session": session_data
            })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Settings Management Endpoints
@app.get("/api/settings")
async def get_user_settings(user_id: str = "default"):
    """
    Get user settings from storage.
    Query params:
        - user_id: User identifier (default: "default")
    """
    if not handler or not handler.sqlite_store:
        raise HTTPException(status_code=503, detail="Storage not available")

    try:
        settings = handler.sqlite_store.get_settings(user_id)
        if not settings:
            # Return default settings if none exist
            return JSONResponse(content={
                "user_id": user_id,
                "settings": {
                    "voice_enabled": True,
                    "tts_enabled": True,
                    "theme": "light",
                    "language": "en",
                    "notification_enabled": True
                }
            })
        return JSONResponse(content={"user_id": user_id, "settings": settings})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/settings")
async def save_user_settings(request: dict):
    """
    Save user settings to storage.
    Body:
        - user_id: User identifier
        - settings: Dictionary of settings to save
    """
    if not handler or not handler.sqlite_store:
        raise HTTPException(status_code=503, detail="Storage not available")

    user_id = request.get("user_id", "default")
    settings = request.get("settings", {})

    if not settings:
        raise HTTPException(status_code=400, detail="Settings object is required")

    try:
        handler.sqlite_store.save_settings(user_id, settings)
        return JSONResponse(content={
            "success": True,
            "message": f"Settings saved for user {user_id}",
            "user_id": user_id,
            "settings": settings
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/settings")
async def update_user_settings(request: dict):
    """
    Update specific user settings (partial update).
    Body:
        - user_id: User identifier
        - settings: Dictionary of settings to update/merge
    """
    if not handler or not handler.sqlite_store:
        raise HTTPException(status_code=503, detail="Storage not available")

    user_id = request.get("user_id", "default")
    settings = request.get("settings", {})

    if not settings:
        raise HTTPException(status_code=400, detail="Settings object is required")

    try:
        # Get existing settings
        existing = handler.sqlite_store.get_settings(user_id) or {}
        # Merge with new settings
        existing.update(settings)
        # Save merged settings
        handler.sqlite_store.save_settings(user_id, existing)
        return JSONResponse(content={
            "success": True,
            "message": f"Settings updated for user {user_id}",
            "user_id": user_id,
            "settings": existing
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/settings")
async def reset_user_settings(user_id: str = "default"):
    """
    Reset user settings to defaults.
    Query params:
        - user_id: User identifier (default: "default")
    """
    if not handler or not handler.sqlite_store:
        raise HTTPException(status_code=503, detail="Storage not available")

    try:
        # Delete user settings (will return defaults on next get)
        handler.sqlite_store.delete_settings(user_id)
        return JSONResponse(content={
            "success": True,
            "message": f"Settings reset for user {user_id}"
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# User Profile Management Endpoints (for persistent user information)
@app.get("/api/profile")
async def get_user_profile(user_id: str = "default"):
    """
    Get user profile information (name, preferences, etc.).
    Query params:
        - user_id: User identifier (default: "default")
    """
    if not handler or not handler.sqlite_store:
        raise HTTPException(status_code=503, detail="Storage not available")

    try:
        profile = handler.sqlite_store.get_user_profile(user_id)
        if not profile:
            return JSONResponse(content={
                "user_id": user_id,
                "profile": {}
            })
        return JSONResponse(content={"user_id": user_id, "profile": profile})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/profile")
async def save_user_profile(request: dict):
    """
    Save or update user profile information.
    Body:
        - user_id: User identifier
        - profile: Dictionary with user information (name, email, preferences, etc.)
    """
    if not handler or not handler.sqlite_store:
        raise HTTPException(status_code=503, detail="Storage not available")

    user_id = request.get("user_id", "default")
    profile = request.get("profile", {})

    if not profile:
        raise HTTPException(status_code=400, detail="Profile object is required")

    try:
        handler.sqlite_store.save_user_profile(user_id, profile)

        # Also store this in persistent memory if available
        if handler.persistent_memory:
            try:
                profile_text = ", ".join([f"{k}: {v}" for k, v in profile.items()])
                handler.persistent_memory.add_conversation(
                    user_message=f"User profile updated: {profile_text}",
                    assistant_message="Profile information stored.",
                    user_id=user_id,
                    metadata={"type": "profile_update"}
                )
            except Exception as e:
                logger.debug(f"Failed to store profile in persistent memory: {e}")

        return JSONResponse(content={
            "success": True,
            "message": f"Profile saved for user {user_id}",
            "user_id": user_id,
            "profile": profile
        })
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