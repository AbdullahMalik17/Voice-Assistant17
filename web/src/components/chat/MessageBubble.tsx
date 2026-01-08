'use client';

import { Message } from '@/types';
import { cn, formatTimestamp } from '@/lib/utils';
import { User, Bot, AlertCircle, Volume2 } from 'lucide-react';
import { useRef, useState } from 'react';

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);

  const isUser = message.type === 'user';
  const isError = message.type === 'error';
  const isSystem = message.type === 'system';

  const playAudio = () => {
    if (audioRef.current) {
      if (isPlaying) {
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
      } else {
        audioRef.current.play();
      }
    }
  };

  return (
    <div
      className={cn(
        'flex gap-3 max-w-[85%]',
        isUser ? 'ml-auto flex-row-reverse' : 'mr-auto',
        isSystem && 'mx-auto max-w-full'
      )}
    >
      {/* Avatar */}
      {!isSystem && (
        <div
          className={cn(
            'flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center',
            isUser
              ? 'bg-blue-100 text-blue-600'
              : isError
                ? 'bg-red-100 text-red-600'
                : 'bg-gray-100 text-gray-600'
          )}
        >
          {isUser ? (
            <User className="w-4 h-4" />
          ) : isError ? (
            <AlertCircle className="w-4 h-4" />
          ) : (
            <Bot className="w-4 h-4" />
          )}
        </div>
      )}

      {/* Message content */}
      <div
        className={cn(
          'rounded-2xl px-4 py-2',
          isUser
            ? 'bg-blue-500 text-white rounded-br-md'
            : isError
              ? 'bg-red-50 text-red-800 border border-red-200 rounded-bl-md'
              : isSystem
                ? 'bg-gray-100 text-gray-500 text-sm text-center py-1 px-3'
                : 'bg-white border border-gray-200 text-gray-800 rounded-bl-md shadow-sm'
        )}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>

        {/* Metadata */}
        {message.metadata && !isUser && (
          <div className="mt-1 text-xs opacity-70">
            {message.metadata.transcription && (
              <p className="italic">"{message.metadata.transcription}"</p>
            )}
            {message.metadata.intent && message.metadata.intent !== 'unknown' && (
              <span className="inline-block mt-1 px-2 py-0.5 bg-gray-100 rounded-full">
                {message.metadata.intent}
              </span>
            )}
            {message.metadata.tool_execution && (
              <span className="inline-block mt-1 px-2 py-0.5 bg-green-100 text-green-800 rounded-full ml-2">
                Tool Execution
              </span>
            )}
          </div>
        )}

        {/* Audio playback */}
        {message.audioUrl && (
          <button
            onClick={playAudio}
            className="mt-2 flex items-center gap-1 text-xs opacity-70 hover:opacity-100 transition-opacity"
          >
            <Volume2 className="w-3 h-3" />
            <span>{isPlaying ? 'Stop' : 'Play'}</span>
            <audio
              ref={audioRef}
              src={message.audioUrl}
              onPlay={() => setIsPlaying(true)}
              onPause={() => setIsPlaying(false)}
              onEnded={() => setIsPlaying(false)}
            />
          </button>
        )}

        {/* Timestamp */}
        <div
          className={cn(
            'text-xs mt-1',
            isUser ? 'text-blue-100' : 'text-gray-400'
          )}
        >
          {formatTimestamp(message.timestamp)}
        </div>
      </div>
    </div>
  );
}
