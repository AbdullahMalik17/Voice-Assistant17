"""
Context Manager
Manages conversation contexts with 5-exchange memory, timeout tracking, and topic shift detection
"""

import re
import time
from collections import Counter
from datetime import datetime
from typing import Dict, List, Optional, Set
from uuid import UUID, uuid4

from ..core.config import Config
from ..models.conversation_context import ConversationContext, ContextStatus
from ..models.intent import Intent
from ..storage.encrypted_store import EncryptedStore
from ..storage.memory_store import MemoryStore
from ..utils.logger import EventLogger, MetricsLogger


class ContextManager:
    """
    Manages conversation contexts with FIFO queue, timeout tracking, and topic shift detection
    """

    def __init__(
        self,
        config: Config,
        logger: EventLogger,
        metrics_logger: MetricsLogger,
        memory_store: Optional[MemoryStore] = None,
        encrypted_store: Optional[EncryptedStore] = None
    ):
        self.config = config
        self.logger = logger
        self.metrics_logger = metrics_logger
        self.memory_store = memory_store or MemoryStore()
        self.encrypted_store = encrypted_store

        # Active context (only one conversation at a time for voice assistant)
        self.current_context: Optional[ConversationContext] = None

        # Configuration
        self.max_exchanges = config.context.max_exchanges
        self.timeout_seconds = config.context.timeout_seconds
        self.topic_shift_threshold = config.context.topic_shift_threshold
        self.persistence_enabled = config.context.enable_persistence

        # Common stopwords for keyword extraction
        self.stopwords = self._load_stopwords()

    def _load_stopwords(self) -> Set[str]:
        """Load common stopwords for keyword extraction"""
        return {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'should', 'could', 'may', 'might', 'can', 'shall', 'must', 'i', 'you',
            'he', 'she', 'it', 'we', 'they', 'them', 'their', 'this', 'that',
            'these', 'those', 'what', 'which', 'who', 'when', 'where', 'why', 'how'
        }

    def get_or_create_context(self) -> ConversationContext:
        """Get current context or create new one if expired/none"""
        # Check if current context exists and is valid
        if self.current_context:
            if self.current_context.is_expired():
                self._expire_context()
            else:
                return self.current_context

        # Create new context
        self.current_context = ConversationContext(
            timeout_seconds=self.timeout_seconds
        )

        self.logger.info(
            event='CONTEXT_CREATED',
            message='New conversation context created',
            context_id=str(self.current_context.id),
            session_id=str(self.current_context.session_id)
        )

        return self.current_context

    def add_exchange(
        self,
        user_input: str,
        intent: Intent,
        assistant_response: str,
        confidence: float
    ) -> None:
        """Add exchange to current context with topic shift detection"""
        start_time = time.time()

        # Get or create context
        context = self.get_or_create_context()

        # Extract keywords from user input
        new_keywords = self._extract_keywords(user_input)

        # Check for topic shift
        if context.has_topic_shift(new_keywords, self.topic_shift_threshold):
            self.logger.info(
                event='TOPIC_SHIFT_DETECTED',
                message='Topic shift detected, resetting context',
                old_keywords=context.topic_keywords,
                new_keywords=new_keywords,
                similarity=self._calculate_similarity(context.topic_keywords, new_keywords)
            )
            context.reset()

            # Record metric
            self.metrics_logger.record_metric('context_topic_shifts', 1)

        # Update topic keywords
        context.update_topic_keywords(new_keywords)

        # Add exchange to context
        context.add_exchange(
            user_input=user_input,
            user_intent_id=intent.id,
            assistant_response=assistant_response,
            confidence=confidence
        )

        # Persist if enabled
        if self.persistence_enabled and self.encrypted_store:
            self._persist_context(context)

        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)

        # Log event
        self.logger.info(
            event='CONTEXT_EXCHANGE_ADDED',
            message=f'Exchange added to context (total: {len(context.exchanges)})',
            context_id=str(context.id),
            exchange_count=len(context.exchanges),
            topic_keywords=new_keywords,
            processing_time_ms=duration_ms
        )

        # Record metrics
        self.metrics_logger.record_metric('context_exchange_count', len(context.exchanges))
        self.metrics_logger.record_metric('context_update_latency_ms', duration_ms)

    def get_context_for_llm(self) -> Optional[str]:
        """Get context summary for LLM prompt"""
        if not self.current_context or not self.current_context.exchanges:
            return None

        # Check expiration
        if self.current_context.is_expired():
            self._expire_context()
            return None

        return self.current_context.get_context_summary()

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from text for topic detection"""
        # Convert to lowercase
        text_lower = text.lower()

        # Remove punctuation and split into words
        words = re.findall(r'\b[a-z]{3,}\b', text_lower)

        # Remove stopwords
        keywords = [w for w in words if w not in self.stopwords]

        # Get most common keywords (max 10)
        if len(keywords) > 10:
            counter = Counter(keywords)
            keywords = [word for word, _ in counter.most_common(10)]

        return keywords

    def _calculate_similarity(self, keywords1: List[str], keywords2: List[str]) -> float:
        """Calculate Jaccard similarity between two keyword sets"""
        if not keywords1 or not keywords2:
            return 0.0

        set1 = set(keywords1)
        set2 = set(keywords2)

        intersection = len(set1 & set2)
        union = len(set1 | set2)

        if union == 0:
            return 0.0

        return intersection / union

    def _expire_context(self) -> None:
        """Expire current context due to timeout"""
        if not self.current_context:
            return

        self.current_context.expire()

        self.logger.info(
            event='CONTEXT_EXPIRED',
            message='Conversation context expired due to timeout',
            context_id=str(self.current_context.id),
            last_activity=self.current_context.last_activity.isoformat(),
            exchange_count=len(self.current_context.exchanges)
        )

        # Clear current context
        self.current_context = None

        # Record metric
        self.metrics_logger.record_metric('context_expirations', 1)

    def interrupt_context(self) -> None:
        """Interrupt current context (e.g., wake word during processing)"""
        if not self.current_context:
            return

        self.current_context.interrupt()

        self.logger.info(
            event='CONTEXT_INTERRUPTED',
            message='Conversation context interrupted',
            context_id=str(self.current_context.id)
        )

        # Clear current context
        self.current_context = None

        # Record metric
        self.metrics_logger.record_metric('context_interruptions', 1)

    def reset_context(self) -> None:
        """Manually reset current context"""
        if not self.current_context:
            return

        self.current_context.reset()

        self.logger.info(
            event='CONTEXT_RESET',
            message='Conversation context manually reset',
            context_id=str(self.current_context.id)
        )

        # Record metric
        self.metrics_logger.record_metric('context_resets', 1)

    def _persist_context(self, context: ConversationContext) -> None:
        """Persist context to encrypted storage"""
        if not self.encrypted_store:
            return

        try:
            # Convert context to JSON
            context_data = context.model_dump_json()

            # Store with session ID as key
            self.encrypted_store.set(
                key=f"context_{context.session_id}",
                value=context_data
            )

            self.logger.debug(
                event='CONTEXT_PERSISTED',
                message='Context persisted to encrypted storage',
                context_id=str(context.id),
                session_id=str(context.session_id)
            )

        except Exception as e:
            self.logger.error(
                event='CONTEXT_PERSISTENCE_FAILED',
                message=f'Failed to persist context: {str(e)}',
                error=str(e)
            )

    def load_context(self, session_id: UUID) -> Optional[ConversationContext]:
        """Load context from encrypted storage"""
        if not self.encrypted_store or not self.persistence_enabled:
            return None

        try:
            # Load context data
            context_data = self.encrypted_store.get(f"context_{session_id}")

            if not context_data:
                return None

            # Parse JSON to ConversationContext
            context = ConversationContext.model_validate_json(context_data)

            # Check if expired
            if context.is_expired():
                return None

            self.logger.info(
                event='CONTEXT_LOADED',
                message='Context loaded from encrypted storage',
                context_id=str(context.id),
                session_id=str(context.session_id),
                exchange_count=len(context.exchanges)
            )

            return context

        except Exception as e:
            self.logger.error(
                event='CONTEXT_LOAD_FAILED',
                message=f'Failed to load context: {str(e)}',
                error=str(e)
            )
            return None

    def get_context_stats(self) -> Dict[str, any]:
        """Get statistics about current context"""
        if not self.current_context:
            return {
                'active': False,
                'exchanges': 0,
                'status': 'NONE'
            }

        return {
            'active': self.current_context.is_active,
            'exchanges': len(self.current_context.exchanges),
            'status': self.current_context.status.value,
            'last_activity': self.current_context.last_activity.isoformat(),
            'topic_keywords': self.current_context.topic_keywords,
            'session_id': str(self.current_context.session_id)
        }


def create_context_manager(
    config: Config,
    logger: EventLogger,
    metrics_logger: MetricsLogger,
    memory_store: Optional[MemoryStore] = None,
    encrypted_store: Optional[EncryptedStore] = None
) -> ContextManager:
    """Factory function to create context manager"""
    manager = ContextManager(
        config=config,
        logger=logger,
        metrics_logger=metrics_logger,
        memory_store=memory_store,
        encrypted_store=encrypted_store
    )
    return manager
