'use client';

import { useState, useCallback } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { Message, WebSocketMessage } from '@/types';
import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';
import { PushToTalk } from '../voice/PushToTalk';
import { Wifi, WifiOff, Loader2, Settings } from 'lucide-react';
import { generateId } from '@/lib/utils';

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws/voice';
console.log('WS_URL:', WS_URL);

export function ChatContainer() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);

  const handleMessage = useCallback((wsMessage: WebSocketMessage) => {
    if (wsMessage.type === 'response' || wsMessage.type === 'audio_response') {
      setIsProcessing(false);
      const content = wsMessage.content;

      // Update transcription in user message if available
      if (content.transcription) {
        setMessages((prev) => {
          const lastUserMsg = [...prev].reverse().find((m) => m.type === 'user');
          if (lastUserMsg && lastUserMsg.content.includes('Voice message')) {
            return prev.map((m) =>
              m.id === lastUserMsg.id
                ? { ...m, content: content.transcription }
                : m
            );
          }
          return prev;
        });
      }

      // Add assistant message
      setMessages((prev) => [
        ...prev,
        {
          id: generateId(),
          type: 'assistant',
          content: content.text,
          timestamp: new Date(),
          metadata: {
            intent: content.intent,
            confidence: content.confidence,
            tool_execution: content.tool_execution,
            tool_results: content.tool_results,
          },
          audioUrl: content.audio
            ? `data:audio/mp3;base64,${content.audio}`
            : undefined,
        },
      ]);

      // Auto-play audio response
      if (content.audio) {
        try {
          const audio = new Audio(`data:audio/mp3;base64,${content.audio}`);
          audio.play().catch(console.error);
        } catch (e) {
          console.error('Failed to play audio:', e);
        }
      }
    } else if (wsMessage.type === 'error') {
      setIsProcessing(false);
      setMessages((prev) => [
        ...prev,
        {
          id: generateId(),
          type: 'error',
          content: wsMessage.content.error || 'An error occurred',
          timestamp: new Date(),
        },
      ]);
    } else if (wsMessage.type === 'system') {
      // Add system message for connection
      if (wsMessage.content.message === 'Connected') {
        setMessages((prev) => [
          ...prev,
          {
            id: generateId(),
            type: 'system',
            content: 'Connected to Voice Assistant',
            timestamp: new Date(),
          },
        ]);
      }
    }
  }, []);

  const { status, sessionId, sendText, sendAudio } = useWebSocket({
    url: WS_URL,
    onMessage: handleMessage,
    onDisconnect: () => {
      setMessages((prev) => [
        ...prev,
        {
          id: generateId(),
          type: 'system',
          content: 'Disconnected. Attempting to reconnect...',
          timestamp: new Date(),
        },
      ]);
    },
  });

  const handleSendText = useCallback(
    (text: string) => {
      if (!text.trim() || status !== 'connected') return;

      // Add user message
      setMessages((prev) => [
        ...prev,
        {
          id: generateId(),
          type: 'user',
          content: text,
          timestamp: new Date(),
        },
      ]);

      setIsProcessing(true);
      sendText(text);
    },
    [sendText, status]
  );

  const handleAudioReady = useCallback(
    (base64: string) => {
      if (status !== 'connected') return;

      // Add placeholder for voice message
      setMessages((prev) => [
        ...prev,
        {
          id: generateId(),
          type: 'user',
          content: '🎤 Voice message...',
          timestamp: new Date(),
        },
      ]);

      setIsProcessing(true);
      sendAudio(base64);
    },
    [sendAudio, status]
  );

  const getStatusColor = () => {
    switch (status) {
      case 'connected':
        return 'text-green-500';
      case 'connecting':
        return 'text-yellow-500';
      case 'error':
        return 'text-red-500';
      default:
        return 'text-gray-400';
    }
  };

  return (
    <div className="flex flex-col h-screen max-w-4xl mx-auto bg-gray-50">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 bg-white border-b shadow-sm">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
            <span className="text-white text-lg">🤖</span>
          </div>
          <div>
            <h1 className="text-lg font-semibold text-gray-800">Voice Assistant</h1>
            <p className="text-xs text-gray-500">Agentic AI System v2.0</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            {status === 'connected' ? (
              <Wifi className={`w-5 h-5 ${getStatusColor()}`} />
            ) : status === 'connecting' ? (
              <Loader2 className={`w-5 h-5 ${getStatusColor()} animate-spin`} />
            ) : (
              <WifiOff className={`w-5 h-5 ${getStatusColor()}`} />
            )}
            <span className={`text-sm capitalize ${getStatusColor()}`}>
              {status}
            </span>
          </div>
          <button className="p-2 hover:bg-gray-100 rounded-full transition-colors">
            <Settings className="w-5 h-5 text-gray-400" />
          </button>
        </div>
      </header>

      {/* Messages */}
      <MessageList messages={messages} isProcessing={isProcessing} />

      {/* Input Area */}
      <div className="bg-white border-t shadow-lg">
        <div className="flex items-center gap-4 p-4">
          <ChatInput
            onSend={handleSendText}
            disabled={status !== 'connected' || isProcessing}
          />
          <PushToTalk
            onAudioReady={handleAudioReady}
            disabled={status !== 'connected' || isProcessing}
          />
        </div>

        {/* Keyboard hint */}
        <div className="pb-3 text-center text-xs text-gray-400">
          Hold{' '}
          <kbd className="px-1.5 py-0.5 bg-gray-100 border border-gray-200 rounded text-gray-500">
            Space
          </kbd>{' '}
          to talk • Press{' '}
          <kbd className="px-1.5 py-0.5 bg-gray-100 border border-gray-200 rounded text-gray-500">
            Enter
          </kbd>{' '}
          to send
        </div>
      </div>
    </div>
  );
}
