"""faster-whisper wrapper — CPU-friendly (int8 by default), matching the
project's no-discrete-GPU constraint."""

from __future__ import annotations

import numpy as np
from faster_whisper import WhisperModel


class Transcriber:
    def __init__(self, model_size: str, device: str = "cpu", compute_type: str = "int8"):
        self._model = WhisperModel(model_size, device=device, compute_type=compute_type)

    def transcribe(self, pcm_int16: np.ndarray) -> str:
        audio = pcm_int16.astype(np.float32) / 32768.0
        segments, _info = self._model.transcribe(audio, language="en", beam_size=1)
        return " ".join(segment.text.strip() for segment in segments).strip()
