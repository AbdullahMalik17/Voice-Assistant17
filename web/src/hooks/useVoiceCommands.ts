'use client';

import { useState, useCallback } from 'react';
import { processVoiceCommand, VoiceCommandContext, CommandResponse } from '@/lib/voice-commands';

interface UseVoiceCommandsState {
  isProcessing: boolean;
  lastResponse: CommandResponse | null;
  error: string | null;
}

export function useVoiceCommands() {
  const [state, setState] = useState<UseVoiceCommandsState>({
    isProcessing: false,
    lastResponse: null,
    error: null,
  });

  const execute = useCallback(async (context: VoiceCommandContext) => {
    setState((prev) => ({ ...prev, isProcessing: true, error: null }));

    try {
      const response = await processVoiceCommand(context);
      setState((prev) => ({
        ...prev,
        isProcessing: false,
        lastResponse: response,
        error: response.status === 'error' ? response.message : null,
      }));
      return response;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      setState((prev) => ({
        ...prev,
        isProcessing: false,
        error: errorMessage,
      }));
      return {
        status: 'error' as const,
        message: errorMessage,
      };
    }
  }, []);

  return {
    execute,
    ...state,
  };
}
