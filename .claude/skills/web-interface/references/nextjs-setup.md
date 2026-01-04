# Next.js Web Interface Setup

Complete Next.js frontend implementation for Voice Assistant.

## Table of Contents
1. [Project Setup](#project-setup)
2. [Core Components](#core-components)
3. [Voice Recording](#voice-recording)
4. [WebSocket Client](#websocket-client)
5. [UI Components](#ui-components)

## Project Setup

### Initialize Project

```bash
npx create-next-app@latest voice-assistant-web --typescript --tailwind --app --src-dir
cd voice-assistant-web

# Install dependencies
npm install lucide-react class-variance-authority clsx tailwind-merge
npm install @radix-ui/react-slot @radix-ui/react-dialog

# Optional: shadcn/ui components
npx shadcn@latest init
npx shadcn@latest add button card input scroll-area
```

### Project Structure

```
voice-assistant-web/
├── src/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   └── globals.css
│   ├── components/
│   │   ├── ui/
│   │   │   ├── button.tsx
│   │   │   └── card.tsx
│   │   ├── chat/
│   │   │   ├── ChatContainer.tsx
│   │   │   ├── MessageList.tsx
│   │   │   ├── MessageBubble.tsx
│   │   │   └── ChatInput.tsx
│   │   └── voice/
│   │       ├── VoiceRecorder.tsx
│   │       ├── PushToTalk.tsx
│   │       ├── AudioVisualizer.tsx
│   │       └── VoiceButton.tsx
│   ├── hooks/
│   │   ├── useWebSocket.ts
│   │   ├── useVoiceRecorder.ts
│   │   └── useAudioPlayback.ts
│   ├── lib/
│   │   ├── utils.ts
│   │   └── websocket-client.ts
│   └── types/
│       └── index.ts
├── public/
├── tailwind.config.ts
└── package.json
```

## Core Components

### Types (`src/types/index.ts`)

```typescript
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
```

### WebSocket Hook (`src/hooks/useWebSocket.ts`)

```typescript
'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
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
  const [status, setStatus] = useState<ConnectionStatus>('disconnected');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectCountRef = useRef(0);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    setStatus('connecting');
    const ws = new WebSocket(url);

    ws.onopen = () => {
      setStatus('connected');
      reconnectCountRef.current = 0;
      onConnect?.();
    };

    ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        if (message.type === 'system' && message.content?.session_id) {
          setSessionId(message.content.session_id);
        }
        onMessage?.(message);
      } catch (e) {
        console.error('Failed to parse message:', e);
      }
    };

    ws.onclose = () => {
      setStatus('disconnected');
      onDisconnect?.();

      // Attempt reconnection
      if (reconnectCountRef.current < reconnectAttempts) {
        reconnectCountRef.current++;
        setTimeout(connect, reconnectInterval);
      }
    };

    ws.onerror = () => {
      setStatus('error');
    };

    wsRef.current = ws;
  }, [url, onMessage, onConnect, onDisconnect, reconnectAttempts, reconnectInterval]);

  const disconnect = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
  }, []);

  const sendMessage = useCallback((type: string, content: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type, content }));
    }
  }, []);

  const sendText = useCallback((text: string) => {
    sendMessage('text', text);
  }, [sendMessage]);

  const sendAudio = useCallback((audioBase64: string) => {
    sendMessage('audio', audioBase64);
  }, [sendMessage]);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

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
```

### Voice Recorder Hook (`src/hooks/useVoiceRecorder.ts`)

```typescript
'use client';

import { useState, useRef, useCallback } from 'react';

interface UseVoiceRecorderOptions {
  onRecordingComplete?: (audioBlob: Blob, base64: string) => void;
  onError?: (error: Error) => void;
}

export function useVoiceRecorder({
  onRecordingComplete,
  onError,
}: UseVoiceRecorderOptions = {}) {
  const [isRecording, setIsRecording] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationRef = useRef<number>();
  const chunksRef = useRef<Blob[]>([]);

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 16000,
        },
      });

      // Set up audio analysis for visualization
      audioContextRef.current = new AudioContext();
      analyserRef.current = audioContextRef.current.createAnalyser();
      const source = audioContextRef.current.createMediaStreamSource(stream);
      source.connect(analyserRef.current);
      analyserRef.current.fftSize = 256;

      // Monitor audio level
      const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
      const updateLevel = () => {
        if (analyserRef.current) {
          analyserRef.current.getByteFrequencyData(dataArray);
          const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
          setAudioLevel(average / 255);
        }
        animationRef.current = requestAnimationFrame(updateLevel);
      };
      updateLevel();

      // Set up MediaRecorder
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus',
      });

      chunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(chunksRef.current, { type: 'audio/webm' });

        // Convert to base64
        const reader = new FileReader();
        reader.onloadend = () => {
          const base64 = (reader.result as string).split(',')[1];
          onRecordingComplete?.(audioBlob, base64);
        };
        reader.readAsDataURL(audioBlob);

        // Cleanup
        stream.getTracks().forEach((track) => track.stop());
      };

      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start(100); // Collect data every 100ms
      setIsRecording(true);
    } catch (error) {
      onError?.(error as Error);
    }
  }, [onRecordingComplete, onError]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current?.state === 'recording') {
      mediaRecorderRef.current.stop();
    }
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
    }
    audioContextRef.current?.close();
    setIsRecording(false);
    setAudioLevel(0);
  }, []);

  return {
    isRecording,
    audioLevel,
    startRecording,
    stopRecording,
  };
}
```

### Push-to-Talk Component (`src/components/voice/PushToTalk.tsx`)

```typescript
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
  const { isRecording, audioLevel, startRecording, stopRecording } =
    useVoiceRecorder({
      onRecordingComplete: (_, base64) => onAudioReady(base64),
    });

  // Keyboard handling (Space bar)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.code === 'Space' && !e.repeat && !disabled) {
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

  return (
    <button
      onMouseDown={startRecording}
      onMouseUp={stopRecording}
      onMouseLeave={stopRecording}
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
  );
}
```

### Chat Container (`src/components/chat/ChatContainer.tsx`)

```typescript
'use client';

import { useState, useCallback } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { Message, WebSocketMessage } from '@/types';
import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';
import { PushToTalk } from '../voice/PushToTalk';
import { Wifi, WifiOff, Loader2 } from 'lucide-react';

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws/voice';

export function ChatContainer() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);

  const handleMessage = useCallback((wsMessage: WebSocketMessage) => {
    if (wsMessage.type === 'response' || wsMessage.type === 'audio_response') {
      setIsProcessing(false);
      const content = wsMessage.content;

      // Add assistant message
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          type: 'assistant',
          content: content.text,
          timestamp: new Date(),
          metadata: {
            intent: content.intent,
            confidence: content.confidence,
            transcription: content.transcription,
          },
          audioUrl: content.audio
            ? `data:audio/mp3;base64,${content.audio}`
            : undefined,
        },
      ]);

      // Auto-play audio response
      if (content.audio) {
        const audio = new Audio(`data:audio/mp3;base64,${content.audio}`);
        audio.play().catch(console.error);
      }
    } else if (wsMessage.type === 'error') {
      setIsProcessing(false);
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          type: 'error',
          content: wsMessage.content.error || 'An error occurred',
          timestamp: new Date(),
        },
      ]);
    }
  }, []);

  const { status, sendText, sendAudio } = useWebSocket({
    url: WS_URL,
    onMessage: handleMessage,
  });

  const handleSendText = useCallback(
    (text: string) => {
      if (!text.trim()) return;

      // Add user message
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          type: 'user',
          content: text,
          timestamp: new Date(),
        },
      ]);

      setIsProcessing(true);
      sendText(text);
    },
    [sendText]
  );

  const handleAudioReady = useCallback(
    (base64: string) => {
      // Add placeholder for voice message
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          type: 'user',
          content: '🎤 Voice message...',
          timestamp: new Date(),
        },
      ]);

      setIsProcessing(true);
      sendAudio(base64);
    },
    [sendAudio]
  );

  return (
    <div className="flex flex-col h-screen max-w-4xl mx-auto bg-gray-50">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 bg-white border-b">
        <h1 className="text-xl font-semibold text-gray-800">Voice Assistant</h1>
        <div className="flex items-center gap-2">
          {status === 'connected' ? (
            <Wifi className="w-5 h-5 text-green-500" />
          ) : status === 'connecting' ? (
            <Loader2 className="w-5 h-5 text-yellow-500 animate-spin" />
          ) : (
            <WifiOff className="w-5 h-5 text-red-500" />
          )}
          <span className="text-sm text-gray-500 capitalize">{status}</span>
        </div>
      </header>

      {/* Messages */}
      <MessageList messages={messages} isProcessing={isProcessing} />

      {/* Input Area */}
      <div className="flex items-center gap-4 p-4 bg-white border-t">
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
      <div className="pb-2 text-center text-xs text-gray-400">
        Hold <kbd className="px-1 py-0.5 bg-gray-100 rounded">Space</kbd> to talk
      </div>
    </div>
  );
}
```

### Main Page (`src/app/page.tsx`)

```typescript
import { ChatContainer } from '@/components/chat/ChatContainer';

export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-b from-gray-50 to-gray-100">
      <ChatContainer />
    </main>
  );
}
```

## Environment Variables

Create `.env.local`:

```bash
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/voice
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Running the Frontend

```bash
# Development
npm run dev

# Production build
npm run build
npm start
```
