"""
Audio Utilities for Voice Assistant
Cross-platform audio I/O using PyAudio with sounddevice fallback
"""

import platform
import struct
import wave
from io import BytesIO
from pathlib import Path
from typing import Optional, Tuple

import numpy as np

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False

try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
except ImportError:
    SOUNDDEVICE_AVAILABLE = False


class AudioConfig:
    """Audio configuration parameters"""
    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_size: int = 1024,
        sample_width: int = 2,  # 2 bytes = 16-bit
        input_device: Optional[int] = None,
        output_device: Optional[int] = None
    ):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.sample_width = sample_width
        self.input_device = input_device
        self.output_device = output_device

        # Calculate format
        if PYAUDIO_AVAILABLE:
            self.format = pyaudio.paInt16  # 16-bit
        else:
            self.format = 'int16'  # For sounddevice


class AudioBackend:
    """Abstract base for audio backends"""

    def __init__(self, config: AudioConfig):
        self.config = config

    def record(self, duration_seconds: float) -> bytes:
        """Record audio for specified duration"""
        raise NotImplementedError

    def play(self, audio_data: bytes) -> None:
        """Play audio data"""
        raise NotImplementedError

    def list_devices(self) -> list:
        """List available audio devices"""
        raise NotImplementedError

    def close(self) -> None:
        """Close audio resources"""
        raise NotImplementedError


class PyAudioBackend(AudioBackend):
    """PyAudio implementation for audio I/O"""

    def __init__(self, config: AudioConfig):
        super().__init__(config)
        if not PYAUDIO_AVAILABLE:
            raise RuntimeError("PyAudio is not available")

        self.audio = pyaudio.PyAudio()

    def record(self, duration_seconds: float) -> bytes:
        """Record audio for specified duration"""
        stream = self.audio.open(
            format=self.config.format,
            channels=self.config.channels,
            rate=self.config.sample_rate,
            input=True,
            input_device_index=self.config.input_device,
            frames_per_buffer=self.config.chunk_size
        )

        frames = []
        num_chunks = int(self.config.sample_rate / self.config.chunk_size * duration_seconds)

        for _ in range(num_chunks):
            data = stream.read(self.config.chunk_size, exception_on_overflow=False)
            frames.append(data)

        stream.stop_stream()
        stream.close()

        return b''.join(frames)

    def play(self, audio_data: bytes) -> None:
        """Play audio data"""
        stream = self.audio.open(
            format=self.config.format,
            channels=self.config.channels,
            rate=self.config.sample_rate,
            output=True,
            output_device_index=self.config.output_device
        )

        stream.write(audio_data)
        stream.stop_stream()
        stream.close()

    def list_devices(self) -> list:
        """List available audio devices"""
        devices = []
        for i in range(self.audio.get_device_count()):
            info = self.audio.get_device_info_by_index(i)
            devices.append({
                'index': i,
                'name': info['name'],
                'channels': info['maxInputChannels'],
                'sample_rate': int(info['defaultSampleRate'])
            })
        return devices

    def close(self) -> None:
        """Close PyAudio"""
        self.audio.terminate()


class SoundDeviceBackend(AudioBackend):
    """sounddevice implementation for audio I/O"""

    def __init__(self, config: AudioConfig):
        super().__init__(config)
        if not SOUNDDEVICE_AVAILABLE:
            raise RuntimeError("sounddevice is not available")

        # Set default devices
        if config.input_device is not None:
            sd.default.device[0] = config.input_device
        if config.output_device is not None:
            sd.default.device[1] = config.output_device

        sd.default.samplerate = config.sample_rate
        sd.default.channels = config.channels

    def record(self, duration_seconds: float) -> bytes:
        """Record audio for specified duration"""
        recording = sd.rec(
            int(duration_seconds * self.config.sample_rate),
            samplerate=self.config.sample_rate,
            channels=self.config.channels,
            dtype='int16'
        )
        sd.wait()  # Wait for recording to complete

        # Convert numpy array to bytes
        return recording.tobytes()

    def play(self, audio_data: bytes) -> None:
        """Play audio data"""
        # Convert bytes to numpy array
        audio_array = np.frombuffer(audio_data, dtype=np.int16)

        # Reshape for channels
        if self.config.channels > 1:
            audio_array = audio_array.reshape(-1, self.config.channels)

        sd.play(audio_array, self.config.sample_rate)
        sd.wait()  # Wait for playback to complete

    def list_devices(self) -> list:
        """List available audio devices"""
        devices = []
        for i, device in enumerate(sd.query_devices()):
            devices.append({
                'index': i,
                'name': device['name'],
                'channels': device['max_input_channels'],
                'sample_rate': int(device['default_samplerate'])
            })
        return devices

    def close(self) -> None:
        """Close sounddevice (no-op)"""
        pass


class AudioUtils:
    """
    High-level audio utilities with automatic backend selection
    """

    def __init__(self, config: Optional[AudioConfig] = None):
        if config is None:
            config = AudioConfig()

        self.config = config
        self.backend = self._select_backend()

    def _select_backend(self) -> AudioBackend:
        """Automatically select best available backend"""
        os_name = platform.system()

        # Prefer sounddevice on macOS, PyAudio elsewhere
        if os_name == "Darwin" and SOUNDDEVICE_AVAILABLE:
            return SoundDeviceBackend(self.config)
        elif PYAUDIO_AVAILABLE:
            return PyAudioBackend(self.config)
        elif SOUNDDEVICE_AVAILABLE:
            return SoundDeviceBackend(self.config)
        else:
            raise RuntimeError("No audio backend available. Install pyaudio or sounddevice.")

    def record_audio(self, duration_seconds: float) -> bytes:
        """Record audio for specified duration"""
        return self.backend.record(duration_seconds)

    def play_audio(self, audio_data: bytes) -> None:
        """Play audio data"""
        self.backend.play(audio_data)

    def save_audio(self, audio_data: bytes, file_path: Path) -> None:
        """Save audio data to WAV file"""
        with wave.open(str(file_path), 'wb') as wf:
            wf.setnchannels(self.config.channels)
            wf.setsampwidth(self.config.sample_width)
            wf.setframerate(self.config.sample_rate)
            wf.writeframes(audio_data)

    def load_audio(self, file_path: Path) -> Tuple[bytes, int]:
        """Load audio data from WAV file"""
        with wave.open(str(file_path), 'rb') as wf:
            sample_rate = wf.getframerate()
            audio_data = wf.readframes(wf.getnframes())
        return audio_data, sample_rate

    def bytes_to_array(self, audio_data: bytes) -> np.ndarray:
        """Convert audio bytes to numpy array"""
        return np.frombuffer(audio_data, dtype=np.int16)

    def array_to_bytes(self, audio_array: np.ndarray) -> bytes:
        """Convert numpy array to audio bytes"""
        return audio_array.astype(np.int16).tobytes()

    def resample(self, audio_data: bytes, original_rate: int, target_rate: int) -> bytes:
        """Resample audio to different sample rate"""
        if original_rate == target_rate:
            return audio_data

        # Convert to numpy array
        audio_array = self.bytes_to_array(audio_data)

        # Calculate resampling ratio
        ratio = target_rate / original_rate
        new_length = int(len(audio_array) * ratio)

        # Simple linear interpolation resampling
        indices = np.linspace(0, len(audio_array) - 1, new_length)
        resampled = np.interp(indices, np.arange(len(audio_array)), audio_array)

        return self.array_to_bytes(resampled)

    def normalize_volume(self, audio_data: bytes, target_level: float = 0.8) -> bytes:
        """Normalize audio volume to target level (0.0 to 1.0)"""
        audio_array = self.bytes_to_array(audio_data)

        # Calculate current peak
        current_peak = np.abs(audio_array).max()

        if current_peak == 0:
            return audio_data

        # Calculate scaling factor
        max_value = 32767  # Max value for int16
        target_peak = max_value * target_level
        scale_factor = target_peak / current_peak

        # Apply scaling
        normalized = audio_array * scale_factor
        normalized = np.clip(normalized, -32768, 32767)

        return self.array_to_bytes(normalized)

    def trim_silence(self, audio_data: bytes, threshold: float = 0.01) -> bytes:
        """Trim silence from beginning and end of audio"""
        audio_array = self.bytes_to_array(audio_data)

        # Normalize to -1.0 to 1.0
        normalized = audio_array.astype(np.float32) / 32768.0

        # Find non-silent regions
        non_silent = np.abs(normalized) > threshold
        non_silent_indices = np.where(non_silent)[0]

        if len(non_silent_indices) == 0:
            return audio_data

        # Trim
        start = non_silent_indices[0]
        end = non_silent_indices[-1] + 1
        trimmed = audio_array[start:end]

        return self.array_to_bytes(trimmed)

    def get_duration(self, audio_data: bytes) -> float:
        """Get duration of audio in seconds"""
        num_samples = len(audio_data) // self.config.sample_width
        return num_samples / self.config.sample_rate

    def list_devices(self) -> list:
        """List available audio devices"""
        return self.backend.list_devices()

    def close(self) -> None:
        """Close audio backend"""
        self.backend.close()


def get_audio_utils(config: Optional[AudioConfig] = None) -> AudioUtils:
    """Factory function to create AudioUtils instance"""
    return AudioUtils(config)
