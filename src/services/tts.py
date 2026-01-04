"""
Text-to-Speech (TTS) Service
Converts text to spoken audio using ElevenLabs API with Piper fallback
"""

import time
from io import BytesIO
from pathlib import Path
from typing import Optional

try:
    from elevenlabs import ElevenLabs
    ELEVENLABS_AVAILABLE = True
except ImportError:
    ELEVENLABS_AVAILABLE = False

# Piper TTS import (local fallback)
# Note: Piper requires additional setup - placeholder for now
PIPER_AVAILABLE = False

from ..core.config import Config
from ..utils.audio_utils import AudioUtils
from ..utils.logger import EventLogger, MetricsLogger


class TTSService:
    """
    Text-to-Speech service with hybrid architecture
    Primary: ElevenLabs API
    Fallback: Piper (local)
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
        self.mode = config.tts.primary_mode

        # Initialize ElevenLabs client
        self.elevenlabs_client = None
        if config.elevenlabs_api_key and ELEVENLABS_AVAILABLE:
            self.elevenlabs_client = ElevenLabs(api_key=config.elevenlabs_api_key)

    def synthesize(self, text: str, play_audio: bool = True) -> Optional[bytes]:
        """
        Convert text to speech
        Returns audio bytes and optionally plays immediately
        """
        if not text or len(text.strip()) == 0:
            raise ValueError("Text must not be empty")

        start_time = time.time()
        audio_bytes = None
        success = False
        mode_used = self.mode

        try:
            if self.mode == "api":
                audio_bytes = self._synthesize_api(text)
                success = True
            elif self.mode == "local":
                audio_bytes = self._synthesize_local(text)
                success = True
            else:  # hybrid
                try:
                    audio_bytes = self._synthesize_api(text)
                    mode_used = "api"
                    success = True
                except Exception as api_error:
                    self.logger.warning(
                        event='TTS_API_FALLBACK',
                        message=f'API TTS failed, falling back to local: {str(api_error)}'
                    )
                    audio_bytes = self._synthesize_local(text)
                    mode_used = "local"
                    success = True

        except Exception as e:
            self.logger.error(
                event='TTS_SYNTHESIS_FAILED',
                message=f'TTS synthesis failed: {str(e)}',
                error=str(e)
            )
            raise

        finally:
            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)

            # Log event
            self.logger.tts_completed(
                text_length=len(text),
                audio_duration_ms=duration_ms,
                mode=mode_used
            )

            # Record metrics
            self.metrics_logger.record_metric('tts_latency_ms', duration_ms)

        # Play audio if requested
        if play_audio and audio_bytes:
            self._play_audio(audio_bytes)

        return audio_bytes

    def _synthesize_api(self, text: str) -> bytes:
        """Synthesize using ElevenLabs API"""
        if not ELEVENLABS_AVAILABLE:
            raise RuntimeError("ElevenLabs library not available")

        if self.elevenlabs_client is None:
            raise RuntimeError("ElevenLabs API key not configured")

        try:
            # Generate audio using ElevenLabs v2 API
            # Using text_to_speech.convert() method
            # Use MP3 format for web browser compatibility
            audio_generator = self.elevenlabs_client.text_to_speech.convert(
                voice_id="JBFqnCBsd6RMkjVDRZzb",  # Rachel voice (default)
                text=text,
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128"  # MP3 format for web playback
            )

            # Collect audio bytes from generator
            audio_bytes = b''
            for chunk in audio_generator:
                audio_bytes += chunk

            return audio_bytes

        except Exception as e:
            raise RuntimeError(f"ElevenLabs API error: {str(e)}")

    def _synthesize_local(self, text: str) -> bytes:
        """Synthesize using Piper (local TTS)"""
        if not PIPER_AVAILABLE:
            # Fallback: Generate simple tone or use system TTS
            # For baseline, we'll use a placeholder
            raise RuntimeError("Piper TTS not available (requires additional setup)")

        # TODO: Implement Piper TTS integration
        # This requires downloading Piper models and voice files
        # See: https://github.com/rhasspy/piper
        raise NotImplementedError("Piper TTS not yet implemented")

    def _play_audio(self, audio_bytes: bytes) -> None:
        """Play audio through speakers"""
        try:
            self.audio_utils.play_audio(audio_bytes)
        except Exception as e:
            self.logger.error(
                event='TTS_PLAYBACK_ERROR',
                message=f'Error playing TTS audio: {str(e)}',
                error=str(e)
            )

    def save_audio(self, audio_bytes: bytes, file_path: Path) -> None:
        """Save synthesized audio to file"""
        try:
            self.audio_utils.save_audio(audio_bytes, file_path)
            self.logger.info(
                event='TTS_AUDIO_SAVED',
                message=f'TTS audio saved to {file_path}',
                file_path=str(file_path)
            )
        except Exception as e:
            self.logger.error(
                event='TTS_SAVE_ERROR',
                message=f'Error saving TTS audio: {str(e)}',
                error=str(e)
            )

    def test_service(self) -> bool:
        """Test TTS service with a simple phrase"""
        try:
            test_text = "Voice assistant is ready."
            self.synthesize(test_text, play_audio=False)
            return True
        except Exception as e:
            self.logger.error(
                event='TTS_TEST_FAILED',
                message=f'TTS service test failed: {str(e)}',
                error=str(e)
            )
            return False


def create_tts_service(
    config: Config,
    logger: EventLogger,
    metrics_logger: MetricsLogger,
    audio_utils: AudioUtils
) -> TTSService:
    """Factory function to create TTS service"""
    service = TTSService(
        config=config,
        logger=logger,
        metrics_logger=metrics_logger,
        audio_utils=audio_utils
    )
    return service


# Simple spoken confirmation helper
def speak_confirmation(tts_service: TTSService, message: str = "I'm listening") -> None:
    """Speak confirmation message"""
    try:
        tts_service.synthesize(message, play_audio=True)
    except Exception as e:
        # Log error but don't crash
        tts_service.logger.warning(
            event='CONFIRMATION_SPEECH_FAILED',
            message=f'Failed to speak confirmation: {str(e)}'
        )
