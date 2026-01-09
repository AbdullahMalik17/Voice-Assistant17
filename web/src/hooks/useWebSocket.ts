'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useSession } from 'next-auth/react';
import { WebSocketMessage, ConnectionStatus } from '@/types';

interface UseWebSocketOptions {
  url: string;
  onMessage?: (message: WebSocketMessage) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
  reconnectAttempts?: number;
  reconnectInterval?: number;
}

export function useWebSocket({
  url,
  onMessage,
  onConnect,
  onDisconnect,
  reconnectAttempts = 5,
  reconnectInterval = 3000,
}: UseWebSocketOptions) {
  const { data: session } = useSession();
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectCountRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const shouldConnectRef = useRef(true);

  // Store callbacks in refs to always use latest versions
  const onMessageRef = useRef(onMessage);
  const onConnectRef = useRef(onConnect);
  const onDisconnectRef = useRef(onDisconnect);

  useEffect(() => {
    onMessageRef.current = onMessage;
    onConnectRef.current = onConnect;
    onDisconnectRef.current = onDisconnect;
  }, [onMessage, onConnect, onDisconnect]);

  const connect = useCallback(() => {
    if (!shouldConnectRef.current) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    // Clear any pending reconnect
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }

    setStatus('connecting');

    try {
      // Append JWT token to WebSocket URL if available
      let wsUrl = url;
      const accessToken = (session as any)?.accessToken;

      if (accessToken) {
        const separator = url.includes('?') ? '&' : '?';
        wsUrl = `${url}${separator}token=${accessToken}`;
        console.log('🔐 Connecting to WebSocket with authentication');
      } else {
        console.log('⚠️  Connecting to WebSocket without authentication');
      }

      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        setStatus('connected');
        reconnectCountRef.current = 0;
        onConnectRef.current?.();
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          if (message.type === 'system' && message.content?.session_id) {
            setSessionId(message.content.session_id);
          }
          onMessageRef.current?.(message);
        } catch (e) {
          console.error('Failed to parse message:', e);
        }
      };

      ws.onclose = () => {
        setStatus('disconnected');
        wsRef.current = null;
        onDisconnectRef.current?.();

        // Attempt reconnection
        if (reconnectCountRef.current < reconnectAttempts) {
          reconnectCountRef.current++;
          reconnectTimeoutRef.current = setTimeout(connect, reconnectInterval);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setStatus('error');
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      setStatus('error');
    }
  }, [url, reconnectAttempts, reconnectInterval, session]);

  const disconnect = useCallback(() => {
    shouldConnectRef.current = false;
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    reconnectCountRef.current = reconnectAttempts; // Prevent auto-reconnect
    wsRef.current?.close();
    wsRef.current = null;
  }, [reconnectAttempts]);

  const sendMessage = useCallback((type: string, content: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type, content }));
      return true;
    }
    return false;
  }, []);

  const sendText = useCallback((text: string) => {
    return sendMessage('text', text);
  }, [sendMessage]);

  const sendAudio = useCallback((audioBase64: string) => {
    return sendMessage('audio', audioBase64);
  }, [sendMessage]);

  useEffect(() => {
    shouldConnectRef.current = true;
    connect();

    return () => {
      shouldConnectRef.current = false;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      wsRef.current?.close();
      wsRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url]); // Only reconnect if URL changes

  return {
    status,
    sessionId,
    sendText,
    sendAudio,
    sendMessage,
    connect,
    disconnect,
  };
}
