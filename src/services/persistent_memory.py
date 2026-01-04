"""
Persistent Memory Service using Mem0
Provides long-term conversational memory for the voice assistant.
"""

from typing import List, Dict, Optional
import logging
import os
from mem0 import MemoryClient

logger = logging.getLogger(__name__)


class PersistentMemoryService:
    """
    Manages persistent conversational memory using Mem0.
    Stores user preferences, past conversations, and context across sessions.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the persistent memory service.

        Args:
            api_key: Optional Mem0 API key for cloud storage
        """
        try:
            # Initialize Mem0 Client
            # If API key is provided, use it; otherwise check environment variable
            if not api_key:
                api_key = os.getenv("MEM0_API_KEY")

            if api_key:
                self.client = MemoryClient(api_key=api_key)
                logger.info("Persistent memory service initialized with Mem0 Cloud")
            else:
                raise ValueError("MEM0_API_KEY not provided. Set it in .env or pass as parameter.")

        except Exception as e:
            logger.error(f"Failed to initialize persistent memory: {e}")
            raise

    def add_conversation(
        self,
        user_message: str,
        assistant_message: str,
        user_id: str = "default_user",
        session_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Store a conversation turn in long-term memory.

        Args:
            user_message: The user's message
            assistant_message: The assistant's response
            user_id: Unique identifier for the user
            session_id: Optional session identifier
            metadata: Optional metadata (intent, confidence, etc.)
        """
        try:
            # Build conversation messages
            messages = [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": assistant_message}
            ]

            # Add to mem0 with user context
            # Note: session_id is not a standard parameter in Mem0 API
            self.client.add(
                messages,
                user_id=user_id,
                metadata=metadata or {}
            )
            logger.debug(f"Stored conversation for user {user_id}")

        except Exception as e:
            logger.error(f"Failed to store conversation: {e}")

    def retrieve_relevant_memories(
        self,
        query: str,
        user_id: str = "default_user",
        session_id: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict]:
        """
        Retrieve relevant memories based on the current query.

        Args:
            query: The current user query/message
            user_id: Unique identifier for the user
            session_id: Optional session identifier
            limit: Maximum number of memories to retrieve

        Returns:
            List of relevant memory entries with content and metadata
        """
        try:
            # Search for relevant memories with proper filters format
            # Note: session_id is not a standard parameter in Mem0 API
            filters = {
                "AND": [
                    {"user_id": user_id}
                ]
            }

            results = self.client.search(
                query=query,
                filters=filters,
                limit=limit
            )

            # Extract memories from results
            memories = []
            if results and "results" in results:
                for entry in results["results"]:
                    memories.append({
                        "memory": entry.get("memory", ""),
                        "score": entry.get("score", 0.0),
                        "metadata": entry.get("metadata", {})
                    })

            logger.debug(f"Retrieved {len(memories)} relevant memories for user {user_id}")
            return memories

        except Exception as e:
            logger.error(f"Failed to retrieve memories: {e}")
            return []

    def get_memory_context(
        self,
        query: str,
        user_id: str = "default_user",
        session_id: Optional[str] = None,
        limit: int = 5
    ) -> str:
        """
        Get formatted memory context to include in LLM prompts.

        Args:
            query: The current user query
            user_id: Unique identifier for the user
            session_id: Optional session identifier
            limit: Maximum number of memories to include

        Returns:
            Formatted string with relevant memories
        """
        memories = self.retrieve_relevant_memories(query, user_id, session_id, limit)

        if not memories:
            return ""

        # Format memories for LLM context
        context_parts = ["Relevant past context:"]
        for mem in memories:
            context_parts.append(f"- {mem['memory']}")

        return "\n".join(context_parts)

    def clear_user_memory(self, user_id: str) -> None:
        """
        Clear all memories for a specific user.

        Args:
            user_id: Unique identifier for the user
        """
        try:
            # Mem0 doesn't have a direct clear method, so we'd need to
            # delete individual memories or use the reset method if available
            logger.warning(f"Memory clearing requested for user {user_id} but not fully implemented")
        except Exception as e:
            logger.error(f"Failed to clear memories: {e}")

    def get_all_memories(
        self,
        user_id: str = "default_user",
        session_id: Optional[str] = None
    ) -> List[Dict]:
        """
        Get all memories for a user (for debugging/admin purposes).

        Args:
            user_id: Unique identifier for the user
            session_id: Optional session identifier

        Returns:
            List of all memory entries
        """
        try:
            get_kwargs = {"user_id": user_id}
            if session_id:
                get_kwargs["session_id"] = session_id

            results = self.client.get_all(**get_kwargs)
            return results if results else []

        except Exception as e:
            logger.error(f"Failed to get all memories: {e}")
            return []
