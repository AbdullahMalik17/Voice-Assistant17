"""Supabase conversation persistence service"""

import os
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
import asyncio

from supabase import create_client, Client
from src.models.conversation import (
    ConversationSession,
    ConversationTurn,
    ConversationSessionCreate,
    ConversationTurnCreate
)

logger = logging.getLogger(__name__)


class SupabaseConversationService:
    """Service for persisting conversations to Supabase PostgreSQL database"""

    def __init__(self, supabase_url: Optional[str] = None, supabase_key: Optional[str] = None):
        """
        Initialize Supabase client

        Args:
            supabase_url: Supabase project URL (defaults to SUPABASE_URL env var)
            supabase_key: Supabase service role key (defaults to SUPABASE_SERVICE_ROLE_KEY env var)
        """
        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        self.supabase_key = supabase_key or os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not self.supabase_url or not self.supabase_key:
            logger.warning(
                "Supabase credentials not configured. "
                "Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables."
            )
            self.client: Optional[Client] = None
        else:
            try:
                self.client: Client = create_client(self.supabase_url, self.supabase_key)
                logger.info("Supabase conversation service initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")
                self.client = None

    def is_available(self) -> bool:
        """Check if Supabase service is available"""
        return self.client is not None

    async def create_session(
        self,
        user_id: str,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Create new conversation session

        Args:
            user_id: UUID of the authenticated user
            title: Optional session title
            metadata: Optional metadata dict

        Returns:
            session_id (UUID as string) on success, None on error
        """
        if not self.is_available():
            logger.warning("Supabase not available, skipping session creation")
            return None

        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.client.table("conversation_sessions").insert({
                    "user_id": user_id,
                    "title": title or f"Conversation {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    "state": "active",
                    "metadata": metadata or {}
                }).execute()
            )

            if result.data and len(result.data) > 0:
                session_id = result.data[0]["session_id"]
                logger.info(f"Created conversation session: {session_id} for user: {user_id}")
                return str(session_id)
            else:
                logger.error("Failed to create session: No data returned")
                return None

        except Exception as e:
            logger.error(f"Error creating conversation session: {e}", exc_info=True)
            return None

    async def add_turn(
        self,
        session_id: str,
        user_input: str,
        assistant_response: str,
        intent: Optional[str] = None,
        intent_confidence: float = 0.0,
        entities: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Add conversation turn to existing session

        Args:
            session_id: UUID of the session
            user_input: User's message
            assistant_response: Assistant's response
            intent: Detected intent type
            intent_confidence: Confidence score (0.0-1.0)
            entities: Extracted entities dict

        Returns:
            True on success, False on error
        """
        if not self.is_available():
            logger.warning("Supabase not available, skipping turn save")
            return False

        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.client.table("conversation_turns").insert({
                    "session_id": session_id,
                    "user_input": user_input,
                    "assistant_response": assistant_response,
                    "intent": intent,
                    "intent_confidence": intent_confidence,
                    "entities": entities or {}
                }).execute()
            )

            if result.data and len(result.data) > 0:
                # Also update session's last_updated timestamp
                await loop.run_in_executor(
                    None,
                    lambda: self.client.table("conversation_sessions")
                    .update({"last_updated": datetime.now().isoformat()})
                    .eq("session_id", session_id)
                    .execute()
                )
                logger.debug(f"Added turn to session: {session_id}")
                return True
            else:
                logger.error("Failed to add turn: No data returned")
                return False

        except Exception as e:
            logger.error(f"Error adding conversation turn: {e}", exc_info=True)
            return False

    async def get_session(
        self,
        session_id: str,
        user_id: str
    ) -> Optional[ConversationSession]:
        """
        Retrieve session by ID (with RLS enforcement via user_id)

        Args:
            session_id: UUID of the session
            user_id: UUID of the user (for RLS check)

        Returns:
            ConversationSession or None
        """
        if not self.is_available():
            return None

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.client.table("conversation_sessions")
                .select("*")
                .eq("session_id", session_id)
                .eq("user_id", user_id)
                .execute()
            )

            if result.data and len(result.data) > 0:
                return ConversationSession(**result.data[0])
            return None

        except Exception as e:
            logger.error(f"Error getting session: {e}", exc_info=True)
            return None

    async def list_sessions(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[ConversationSession]:
        """
        List user's conversation sessions (most recent first)

        Args:
            user_id: UUID of the user
            limit: Max number of sessions to return
            offset: Number of sessions to skip

        Returns:
            List of ConversationSession objects
        """
        if not self.is_available():
            return []

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.client.table("conversation_sessions")
                .select("*")
                .eq("user_id", user_id)
                .order("last_updated", desc=True)
                .range(offset, offset + limit - 1)
                .execute()
            )

            if result.data:
                return [ConversationSession(**session) for session in result.data]
            return []

        except Exception as e:
            logger.error(f"Error listing sessions: {e}", exc_info=True)
            return []

    async def get_turns(
        self,
        session_id: str,
        user_id: str
    ) -> List[ConversationTurn]:
        """
        Get all turns for a session (with RLS check)

        Args:
            session_id: UUID of the session
            user_id: UUID of the user (to verify ownership)

        Returns:
            List of ConversationTurn objects, ordered by timestamp
        """
        if not self.is_available():
            return []

        try:
            # First verify user owns this session
            session = await self.get_session(session_id, user_id)
            if not session:
                logger.warning(f"Session {session_id} not found or unauthorized for user {user_id}")
                return []

            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.client.table("conversation_turns")
                .select("*")
                .eq("session_id", session_id)
                .order("timestamp", desc=False)
                .execute()
            )

            if result.data:
                return [ConversationTurn(**turn) for turn in result.data]
            return []

        except Exception as e:
            logger.error(f"Error getting turns: {e}", exc_info=True)
            return []

    async def delete_session(
        self,
        session_id: str,
        user_id: str
    ) -> bool:
        """
        Delete a conversation session (cascades to turns via DB constraint)

        Args:
            session_id: UUID of the session
            user_id: UUID of the user (for RLS check)

        Returns:
            True on success, False on error
        """
        if not self.is_available():
            return False

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.client.table("conversation_sessions")
                .delete()
                .eq("session_id", session_id)
                .eq("user_id", user_id)
                .execute()
            )

            if result.data:
                logger.info(f"Deleted session: {session_id}")
                return True
            return False

        except Exception as e:
            logger.error(f"Error deleting session: {e}", exc_info=True)
            return False

    async def update_session_title(
        self,
        session_id: str,
        user_id: str,
        title: str
    ) -> bool:
        """
        Update session title

        Args:
            session_id: UUID of the session
            user_id: UUID of the user (for RLS check)
            title: New title

        Returns:
            True on success, False on error
        """
        if not self.is_available():
            return False

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.client.table("conversation_sessions")
                .update({"title": title})
                .eq("session_id", session_id)
                .eq("user_id", user_id)
                .execute()
            )

            if result.data:
                logger.info(f"Updated title for session: {session_id}")
                return True
            return False

        except Exception as e:
            logger.error(f"Error updating session title: {e}", exc_info=True)
            return False
