'use client';

import { useState, useRef, useCallback } from 'react';

interface UseVoiceRecorderOptions {
  onRecordingComplete?: (audioBlob: Blob, base64: string) => void;
  onError?: (error: Error) => void;
  maxDuration?: number; // Maximum recording duration in seconds
  minDuration?: number; // Minimum recording duration in seconds
}

export function useVoiceRecorder({
  onRecordingComplete,
  onError,
  maxDuration = 30, // Maximum 30 seconds (auto-stop)
  minDuration = 0.3, // Minimum 300ms recording (more forgiving)
}: UseVoiceRecorderOptions = {}) {
  const [isRecording, setIsRecording] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);
  const [duration, setDuration] = useState(0);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationRef = useRef<number>();
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const durationIntervalRef = useRef<NodeJS.Timeout>();
  const maxDurationTimeoutRef = useRef<NodeJS.Timeout>();
  const recordingStartTimeRef = useRef<number>(0);

  const cleanup = useCallback(() => {
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
    }
    if (durationIntervalRef.current) {
      clearInterval(durationIntervalRef.current);
    }
    if (maxDurationTimeoutRef.current) {
      clearTimeout(maxDurationTimeoutRef.current);
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (audioContextRef.current?.state !== 'closed') {
      audioContextRef.current?.close();
    }
    audioContextRef.current = null;
    analyserRef.current = null;
  }, []);

  const startRecording = useCallback(async () => {
    try {
      // Request microphone permission
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          sampleRate: 16000,
        },
      });
      streamRef.current = stream;

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
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/webm';

      const mediaRecorder = new MediaRecorder(stream, { mimeType });
      chunksRef.current = [];
      recordingStartTimeRef.current = Date.now();

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const recordingDuration = (Date.now() - recordingStartTimeRef.current) / 1000;

        // Check if recording is too short
        if (recordingDuration < minDuration) {
          console.warn(`Recording too short: ${recordingDuration.toFixed(2)}s (min: ${minDuration}s)`);
          onError?.(new Error('Recording too short. Please hold and speak for a bit longer.'));
          cleanup();
          setDuration(0);
          return;
        }

        // Check if we have audio data
        if (chunksRef.current.length === 0) {
          console.error('No audio data collected');
          onError?.(new Error('No audio data collected. Please try again.'));
          cleanup();
          setDuration(0);
          return;
        }

        const audioBlob = new Blob(chunksRef.current, { type: mimeType });

        // Check blob size
        if (audioBlob.size === 0) {
          console.error('Audio blob is empty');
          onError?.(new Error('Audio recording failed. Please try again.'));
          cleanup();
          setDuration(0);
          return;
        }

        console.log(`Audio recorded: ${audioBlob.size} bytes, ${recordingDuration.toFixed(2)}s`);

        // Convert to base64
        const reader = new FileReader();
        reader.onloadend = () => {
          const base64 = (reader.result as string).split(',')[1];
          if (base64 && base64.length > 0) {
            onRecordingComplete?.(audioBlob, base64);
          } else {
            console.error('Base64 conversion failed');
            onError?.(new Error('Audio encoding failed. Please try again.'));
          }
        };
        reader.onerror = () => {
          console.error('FileReader error');
          onError?.(new Error('Audio encoding failed. Please try again.'));
        };
        reader.readAsDataURL(audioBlob);

        cleanup();
        setDuration(0);
      };

      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start(100); // Collect data every 100ms
      setIsRecording(true);
      setDuration(0);

      // Track duration
      durationIntervalRef.current = setInterval(() => {
        setDuration((d) => d + 1);
      }, 1000);

      // Auto-stop at max duration
      maxDurationTimeoutRef.current = setTimeout(() => {
        stopRecording();
      }, maxDuration * 1000);

    } catch (error) {
      console.error('Failed to start recording:', error);
      const errorMessage = error instanceof Error
        ? error.message
        : 'Microphone access denied or not available';
      onError?.(new Error(errorMessage));
      cleanup();
    }
  }, [cleanup, maxDuration, minDuration, onRecordingComplete, onError]);

  const stopRecording = useCallback(() => {
    const recordingDuration = (Date.now() - recordingStartTimeRef.current) / 1000;

    // Warn if stopping too quickly
    if (recordingDuration < minDuration && mediaRecorderRef.current?.state === 'recording') {
      console.warn(`Stopping recording after only ${recordingDuration.toFixed(2)}s`);
    }

    if (mediaRecorderRef.current?.state === 'recording') {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
    setAudioLevel(0);
  }, [minDuration]);

  return {
    isRecording,
    audioLevel,
    duration,
    startRecording,
    stopRecording,
  };
}
