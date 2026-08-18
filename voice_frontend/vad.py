"""Cobra VAD wrapper — detects end-of-utterance as N consecutive
below-threshold frames *after* speech has actually been heard, so silence
before the user starts talking doesn't count as "done"."""

from __future__ import annotations

import numpy as np
import pvcobra


class EndOfSpeechDetector:
    def __init__(self, access_key: str, silence_hangover_ms: int, voice_threshold: float):
        self._cobra = pvcobra.create(access_key=access_key)
        self._threshold = voice_threshold
        self._hangover_frames = max(
            1,
            round(
                silence_hangover_ms
                / 1000
                * self._cobra.sample_rate
                / self._cobra.frame_length
            ),
        )
        self._silent_run = 0
        self._heard_speech = False

    @property
    def frame_length(self) -> int:
        return self._cobra.frame_length

    @property
    def sample_rate(self) -> int:
        return self._cobra.sample_rate

    @property
    def heard_speech(self) -> bool:
        return self._heard_speech

    def reset(self) -> None:
        self._silent_run = 0
        self._heard_speech = False

    def update(self, frame: np.ndarray) -> bool:
        """Feed one frame; returns True once end-of-utterance is detected."""
        probability = self._cobra.process(frame)
        if probability >= self._threshold:
            self._heard_speech = True
            self._silent_run = 0
        else:
            self._silent_run += 1
        return self._heard_speech and self._silent_run >= self._hangover_frames

    def close(self) -> None:
        self._cobra.delete()
