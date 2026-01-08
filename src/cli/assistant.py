"""
Voice Assistant CLI Entry Point
Main command-line interface for the voice assistant
"""

import sys
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional

from ..core.config import get_config
from ..core.context_manager import create_context_manager
from ..core.request_queue_manager import create_request_queue_manager, RequestQueueManager
from ..models.voice_command import VoiceCommand
from ..models.intent import IntentType
from ..models.request_queue import RequestType
from ..services.tts import create_tts_service, speak_confirmation
from ..services.stt import create_stt_service
from ..services.llm import create_llm_service
from ..services.intent_classifier import create_intent_classifier
from ..services.wake_word import create_wake_word_detector
from ..services.action_executor import create_action_executor
from ..storage.memory_store import MemoryStore
from ..storage.encrypted_store import EncryptedStore
from ..utils.audio_utils import AudioConfig, get_audio_utils
from ..utils.logger import get_event_logger, get_metrics_logger
from ..utils.network_monitor import get_network_monitor


class VoiceAssistant:
    """
    Main voice assistant application
    Coordinates wake word detection, TTS, and voice interaction
    """

    def __init__(self):
        # Load configuration
        print("Initializing Voice Assistant...")
        self.config = get_config()

        # Processing state for interrupt handling
        self._is_processing = False
        self._processing_lock = threading.Lock()
        self._interrupt_requested = False
        self._network_status = True  # Assume online initially

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

        # Initialize STT service
        self.stt_service = create_stt_service(
            config=self.config,
            logger=self.event_logger,
            metrics_logger=self.metrics_logger,
            audio_utils=self.audio_utils
        )

        self.event_logger.info(
            event='STT_SERVICE_READY',
            message=f'STT service ready (mode: {self.config.stt.primary_mode})',
            mode=self.config.stt.primary_mode
        )

        # Initialize LLM service
        self.llm_service = create_llm_service(
            config=self.config,
            logger=self.event_logger,
            metrics_logger=self.metrics_logger
        )

        self.event_logger.info(
            event='LLM_SERVICE_READY',
            message=f'LLM service ready (mode: {self.config.llm.primary_mode})',
            mode=self.config.llm.primary_mode
        )

        # Initialize intent classifier
        self.intent_classifier = create_intent_classifier(
            config=self.config,
            logger=self.event_logger,
            metrics_logger=self.metrics_logger
        )

        self.event_logger.info(
            event='INTENT_CLASSIFIER_READY',
            message='Intent classifier ready'
        )

        # Initialize storage (for context persistence)
        self.memory_store = MemoryStore()
        self.encrypted_store = None
        if self.config.context.enable_persistence:
            try:
                self.encrypted_store = EncryptedStore(
                    storage_dir=self.config.log_dir / "contexts"
                )
                self.event_logger.info(
                    event='ENCRYPTED_STORAGE_READY',
                    message='Encrypted context storage initialized'
                )
            except Exception as e:
                self.event_logger.warning(
                    event='ENCRYPTED_STORAGE_FAILED',
                    message=f'Failed to initialize encrypted storage: {str(e)}',
                    error=str(e)
                )

        # Initialize context manager
        self.context_manager = create_context_manager(
            config=self.config,
            logger=self.event_logger,
            metrics_logger=self.metrics_logger,
            memory_store=self.memory_store,
            encrypted_store=self.encrypted_store
        )

        self.event_logger.info(
            event='CONTEXT_MANAGER_READY',
            message='Context manager ready',
            max_exchanges=self.config.context.max_exchanges,
            timeout_seconds=self.config.context.timeout_seconds,
            persistence_enabled=self.config.context.enable_persistence
        )

        # Initialize action executor
        self.action_executor = create_action_executor(
            config=self.config,
            logger=self.event_logger,
            metrics_logger=self.metrics_logger
        )

        self.event_logger.info(
            event='ACTION_EXECUTOR_READY',
            message='Action executor ready'
        )

        # Initialize network monitor
        self.network_monitor = get_network_monitor()
        self._network_status = self.network_monitor.is_connected()

        # Initialize request queue manager for offline resilience
        self.queue_manager = create_request_queue_manager(
            logger=self.event_logger,
            metrics_logger=self.metrics_logger,
            max_queue_size=10,
            check_interval_seconds=5.0,
            network_monitor=self.network_monitor
        )

        # Set up network status callback
        self.queue_manager.set_network_status_callback(self._on_network_status_change)

        # Start network monitoring
        self.queue_manager.start_monitoring()

        self.event_logger.info(
            event='NETWORK_MONITOR_READY',
            message=f'Network monitor ready (status: {"online" if self._network_status else "offline"})',
            is_online=self._network_status
        )

        # Initialize wake word detector
        try:
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
        except RuntimeError as e:
            self.event_logger.warning(
                event='WAKE_WORD_INIT_FAILED',
                message=f'Wake word detector failed: {e}. Falling back to manual activation.',
                error=str(e)
            )
            self.wake_word_detector = None

        print(f"✓ Voice Assistant v{self.config.assistant.version} initialized")
        if self.wake_word_detector:
            print(f"✓ Wake word: \"{self.config.assistant.wake_word}\"")
            print(f"✓ Sensitivity: {self.config.wake_word.sensitivity}")
        else:
            print("⚠️  Wake word detection disabled. Press Enter to activate.")
        print(f"✓ STT mode: {self.config.stt.primary_mode}")
        print(f"✓ LLM mode: {self.config.llm.primary_mode}")
        print(f"✓ TTS mode: {self.config.tts.primary_mode}")
        print(f"✓ Log level: {self.config.logging.level}")
        print()

    def _on_network_status_change(self, is_connected: bool) -> None:
        """Callback when network status changes"""
        self._network_status = is_connected

        if is_connected:
            print("🌐 Network connection restored")
            self.event_logger.info(
                event='NETWORK_RESTORED',
                message='Network connection restored'
            )
        else:
            print("📡 Network connection lost")
            self.event_logger.warning(
                event='NETWORK_LOST',
                message='Network connection lost'
            )
            # Speak notification if not currently processing
            if not self._is_processing:
                try:
                    self.tts_service.synthesize(
                        "Waiting for network connection. Local features are still available.",
                        play_audio=True
                    )
                except:
                    pass  # Don't crash if TTS fails

    def _request_interrupt(self) -> None:
        """Request interruption of current processing"""
        with self._processing_lock:
            if self._is_processing:
                self._interrupt_requested = True
                self.event_logger.info(
                    event='INTERRUPT_REQUESTED',
                    message='Processing interrupt requested'
                )
                # Interrupt context manager
                self.context_manager.interrupt_context()
                # Cancel pending queue requests
                self.queue_manager.cancel_all_pending()
                print("⚡ Interrupting current task...")

    def _check_interrupt(self) -> bool:
        """Check if interrupt was requested and clear flag"""
        with self._processing_lock:
            if self._interrupt_requested:
                self._interrupt_requested = False
                return True
            return False

    def _on_wake_word_detected(self) -> None:
        """Callback when wake word is detected"""
        if not self.wake_word_detector: # Manual activation
             print(f"\n🎙️  Manual activation detected!")
        else:
            print(f"\n🎙️  Wake word detected!")

        # Check if we're already processing - if so, request interrupt
        with self._processing_lock:
            if self._is_processing:
                self._request_interrupt()
                print("⚡ Interrupting previous command...")
                return

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

        # Process voice command
        try:
            self._process_voice_command()
        except Exception as e:
            self.event_logger.error(
                event='VOICE_COMMAND_PROCESSING_FAILED',
                message=f'Failed to process voice command: {str(e)}',
                error=str(e)
            )
            print(f"❌ Error processing command: {str(e)}")

            # Speak error message
            try:
                error_response = "I'm sorry, I couldn't process that request."
                self.tts_service.synthesize(error_response, play_audio=True)
            except:
                pass  # Don't crash on TTS error

        # For manual activation loop, we don't print this
        if self.wake_word_detector:
            print("✓ Ready for next command. Returning to wake word detection...")
            print()

    def _process_voice_command(self) -> None:
        """Process complete voice command pipeline with interrupt support"""
        # Set processing state
        with self._processing_lock:
            self._is_processing = True
            self._interrupt_requested = False

        try:
            # Step 1: Record audio
            print("🎤 Recording... (speak now)")
            recording_duration = 5.0  # 5 seconds for user query

            try:
                audio_data = self.audio_utils.record_audio(recording_duration)
                duration_ms = int(self.audio_utils.get_duration(audio_data) * 1000)

                print(f"✓ Recording complete ({duration_ms}ms)")

                # Create VoiceCommand model
                voice_command = VoiceCommand(
                    audio_data=audio_data,
                    duration_ms=duration_ms
                )

            except Exception as e:
                self.event_logger.error(
                    event='AUDIO_RECORDING_FAILED',
                    message=f'Failed to record audio: {str(e)}',
                    error=str(e)
                )
                print(f"❌ Recording failed: {str(e)}")
                raise

            # Check for interrupt after recording
            if self._check_interrupt():
                print("⚡ Command interrupted")
                return

            # Step 2: Transcribe with STT
            print("📝 Transcribing...")

            try:
                voice_command = self.stt_service.transcribe_voice_command(voice_command)
                transcribed_text = voice_command.transcribed_text

                print(f"✓ Transcribed: \"{transcribed_text}\"")
                print(f"  Confidence: {voice_command.confidence_score:.2f}")

                if not transcribed_text or len(transcribed_text.strip()) == 0:
                    print("⚠️  No speech detected")
                    return

            except Exception as e:
                error_str = str(e)
                if "401" in error_str and "API key" in error_str:
                    self.event_logger.error(
                        event='STT_AUTH_FAILED',
                        message='OpenAI API authentication failed',
                        error='Invalid API Key'
                    )
                    print("❌ STT Authentication failed: Invalid OpenAI API Key.")
                    print("   Please check your configuration or .env file.")
                    
                    try:
                        self.tts_service.synthesize("Please check your API key configuration.", play_audio=True)
                    except:
                        pass
                    return

                self.event_logger.error(
                    event='STT_FAILED',
                    message=f'Speech recognition failed: {str(e)}',
                    error=str(e)
                )
                print(f"❌ Speech recognition failed: {str(e)}")
                raise

            # Check for interrupt after STT
            if self._check_interrupt():
                print("⚡ Command interrupted")
                return

            # Step 3: Classify intent
            print("🎯 Classifying intent...")

            try:
                intent = self.intent_classifier.classify_voice_command(voice_command)

                print(f"✓ Intent: {intent.intent_type.value}")
                if intent.action_type:
                    print(f"  Action: {intent.action_type.value}")
                print(f"  Confidence: {intent.confidence_score:.2f}")

                # Check if intent is actionable
                if not self.intent_classifier.is_actionable(intent):
                    print(f"⚠️  Intent confidence too low ({intent.confidence_score:.2f})")
                    response = "I'm not sure I understood that. Could you repeat?"
                    self.tts_service.synthesize(response, play_audio=True)
                    return

            except Exception as e:
                self.event_logger.error(
                    event='INTENT_CLASSIFICATION_FAILED',
                    message=f'Intent classification failed: {str(e)}',
                    error=str(e)
                )
                print(f"❌ Intent classification failed: {str(e)}")
                raise

            # Check for interrupt after intent classification
            if self._check_interrupt():
                print("⚡ Command interrupted")
                return

            # Step 4: Generate response with LLM or execute action
            print("🤖 Generating response...")

            try:
                # Get current conversation context
                context = self.context_manager.get_or_create_context()

                # Handle informational and conversational intents with LLM
                if intent.intent_type in [IntentType.INFORMATIONAL, IntentType.CONVERSATIONAL]:
                    response = self.llm_service.generate_response(
                        query=transcribed_text,
                        intent=intent,
                        context=context  # Include conversation context
                    )

                    print(f"✓ Response: \"{response}\"")

                    # Add exchange to context
                    self.context_manager.add_exchange(
                        user_input=transcribed_text,
                        intent=intent,
                        assistant_response=response,
                        confidence=intent.confidence_score
                    )

                    # Show context stats
                    stats = self.context_manager.get_context_stats()
                    if stats['exchanges'] > 0:
                        print(f"  Context: {stats['exchanges']} exchanges, topics: {', '.join(stats.get('topic_keywords', [])[:3])}")

                elif intent.intent_type == IntentType.TASK_BASED:
                    # Execute task-based actions
                    print(f"⚙️  Executing action: {intent.action_type.value if intent.action_type else 'UNKNOWN'}")
                    response = self.action_executor.execute_action(intent)
                    print(f"✓ Action result: \"{response}\"")

                else:
                    response = "I'm not sure how to handle that request."
                    print(f"⚠️  Unknown intent type")

            except Exception as e:
                self.event_logger.error(
                    event='LLM_FAILED',
                    message=f'LLM response generation failed: {str(e)}',
                    error=str(e)
                )
                print(f"❌ Response generation failed: {str(e)}")
                raise

            # Check for interrupt before TTS
            if self._check_interrupt():
                print("⚡ Command interrupted (response not spoken)")
                return

            # Step 5: Speak response with TTS
            print("🔊 Speaking response...")

            try:
                self.tts_service.synthesize(response, play_audio=True)
                print(f"✓ Response delivered")

            except Exception as e:
                self.event_logger.error(
                    event='TTS_RESPONSE_FAILED',
                    message=f'Failed to speak response: {str(e)}',
                    error=str(e)
                )
                print(f"❌ TTS failed: {str(e)}")
                # Don't raise - response was generated, just couldn't speak it
                print(f"   (Response was: \"{response}\")")

        finally:
            # Always clear processing state
            with self._processing_lock:
                self._is_processing = False
    
    def _manual_activation_loop(self) -> None:
        """Loop that waits for user to press Enter to activate."""
        while True:
            try:
                input("Press Enter to speak...")
                self._on_wake_word_detected()
            except EOFError: # Handle piped input or script ending
                break
            except KeyboardInterrupt:
                break

    def run(self) -> None:
        """Start the voice assistant main loop"""
        try:
            print("=" * 50)
            print("Voice Assistant - Ready")
            print("=" * 50)
            if self.wake_word_detector:
                print(f"Say \"{self.config.assistant.wake_word}\" to activate")
            else:
                print("Wake word detection failed. Press Enter to activate.")
            print("Press Ctrl+C to exit")
            print("=" * 50)
            print()

            # Start main loop
            if self.wake_word_detector:
                self.wake_word_detector.start()
            else:
                self._manual_activation_loop()

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

        # Stop network monitoring
        if self.queue_manager:
            self.queue_manager.stop_monitoring()
            # Cancel any pending requests
            cancelled = self.queue_manager.cancel_all_pending()
            if cancelled > 0:
                print(f"  Cancelled {cancelled} pending requests")

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
