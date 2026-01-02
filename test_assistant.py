"""
Test Voice Assistant without Wake Word Detection
Press ENTER to trigger voice recording
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.config import get_config
from src.core.context_manager import create_context_manager
from src.models.voice_command import VoiceCommand
from src.models.intent import IntentType
from src.services.tts import create_tts_service
from src.services.stt import create_stt_service
from src.services.llm import create_llm_service
from src.services.intent_classifier import create_intent_classifier
from src.services.action_executor import create_action_executor
from src.storage.memory_store import MemoryStore
from src.utils.audio_utils import AudioConfig, get_audio_utils
from src.utils.logger import get_event_logger, get_metrics_logger


class VoiceAssistantTest:
    """Voice Assistant test harness without wake word"""

    def __init__(self):
        print("Initializing Voice Assistant (Test Mode - No Wake Word)...")
        self.config = get_config()

        # Initialize logging
        self.event_logger = get_event_logger(
            name="voice_assistant_test",
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

        # Initialize audio utilities
        audio_config = AudioConfig(
            sample_rate=self.config.audio.sample_rate,
            channels=self.config.audio.channels,
            chunk_size=self.config.audio.chunk_size,
            input_device=self.config.audio.input_device,
            output_device=self.config.audio.output_device
        )
        self.audio_utils = get_audio_utils(audio_config)

        # Initialize services
        self.tts_service = create_tts_service(
            config=self.config,
            logger=self.event_logger,
            metrics_logger=self.metrics_logger,
            audio_utils=self.audio_utils
        )
        print("  [OK] TTS service ready")

        self.stt_service = create_stt_service(
            config=self.config,
            logger=self.event_logger,
            metrics_logger=self.metrics_logger,
            audio_utils=self.audio_utils
        )
        print("  [OK] STT service ready")

        self.llm_service = create_llm_service(
            config=self.config,
            logger=self.event_logger,
            metrics_logger=self.metrics_logger
        )
        print("  [OK] LLM service ready")

        self.intent_classifier = create_intent_classifier(
            config=self.config,
            logger=self.event_logger,
            metrics_logger=self.metrics_logger
        )
        print("  [OK] Intent classifier ready")

        # Initialize context manager
        self.memory_store = MemoryStore()
        self.context_manager = create_context_manager(
            config=self.config,
            logger=self.event_logger,
            metrics_logger=self.metrics_logger,
            memory_store=self.memory_store,
            encrypted_store=None  # Encryption disabled in test mode
        )
        print("  [OK] Context manager ready")

        # Initialize action executor
        self.action_executor = create_action_executor(
            config=self.config,
            logger=self.event_logger,
            metrics_logger=self.metrics_logger
        )
        print("  [OK] Action executor ready")

        print(f"\n[OK] Voice Assistant initialized")
        print(f"  STT mode: {self.config.stt.primary_mode}")
        print(f"  LLM mode: {self.config.llm.primary_mode}")
        print(f"  TTS mode: {self.config.tts.primary_mode}")
        print()

    def process_voice_command(self):
        """Process complete voice command pipeline"""
        # Step 1: Record audio
        print("\n" + "=" * 60)
        print("RECORDING... (speak now, 5 seconds)")
        print("=" * 60)
        recording_duration = 20.0

        try:
            audio_data = self.audio_utils.record_audio(recording_duration)
            duration_ms = int(self.audio_utils.get_duration(audio_data) * 1000)

            print(f"[OK] Recording complete ({duration_ms}ms)")

            # Create VoiceCommand model
            voice_command = VoiceCommand(
                audio_data=audio_data,
                duration_ms=duration_ms
            )

        except Exception as e:
            print(f"[ERROR] Recording failed: {str(e)}")
            return

        # Step 2: Transcribe with STT
        print("\n[STEP 2] Transcribing...")

        try:
            voice_command = self.stt_service.transcribe_voice_command(voice_command)
            transcribed_text = voice_command.transcribed_text

            print(f"[OK] Transcribed: \"{transcribed_text}\"")
            print(f"     Confidence: {voice_command.confidence_score:.2f}")

            if not transcribed_text or len(transcribed_text.strip()) == 0:
                print("[WARN] No speech detected")
                return

        except Exception as e:
            print(f"[ERROR] Speech recognition failed: {str(e)}")
            return

        # Step 3: Classify intent
        print("\n[STEP 3] Classifying intent...")

        try:
            intent = self.intent_classifier.classify_voice_command(voice_command)

            print(f"[OK] Intent: {intent.intent_type.value}")
            if intent.action_type:
                print(f"     Action: {intent.action_type.value}")
            print(f"     Confidence: {intent.confidence_score:.2f}")

            # Check if intent is actionable
            if not self.intent_classifier.is_actionable(intent):
                print(f"[WARN] Intent confidence too low ({intent.confidence_score:.2f})")
                response = "I'm not sure I understood that. Could you repeat?"
                self.tts_service.synthesize(response, play_audio=True)
                return

        except Exception as e:
            print(f"[ERROR] Intent classification failed: {str(e)}")
            return

        # Step 4: Generate response with LLM
        print("\n[STEP 4] Generating response...")

        try:
            # Get current conversation context
            context = self.context_manager.get_or_create_context()

            if intent.intent_type in [IntentType.INFORMATIONAL, IntentType.CONVERSATIONAL]:
                response = self.llm_service.generate_response(
                    query=transcribed_text,
                    intent=intent,
                    context=context  # Include conversation context
                )

                print(f"[OK] Response: \"{response}\"")

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
                    print(f"     Context: {stats['exchanges']} exchanges")
                    if stats.get('topic_keywords'):
                        print(f"     Topics: {', '.join(stats['topic_keywords'][:5])}")

            elif intent.intent_type == IntentType.TASK_BASED:
                # Execute task-based actions
                print(f"     Executing action: {intent.action_type.value if intent.action_type else 'UNKNOWN'}")
                response = self.action_executor.execute_action(intent)
                print(f"[OK] Action result: \"{response}\"")

            else:
                response = "I'm not sure how to handle that request."
                print(f"[WARN] Unknown intent type")

        except Exception as e:
            print(f"[ERROR] Response generation failed: {str(e)}")
            return

        # Step 5: Speak response with TTS
        print("\n[STEP 5] Speaking response...")

        try:
            self.tts_service.synthesize(response, play_audio=True)
            print(f"[OK] Response delivered")

        except Exception as e:
            print(f"[ERROR] TTS failed: {str(e)}")
            print(f"     (Response was: \"{response}\")")

        print("\n" + "=" * 60)
        print("COMMAND COMPLETE")
        print("=" * 60)

    def run(self):
        """Run test loop"""
        print("\n" + "=" * 60)
        print("Voice Assistant - Test Mode (Keyboard Triggered)")
        print("=" * 60)
        print("Press ENTER to start recording")
        print("Press Ctrl+C to exit")
        print("=" * 60)

        try:
            while True:
                input("\nPress ENTER to record...")
                self.process_voice_command()

        except KeyboardInterrupt:
            print("\n\nShutting down...")
            self.shutdown()

    def shutdown(self):
        """Shutdown assistant"""
        if self.metrics_logger:
            self.metrics_logger.export_metrics()

        if self.audio_utils:
            self.audio_utils.close()

        print("[OK] Voice Assistant stopped")


def main():
    """Test entry point"""
    try:
        assistant = VoiceAssistantTest()
        assistant.run()
    except Exception as e:
        print(f"[ERROR] Failed to start Voice Assistant: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
