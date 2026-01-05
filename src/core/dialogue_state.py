"""
Dialogue State Management Module
Tracks the state of the conversation including history, slots, and context.
Integration with semantic memory for long-term recall.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
import uuid

from ..memory.semantic_memory import SemanticMemory, RetrievedMemory


@dataclass
class DialogueTurn:
    """A single turn in the dialogue"""
    id: str
    user_input: str
    assistant_response: str
    intent: Optional[str] = None
    slots: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    memories_retrieved: List[str] = field(default_factory=list)  # IDs of retrieved memories

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "user_input": self.user_input,
            "assistant_response": self.assistant_response,
            "intent": self.intent,
            "slots": self.slots,
            "timestamp": self.timestamp.isoformat(),
            "memories_retrieved": self.memories_retrieved
        }


@dataclass
class DialogueState:
    """Current state of the conversation"""
    session_id: str
    user_id: str = "default"
    history: List[DialogueTurn] = field(default_factory=list)
    current_slots: Dict[str, Any] = field(default_factory=dict)
    current_intent: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    context_variables: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "history": [turn.to_dict() for turn in self.history],
            "current_slots": self.current_slots,
            "current_intent": self.current_intent,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "context_variables": self.context_variables
        }


class DialogueStateManager:
    """
    Manages the state of the conversation, including history tracking,
    slot filling status, and context retrieval from semantic memory.
    """

    def __init__(self, memory: Optional[SemanticMemory] = None, max_history: int = 10):
        self.memory = memory
        self.max_history = max_history
        self._states: Dict[str, DialogueState] = {}
        self._active_session: Optional[str] = None

    def get_or_create_state(self, session_id: Optional[str] = None, user_id: str = "default") -> DialogueState:
        """Get existing state or create a new one"""
        if not session_id:
            session_id = str(uuid.uuid4())

        if session_id not in self._states:
            self._states[session_id] = DialogueState(session_id=session_id, user_id=user_id)
            self._active_session = session_id

        return self._states[session_id]

    def update_state(
        self,
        session_id: str,
        user_input: str,
        assistant_response: str,
        intent: Optional[str] = None,
        slots: Optional[Dict[str, Any]] = None,
        context_updates: Optional[Dict[str, Any]] = None
    ) -> DialogueTurn:
        """
        Update state with a new turn.
        Returns the created DialogueTurn.
        """
        state = self.get_or_create_state(session_id)

        # Update timestamp
        state.last_updated = datetime.now()

        # Update current context
        state.current_intent = intent
        if slots:
            state.current_slots.update(slots)

        if context_updates:
            state.context_variables.update(context_updates)

        # Create turn
        turn = DialogueTurn(
            id=str(uuid.uuid4()),
            user_input=user_input,
            assistant_response=assistant_response,
            intent=intent,
            slots=slots or {}
        )

        # Add to history
        state.history.append(turn)

        # Trim history if needed
        if len(state.history) > self.max_history:
            state.history = state.history[-self.max_history:]

        # Store in semantic memory if available
        if self.memory:
            # Store user input
            self.memory.store(
                content=user_input,
                session_id=session_id,
                user_id=state.user_id,
                intent=intent,
                entities=slots,
                source="conversation",
                turn_id=turn.id
            )

            # Store assistant response (usually lower importance unless it contains facts)
            self.memory.store(
                content=assistant_response,
                session_id=session_id,
                user_id=state.user_id,
                source="conversation",
                turn_id=turn.id,
                importance=0.3
            )

        return turn

    def get_context_for_llm(self, session_id: str, max_turns: int = 5) -> str:
        """Format history for LLM context window"""
        state = self.get_or_create_state(session_id)
        turns = state.history[-max_turns:]

        context_lines = []
        for turn in turns:
            context_lines.append(f"User: {turn.user_input}")
            context_lines.append(f"Assistant: {turn.assistant_response}")

        return "\n".join(context_lines)

    def retrieve_relevant_memories(
        self,
        query: str,
        session_id: str,
        top_k: int = 3
    ) -> List[RetrievedMemory]:
        """Retrieve relevant memories for the current context"""
        if not self.memory:
            return []

        state = self.get_or_create_state(session_id)

        return self.memory.retrieve(
            query=query,
            top_k=top_k,
            user_id=state.user_id
            # We don't filter by session_id to allow cross-session recall
        )

    def clear_state(self, session_id: str) -> bool:
        """Clear state for a session"""
        if session_id in self._states:
            del self._states[session_id]
            if self._active_session == session_id:
                self._active_session = None
            return True
        return False

def create_dialogue_manager(memory: Optional[SemanticMemory] = None) -> DialogueStateManager:
    """Factory function to create DialogueStateManager"""
    return DialogueStateManager(memory=memory)
