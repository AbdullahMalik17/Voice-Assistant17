"""
Audio fixtures for testing.
"""
import numpy as np

def generate_sine_wave(frequency: int = 440, duration: float = 1.0, sample_rate: int = 16000, amplitude: float = 0.5) -> np.ndarray:
    """Generate a sine wave."""
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    audio = amplitude * np.sin(2 * np.pi * frequency * t)
    return (audio * 32767).astype(np.int16)

def generate_speech_like(duration: float = 1.0, sample_rate: int = 16000) -> np.ndarray:
    """Generate speech-like signal (harmonics)."""
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    # Fundamental frequency + harmonics (like a vowel)
    f0 = 150
    audio = np.sin(2 * np.pi * f0 * t)
    audio += 0.5 * np.sin(2 * np.pi * 2 * f0 * t)
    audio += 0.3 * np.sin(2 * np.pi * 3 * f0 * t)
    
    # Envelope modulation
    envelope = np.sin(2 * np.pi * 2 * t) * 0.5 + 0.5
    audio = audio * envelope
    
    # Normalize
    audio = audio / np.max(np.abs(audio)) * 0.5
    
    return (audio * 32767).astype(np.int16)

def add_noise(audio: np.ndarray, snr_db: float = 10.0) -> np.ndarray:
    """Add white noise to audio with specific SNR."""
    audio_float = audio.astype(np.float32)
    signal_power = np.mean(audio_float ** 2)
    if signal_power == 0:
        return audio
        
    noise_power = signal_power / (10 ** (snr_db / 10))
    
    noise = np.random.normal(0, np.sqrt(noise_power), len(audio))
    noisy = audio_float + noise
    return np.clip(noisy, -32768, 32767).astype(np.int16)
