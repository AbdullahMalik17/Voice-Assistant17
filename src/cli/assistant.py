"""
Voice Assistant CLI Entry Point
Main command-line interface for the voice assistant
"""

import sys
from pathlib import Path

from ..core.config import get_config
from ..services.tts import create_tts_service, speak_confirmation
from ..services.wake_word import create_wake_word_detector
from ..utils.audio_utils import AudioConfig, get_audio_utils
from ..utils.logger import get_event_logger, get_metrics_logger


class VoiceAssistant:
    """
    Main voice assistant application
    Coordinates wake word detection, TTS, and voice interaction
    """

    def __init__(self):
        # Load configuration
        print("Initializing Voice Assistant...")
        self.config = get_config()

        # Initialize logging
        self.event_logger = get_event_logger(
            name="voice_assistant",
            log_dir=self.config.log_dir,
            level=self.config.logging.level,
            format_type=self.config.logging.format,
            max_size_mb=self.config.logging.event_log_max_size_mb,
            backup_count=self.config.logging.event_log_backup_count,
            console_output=self.config.logging.console_output
        )

        self.metrics_logger = get_metrics_logger(
            log_dir=self.config.log_dir,
            export_interval_seconds=self.config.logging.metrics_export_interval_seconds
        )

        self.event_logger.info(
            event='SYSTEM_STARTUP',
            message=f'Voice Assistant v{self.config.assistant.version} starting up'
        )

        # Initialize audio utilities
        audio_config = AudioConfig(
            sample_rate=self.config.audio.sample_rate,
            channels=self.config.audio.channels,
            chunk_size=self.config.audio.chunk_size,
            input_device=self.config.audio.input_device,
            output_device=self.config.audio.output_device
        )
        self.audio_utils = get_audio_utils(audio_config)

        self.event_logger.info(
            event='AUDIO_INITIALIZED',
            message='Audio utilities initialized',
            sample_rate=audio_config.sample_rate,
            channels=audio_config.channels
        )

        # Initialize TTS service
        self.tts_service = create_tts_service(
            config=self.config,
            logger=self.event_logger,
            metrics_logger=self.metrics_logger,
            audio_utils=self.audio_utils
        )

        self.event_logger.info(
            event='TTS_SERVICE_READY',
            message=f'TTS service ready (mode: {self.config.tts.primary_mode})',
            mode=self.config.tts.primary_mode
        )

        # Initialize wake word detector
        self.wake_word_detector = create_wake_word_detector(
            config=self.config,
            logger=self.event_logger,
            audio_utils=self.audio_utils,
            on_wake_word=self._on_wake_word_detected
        )

        self.event_logger.info(
            event='WAKE_WORD_SERVICE_READY',
            message=f'Wake word detector ready (sensitivity: {self.config.wake_word.sensitivity})',
            sensitivity=self.config.wake_word.sensitivity
        )

        print(f"✓ Voice Assistant v{self.config.assistant.version} initialized")
        print(f"✓ Wake word: \"{self.config.assistant.wake_word}\"")
        print(f"✓ Sensitivity: {self.config.wake_word.sensitivity}")
        print(f"✓ TTS mode: {self.config.tts.primary_mode}")
        print(f"✓ Log level: {self.config.logging.level}")
        print()

    def _on_wake_word_detected(self) -> None:
        """Callback when wake word is detected"""
        print(f"\n🎙️  Wake word detected!")

        # Speak confirmation
        confirmation_message = "I'm listening"
        print(f"🔊 {confirmation_message}")

        try:
            speak_confirmation(self.tts_service, confirmation_message)
        except Exception as e:
            self.event_logger.error(
                event='CONFIRMATION_FAILED',
                message=f'Failed to speak confirmation: {str(e)}',
                error=str(e)
            )
            print(f"⚠️  Could not speak confirmation: {str(e)}")

        # TODO: Capture voice command and process
        # For Phase 3 (User Story 1), we just confirm and return to listening
        print("✓ Confirmation spoken. Returning to wake word detection...")
        print()

    def run(self) -> None:
        """Start the voice assistant main loop"""
        try:
            print("=" * 50)
            print("Voice Assistant - Ready")
            print("=" * 50)
            print(f"Say \"{self.config.assistant.wake_word}\" to activate")
            print("Press Ctrl+C to exit")
            print("=" * 50)
            print()

            # Start wake word detection loop
            self.wake_word_detector.start()

        except KeyboardInterrupt:
            print("\n\nShutting down gracefully...")
            self.shutdown()

        except Exception as e:
            self.event_logger.critical(
                event='SYSTEM_CRASH',
                message=f'Fatal error: {str(e)}',
                error=str(e)
            )
            print(f"\n❌ Fatal error: {str(e)}")
            self.shutdown()
            sys.exit(1)

    def shutdown(self) -> None:
        """Shutdown assistant gracefully"""
        self.event_logger.info(
            event='SYSTEM_SHUTDOWN',
            message='Voice Assistant shutting down'
        )

        # Stop wake word detector
        if self.wake_word_detector:
            self.wake_word_detector.stop()

        # Export final metrics
        if self.metrics_logger:
            self.metrics_logger.export_metrics()

        # Close audio
        if self.audio_utils:
            self.audio_utils.close()

        print("✓ Voice Assistant stopped")


def main():
    """CLI entry point"""
    try:
        assistant = VoiceAssistant()
        assistant.run()
    except Exception as e:
        print(f"❌ Failed to start Voice Assistant: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
