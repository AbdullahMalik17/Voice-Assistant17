/**
 * React hooks for querying conversation history from SQLite backend
 */

import { useState, useEffect, useCallback } from 'react';

// API base URL
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface ConversationSession {
  session_id: string;
  user_id: string;
  title?: string;
  created_at: string;
  last_updated: string;
  state: string;
  current_intent?: string;
  metadata: Record<string, any>;
}

export interface ConversationTurn {
  turn_id: string;
  session_id: string;
  user_input: string;
  assistant_response: string;
  intent?: string;
  intent_confidence: number;
  entities: Record<string, any>;
  timestamp: string;
}

/**
 * Hook to fetch conversation sessions for a user
 */
export function useConversations(userId?: string) {
  const [sessions, setSessions] = useState<ConversationSession[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchSessions = useCallback(async () => {
    if (!userId) {
      setSessions([]);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/conversations?user_id=${encodeURIComponent(userId)}&limit=20`,
        {
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch conversations: ${response.statusText}`);
      }

      const result = await response.json();
      setSessions(result.sessions || []);
    } catch (err) {
      console.error('Error fetching conversations:', err);
      setError(err instanceof Error ? err : new Error('Failed to fetch conversations'));
      setSessions([]);
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  return {
    sessions,
    loading,
    error,
    refetch: fetchSessions,
  };
}

/**
 * Hook to fetch conversation turns for a specific session
 */
export function useConversationTurns(sessionId?: string, userId?: string) {
  const [turns, setTurns] = useState<ConversationTurn[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchTurns = useCallback(async () => {
    if (!sessionId) {
      setTurns([]);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/conversations/${encodeURIComponent(sessionId)}?user_id=${encodeURIComponent(userId || 'default')}`,
        {
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Session not found');
        } else if (response.status === 403) {
          throw new Error('Unauthorized: You do not own this session');
        }
        throw new Error(`Failed to fetch conversation: ${response.statusText}`);
      }

      const result = await response.json();
      const sessionData = result.session;

      // Extract turns from session data
      if (sessionData && sessionData.turns) {
        setTurns(sessionData.turns);
      } else {
        setTurns([]);
      }
    } catch (err) {
      console.error('Error fetching conversation turns:', err);
      setError(err instanceof Error ? err : new Error('Failed to fetch conversation turns'));
      setTurns([]);
    } finally {
      setLoading(false);
    }
  }, [sessionId, userId]);

  useEffect(() => {
    fetchTurns();
  }, [fetchTurns]);

  return {
    turns,
    loading,
    error,
    refetch: fetchTurns,
  };
}

/**
 * Hook to delete a conversation session
 */
export function useDeleteConversation() {
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const deleteSession = useCallback(async (sessionId: string, userId: string) => {
    setDeleting(true);
    setError(null);

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/conversations/${encodeURIComponent(sessionId)}?user_id=${encodeURIComponent(userId)}`,
        {
          method: 'DELETE',
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('Session not found');
        } else if (response.status === 403) {
          throw new Error('Unauthorized: You do not own this session');
        }
        throw new Error(`Failed to delete conversation: ${response.statusText}`);
      }

      return true;
    } catch (err) {
      console.error('Error deleting conversation:', err);
      setError(err instanceof Error ? err : new Error('Failed to delete conversation'));
      return false;
    } finally {
      setDeleting(false);
    }
  }, []);

  return {
    deleteSession,
    deleting,
    error,
  };
}

/**
 * Hook to update conversation session title
 */
export function useUpdateConversationTitle() {
  const [updating, setUpdating] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const updateTitle = useCallback(async (
    sessionId: string,
    userId: string,
    title: string
  ) => {
    setUpdating(true);
    setError(null);

    try {
      // NOTE: Update title endpoint not yet implemented in backend
      // For now, this is a placeholder that always succeeds
      console.log(`Update title requested for session ${sessionId}: ${title}`);
      return true;
    } catch (err) {
      console.error('Error updating conversation title:', err);
      setError(err instanceof Error ? err : new Error('Failed to update conversation title'));
      return false;
    } finally {
      setUpdating(false);
    }
  }, []);

  return {
    updateTitle,
    updating,
    error,
  };
}
