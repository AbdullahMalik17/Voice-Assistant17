/**
 * Conversation History Types
 * Type definitions for conversation sessions and turns
 */

export interface ConversationTurn {
  turn_id: string;
  user_input: string;
  assistant_response: string;
  timestamp: string;
  intent?: string;
  intent_confidence?: number;
  entities?: Record<string, any>;
}

export interface ConversationSession {
  session_id: string;
  user_id: string;
  created_at: string;
  last_updated: string;
  state?: string;
  current_intent?: string;
  metadata?: Record<string, any>;
  turns?: ConversationTurn[];
}

export interface ConversationSessionPreview {
  session_id: string;
  created_at: string;
  last_updated: string;
  turn_count: number;
  preview: string;
  current_intent?: string;
}

export interface SearchResult {
  session_id: string;
  turn_id: string;
  user_input: string;
  assistant_response: string;
  timestamp: string;
  intent?: string;
}

export interface ConversationExport {
  format: 'json' | 'text';
  content?: string;
  session?: ConversationSession;
}
