"""
Audio Preprocessor Module
Provides noise reduction, acoustic echo cancellation, and audio normalization
for improved STT accuracy in noisy environments.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, Tuple
import time

import numpy as np

# Optional imports for noise reduction
try:
    import noisereduce as nr
    NOISEREDUCE_AVAILABLE = True
except ImportError:
    NOISEREDUCE_AVAILABLE = False

# Optional imports for voice activity detection
try:
    import webrtcvad
    WEBRTCVAD_AVAILABLE = True
except ImportError:
    WEBRTCVAD_AVAILABLE = False

from scipy import signal
from scipy.ndimage import uniform_filter1d


class NoiseReductionMethod(str, Enum):
    """Noise reduction methods available"""
    SPECTRAL_GATING = "spectral_gating"
    WIENER = "wiener"
    SIMPLE_GATE = "simple_gate"


@dataclass
class AudioPreprocessorConfig:
    """Configuration for audio preprocessing"""
    # Noise reduction settings
    noise_reduction_enabled: bool = True
    noise_reduction_method: NoiseReductionMethod = NoiseReductionMethod.SPECTRAL_GATING
    noise_threshold_db: float = -40.0

    # Acoustic echo cancellation
    aec_enabled: bool = False
    aec_filter_length: int = 1024

    # Normalization
    normalization_enabled: bool = True
    target_level_db: float = -3.0

    # Voice activity detection
    vad_enabled: bool = True
    vad_aggressiveness: int = 2  # 0-3, higher is more aggressive

    # Audio parameters (should match main config)
    sample_rate: int = 16000
    channels: int = 1


@dataclass
class ProcessedAudio:
    """Result of audio preprocessing"""
    audio_bytes: bytes
    original_bytes: bytes
    sample_rate: int

    # Processing metadata
    processing_time_ms: float = 0.0
    noise_reduced: bool = False
    normalized: bool = False
    aec_applied: bool = False
    vad_applied: bool = False

    # Quality metrics
    original_rms_db: float = 0.0
    processed_rms_db: float = 0.0
    estimated_snr_improvement_db: float = 0.0
    voice_activity_ratio: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging"""
        return {
            "processing_time_ms": self.processing_time_ms,
            "noise_reduced": self.noise_reduced,
            "normalized": self.normalized,
            "aec_applied": self.aec_applied,
            "vad_applied": self.vad_applied,
            "original_rms_db": round(self.original_rms_db, 2),
            "processed_rms_db": round(self.processed_rms_db, 2),
            "snr_improvement_db": round(self.estimated_snr_improvement_db, 2),
            "voice_activity_ratio": round(self.voice_activity_ratio, 3)
        }


class NoiseGate:
    """
    Simple noise gate using spectral gating via noisereduce library
    or fallback to simple amplitude-based gating.
    """

    def __init__(self, threshold_db: float = -40.0, sample_rate: int = 16000):
        self.threshold_db = threshold_db
        self.sample_rate = sample_rate
        self.threshold_linear = 10 ** (threshold_db / 20)

    def apply(self, audio_array: np.ndarray) -> Tuple[np.ndarray, float]:
        """
        Apply noise reduction to audio.
        Returns (processed_audio, estimated_snr_improvement_db)
        """
        if len(audio_array) == 0:
            return audio_array, 0.0

        # Normalize to float32 [-1, 1]
        if audio_array.dtype == np.int16:
            audio_float = audio_array.astype(np.float32) / 32768.0
        else:
            audio_float = audio_array.astype(np.float32)

        original_rms = np.sqrt(np.mean(audio_float ** 2))

        if NOISEREDUCE_AVAILABLE:
            # Use spectral gating from noisereduce
            try:
                reduced = nr.reduce_noise(
                    y=audio_float,
                    sr=self.sample_rate,
                    stationary=True,
                    prop_decrease=0.8,
                    n_fft=512,
                    win_length=256,
                    hop_length=128
                )
            except Exception:
                # Fallback to simple gate
                reduced = self._simple_gate(audio_float)
        else:
            # Simple amplitude-based noise gate
            reduced = self._simple_gate(audio_float)

        processed_rms = np.sqrt(np.mean(reduced ** 2))

        # Estimate SNR improvement (rough heuristic)
        noise_rms_original = self._estimate_noise_floor(audio_float)
        noise_rms_processed = self._estimate_noise_floor(reduced)

        if noise_rms_original > 0 and noise_rms_processed > 0:
            snr_improvement = 20 * np.log10(
                (original_rms / noise_rms_original) /
                (processed_rms / noise_rms_processed + 1e-10)
            )
        else:
            snr_improvement = 0.0

        # Convert back to int16
        reduced_int16 = (np.clip(reduced, -1.0, 1.0) * 32767).astype(np.int16)

        return reduced_int16, snr_improvement

    def _simple_gate(self, audio_float: np.ndarray) -> np.ndarray:
        """Simple amplitude-based noise gate"""
        # Calculate envelope using smoothed absolute value
        envelope = uniform_filter1d(np.abs(audio_float), size=int(self.sample_rate * 0.01))

        # Create gate mask
        gate_mask = envelope > self.threshold_linear

        # Apply soft knee gating
        attack_samples = int(self.sample_rate * 0.005)
        release_samples = int(self.sample_rate * 0.05)

        # Smooth the gate mask
        gate_float = gate_mask.astype(np.float32)
        gate_smoothed = uniform_filter1d(gate_float, size=attack_samples)

        return audio_float * gate_smoothed

    def _estimate_noise_floor(self, audio: np.ndarray, percentile: int = 10) -> float:
        """Estimate noise floor from quiet portions of audio"""
        frame_size = int(self.sample_rate * 0.02)
        num_frames = len(audio) // frame_size

        if num_frames == 0:
            return np.sqrt(np.mean(audio ** 2))

        frame_rms = []
        for i in range(num_frames):
            frame = audio[i * frame_size:(i + 1) * frame_size]
            frame_rms.append(np.sqrt(np.mean(frame ** 2)))

        return np.percentile(frame_rms, percentile)


class WienerFilter:
    """
    Wiener filter for noise reduction.
    Estimates noise spectrum and applies frequency-domain filtering.
    """

    def __init__(self, sample_rate: int = 16000, frame_size: int = 512):
        self.sample_rate = sample_rate
        self.frame_size = frame_size
        self.hop_size = frame_size // 2
        self.noise_estimate = None

    def apply(self, audio_array: np.ndarray, noise_profile: Optional[np.ndarray] = None) -> np.ndarray:
        """Apply Wiener filter to reduce noise"""
        if len(audio_array) == 0:
            return audio_array

        # Convert to float
        if audio_array.dtype == np.int16:
            audio_float = audio_array.astype(np.float32) / 32768.0
        else:
            audio_float = audio_array.astype(np.float32)

        # Compute STFT
        f, t, stft = signal.stft(
            audio_float,
            fs=self.sample_rate,
            nperseg=self.frame_size,
            noverlap=self.hop_size
        )

        # Estimate noise if no profile provided
        if noise_profile is None:
            # Use first 0.5 seconds or last 10% as noise estimate
            noise_frames = max(1, int(t.shape[0] * 0.1))
            noise_spectrum = np.mean(np.abs(stft[:, :noise_frames]) ** 2, axis=1)
        else:
            noise_spectrum = noise_profile

        # Apply Wiener filter
        signal_spectrum = np.abs(stft) ** 2
        noise_expanded = noise_spectrum[:, np.newaxis]

        # Wiener gain
        gain = np.maximum(signal_spectrum - noise_expanded, 0) / (signal_spectrum + 1e-10)
        gain = np.maximum(gain, 0.1)  # Minimum gain to avoid musical noise

        # Apply gain
        stft_filtered = stft * gain

        # Inverse STFT
        _, audio_filtered = signal.istft(
            stft_filtered,
            fs=self.sample_rate,
            nperseg=self.frame_size,
            noverlap=self.hop_size
        )

        # Match length
        if len(audio_filtered) > len(audio_array):
            audio_filtered = audio_filtered[:len(audio_array)]
        elif len(audio_filtered) < len(audio_array):
            audio_filtered = np.pad(audio_filtered, (0, len(audio_array) - len(audio_filtered)))

        # Convert back to int16
        return (np.clip(audio_filtered, -1.0, 1.0) * 32767).astype(np.int16)


class AcousticEchoCanceller:
    """
    Basic acoustic echo cancellation using adaptive filtering.
    Removes the assistant's own voice from the input audio.
    """

    def __init__(self, filter_length: int = 1024, step_size: float = 0.01):
        self.filter_length = filter_length
        self.step_size = step_size
        self.filter_coeffs = np.zeros(filter_length, dtype=np.float32)
        self.reference_buffer = np.zeros(filter_length, dtype=np.float32)

    def apply(
        self,
        audio_array: np.ndarray,
        reference_audio: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Apply echo cancellation.

        Args:
            audio_array: Microphone input (with echo)
            reference_audio: Reference signal (what was played through speakers)

        Returns:
            Echo-cancelled audio
        """
        if reference_audio is None or len(reference_audio) == 0:
            return audio_array

        # Convert to float
        if audio_array.dtype == np.int16:
            mic_float = audio_array.astype(np.float32) / 32768.0
        else:
            mic_float = audio_array.astype(np.float32)

        if reference_audio.dtype == np.int16:
            ref_float = reference_audio.astype(np.float32) / 32768.0
        else:
            ref_float = reference_audio.astype(np.float32)

        # Ensure same length
        min_len = min(len(mic_float), len(ref_float))
        mic_float = mic_float[:min_len]
        ref_float = ref_float[:min_len]

        # Apply NLMS adaptive filter
        output = np.zeros_like(mic_float)

        for i in range(self.filter_length, len(mic_float)):
            # Get reference window
            ref_window = ref_float[i - self.filter_length:i]

            # Estimate echo
            echo_estimate = np.dot(self.filter_coeffs, ref_window[::-1])

            # Subtract echo
            error = mic_float[i] - echo_estimate
            output[i] = error

            # Update filter (NLMS)
            norm = np.dot(ref_window, ref_window) + 1e-10
            self.filter_coeffs += self.step_size * error * ref_window[::-1] / norm

        # Copy beginning samples unchanged
        output[:self.filter_length] = mic_float[:self.filter_length]

        # Convert back to int16
        return (np.clip(output, -1.0, 1.0) * 32767).astype(np.int16)

    def reset(self):
        """Reset adaptive filter state"""
        self.filter_coeffs = np.zeros(self.filter_length, dtype=np.float32)


class VoiceActivityDetector:
    """
    Voice Activity Detection using WebRTC VAD or energy-based fallback.
    """

    def __init__(self, sample_rate: int = 16000, aggressiveness: int = 2):
        self.sample_rate = sample_rate
        self.aggressiveness = aggressiveness

        # WebRTC VAD only supports 8000, 16000, 32000, 48000 Hz
        self.vad = None
        if WEBRTCVAD_AVAILABLE and sample_rate in [8000, 16000, 32000, 48000]:
            self.vad = webrtcvad.Vad(aggressiveness)

    def detect(self, audio_array: np.ndarray) -> Tuple[np.ndarray, float]:
        """
        Detect voice activity in audio.

        Returns:
            (vad_mask, voice_activity_ratio)
            vad_mask: boolean array indicating voice frames
            voice_activity_ratio: percentage of audio that is voice
        """
        if len(audio_array) == 0:
            return np.array([], dtype=bool), 0.0

        # Frame size must be 10, 20, or 30 ms for WebRTC VAD
        frame_duration_ms = 20
        frame_size = int(self.sample_rate * frame_duration_ms / 1000)

        # Ensure audio is int16
        if audio_array.dtype != np.int16:
            audio_int16 = (np.clip(audio_array, -1.0, 1.0) * 32767).astype(np.int16)
        else:
            audio_int16 = audio_array

        num_frames = len(audio_int16) // frame_size
        vad_results = []

        for i in range(num_frames):
            frame = audio_int16[i * frame_size:(i + 1) * frame_size]

            if self.vad is not None:
                try:
                    is_speech = self.vad.is_speech(frame.tobytes(), self.sample_rate)
                except Exception:
                    is_speech = self._energy_vad(frame)
            else:
                is_speech = self._energy_vad(frame)

            vad_results.append(is_speech)

        # Expand VAD results to sample-level mask
        vad_mask = np.repeat(vad_results, frame_size)

        # Pad to match original length
        if len(vad_mask) < len(audio_array):
            vad_mask = np.pad(vad_mask, (0, len(audio_array) - len(vad_mask)), constant_values=vad_results[-1] if vad_results else False)
        elif len(vad_mask) > len(audio_array):
            vad_mask = vad_mask[:len(audio_array)]

        voice_ratio = np.mean(vad_results) if vad_results else 0.0

        return vad_mask, voice_ratio

    def _energy_vad(self, frame: np.ndarray, threshold: float = 0.01) -> bool:
        """Simple energy-based VAD as fallback"""
        frame_float = frame.astype(np.float32) / 32768.0
        energy = np.sqrt(np.mean(frame_float ** 2))
        return energy > threshold


class Normalizer:
    """
    Audio level normalization to consistent target level.
    """

    def __init__(self, target_db: float = -3.0):
        self.target_db = target_db
        self.target_linear = 10 ** (target_db / 20)

    def apply(self, audio_array: np.ndarray) -> Tuple[np.ndarray, float, float]:
        """
        Normalize audio to target level.

        Returns:
            (normalized_audio, original_rms_db, processed_rms_db)
        """
        if len(audio_array) == 0:
            return audio_array, -96.0, -96.0

        # Convert to float
        if audio_array.dtype == np.int16:
            audio_float = audio_array.astype(np.float32) / 32768.0
        else:
            audio_float = audio_array.astype(np.float32)

        # Calculate RMS
        rms = np.sqrt(np.mean(audio_float ** 2))

        if rms < 1e-10:
            return audio_array, -96.0, -96.0

        original_db = 20 * np.log10(rms)

        # Calculate gain
        gain = self.target_linear / rms

        # Apply gain with limiting
        normalized = audio_float * gain
        normalized = np.clip(normalized, -0.99, 0.99)

        processed_rms = np.sqrt(np.mean(normalized ** 2))
        processed_db = 20 * np.log10(processed_rms) if processed_rms > 0 else -96.0

        # Convert back to int16
        normalized_int16 = (normalized * 32767).astype(np.int16)

        return normalized_int16, original_db, processed_db


class AudioPreprocessor:
    """
    Main audio preprocessor that chains noise reduction, AEC, VAD, and normalization.
    """

    def __init__(self, config: Optional[AudioPreprocessorConfig] = None):
        if config is None:
            config = AudioPreprocessorConfig()

        self.config = config

        # Initialize components
        self.noise_gate = NoiseGate(
            threshold_db=config.noise_threshold_db,
            sample_rate=config.sample_rate
        )
        self.wiener_filter = WienerFilter(sample_rate=config.sample_rate)
        self.aec = AcousticEchoCanceller(filter_length=config.aec_filter_length)
        self.vad = VoiceActivityDetector(
            sample_rate=config.sample_rate,
            aggressiveness=config.vad_aggressiveness
        )
        self.normalizer = Normalizer(target_db=config.target_level_db)

    def process(
        self,
        audio_bytes: bytes,
        reference_audio: Optional[bytes] = None
    ) -> ProcessedAudio:
        """
        Process raw audio bytes through the preprocessing pipeline.

        Args:
            audio_bytes: Raw 16-bit PCM audio bytes
            reference_audio: Optional reference for AEC (TTS output)

        Returns:
            ProcessedAudio with processed audio and metadata
        """
        start_time = time.time()

        # Convert bytes to numpy array
        audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
        original_array = audio_array.copy()

        processed = audio_array
        noise_reduced = False
        aec_applied = False
        vad_applied = False
        normalized = False
        snr_improvement = 0.0
        voice_ratio = 1.0
        original_db = -96.0
        processed_db = -96.0

        # 1. Apply AEC if enabled and reference provided
        if self.config.aec_enabled and reference_audio is not None:
            ref_array = np.frombuffer(reference_audio, dtype=np.int16)
            processed = self.aec.apply(processed, ref_array)
            aec_applied = True

        # 2. Apply noise reduction
        if self.config.noise_reduction_enabled:
            if self.config.noise_reduction_method == NoiseReductionMethod.SPECTRAL_GATING:
                processed, snr_improvement = self.noise_gate.apply(processed)
            elif self.config.noise_reduction_method == NoiseReductionMethod.WIENER:
                processed = self.wiener_filter.apply(processed)
                snr_improvement = 3.0  # Estimated
            else:
                processed, snr_improvement = self.noise_gate.apply(processed)
            noise_reduced = True

        # 3. Apply VAD (for metrics, not filtering)
        if self.config.vad_enabled:
            _, voice_ratio = self.vad.detect(processed)
            vad_applied = True

        # 4. Apply normalization
        if self.config.normalization_enabled:
            processed, original_db, processed_db = self.normalizer.apply(processed)
            normalized = True

        processing_time = (time.time() - start_time) * 1000

        return ProcessedAudio(
            audio_bytes=processed.tobytes(),
            original_bytes=audio_bytes,
            sample_rate=self.config.sample_rate,
            processing_time_ms=processing_time,
            noise_reduced=noise_reduced,
            normalized=normalized,
            aec_applied=aec_applied,
            vad_applied=vad_applied,
            original_rms_db=original_db,
            processed_rms_db=processed_db,
            estimated_snr_improvement_db=snr_improvement,
            voice_activity_ratio=voice_ratio
        )

    def reset_aec(self):
        """Reset AEC adaptive filter state"""
        self.aec.reset()


def create_audio_preprocessor(
    noise_reduction: bool = True,
    aec: bool = False,
    normalization: bool = True,
    sample_rate: int = 16000
) -> AudioPreprocessor:
    """Factory function to create AudioPreprocessor with common settings"""
    config = AudioPreprocessorConfig(
        noise_reduction_enabled=noise_reduction,
        aec_enabled=aec,
        normalization_enabled=normalization,
        sample_rate=sample_rate
    )
    return AudioPreprocessor(config)
