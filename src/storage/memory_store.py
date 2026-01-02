"""
In-Memory Storage Implementation
Default storage backend for conversation context and event logs
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from ..models.conversation_context import ConversationContext
from ..models.event_log import EventLog


class MemoryStore:
    """
    In-memory storage for conversation contexts and event logs
    Data is not persisted and will be lost on application restart
    """

    def __init__(self, max_contexts: int = 10, max_events: int = 1000):
        self.max_contexts = max_contexts
        self.max_events = max_events

        # Storage
        self._contexts: Dict[UUID, ConversationContext] = {}
        self._events: List[EventLog] = []

        # Active session tracking
        self._active_session_id: Optional[UUID] = None

    # ===========================
    # Conversation Context Operations
    # ===========================

    def save_context(self, context: ConversationContext) -> None:
        """Save or update conversation context"""
        # Enforce max contexts limit (LRU)
        if len(self._contexts) >= self.max_contexts and context.id not in self._contexts:
            # Remove oldest context
            oldest = min(self._contexts.values(), key=lambda c: c.last_activity)
            del self._contexts[oldest.id]

        self._contexts[context.id] = context

    def get_context(self, context_id: UUID) -> Optional[ConversationContext]:
        """Get conversation context by ID"""
        return self._contexts.get(context_id)

    def get_active_context(self) -> Optional[ConversationContext]:
        """Get the current active conversation context"""
        if self._active_session_id is None:
            return None

        # Find context by session ID
        for context in self._contexts.values():
            if context.session_id == self._active_session_id and context.is_active:
                return context

        return None

    def set_active_session(self, session_id: UUID) -> None:
        """Set the active session ID"""
        self._active_session_id = session_id

    def get_context_by_session(self, session_id: UUID) -> Optional[ConversationContext]:
        """Get conversation context by session ID"""
        for context in self._contexts.values():
            if context.session_id == session_id:
                return context
        return None

    def delete_context(self, context_id: UUID) -> bool:
        """Delete conversation context"""
        if context_id in self._contexts:
            del self._contexts[context_id]
            return True
        return False

    def clear_expired_contexts(self) -> int:
        """Remove expired contexts and return count"""
        expired_ids = []

        for context_id, context in self._contexts.items():
            if context.is_expired():
                expired_ids.append(context_id)

        for context_id in expired_ids:
            del self._contexts[context_id]

        return len(expired_ids)

    def get_all_contexts(self) -> List[ConversationContext]:
        """Get all conversation contexts"""
        return list(self._contexts.values())

    def get_context_count(self) -> int:
        """Get total number of stored contexts"""
        return len(self._contexts)

    # ===========================
    # Event Log Operations
    # ===========================

    def add_event(self, event: EventLog) -> None:
        """Add event log entry"""
        self._events.append(event)

        # Enforce max events limit (FIFO)
        if len(self._events) > self.max_events:
            self._events = self._events[-self.max_events:]

    def get_event(self, event_id: UUID) -> Optional[EventLog]:
        """Get event log by ID"""
        for event in self._events:
            if event.id == event_id:
                return event
        return None

    def get_events(
        self,
        limit: int = 100,
        offset: int = 0,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[EventLog]:
        """
        Get event logs with filtering and pagination
        Returns events in reverse chronological order (newest first)
        """
        # Start with all events
        filtered = self._events.copy()

        # Apply filters
        if event_type:
            filtered = [e for e in filtered if e.event_type.value == event_type]

        if severity:
            filtered = [e for e in filtered if e.severity.value == severity]

        if start_time:
            filtered = [e for e in filtered if e.timestamp >= start_time]

        if end_time:
            filtered = [e for e in filtered if e.timestamp <= end_time]

        # Sort by timestamp (newest first)
        filtered.sort(key=lambda e: e.timestamp, reverse=True)

        # Apply pagination
        return filtered[offset:offset + limit]

    def get_recent_events(self, count: int = 10) -> List[EventLog]:
        """Get N most recent events"""
        return sorted(self._events, key=lambda e: e.timestamp, reverse=True)[:count]

    def delete_event(self, event_id: UUID) -> bool:
        """Delete event log"""
        for i, event in enumerate(self._events):
            if event.id == event_id:
                self._events.pop(i)
                return True
        return False

    def clear_events(self) -> int:
        """Clear all event logs and return count"""
        count = len(self._events)
        self._events.clear()
        return count

    def get_event_count(self) -> int:
        """Get total number of events"""
        return len(self._events)

    def get_event_stats(self) -> Dict[str, Any]:
        """Get event statistics"""
        stats = {
            "total": len(self._events),
            "by_type": {},
            "by_severity": {},
            "success_rate": 0.0
        }

        if not self._events:
            return stats

        # Count by type
        for event in self._events:
            event_type = event.event_type.value
            stats["by_type"][event_type] = stats["by_type"].get(event_type, 0) + 1

        # Count by severity
        for event in self._events:
            severity = event.severity.value
            stats["by_severity"][severity] = stats["by_severity"].get(severity, 0) + 1

        # Calculate success rate
        success_count = len([e for e in self._events if e.success])
        stats["success_rate"] = (success_count / len(self._events)) * 100

        return stats

    # ===========================
    # General Operations
    # ===========================

    def clear_all(self) -> None:
        """Clear all stored data"""
        self._contexts.clear()
        self._events.clear()
        self._active_session_id = None

    def get_storage_stats(self) -> Dict[str, Any]:
        """Get overall storage statistics"""
        return {
            "contexts": {
                "count": len(self._contexts),
                "max": self.max_contexts,
                "active": len([c for c in self._contexts.values() if c.is_active])
            },
            "events": {
                "count": len(self._events),
                "max": self.max_events
            },
            "active_session_id": str(self._active_session_id) if self._active_session_id else None
        }


# Global memory store instance
_memory_store: Optional[MemoryStore] = None


def get_memory_store(
    max_contexts: int = 10,
    max_events: int = 1000
) -> MemoryStore:
    """Get or create global memory store instance"""
    global _memory_store
    if _memory_store is None:
        _memory_store = MemoryStore(
            max_contexts=max_contexts,
            max_events=max_events
        )
    return _memory_store
