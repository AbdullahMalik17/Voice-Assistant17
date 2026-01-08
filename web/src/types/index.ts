export type MessageType = 'user' | 'assistant' | 'system' | 'error';

export interface Message {
  id: string;
  type: MessageType;
  content: string;
  timestamp: Date;
  audioUrl?: string;
  metadata?: {
    intent?: string;
    confidence?: number;
    transcription?: string;
    tool_execution?: boolean;
    tool_results?: any;
  };
}

export interface WebSocketMessage {
  type: string;
  content: any;
  session_id: string;
  timestamp: string;
  metadata?: Record<string, any>;
}

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected' | 'error';

export interface ChatState {
  messages: Message[];
  isProcessing: boolean;
  connectionStatus: ConnectionStatus;
  sessionId: string | null;
}
