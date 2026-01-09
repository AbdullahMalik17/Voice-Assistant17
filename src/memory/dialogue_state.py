"""
Dialogue State Manager
Provides dynamic conversation state tracking with slot filling support
and integration with semantic memory for RAG-based context retrieval.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .semantic_memory import SemanticMemory, MemoryConfig, RetrievedMemory
from ..storage.sqlite_store import SqliteStore


class ConversationState(str, Enum):
    """States of a conversation"""
    ACTIVE = "active"
    WAITING_FOR_SLOT = "waiting_for_slot"
    EXECUTING_PLAN = "executing_plan"
    COMPLETED = "completed"
    EXPIRED = "expired"


@dataclass
class SlotValue:
    """A filled slot value with metadata"""
    name: str
    value: Any
    entity_type: Optional[str] = None
    confidence: float = 1.0
    source_turn_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "entity_type": self.entity_type,
            "confidence": self.confidence,
            "source_turn_id": self.source_turn_id,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class Turn:
    """A single conversation turn (user input + assistant response)"""
    id: str
    user_input: str
    assistant_response: str
    timestamp: datetime = field(default_factory=datetime.now)

    # Classification
    intent: Optional[str] = None
    intent_confidence: float = 0.0
    entities: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    stt_confidence: float = 0.0
    processing_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_input": self.user_input,
            "assistant_response": self.assistant_response,
            "timestamp": self.timestamp.isoformat(),
            "intent": self.intent,
            "intent_confidence": self.intent_confidence,
            "entities": self.entities,
            "stt_confidence": self.stt_confidence,
            "processing_time_ms": self.processing_time_ms
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Turn":
        return cls(
            id=data["id"],
            user_input=data["user_input"],
            assistant_response=data["assistant_response"],
            timestamp=datetime.fromisoformat(data["timestamp"]) if data.get("timestamp") else datetime.now(),
            intent=data.get("intent"),
            intent_confidence=data.get("intent_confidence", 0.0),
            entities=data.get("entities", {}),
            stt_confidence=data.get("stt_confidence", 0.0),
            processing_time_ms=data.get("processing_time_ms", 0.0)
        )


@dataclass
class DialogueState:
    """
    Complete state of an ongoing conversation.
    Replaces the fixed 5-exchange FIFO with dynamic state tracking.
    """
    session_id: str
    user_id: str = "default"
    state: ConversationState = ConversationState.ACTIVE

    # Current intent and slots
    current_intent: Optional[str] = None
    filled_slots: Dict[str, SlotValue] = field(default_factory=dict)
    pending_slots: List[str] = field(default_factory=list)

    # Active plan (if executing multi-step task)
    active_plan_id: Optional[str] = None
    current_plan_step: int = 0

    # Conversation history
    turns: List[Turn] = field(default_factory=list)
    summary: Optional[str] = None  # Compressed summary for long conversations

    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    timeout_seconds: int = 300  # 5 minutes default

    # Retrieved context from semantic memory
    relevant_memories: List[RetrievedMemory] = field(default_factory=list)

    def add_turn(
        self,
        user_input: str,
        assistant_response: str,
        intent: Optional[str] = None,
        intent_confidence: float = 0.0,
        entities: Optional[Dict[str, Any]] = None,
        stt_confidence: float = 0.0,
        processing_time_ms: float = 0.0
    ) -> Turn:
        """Add a new conversation turn"""
        turn = Turn(
            id=str(uuid.uuid4()),
            user_input=user_input,
            assistant_response=assistant_response,
            intent=intent,
            intent_confidence=intent_confidence,
            entities=entities or {},
            stt_confidence=stt_confidence,
            processing_time_ms=processing_time_ms
        )
        self.turns.append(turn)
        self.last_updated = datetime.now()

        # Update current intent if provided
        if intent:
            self.current_intent = intent

        return turn

    def fill_slot(
        self,
        name: str,
        value: Any,
        entity_type: Optional[str] = None,
        confidence: float = 1.0,
        source_turn_id: Optional[str] = None
    ) -> None:
        """Fill a slot with a value"""
        self.filled_slots[name] = SlotValue(
            name=name,
            value=value,
            entity_type=entity_type,
            confidence=confidence,
            source_turn_id=source_turn_id
        )
        # Remove from pending if present
        if name in self.pending_slots:
            self.pending_slots.remove(name)
        self.last_updated = datetime.now()

    def get_slot_value(self, name: str) -> Optional[Any]:
        """Get the value of a filled slot"""
        slot = self.filled_slots.get(name)
        return slot.value if slot else None

    def has_all_required_slots(self, required_slots: List[str]) -> bool:
        """Check if all required slots are filled"""
        return all(slot in self.filled_slots for slot in required_slots)

    def get_missing_slots(self, required_slots: List[str]) -> List[str]:
        """Get list of required slots that are not filled"""
        return [slot for slot in required_slots if slot not in self.filled_slots]

    def clear_slots(self) -> None:
        """Clear all filled slots"""
        self.filled_slots.clear()
        self.pending_slots.clear()
        self.current_intent = None

    def is_expired(self) -> bool:
        """Check if the conversation has timed out"""
        elapsed = datetime.now() - self.last_updated
        return elapsed.total_seconds() > self.timeout_seconds

    def get_recent_turns(self, n: int = 5) -> List[Turn]:
        """Get the n most recent turns"""
        return self.turns[-n:] if self.turns else []

    def get_context_for_llm(self, max_turns: int = 5) -> str:
        """
        Format conversation context for LLM prompts.
        Includes recent turns and relevant memories.
        """
        context_parts = []

        # Add relevant memories
        if self.relevant_memories:
            memory_context = "Relevant context from previous conversations:\n"
            for mem in self.relevant_memories[:3]:  # Top 3 memories
                memory_context += f"- {mem.entry.content}\n"
            context_parts.append(memory_context)

        # Add recent conversation history
        recent_turns = self.get_recent_turns(max_turns)
        if recent_turns:
            history = "Recent conversation:\n"
            for turn in recent_turns:
                history += f"User: {turn.user_input}\n"
                history += f"Assistant: {turn.assistant_response}\n"
            context_parts.append(history)

        # Add current slots if any
        if self.filled_slots:
            slots_context = "Current information:\n"
            for name, slot in self.filled_slots.items():
                slots_context += f"- {name}: {slot.value}\n"
            context_parts.append(slots_context)

        return "\n".join(context_parts)

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "state": self.state.value,
            "current_intent": self.current_intent,
            "filled_slots": {k: v.to_dict() for k, v in self.filled_slots.items()},
            "pending_slots": self.pending_slots,
            "active_plan_id": self.active_plan_id,
            "current_plan_step": self.current_plan_step,
            "turns": [t.to_dict() for t in self.turns],
            "summary": self.summary,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "timeout_seconds": self.timeout_seconds
        }


class DialogueStateManager:
    """
    Manages dialogue states with semantic memory integration.
    Provides session management, context retrieval, and automatic cleanup.
    """

    def __init__(
        self,
        semantic_memory: Optional[SemanticMemory] = None,
        sqlite_store: Optional[SqliteStore] = None,
        timeout_seconds: int = 300,
        max_sessions: int = 100
    ):
        self.timeout_seconds = timeout_seconds
        self.max_sessions = max_sessions

        # Active sessions
        self._sessions: Dict[str, DialogueState] = {}

        # Semantic memory for RAG
        self.semantic_memory = semantic_memory or SemanticMemory()
        
        # SQLite store for persistence
        self.sqlite_store = sqlite_store

    def create_session(
        self,
        session_id: Optional[str] = None,
        user_id: str = "default"
    ) -> DialogueState:
        """Create a new dialogue session"""
        if session_id is None:
            session_id = str(uuid.uuid4())

        state = DialogueState(
            session_id=session_id,
            user_id=user_id,
            timeout_seconds=self.timeout_seconds
        )

        self._sessions[session_id] = state
        
        # Persist if SQLite store is available
        if self.sqlite_store:
            self.sqlite_store.save_session(
                session_id=session_id,
                user_id=user_id,
                state=state.state.value
            )

        # Cleanup old sessions if too many
        if len(self._sessions) > self.max_sessions:
            self._cleanup_old_sessions()

        return state

    def get_session(self, session_id: str) -> Optional[DialogueState]:
        """Get an existing session by ID, trying memory then SQLite"""
        state = self._sessions.get(session_id)

        # If not in memory, try loading from SQLite
        if state is None and self.sqlite_store:
            session_data = self.sqlite_store.get_session(session_id)
            if session_data:
                # Reconstruct state
                state = DialogueState(
                    session_id=session_id,
                    user_id=session_data['user_id'],
                    state=ConversationState(session_data['state']),
                    current_intent=session_data['current_intent'],
                    timeout_seconds=self.timeout_seconds
                )
                # Reconstruct turns
                for turn_data in session_data.get('turns', []):
                    # Convert dict from DB to Turn object
                    turn = Turn(
                        id=turn_data['turn_id'],
                        user_input=turn_data['user_input'],
                        assistant_response=turn_data['assistant_response'],
                        timestamp=datetime.fromisoformat(turn_data['timestamp']),
                        intent=turn_data['intent'],
                        intent_confidence=turn_data['intent_confidence'],
                        entities=turn_data['entities']
                    )
                    state.turns.append(turn)
                
                # Cache in memory
                self._sessions[session_id] = state

        if state and state.is_expired():
            state.state = ConversationState.EXPIRED
            # Don't remove yet - let caller decide

        return state

    def get_or_create_session(
        self,
        session_id: str,
        user_id: str = "default"
    ) -> DialogueState:
        """Get existing session or create new one"""
        state = self.get_session(session_id)

        if state is None:
            state = self.create_session(session_id, user_id)

        return state

    def update_session(
        self,
        session_id: str,
        user_input: str,
        assistant_response: str,
        intent: Optional[str] = None,
        intent_confidence: float = 0.0,
        entities: Optional[Dict[str, Any]] = None,
        stt_confidence: float = 0.0,
        processing_time_ms: float = 0.0,
        store_in_memory: bool = True
    ) -> Turn:
        """
        Update a session with a new turn and optionally store in semantic memory and SQLite.

        Returns:
            The created Turn object
        """
        state = self.get_or_create_session(session_id)

        # Add turn to dialogue state
        turn = state.add_turn(
            user_input=user_input,
            assistant_response=assistant_response,
            intent=intent,
            intent_confidence=intent_confidence,
            entities=entities,
            stt_confidence=stt_confidence,
            processing_time_ms=processing_time_ms
        )

        # Persist to SQLite
        if self.sqlite_store:
            # Update session info
            self.sqlite_store.save_session(
                session_id=session_id,
                user_id=state.user_id,
                state=state.state.value,
                current_intent=state.current_intent
            )
            # Add new turn
            self.sqlite_store.add_turn(
                turn_id=turn.id,
                session_id=session_id,
                user_input=user_input,
                assistant_response=assistant_response,
                intent=intent,
                intent_confidence=intent_confidence,
                entities=entities
            )

        # Store in semantic memory for future retrieval
        if store_in_memory and self.semantic_memory:
            # Store user input
            self.semantic_memory.store(
                content=user_input,
                session_id=session_id,
                user_id=state.user_id,
                intent=intent,
                entities=entities,
                importance=0.6,
                source="user_input",
                turn_id=turn.id
            )

            # Store important assistant responses
            if len(assistant_response) > 50:  # Non-trivial response
                self.semantic_memory.store(
                    content=assistant_response,
                    session_id=session_id,
                    user_id=state.user_id,
                    intent=intent,
                    importance=0.4,
                    source="assistant_response",
                    turn_id=turn.id
                )

        return turn

    def retrieve_context(
        self,
        session_id: str,
        query: str,
        top_k: int = 5,
        include_current_session: bool = True
    ) -> List[RetrievedMemory]:
        """
        Retrieve relevant context from semantic memory.

        Args:
            session_id: Current session ID
            query: The query to find relevant context for
            top_k: Maximum number of memories to retrieve
            include_current_session: Whether to include memories from current session

        Returns:
            List of retrieved memories sorted by relevance
        """
        if not self.semantic_memory:
            return []

        # Retrieve from all sessions if include_current_session, else exclude current
        memories = self.semantic_memory.retrieve(
            query=query,
            top_k=top_k * 2,  # Get extra to filter
            session_id=None  # Search all sessions
        )

        # Optionally filter out current session memories
        if not include_current_session:
            memories = [m for m in memories if m.entry.session_id != session_id]

        # Update state with retrieved memories
        state = self.get_session(session_id)
        if state:
            state.relevant_memories = memories[:top_k]

        return memories[:top_k]

    def fill_slot(
        self,
        session_id: str,
        slot_name: str,
        value: Any,
        entity_type: Optional[str] = None,
        confidence: float = 1.0
    ) -> None:
        """Fill a slot in a session"""
        state = self.get_session(session_id)
        if state:
            state.fill_slot(
                name=slot_name,
                value=value,
                entity_type=entity_type,
                confidence=confidence
            )

    def get_slot_value(self, session_id: str, slot_name: str) -> Optional[Any]:
        """Get a slot value from a session"""
        state = self.get_session(session_id)
        if state:
            return state.get_slot_value(slot_name)
        return None

    def set_pending_slots(self, session_id: str, slots: List[str]) -> None:
        """Set the pending slots that need to be filled"""
        state = self.get_session(session_id)
        if state:
            state.pending_slots = slots

    def close_session(self, session_id: str) -> None:
        """Close and cleanup a session"""
        state = self._sessions.get(session_id)
        if state:
            state.state = ConversationState.COMPLETED
            del self._sessions[session_id]

    def _cleanup_old_sessions(self) -> int:
        """Remove expired and old sessions"""
        expired = []
        for session_id, state in self._sessions.items():
            if state.is_expired():
                expired.append(session_id)

        for session_id in expired:
            del self._sessions[session_id]

        return len(expired)

    def get_active_sessions(self) -> List[str]:
        """Get list of active (non-expired) session IDs"""
        return [
            sid for sid, state in self._sessions.items()
            if not state.is_expired()
        ]

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the dialogue manager"""
        active_count = len([s for s in self._sessions.values() if not s.is_expired()])
        total_turns = sum(len(s.turns) for s in self._sessions.values())

        return {
            "total_sessions": len(self._sessions),
            "active_sessions": active_count,
            "total_turns": total_turns,
            "timeout_seconds": self.timeout_seconds,
            "memory_stats": self.semantic_memory.get_stats() if self.semantic_memory else None
        }