'use client';

import { useEffect, useRef } from 'react';
import { Message } from '@/types';
import { MessageBubble } from './MessageBubble';
import { TypingIndicator } from './TypingIndicator';

interface MessageListProps {
  messages: Message[];
  isProcessing?: boolean;
}

export function MessageList({ messages, isProcessing }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isProcessing]);

  return (
    <div className="flex-1 overflow-y-auto px-3 sm:px-4 py-3 sm:py-4 space-y-3 sm:space-y-4">
      {messages.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-full text-gray-400">
          <div className="text-5xl sm:text-6xl mb-4">🎙️</div>
          <p className="text-base sm:text-lg">Start a conversation</p>
          <p className="text-xs sm:text-sm mt-2">
            Type a message or hold{' '}
            <kbd className="px-2 py-0.5 bg-gray-100 dark:bg-dark-card rounded text-gray-600 dark:text-gray-400">Space</kbd>{' '}
            to speak
          </p>
        </div>
      ) : (
        messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))
      )}

      {/* Processing indicator */}
      {isProcessing && <TypingIndicator />}

      <div ref={bottomRef} />
    </div>
  );
}
