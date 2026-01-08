"""
Wake Word Detection Service
Continuous audio monitoring for wake word detection using OpenWakeWord
Free, open-source wake word detection - no API keys required!
"""

import struct
import time
from typing import Callable, Optional

import numpy as np
from openwakeword.model import Model as OpenWakeWordModel

from ..core.config import Config
from ..utils.audio_utils import AudioConfig, AudioUtils
from ..utils.logger import EventLogger


class WakeWordDetector:
    """
    Wake word detection service using OpenWakeWord
    Monitors audio stream for wake word activation

    OpenWakeWord is a free, open-source wake word detection system that requires
    no API keys and supports multiple pre-trained models and custom training.
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

        # Initialize OpenWakeWord
        self.oww_model: Optional[OpenWakeWordModel] = None
        self._is_running = False
        self._detection_start_time: Optional[float] = None

        # Audio configuration for OpenWakeWord (16kHz required)
        self.sample_rate = 16000
        self.chunk_size = 1280  # 80ms at 16kHz

    def initialize(self) -> None:
        """Initialize OpenWakeWord wake word detector"""
        try:
            # Create OpenWakeWord model with pre-trained models
            # Available models: alexa, hey_jarvis, hey_mycroft, etc.
            self.oww_model = OpenWakeWordModel(
                wakeword_models=self.config.wake_word.models,
                inference_framework='onnx'  # Use ONNX for cross-platform support
            )

            self.logger.info(
                event='WAKE_WORD_SERVICE_INITIALIZED',
                message=f'OpenWakeWord initialized with models: {self.config.wake_word.models}',
                models=self.config.wake_word.models,
                sensitivity=self.config.wake_word.sensitivity,
                sample_rate=self.sample_rate,
                chunk_size=self.chunk_size
            )
        except Exception as e:
            self.logger.error(
                event='WAKE_WORD_INITIALIZATION_FAILED',
                message=f'Failed to initialize OpenWakeWord: {str(e)}',
                error=str(e)
            )
            raise RuntimeError(f"OpenWakeWord initialization failed: {str(e)}")

    def start(self) -> None:
        """Start wake word detection loop"""
        if not self.oww_model:
            raise RuntimeError("Wake word detector not initialized. Call initialize() first.")

        self._is_running = True
        self.logger.info(
            event='WAKE_WORD_DETECTION_STARTED',
            message='Wake word detection started (OpenWakeWord)'
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
        # Audio config for OpenWakeWord (requires 16kHz)
        audio_config = AudioConfig(
            sample_rate=self.sample_rate,
            channels=1,
            chunk_size=self.chunk_size
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
            message=f'Listening for wake words: {", ".join(self.config.wake_word.models)}...'
        )

        while self._is_running:
            try:
                # Read audio frame (1280 samples = 80ms at 16kHz)
                audio_data = stream.read(
                    self.chunk_size,
                    exception_on_overflow=False
                )

                # Convert bytes to int16 array
                audio_array = np.frombuffer(audio_data, dtype=np.int16)

                # Process frame with OpenWakeWord
                self._detection_start_time = time.time()
                prediction = self.oww_model.predict(audio_array)

                # Check if any wake word was detected
                for model_name, score in prediction.items():
                    if score >= self.config.wake_word.sensitivity:
                        detection_duration_ms = int((time.time() - self._detection_start_time) * 1000)
                        self._handle_wake_word_detected(model_name, score, detection_duration_ms)
                        break  # Only trigger once per detection

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

    def _handle_wake_word_detected(self, model_name: str, confidence: float, duration_ms: int) -> None:
        """Handle wake word detection event"""
        # Log detection
        self.logger.wake_word_detected(
            confidence=confidence,
            duration_ms=duration_ms
        )

        self.logger.info(
            event='WAKE_WORD_DETECTED',
            message=f'Wake word "{model_name}" detected with confidence {confidence:.2f}',
            model=model_name,
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

        if self.oww_model:
            # OpenWakeWord doesn't require explicit cleanup
            self.oww_model = None

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

    def add_custom_model(self, model_path: str) -> None:
        """
        Add a custom trained wake word model

        Args:
            model_path: Path to the custom .onnx or .tflite model file
        """
        if not self.oww_model:
            raise RuntimeError("Wake word detector not initialized")

        try:
            # OpenWakeWord supports loading custom models dynamically
            self.oww_model = OpenWakeWordModel(
                wakeword_models=self.config.wake_word.models,
                custom_verifier_models={model_path: 0.5},
                inference_framework='onnx'
            )

            self.logger.info(
                event='CUSTOM_WAKE_WORD_MODEL_ADDED',
                message=f'Added custom wake word model: {model_path}',
                model_path=model_path
            )
        except Exception as e:
            self.logger.error(
                event='CUSTOM_WAKE_WORD_MODEL_FAILED',
                message=f'Failed to add custom model: {str(e)}',
                error=str(e)
            )
            raise


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
