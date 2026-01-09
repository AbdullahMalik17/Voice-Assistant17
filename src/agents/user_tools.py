"""
User Data Access Tools
Provides agent tools to access user profile, preferences, and conversation history.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging

from .tools import Tool, ToolParameter, ToolResult

logger = logging.getLogger(__name__)


class SearchConversationHistoryTool(Tool):
    """
    Tool for agent to search through user's past conversations.

    Usage examples:
        - "What did we talk about yesterday?"
        - "When did I ask about weather?"
        - "Find conversations about emails"
    """

    name = "search_conversation_history"
    description = (
        "Search through the user's past conversations for specific topics, keywords, or timeframes. "
        "Useful when the user asks about previous interactions or wants to recall past discussions."
    )

    parameters = [
        ToolParameter(
            name="query",
            type="string",
            description="The search query or topic to find in past conversations",
            required=True
        ),
        ToolParameter(
            name="days_back",
            type="integer",
            description="How many days back to search (default: 7)",
            required=False
        ),
        ToolParameter(
            name="limit",
            type="integer",
            description="Maximum number of results to return (default: 5)",
            required=False
        )
    ]

    requires_confirmation = False

    def __init__(self, sqlite_store=None):
        """
        Initialize tool with SQLite store reference.

        Args:
            sqlite_store: SqliteStore instance for database access
        """
        self.sqlite_store = sqlite_store

    def execute(
        self,
        query: str,
        days_back: int = 7,
        limit: int = 5,
        user_id: str = "default",
        **kwargs
    ) -> ToolResult:
        """
        Search conversation history for matching turns.

        Args:
            query: Search term or topic
            days_back: Number of days to search back
            limit: Maximum results to return
            user_id: User identifier

        Returns:
            ToolResult with matching conversation turns
        """
        try:
            if not self.sqlite_store:
                return ToolResult(
                    success=False,
                    data={},
                    message="Conversation history is not available",
                    error="SQLite store not initialized"
                )

            # Calculate cutoff date
            cutoff_date = datetime.now() - timedelta(days=days_back)

            # Get user's recent sessions
            sessions = self.sqlite_store.get_user_sessions(user_id, limit=50)

            # Search through turns
            results = []
            query_lower = query.lower()

            for session in sessions:
                # Check if session is within timeframe
                session_date = datetime.fromisoformat(session['last_updated'])
                if session_date < cutoff_date:
                    continue

                # Get session details
                session_data = self.sqlite_store.get_session(session['session_id'])
                if not session_data or 'turns' not in session_data:
                    continue

                # Search turns
                for turn in session_data['turns']:
                    # Case-insensitive search
                    if (query_lower in turn['user_input'].lower() or
                        query_lower in turn['assistant_response'].lower()):

                        results.append({
                            "session_id": session['session_id'],
                            "timestamp": turn['timestamp'],
                            "user_input": turn['user_input'],
                            "assistant_response": turn['assistant_response'],
                            "intent": turn.get('intent', 'unknown'),
                            "confidence": turn.get('intent_confidence', 0.0)
                        })

                        if len(results) >= limit:
                            break

                if len(results) >= limit:
                    break

            if not results:
                return ToolResult(
                    success=True,
                    data={"results": [], "count": 0},
                    message=f"No conversations found matching '{query}' in the last {days_back} days"
                )

            # Format results message
            result_summary = f"Found {len(results)} conversation(s) matching '{query}':\n"
            for i, result in enumerate(results, 1):
                timestamp = datetime.fromisoformat(result['timestamp']).strftime("%Y-%m-%d %H:%M")
                result_summary += f"\n{i}. [{timestamp}] User: {result['user_input'][:100]}..."

            return ToolResult(
                success=True,
                data={
                    "results": results,
                    "count": len(results),
                    "query": query,
                    "days_searched": days_back
                },
                message=result_summary
            )

        except Exception as e:
            logger.error(f"Error searching conversation history: {e}")
            return ToolResult(
                success=False,
                data={},
                message=f"Failed to search conversation history: {str(e)}",
                error=str(e)
            )


class GetRecentConversationsTool(Tool):
    """
    Tool to retrieve user's recent conversation sessions.

    Usage examples:
        - "Show me my recent conversations"
        - "What did we talk about recently?"
    """

    name = "get_recent_conversations"
    description = (
        "Retrieve the user's most recent conversation sessions with summaries. "
        "Useful when the user wants to review or continue previous discussions."
    )

    parameters = [
        ToolParameter(
            name="limit",
            type="integer",
            description="Number of recent conversations to retrieve (default: 5)",
            required=False
        )
    ]

    requires_confirmation = False

    def __init__(self, sqlite_store=None):
        """
        Initialize tool with SQLite store reference.

        Args:
            sqlite_store: SqliteStore instance for database access
        """
        self.sqlite_store = sqlite_store

    def execute(
        self,
        limit: int = 5,
        user_id: str = "default",
        **kwargs
    ) -> ToolResult:
        """
        Get recent conversation sessions.

        Args:
            limit: Number of sessions to retrieve
            user_id: User identifier

        Returns:
            ToolResult with recent sessions
        """
        try:
            if not self.sqlite_store:
                return ToolResult(
                    success=False,
                    data={},
                    message="Conversation history is not available",
                    error="SQLite store not initialized"
                )

            # Get recent sessions
            sessions = self.sqlite_store.get_user_sessions(user_id, limit)

            if not sessions:
                return ToolResult(
                    success=True,
                    data={"sessions": [], "count": 0},
                    message="No previous conversations found"
                )

            # Enrich with turn counts
            enriched_sessions = []
            for session in sessions:
                session_data = self.sqlite_store.get_session(session['session_id'])
                turn_count = len(session_data.get('turns', [])) if session_data else 0

                # Get first user input as preview
                preview = "No messages"
                if session_data and session_data.get('turns'):
                    first_turn = session_data['turns'][0]
                    preview = first_turn.get('user_input', '')[:100]

                enriched_sessions.append({
                    "session_id": session['session_id'],
                    "created_at": session['created_at'],
                    "last_updated": session['last_updated'],
                    "turn_count": turn_count,
                    "preview": preview,
                    "current_intent": session.get('current_intent', 'unknown')
                })

            # Format summary
            summary = f"Found {len(enriched_sessions)} recent conversation(s):\n"
            for i, session in enumerate(enriched_sessions, 1):
                date = datetime.fromisoformat(session['last_updated']).strftime("%Y-%m-%d %H:%M")
                summary += f"\n{i}. [{date}] {session['turn_count']} messages - {session['preview']}"

            return ToolResult(
                success=True,
                data={
                    "sessions": enriched_sessions,
                    "count": len(enriched_sessions)
                },
                message=summary
            )

        except Exception as e:
            logger.error(f"Error retrieving recent conversations: {e}")
            return ToolResult(
                success=False,
                data={},
                message=f"Failed to retrieve conversations: {str(e)}",
                error=str(e)
            )
