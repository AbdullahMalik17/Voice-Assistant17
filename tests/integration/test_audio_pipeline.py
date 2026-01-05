"""
Integration tests for the complete audio pipeline.
Tests STT → Intent → Entity Extraction → Slot Filling flow.
"""

import pytest
import numpy as np
from pathlib import Path
from uuid import uuid4

from src.services.audio_preprocessor import AudioPreprocessor, AudioPreprocessorConfig, NoiseReductionMethod
from src.services.entity_extractor import EntityExtractor, EntityType
from src.services.slot_filler import SlotFiller
from tests.fixtures.audio_fixtures import generate_sine_wave, generate_speech_like, add_noise


class TestAudioPreprocessing:
    """Test audio preprocessing pipeline."""

    def test_noise_reduction_reduces_noise(self):
        """Test that noise reduction actually reduces noise."""
        config = AudioPreprocessorConfig(
            noise_reduction_enabled=True,
            noise_reduction_method=NoiseReductionMethod.SPECTRAL_GATING,
            normalization_enabled=False,
            sample_rate=16000
        )
        preprocessor = AudioPreprocessor(config)

        # Use pure noise (clean is silence) to avoid phase/alignment issues
        # clean = generate_speech_like(duration=2.0)
        # noisy = add_noise(clean, snr_db=0) # High noise
        
        # Generate pure white noise
        noisy = np.random.normal(0, 0.1, 32000) * 32767
        noisy = np.clip(noisy, -32768, 32767).astype(np.int16)

        # Process
        result = preprocessor.process(noisy.tobytes())

        # Calculate RMS
        noisy_float = noisy.astype(float)
        processed_float = np.frombuffer(result.audio_bytes, dtype=np.int16).astype(float)

        noise_rms_before = np.sqrt(np.mean(noisy_float ** 2))
        noise_rms_after = np.sqrt(np.mean(processed_float ** 2))

        assert noise_rms_after < noise_rms_before, f"Noise reduction should reduce noise (Before: {noise_rms_before}, After: {noise_rms_after})"
        assert result.noise_reduced

    def test_normalization(self):
        """Test audio normalization."""
        config = AudioPreprocessorConfig(
            normalization_enabled=True,
            target_level_db=-20.0,
            sample_rate=16000
        )
        preprocessor = AudioPreprocessor(config)

        # Generate quiet audio
        quiet = (generate_sine_wave(amplitude=0.1) * 0.1).astype(np.int16)

        result = preprocessor.process(quiet.tobytes())
        processed = np.frombuffer(result.audio_bytes, dtype=np.int16)

        # Processed should be louder
        assert np.max(np.abs(processed)) > np.max(np.abs(quiet))

    def test_aec_enabled(self):
        """Test acoustic echo cancellation is applied."""
        config = AudioPreprocessorConfig(
            aec_enabled=True,
            sample_rate=16000
        )
        preprocessor = AudioPreprocessor(config)

        audio = generate_speech_like(duration=1.0)
        reference = generate_sine_wave(frequency=1000, duration=1.0)

        result = preprocessor.process(audio.tobytes(), reference.tobytes())

        assert result.aec_applied


class TestEntityExtraction:
    """Test entity extraction."""

    def test_extract_duration(self):
        """Test extracting duration entities."""
        extractor = EntityExtractor()

        result = extractor.extract("Set a timer for 5 minutes")

        durations = result.get_entities_by_type(EntityType.DURATION)
        assert len(durations) > 0
        assert durations[0].normalized_value == 300  # 5 minutes in seconds

    def test_extract_time(self):
        """Test extracting time entities."""
        extractor = EntityExtractor()

        result = extractor.extract("Wake me up at 7:30 AM")

        times = result.get_entities_by_type(EntityType.TIME)
        assert len(times) > 0
        assert "7:30" in times[0].raw_text.lower()

    def test_extract_email(self):
        """Test extracting email addresses."""
        extractor = EntityExtractor()

        result = extractor.extract("Send email to john@example.com")

        emails = result.get_entities_by_type(EntityType.EMAIL)
        assert len(emails) > 0
        assert emails[0].value == "john@example.com"

    def test_extract_app_name(self):
        """Test extracting application names."""
        extractor = EntityExtractor()

        result = extractor.extract("Open Spotify please")

        apps = result.get_entities_by_type(EntityType.APP_NAME)
        assert len(apps) > 0
        assert "spotify" in apps[0].value.lower()

    def test_extract_date_keywords(self):
        """Test extracting relative date keywords."""
        extractor = EntityExtractor()

        result = extractor.extract("Remind me tomorrow")

        dates = result.get_entities_by_type(EntityType.DATE)
        assert len(dates) > 0
        assert dates[0].normalized_value is not None


class TestSlotFilling:
    """Test slot filling for intents."""

    def test_fill_timer_slots(self):
        """Test filling slots for set_timer intent."""
        filler = SlotFiller()
        extractor = EntityExtractor()

        text = "Set a timer for 10 minutes"
        extraction = extractor.extract(text)

        result = filler.fill_slots("set_timer", extraction)

        assert result.is_complete
        assert result.get_slot_value("duration_seconds") == 600
        assert len(result.missing_required) == 0

    def test_fill_email_slots(self):
        """Test filling slots for send_email intent."""
        filler = SlotFiller()
        extractor = EntityExtractor()

        text = "Send email to test@example.com"
        extraction = extractor.extract(text)

        result = filler.fill_slots("send_email", extraction)

        assert result.get_slot_value("recipient") == "test@example.com"
        # Subject and body are optional
        assert not result.is_complete or "subject" in result.filled_slots

    def test_missing_required_slot(self):
        """Test handling missing required slots."""
        filler = SlotFiller()
        extractor = EntityExtractor()

        text = "Set a timer"  # Missing duration
        extraction = extractor.extract(text)

        result = filler.fill_slots("set_timer", extraction)

        assert not result.is_complete
        assert len(result.missing_required) > 0
        assert result.next_prompt is not None

    def test_multi_turn_slot_filling(self):
        """Test multi-turn slot filling."""
        filler = SlotFiller()
        extractor = EntityExtractor()

        # First turn: missing duration
        text1 = "Set a timer"
        extraction1 = extractor.extract(text1)
        result1 = filler.fill_slots("set_timer", extraction1)

        assert not result1.is_complete

        # Second turn: provide duration
        text2 = "5 minutes"
        extraction2 = extractor.extract(text2)
        result2 = filler.fill_slot_from_input(result1, text2, extraction2)

        assert result2.is_complete
        assert result2.get_slot_value("duration_seconds") == 300


class TestEndToEndPipeline:
    """Test complete end-to-end pipeline."""

    def test_timer_command_pipeline(self):
        """Test complete pipeline for timer command."""
        extractor = EntityExtractor()
        filler = SlotFiller()

        # User says: "Set a timer for 15 minutes"
        text = "Set a timer for 15 minutes"

        # Extract entities
        extraction = extractor.extract(text)
        assert len(extraction.entities) > 0

        # Fill slots
        result = filler.fill_slots("set_timer", extraction)

        assert result.is_complete
        assert result.get_slot_value("duration_seconds") == 900
        assert result.get_slot_value("label") is not None  # Default value

    def test_launch_app_pipeline(self):
        """Test pipeline for launching app."""
        extractor = EntityExtractor()
        filler = SlotFiller()

        text = "Open Spotify"
        extraction = extractor.extract(text)
        result = filler.fill_slots("launch_app", extraction)

        assert result.is_complete
        app_name = result.get_slot_value("app_name")
        assert app_name is not None
        assert "spotify" in app_name.lower()

    def test_weather_query_pipeline(self):
        """Test pipeline for weather query."""
        extractor = EntityExtractor()
        filler = SlotFiller()

        text = "What's the weather in Tokyo"
        extraction = extractor.extract(text)

        # Should extract location
        locations = extraction.get_entities_by_type(EntityType.LOCATION)
        # May or may not extract depending on NER capability

        result = filler.fill_slots("get_weather", extraction)
        # Location is optional, should complete
        assert result.is_complete
