"""
Wake Word Detection Service
Continuous audio monitoring for wake word detection using pvporcupine
"""

import struct
import time
from typing import Callable, Optional

import pvporcupine

from ..core.config import Config
from ..utils.audio_utils import AudioConfig, AudioUtils
from ..utils.logger import EventLogger


class WakeWordDetector:
    """
    Wake word detection service using pvporcupine
    Monitors audio stream for wake word activation
    """

    def __init__(
        self,
        config: Config,
        logger: EventLogger,
        audio_utils: AudioUtils,
        on_wake_word: Optional[Callable[[], None]] = None
    ):
        self.config = config
        self.logger = logger
        self.audio_utils = audio_utils
        self.on_wake_word = on_wake_word

        # Initialize pvporcupine
        self.porcupine: Optional[pvporcupine.Porcupine] = None
        self._is_running = False
        self._detection_start_time: Optional[float] = None

    def initialize(self) -> None:
        """Initialize pvporcupine wake word detector"""
        try:
            # Create porcupine instance
            # Using built-in "porcupine" keyword for baseline
            # For custom "Hey Assistant", users need to train on Picovoice Console
            self.porcupine = pvporcupine.create(
                keywords=["porcupine"],  # Built-in wake word
                sensitivities=[self.config.wake_word.sensitivity]
            )

            self.logger.info(
                event='WAKE_WORD_SERVICE_INITIALIZED',
                message=f'Wake word detector initialized with sensitivity {self.config.wake_word.sensitivity}',
                sensitivity=self.config.wake_word.sensitivity,
                sample_rate=self.porcupine.sample_rate,
                frame_length=self.porcupine.frame_length
            )

        except Exception as e:
            self.logger.error(
                event='WAKE_WORD_INIT_FAILED',
                message=f'Failed to initialize wake word detector: {str(e)}',
                error=str(e)
            )
            raise

    def start(self) -> None:
        """Start wake word detection loop"""
        if not self.porcupine:
            raise RuntimeError("Wake word detector not initialized. Call initialize() first.")

        self._is_running = True
        self.logger.info(
            event='WAKE_WORD_DETECTION_STARTED',
            message='Wake word detection started'
        )

        try:
            self._detection_loop()
        except KeyboardInterrupt:
            self.logger.info(
                event='WAKE_WORD_DETECTION_STOPPED',
                message='Wake word detection stopped by user'
            )
        finally:
            self.stop()

    def _detection_loop(self) -> None:
        """Main detection loop"""
        # Audio config for pvporcupine
        audio_config = AudioConfig(
            sample_rate=self.porcupine.sample_rate,
            channels=1,
            chunk_size=self.porcupine.frame_length
        )

        # Create audio backend
        audio_backend = self.audio_utils.backend.__class__(audio_config)

        # Open audio stream
        stream = audio_backend.audio.open(
            format=audio_backend.config.format,
            channels=audio_backend.config.channels,
            rate=audio_backend.config.sample_rate,
            input=True,
            frames_per_buffer=audio_backend.config.chunk_size
        )

        self.logger.info(
            event='WAKE_WORD_LISTENING',
            message=f'Listening for wake word "{self.config.assistant.wake_word}"...'
        )

        while self._is_running:
            try:
                # Read audio frame
                pcm = stream.read(
                    self.porcupine.frame_length,
                    exception_on_overflow=False
                )

                # Convert bytes to int16 array
                pcm = struct.unpack_from(
                    "h" * self.porcupine.frame_length,
                    pcm
                )

                # Process frame
                self._detection_start_time = time.time()
                keyword_index = self.porcupine.process(pcm)

                if keyword_index >= 0:
                    # Wake word detected!
                    detection_duration_ms = int((time.time() - self._detection_start_time) * 1000)
                    self._handle_wake_word_detected(detection_duration_ms)

            except Exception as e:
                self.logger.error(
                    event='WAKE_WORD_DETECTION_ERROR',
                    message=f'Error in detection loop: {str(e)}',
                    error=str(e)
                )

        # Cleanup
        stream.stop_stream()
        stream.close()
        audio_backend.close()

    def _handle_wake_word_detected(self, duration_ms: int) -> None:
        """Handle wake word detection event"""
        confidence = self.config.wake_word.sensitivity  # Porcupine doesn't provide confidence

        # Log detection
        self.logger.wake_word_detected(
            confidence=confidence,
            duration_ms=duration_ms
        )

        # Call callback
        if self.on_wake_word:
            try:
                self.on_wake_word()
            except Exception as e:
                self.logger.error(
                    event='WAKE_WORD_CALLBACK_ERROR',
                    message=f'Error in wake word callback: {str(e)}',
                    error=str(e)
                )

    def stop(self) -> None:
        """Stop wake word detection"""
        self._is_running = False

        if self.porcupine:
            self.porcupine.delete()
            self.porcupine = None

        self.logger.info(
            event='WAKE_WORD_SERVICE_STOPPED',
            message='Wake word detection stopped'
        )

    def is_running(self) -> bool:
        """Check if detector is running"""
        return self._is_running

    def update_sensitivity(self, sensitivity: float) -> None:
        """Update wake word detection sensitivity (requires restart)"""
        if not 0.0 <= sensitivity <= 1.0:
            raise ValueError("Sensitivity must be between 0.0 and 1.0")

        self.config.wake_word.sensitivity = sensitivity

        # Restart detector with new sensitivity
        was_running = self._is_running
        if was_running:
            self.stop()
            self.initialize()

        self.logger.info(
            event='WAKE_WORD_SENSITIVITY_UPDATED',
            message=f'Wake word sensitivity updated to {sensitivity}',
            sensitivity=sensitivity,
            restarted=was_running
        )


def create_wake_word_detector(
    config: Config,
    logger: EventLogger,
    audio_utils: AudioUtils,
    on_wake_word: Optional[Callable[[], None]] = None
) -> WakeWordDetector:
    """Factory function to create and initialize wake word detector"""
    detector = WakeWordDetector(
        config=config,
        logger=logger,
        audio_utils=audio_utils,
        on_wake_word=on_wake_word
    )
    detector.initialize()
    return detector
