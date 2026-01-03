'use client';

import { useEffect, useCallback } from 'react';
import { Mic, MicOff } from 'lucide-react';
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
    <div className="flex flex-col items-center gap-2">
      <button
        onMouseDown={startRecording}
        onMouseUp={stopRecording}
        onMouseLeave={isRecording ? stopRecording : undefined}
        onTouchStart={startRecording}
        onTouchEnd={stopRecording}
        disabled={disabled}
        className={cn(
          'relative flex items-center justify-center w-16 h-16 rounded-full',
          'transition-all duration-200 ease-in-out',
          'focus:outline-none focus:ring-4 focus:ring-blue-300',
          isRecording
            ? 'bg-red-500 hover:bg-red-600 scale-110'
            : 'bg-blue-500 hover:bg-blue-600',
          disabled && 'opacity-50 cursor-not-allowed'
        )}
        style={{
          boxShadow: isRecording
            ? `0 0 ${20 + audioLevel * 40}px rgba(239, 68, 68, ${0.5 + audioLevel * 0.5})`
            : undefined,
        }}
        aria-label={isRecording ? 'Recording... Release to send' : 'Hold to speak'}
      >
        {isRecording ? (
          <Mic className="w-8 h-8 text-white animate-pulse" />
        ) : (
          <MicOff className="w-8 h-8 text-white" />
        )}

        {/* Audio level indicator ring */}
        {isRecording && (
          <div
            className="absolute inset-0 rounded-full border-4 border-white opacity-50"
            style={{
              transform: `scale(${1 + audioLevel * 0.3})`,
              transition: 'transform 50ms ease-out',
            }}
          />
        )}
      </button>

      {/* Duration display */}
      {isRecording && (
        <span className="text-sm text-red-500 font-mono">
          {formatDuration(duration)}
        </span>
      )}
    </div>
  );
}
