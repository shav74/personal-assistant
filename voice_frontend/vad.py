"""End-of-speech detection via openWakeWord's bundled Silero VAD wrapper.

Not the official `silero-vad` pip package — that one unconditionally
imports torchaudio (and therefore wants a CUDA runtime) even for CPU-only
use, which is both fragile and wrong for a project with no discrete GPU.
openWakeWord already ships a working, CPU-only ONNX Silero VAD internally
(openwakeword.VAD) as a dependency we need anyway, so this reuses that
directly instead of adding a second, heavier VAD dependency.

Detects end-of-utterance as N consecutive below-threshold frames *after*
speech has actually been heard, so silence before the user starts talking
doesn't count as "done".
"""

from __future__ import annotations

import numpy as np
from openwakeword import VAD

SAMPLE_RATE = 16000
FRAME_LENGTH = 512  # Silero VAD's native chunk size @ 16kHz


class EndOfSpeechDetector:
    def __init__(self, silence_hangover_ms: int, voice_threshold: float):
        self._vad = VAD()
        self._threshold = voice_threshold
        self._hangover_frames = max(
            1, round(silence_hangover_ms / 1000 * SAMPLE_RATE / FRAME_LENGTH)
        )
        self._silent_run = 0
        self._heard_speech = False

    @property
    def frame_length(self) -> int:
        return FRAME_LENGTH

    @property
    def heard_speech(self) -> bool:
        return self._heard_speech

    def reset(self) -> None:
        self._silent_run = 0
        self._heard_speech = False
        self._vad.reset_states()

    def update(self, frame: np.ndarray) -> bool:
        """Feed one frame; returns True once end-of-utterance is detected."""
        probability = self._vad.predict(frame, frame_size=FRAME_LENGTH)
        if probability >= self._threshold:
            self._heard_speech = True
            self._silent_run = 0
        else:
            self._silent_run += 1
        return self._heard_speech and self._silent_run >= self._hangover_frames

    def close(self) -> None:
        pass  # no explicit teardown needed
