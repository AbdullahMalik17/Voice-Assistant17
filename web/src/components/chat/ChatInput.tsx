'use client';

import { useState, useCallback, KeyboardEvent } from 'react';
import { Send } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface ChatInputProps {
  onSend: (text: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function ChatInput({
  onSend,
  disabled,
  placeholder = 'Type a message...',
}: ChatInputProps) {
  const [text, setText] = useState('');

  const handleSend = useCallback(() => {
    const trimmed = text.trim();
    if (trimmed && !disabled) {
      onSend(trimmed);
      setText('');
    }
  }, [text, disabled, onSend]);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex items-end gap-2 flex-1">
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        rows={1}
        className={cn(
          'flex-1 resize-none rounded-xl border border-gray-300 dark:border-gray-600 dark:bg-dark-card dark:text-white px-3 sm:px-4 py-2 sm:py-3',
          'focus:outline-none focus:ring-2 focus:ring-neon-blue focus:border-transparent dark:focus:ring-neon-blue',
          'placeholder:text-gray-400 dark:placeholder:text-gray-500 text-gray-800 dark:text-white text-sm sm:text-base',
          'min-h-[40px] sm:min-h-[48px] max-h-[120px]',
          disabled && 'opacity-50 cursor-not-allowed bg-gray-50 dark:bg-dark-bg'
        )}
        style={{
          height: 'auto',
          minHeight: '40px',
        }}
      />
      <Button
        onClick={handleSend}
        disabled={disabled || !text.trim()}
        size="icon"
        className="h-10 w-10 sm:h-12 sm:w-12 rounded-lg sm:rounded-xl flex-shrink-0"
      >
        <Send className="w-4 h-4 sm:w-5 sm:h-5" />
      </Button>
    </div>
  );
}
