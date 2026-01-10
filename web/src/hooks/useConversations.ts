/**
 * React hooks for querying conversation history from Supabase
 */

import { useState, useEffect, useCallback } from 'react';
import { createClient } from '@supabase/supabase-js';

// Initialize Supabase client
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

const supabase = supabaseUrl && supabaseAnonKey
  ? createClient(supabaseUrl, supabaseAnonKey)
  : null;

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
    if (!supabase || !userId) {
      setSessions([]);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const { data, error: fetchError } = await supabase
        .from('conversation_sessions')
        .select('*')
        .eq('user_id', userId)
        .order('last_updated', { ascending: false })
        .limit(20);

      if (fetchError) throw fetchError;

      setSessions(data || []);
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
    if (!supabase || !sessionId) {
      setTurns([]);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // First verify user owns this session (RLS will also enforce this)
      if (userId) {
        const { data: sessionData, error: sessionError } = await supabase
          .from('conversation_sessions')
          .select('session_id')
          .eq('session_id', sessionId)
          .eq('user_id', userId)
          .single();

        if (sessionError || !sessionData) {
          throw new Error('Session not found or unauthorized');
        }
      }

      // Fetch turns
      const { data, error: fetchError } = await supabase
        .from('conversation_turns')
        .select('*')
        .eq('session_id', sessionId)
        .order('timestamp', { ascending: true });

      if (fetchError) throw fetchError;

      setTurns(data || []);
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
    if (!supabase) {
      throw new Error('Supabase not configured');
    }

    setDeleting(true);
    setError(null);

    try {
      const { error: deleteError } = await supabase
        .from('conversation_sessions')
        .delete()
        .eq('session_id', sessionId)
        .eq('user_id', userId);

      if (deleteError) throw deleteError;

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
    if (!supabase) {
      throw new Error('Supabase not configured');
    }

    setUpdating(true);
    setError(null);

    try {
      const { error: updateError } = await supabase
        .from('conversation_sessions')
        .update({ title })
        .eq('session_id', sessionId)
        .eq('user_id', userId);

      if (updateError) throw updateError;

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
