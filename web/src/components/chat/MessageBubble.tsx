'use client';

import { Message } from '@/types';
import { cn, formatTimestamp } from '@/lib/utils';
import { User, Bot, AlertCircle, Volume2, Zap } from 'lucide-react';
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
        'flex gap-3 max-w-[85%] animate-slide-up',
        isUser ? 'ml-auto flex-row-reverse' : 'mr-auto',
        isSystem && 'mx-auto max-w-full'
      )}
    >
      {/* Avatar with glow effect */}
      {!isSystem && (
        <div
          className={cn(
            'flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center transition-all duration-300',
            isUser
              ? 'bg-gradient-to-br from-neon-blue to-neon-purple shadow-lg dark:shadow-neon-blue/50'
              : isError
                ? 'bg-gradient-to-br from-red-500 to-red-600 shadow-lg dark:shadow-red-500/50'
                : 'bg-gradient-to-br from-neon-purple to-neon-pink shadow-lg dark:shadow-neon-purple/50 animate-float'
          )}
        >
          {isUser ? (
            <User className="w-5 h-5 text-white" />
          ) : isError ? (
            <AlertCircle className="w-5 h-5 text-white" />
          ) : (
            <Zap className="w-5 h-5 text-white" />
          )}
        </div>
      )}

      {/* Message content with glassmorphism */}
      <div
        className={cn(
          'rounded-2xl px-4 py-3 backdrop-blur-sm transition-all duration-300 card-shadow',
          isUser
            ? 'bg-gradient-to-br from-neon-blue/90 to-neon-purple/90 text-white rounded-br-md border border-neon-blue/30 dark:border-neon-blue/50'
            : isError
              ? 'bg-red-500/20 dark:bg-red-500/30 text-red-900 dark:text-red-200 border border-red-500/50 rounded-bl-md'
              : isSystem
                ? 'glass text-gray-600 dark:text-gray-300 text-sm text-center py-2 px-4 border border-gray-300/30 dark:border-neon-blue/20'
                : 'glass text-gray-800 dark:text-gray-100 rounded-bl-md border border-gray-300/30 dark:border-neon-purple/30'
        )}
      >
        <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>

        {/* Metadata with futuristic badges */}
        {message.metadata && !isUser && (
          <div className="mt-2 flex flex-wrap gap-2 text-xs">
            {message.metadata.transcription && (
              <p className="italic text-gray-600 dark:text-gray-400 w-full">
                "{message.metadata.transcription}"
              </p>
            )}
            {message.metadata.intent && message.metadata.intent !== 'unknown' && (
              <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-cyan-100 dark:bg-cyan-900/50 text-cyan-800 dark:text-cyan-200 rounded-full border border-cyan-300 dark:border-cyan-500/50 font-medium uppercase tracking-wider">
                <Zap className="w-3 h-3" />
                {message.metadata.intent}
              </span>
            )}
            {message.metadata.tool_execution && (
              <span className="inline-flex items-center gap-1 px-2.5 py-1 bg-emerald-100 dark:bg-emerald-900/50 text-emerald-800 dark:text-emerald-200 rounded-full border border-emerald-300 dark:border-emerald-500/50 font-medium uppercase tracking-wider">
                Tool Execution
              </span>
            )}
          </div>
        )}

        {/* Audio playback with neon effect */}
        {message.audioUrl && (
          <button
            onClick={playAudio}
            className="mt-3 flex items-center gap-2 text-xs px-3 py-1.5 rounded-full glass border border-neon-blue/30 hover:border-neon-blue/60 transition-all duration-300 hover:scale-105 group"
          >
            <Volume2 className={cn(
              "w-4 h-4 transition-colors",
              isPlaying
                ? "text-neon-blue animate-pulse"
                : "text-gray-600 dark:text-gray-300 group-hover:text-neon-blue"
            )} />
            <span className="font-medium text-gray-700 dark:text-gray-200 group-hover:text-neon-blue transition-colors">
              {isPlaying ? 'Stop Audio' : 'Play Audio'}
            </span>
            <audio
              ref={audioRef}
              src={message.audioUrl}
              onPlay={() => setIsPlaying(true)}
              onPause={() => setIsPlaying(false)}
              onEnded={() => setIsPlaying(false)}
            />
          </button>
        )}

        {/* Timestamp with subtle glow */}
        <div
          className={cn(
            'text-[10px] mt-2 font-mono tracking-wider uppercase',
            isUser
              ? 'text-white/70'
              : 'text-gray-500 dark:text-gray-400'
          )}
        >
          {formatTimestamp(message.timestamp)}
        </div>
      </div>
    </div>
  );
}
