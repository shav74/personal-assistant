"""A generated wake-acknowledgment beep — no audio asset file, no Piper
round-trip on every wake."""

from __future__ import annotations

import numpy as np
import sounddevice as sd


def generate_beep(
    frequency: float = 880.0, duration_s: float = 0.15, sample_rate: int = 16000
) -> np.ndarray:
    t = np.linspace(0, duration_s, int(sample_rate * duration_s), endpoint=False)
    # Short fade-in/out to avoid an audible click at the edges.
    envelope = np.ones_like(t)
    fade_samples = max(1, int(sample_rate * 0.01))
    envelope[:fade_samples] = np.linspace(0, 1, fade_samples)
    envelope[-fade_samples:] = np.linspace(1, 0, fade_samples)
    wave = np.sin(2 * np.pi * frequency * t) * envelope
    return (wave * 0.3 * np.iinfo(np.int16).max).astype(np.int16)


def play_blocking(pcm: np.ndarray, sample_rate: int, device: str | None = None) -> None:
    sd.play(pcm, samplerate=sample_rate, device=device)
    sd.wait()
