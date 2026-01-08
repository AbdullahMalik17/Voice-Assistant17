"""
Pytest configuration and shared fixtures for tests.
"""

import pytest
import numpy as np
import tempfile
from pathlib import Path
from typing import Generator

from src.core.config import Config, get_config
from src.utils.logger import EventLogger, MetricsLogger


@pytest.fixture
def test_config() -> Config:
    """Get test configuration."""
    config = get_config()
    # Override with test-specific settings
    config.logging.level = "DEBUG"
    config.logging.console_output = False
    return config


@pytest.fixture
def event_logger(tmp_path) -> EventLogger:
    """Create event logger for testing."""
    from src.utils.logger import EventLogger
    return EventLogger(
        name="test",
        log_dir=str(tmp_path),
        level="DEBUG",
        format_type="json",
        console_output=False
    )


@pytest.fixture
def metrics_logger(tmp_path) -> MetricsLogger:
    """Create metrics logger for testing."""
    from src.utils.logger import MetricsLogger
    return MetricsLogger(
        log_dir=str(tmp_path),
        export_interval_seconds=60
    )


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_audio_data() -> np.ndarray:
    """Generate sample audio data for testing."""
    # Generate 1 second of 440Hz sine wave at 16kHz
    sample_rate = 16000
    duration = 1.0
    frequency = 440.0

    t = np.linspace(0, duration, int(sample_rate * duration))
    audio = np.sin(2 * np.pi * frequency * t)

    # Convert to int16
    audio = (audio * 32767).astype(np.int16)
    return audio


@pytest.fixture
def sample_audio_bytes(sample_audio_data) -> bytes:
    """Convert sample audio to bytes."""
    return sample_audio_data.tobytes()


@pytest.fixture
def silent_audio_data() -> np.ndarray:
    """Generate silent audio for testing."""
    sample_rate = 16000
    duration = 1.0
    return np.zeros(int(sample_rate * duration), dtype=np.int16)


@pytest.fixture
def noisy_audio_data() -> np.ndarray:
    """Generate noisy audio data for testing."""
    sample_rate = 16000
    duration = 1.0

    # Generate signal
    t = np.linspace(0, duration, int(sample_rate * duration))
    signal = np.sin(2 * np.pi * 440 * t)

    # Add white noise
    noise = np.random.normal(0, 0.1, len(signal))
    noisy = signal + noise

    # Convert to int16
    noisy = (noisy * 32767 * 0.5).astype(np.int16)
    return noisy
