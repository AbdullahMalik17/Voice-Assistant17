'use client';

import { useEffect, useCallback } from 'react';
import { Mic, Radio } from 'lucide-react';
import { useVoiceRecorder } from '@/hooks/useVoiceRecorder';
import { cn } from '@/lib/utils';

interface PushToTalkProps {
  onAudioReady: (base64: string) => void;
  disabled?: boolean;
}

export function PushToTalk({ onAudioReady, disabled }: PushToTalkProps) {
  const { isRecording, audioLevel, duration, startRecording, stopRecording } =
    useVoiceRecorder({
      onRecordingComplete: (_, base64) => onAudioReady(base64),
      onError: (error) => console.error('Recording error:', error),
    });

  // Keyboard handling (Space bar for push-to-talk)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Only trigger if not typing in an input
      if (
        e.code === 'Space' &&
        !e.repeat &&
        !disabled &&
        !(e.target instanceof HTMLInputElement) &&
        !(e.target instanceof HTMLTextAreaElement)
      ) {
        e.preventDefault();
        startRecording();
      }
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      if (e.code === 'Space') {
        e.preventDefault();
        stopRecording();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    window.addEventListener('keyup', handleKeyUp);

    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      window.removeEventListener('keyup', handleKeyUp);
    };
  }, [startRecording, stopRecording, disabled]);

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="flex flex-col items-center gap-3">
      <button
        onMouseDown={startRecording}
        onMouseUp={stopRecording}
        onTouchStart={startRecording}
        onTouchEnd={stopRecording}
        disabled={disabled}
        className={cn(
          'relative flex items-center justify-center w-14 h-14 sm:w-16 sm:h-16 rounded-full',
          'transition-all duration-300 ease-out',
          'focus:outline-none focus-visible:ring-4 focus-visible:ring-neon-blue/50',
          'btn-hover group',
          isRecording
            ? 'bg-gradient-to-br from-red-500 to-red-600 scale-110 animate-pulse'
            : 'bg-gradient-to-br from-neon-blue via-neon-purple to-neon-pink hover:scale-105',
          disabled && 'opacity-50 cursor-not-allowed'
        )}
        style={{
          boxShadow: isRecording
            ? `0 0 ${25 + audioLevel * 50}px rgba(239, 68, 68, ${0.6 + audioLevel * 0.4}),
               0 0 ${50 + audioLevel * 100}px rgba(239, 68, 68, ${0.3 + audioLevel * 0.3})`
            : '0 0 20px rgba(0, 245, 255, 0.3), 0 0 40px rgba(191, 0, 255, 0.2)',
        }}
        aria-label={isRecording ? 'Recording... Release to send' : 'Hold to speak'}
      >
        {isRecording ? (
          <Radio className="w-7 h-7 sm:w-8 sm:h-8 text-white animate-pulse" />
        ) : (
          <Mic className="w-7 h-7 sm:w-8 sm:h-8 text-white group-hover:scale-110 transition-transform" />
        )}

        {/* Animated pulse rings when recording */}
        {isRecording && (
          <>
            {/* Inner ring */}
            <div
              className="absolute inset-0 rounded-full border-2 border-white/50"
              style={{
                transform: `scale(${1 + audioLevel * 0.3})`,
                transition: 'transform 100ms ease-out',
              }}
            />
            {/* Outer ring */}
            <div
              className="absolute inset-0 rounded-full border-2 border-white/30"
              style={{
                transform: `scale(${1.2 + audioLevel * 0.5})`,
                transition: 'transform 100ms ease-out',
              }}
            />
          </>
        )}

        {/* Static glow ring when not recording */}
        {!isRecording && !disabled && (
          <div className="absolute inset-0 rounded-full bg-gradient-to-br from-neon-blue/20 to-neon-purple/20 animate-glow-pulse" />
        )}
      </button>

      {/* Duration display with futuristic styling */}
      {isRecording && (
        <div className="flex flex-col items-center gap-1">
          <div className="flex items-center gap-2 px-3 py-1 rounded-full glass border border-red-500/50 animate-pulse">
            <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
            <span className="text-sm text-red-500 dark:text-red-400 font-mono font-bold tracking-wider">
              {formatDuration(duration)}
            </span>
          </div>
          {duration < 5 && (
            <span className="text-[9px] text-gray-400 dark:text-gray-500">
              Keep holding... (5-10s ideal)
            </span>
          )}
          {duration >= 5 && duration < 10 && (
            <span className="text-[9px] text-green-500 dark:text-green-400 animate-pulse">
              ✓ Good! Release when done
            </span>
          )}
          {duration >= 10 && duration < 25 && (
            <span className="text-[9px] text-yellow-500 dark:text-yellow-400">
              Release when done (auto-stop at 30s)
            </span>
          )}
          {duration >= 25 && (
            <span className="text-[9px] text-orange-500 dark:text-orange-400 animate-pulse">
              ⚠ Auto-stopping soon...
            </span>
          )}
        </div>
      )}

      {/* Recording hint when not recording */}
      {!isRecording && !disabled && (
        <span className="text-[10px] text-gray-500 dark:text-gray-400 font-medium uppercase tracking-wider text-center">
          Click & Hold
        </span>
      )}

      {/* Recording active indicator */}
      {isRecording && (
        <div className="text-[10px] text-red-500 dark:text-red-400 font-bold uppercase tracking-wider animate-pulse text-center">
          🔴 Recording... Release to send
        </div>
      )}
    </div>
  );
}
