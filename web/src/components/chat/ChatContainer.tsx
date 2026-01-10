'use client';

import { useState, useCallback } from 'react';
import { useSession } from 'next-auth/react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { Message, WebSocketMessage } from '@/types';
import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';
import { PushToTalk } from '../voice/PushToTalk';
import { Wifi, WifiOff, Loader2, Settings, Zap, History } from 'lucide-react';
import { generateId } from '@/lib/utils';
import { ThemeToggle } from '../ui/ThemeToggle';
import { ConversationSidebar } from './ConversationSidebar';
import { UserMenu } from '../auth/UserMenu';

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws/voice';
console.log('WS_URL:', WS_URL);

export function ChatContainer() {
  const { data: session } = useSession();
  const [messages, setMessages] = useState<Message[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

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
            content: 'Malik link established • System online',
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
          content: 'Connection lost • Attempting reconnect...',
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
        return 'text-neon-green';
      case 'connecting':
        return 'text-neon-yellow';
      case 'error':
        return 'text-red-500';
      default:
        return 'text-gray-400';
    }
  };

  const getStatusGlow = () => {
    switch (status) {
      case 'connected':
        return 'drop-shadow-[0_0_8px_rgba(0,255,136,0.8)]';
      case 'connecting':
        return 'drop-shadow-[0_0_8px_rgba(255,234,0,0.8)]';
      default:
        return '';
    }
  };

  return (
    <div className="flex min-h-screen w-full relative">
      {/* Conversation Sidebar */}
      <ConversationSidebar
        userId={session?.user?.id || 'default'}
        onSelectConversation={(sessionId) => {
          console.log('Selected conversation:', sessionId);
          // TODO: Load conversation history into messages
        }}
        currentSessionId={sessionId ?? undefined}
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      {/* Main Chat Area */}
      <div className="flex flex-col flex-1 min-h-screen w-full relative">
        {/* Animated background grid (dark mode only) */}
        <div className="absolute inset-0 dark:cyber-grid-bg opacity-20 pointer-events-none" />

      {/* Header with glassmorphism */}
      <header className="relative z-10 px-3 sm:px-6 py-2.5 sm:py-4 glass border-b dark:border-neon-blue/20 card-shadow animate-slide-down">
        <div className="flex items-center justify-between gap-2 sm:gap-4">
          {/* Logo and title */}
          <div className="flex items-center gap-2 sm:gap-4 min-w-0">
            {/* Animated logo */}
            <div className="relative w-9 h-9 sm:w-12 sm:h-12 rounded-xl bg-gradient-to-br from-neon-blue via-neon-purple to-neon-pink p-[2px] animate-float flex-shrink-0">
              <div className="w-full h-full rounded-xl bg-dark-bg dark:bg-black flex items-center justify-center">
                <Zap className="w-5 h-5 sm:w-6 sm:h-6 text-neon-blue dark:drop-shadow-[0_0_10px_rgba(0,245,255,0.8)]" />
              </div>
            </div>

            <div className="min-w-0">
              <h1 className="text-base sm:text-xl font-bold bg-gradient-to-r from-neon-blue via-neon-purple to-neon-pink bg-clip-text text-transparent font-[family-name:var(--font-orbitron)] truncate">
                MALIK AI
              </h1>
              <p className="text-[10px] sm:text-xs text-gray-500 dark:text-gray-400 truncate">
                Neural Voice Interface v2.0
              </p>
            </div>
          </div>

          {/* Status and controls */}
          <div className="flex items-center gap-1.5 sm:gap-3 flex-shrink-0">
            {/* Connection status - compact on mobile */}
            <div className="flex items-center gap-1 sm:gap-2 px-2 sm:px-3 py-1 sm:py-1.5 rounded-full glass">
              {status === 'connected' ? (
                <Wifi className={`w-3.5 h-3.5 sm:w-4 sm:h-4 ${getStatusColor()} ${getStatusGlow()}`} />
              ) : status === 'connecting' ? (
                <Loader2 className={`w-3.5 h-3.5 sm:w-4 sm:h-4 ${getStatusColor()} ${getStatusGlow()} animate-spin`} />
              ) : (
                <WifiOff className={`w-3.5 h-3.5 sm:w-4 sm:h-4 ${getStatusColor()}`} />
              )}
              <span className={`hidden sm:inline text-xs font-medium uppercase tracking-wider ${getStatusColor()}`}>
                {status}
              </span>
            </div>

            {/* History button */}
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-1.5 sm:p-2 rounded-full glass hover:bg-white/10 dark:hover:bg-neon-blue/10 transition-all duration-300 btn-hover group"
              aria-label="Conversation History"
            >
              <History className={`w-4 h-4 sm:w-5 sm:h-5 text-gray-600 dark:text-gray-300 group-hover:text-neon-blue transition-colors duration-300 ${sidebarOpen ? 'text-neon-blue' : ''}`} />
            </button>

            {/* Theme toggle */}
            <ThemeToggle />

            {/* Settings button */}
            <button
              className="p-1.5 sm:p-2 rounded-full glass hover:bg-white/10 dark:hover:bg-neon-blue/10 transition-all duration-300 btn-hover group"
              aria-label="Settings"
            >
              <Settings className="w-4 h-4 sm:w-5 sm:h-5 text-gray-600 dark:text-gray-300 group-hover:text-neon-blue transition-colors duration-300 group-hover:rotate-90 transform" />
            </button>

            {/* User Menu with logout */}
            <UserMenu />
          </div>
        </div>
      </header>

      {/* Messages */}
      <MessageList messages={messages} isProcessing={isProcessing} />

      {/* Input Area with glassmorphism */}
      <div className="relative z-10 glass border-t dark:border-neon-blue/20 card-shadow">
        <div className="flex items-end gap-2 sm:gap-4 p-3 sm:p-4">
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
        <div className="pb-2 sm:pb-3 px-3 sm:px-4 text-center text-xs text-gray-400 dark:text-gray-500">
          <div className="flex flex-col gap-1">
            <span className="block text-[10px] sm:text-xs">
              🎤 Hold mic button or{' '}
              <kbd className="px-2 py-1 bg-gray-100 dark:bg-dark-card border border-gray-300 dark:border-neon-blue/30 rounded text-gray-600 dark:text-neon-blue font-mono text-[9px]">
                Space
              </kbd>
              {' '}for 5-10 seconds
            </span>
            <span className="block text-[10px] sm:text-xs">
              Type message + press{' '}
              <kbd className="px-1.5 py-0.5 bg-gray-100 dark:bg-dark-card border border-gray-300 dark:border-neon-blue/30 rounded text-gray-600 dark:text-neon-blue font-mono text-[8px] sm:text-[9px]">
                Enter
              </kbd>
            </span>
          </div>
        </div>
      </div>
      </div>
    </div>
  );
}
