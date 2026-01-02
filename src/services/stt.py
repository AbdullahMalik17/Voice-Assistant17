"""
Speech-to-Text (STT) Service
Converts spoken audio to text using Whisper (local) with OpenAI API fallback
"""

import io
import time
from pathlib import Path
from typing import Optional, Tuple

import numpy as np

# Whisper imports
try:
    import whisper
    WHISPER_LOCAL_AVAILABLE = True
except ImportError:
    WHISPER_LOCAL_AVAILABLE = False

# OpenAI API import
try:
    from openai import OpenAI
    OPENAI_API_AVAILABLE = True
except ImportError:
    OPENAI_API_AVAILABLE = False

from ..core.config import Config
from ..models.voice_command import VoiceCommand, VoiceCommandStatus
from ..utils.audio_utils import AudioUtils
from ..utils.logger import EventLogger, MetricsLogger


class STTService:
    """
    Speech-to-Text service with hybrid architecture
    Primary: Whisper (local)
    Fallback: OpenAI Whisper API
    """

    def __init__(
        self,
        config: Config,
        logger: EventLogger,
        metrics_logger: MetricsLogger,
        audio_utils: AudioUtils
    ):
        self.config = config
        self.logger = logger
        self.metrics_logger = metrics_logger
        self.audio_utils = audio_utils
        self.mode = config.stt.primary_mode

        # Initialize local Whisper model
        self.whisper_model = None
        if WHISPER_LOCAL_AVAILABLE and self.mode in ["local", "hybrid"]:
            self._initialize_local_model()

        # Initialize OpenAI API client
        self.openai_client = None
        if OPENAI_API_AVAILABLE and config.openai_api_key and self.mode in ["api", "hybrid"]:
            self.openai_client = OpenAI(api_key=config.openai_api_key)

    def _initialize_local_model(self) -> None:
        """Initialize local Whisper model"""
        try:
            model_name = self.config.stt.local_model
            self.logger.info(
                event='STT_MODEL_LOADING',
                message=f'Loading Whisper model: {model_name}'
            )

            # Load Whisper model (base, small, medium, large)
            # Extract just the size from names like "whisper-base"
            model_size = model_name.replace("whisper-", "")
            self.whisper_model = whisper.load_model(model_size)

            self.logger.info(
                event='STT_MODEL_LOADED',
                message=f'Whisper model loaded: {model_name}'
            )
        except Exception as e:
            self.logger.error(
                event='STT_MODEL_LOAD_FAILED',
                message=f'Failed to load Whisper model: {str(e)}',
                error=str(e)
            )
            self.whisper_model = None

    def transcribe(
        self,
        audio_data: bytes,
        duration_ms: int
    ) -> Tuple[str, float]:
        """
        Transcribe audio to text
        Returns: (transcribed_text, confidence_score)
        """
        if not audio_data or len(audio_data) == 0:
            raise ValueError("Audio data must not be empty")

        start_time = time.time()
        transcribed_text = ""
        confidence = 0.0
        success = False
        mode_used = self.mode

        try:
            if self.mode == "api":
                transcribed_text, confidence = self._transcribe_api(audio_data)
                mode_used = "api"
                success = True
            elif self.mode == "local":
                transcribed_text, confidence = self._transcribe_local(audio_data)
                mode_used = "local"
                success = True
            else:  # hybrid mode
                try:
                    transcribed_text, confidence = self._transcribe_local(audio_data)
                    mode_used = "local"
                    success = True
                except Exception as local_error:
                    self.logger.warning(
                        event='STT_LOCAL_FALLBACK',
                        message=f'Local STT failed, falling back to API: {str(local_error)}'
                    )
                    transcribed_text, confidence = self._transcribe_api(audio_data)
                    mode_used = "api"
                    success = True

        except Exception as e:
            self.logger.error(
                event='STT_TRANSCRIPTION_FAILED',
                message=f'STT transcription failed: {str(e)}',
                error=str(e)
            )
            raise

        finally:
            # Calculate duration
            duration_ms_actual = int((time.time() - start_time) * 1000)

            # Log event
            self.logger.info(
                event='STT_TRANSCRIPTION_COMPLETED',
                message=f'Transcription completed: "{transcribed_text[:50]}..."',
                text_length=len(transcribed_text),
                processing_time_ms=duration_ms_actual,
                audio_duration_ms=duration_ms,
                mode=mode_used,
                confidence=confidence,
                success=success
            )

            # Record metrics
            self.metrics_logger.record_metric('stt_latency_ms', duration_ms_actual)
            self.metrics_logger.record_metric('stt_confidence', confidence)

        return transcribed_text, confidence

    def _transcribe_local(self, audio_data: bytes) -> Tuple[str, float]:
        """Transcribe using local Whisper model"""
        if not WHISPER_LOCAL_AVAILABLE:
            raise RuntimeError("Whisper library not available")

        if self.whisper_model is None:
            raise RuntimeError("Whisper model not loaded")

        try:
            # Convert audio bytes to numpy array
            audio_array = self.audio_utils.bytes_to_array(audio_data)

            # Whisper expects float32 normalized to [-1, 1]
            if audio_array.dtype != np.float32:
                audio_array = audio_array.astype(np.float32) / 32768.0

            # Transcribe with Whisper
            result = self.whisper_model.transcribe(
                audio_array,
                language=self.config.stt.language,
                fp16=False  # Use FP32 for CPU compatibility
            )

            text = result['text'].strip()

            # Calculate average confidence from segments
            confidence = 0.0
            if 'segments' in result and len(result['segments']) > 0:
                confidences = [
                    seg.get('no_speech_prob', 0.0)
                    for seg in result['segments']
                ]
                # Convert no_speech_prob to confidence (inverse)
                confidence = 1.0 - (sum(confidences) / len(confidences))
            else:
                # Default confidence if no segments
                confidence = 0.8 if text else 0.0

            return text, confidence

        except Exception as e:
            raise RuntimeError(f"Local Whisper transcription error: {str(e)}")

    def _transcribe_api(self, audio_data: bytes) -> Tuple[str, float]:
        """Transcribe using OpenAI Whisper API"""
        if not OPENAI_API_AVAILABLE:
            raise RuntimeError("OpenAI library not available")

        if self.openai_client is None:
            raise RuntimeError("OpenAI API client not initialized (check API key)")

        try:
            # Convert raw audio bytes to WAV format with proper headers
            import wave
            wav_buffer = io.BytesIO()

            with wave.open(wav_buffer, 'wb') as wf:
                wf.setnchannels(self.config.audio.channels)
                wf.setsampwidth(2)  # 16-bit audio = 2 bytes
                wf.setframerate(self.config.audio.sample_rate)
                wf.writeframes(audio_data)

            # Reset buffer position to beginning
            wav_buffer.seek(0)
            wav_buffer.name = "audio.wav"  # API expects a filename

            # Call OpenAI Whisper API
            response = self.openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=wav_buffer,
                language=self.config.stt.language,
                response_format="json"
            )

            text = response.text.strip()

            # OpenAI API doesn't provide confidence scores
            # Use a default high confidence for successful API calls
            confidence = 0.9 if text else 0.0

            return text, confidence

        except Exception as e:
            raise RuntimeError(f"OpenAI Whisper API error: {str(e)}")

    def transcribe_voice_command(self, voice_command: VoiceCommand) -> VoiceCommand:
        """
        Transcribe a VoiceCommand model
        Updates the voice command with transcription results
        """
        try:
            # Transition to TRANSCRIBING state
            voice_command.to_transcribing()

            # Transcribe audio
            text, confidence = self.transcribe(
                voice_command.audio_data,
                voice_command.duration_ms
            )

            # Transition to TRANSCRIBED state
            voice_command.to_transcribed(text, confidence)

            return voice_command

        except Exception as e:
            # Transition to FAILED state
            voice_command.to_failed()

            self.logger.error(
                event='VOICE_COMMAND_TRANSCRIPTION_FAILED',
                message=f'Failed to transcribe voice command: {str(e)}',
                voice_command_id=str(voice_command.id),
                error=str(e)
            )

            raise

    def test_service(self) -> bool:
        """Test STT service with a simple audio file or test pattern"""
        try:
            # Generate a simple test audio (1 second of silence)
            sample_rate = self.config.audio.sample_rate
            duration_seconds = 1
            silence = np.zeros(sample_rate * duration_seconds, dtype=np.int16)

            # Convert to bytes
            test_audio = silence.tobytes()

            # Try transcription (should return empty or minimal text)
            text, confidence = self.transcribe(test_audio, duration_ms=1000)

            self.logger.info(
                event='STT_TEST_COMPLETED',
                message=f'STT service test completed: "{text}"',
                confidence=confidence
            )

            return True

        except Exception as e:
            self.logger.error(
                event='STT_TEST_FAILED',
                message=f'STT service test failed: {str(e)}',
                error=str(e)
            )
            return False


def create_stt_service(
    config: Config,
    logger: EventLogger,
    metrics_logger: MetricsLogger,
    audio_utils: AudioUtils
) -> STTService:
    """Factory function to create STT service"""
    service = STTService(
        config=config,
        logger=logger,
        metrics_logger=metrics_logger,
        audio_utils=audio_utils
    )
    return service
