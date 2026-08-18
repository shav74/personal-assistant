"""Porcupine wake-word wrapper — multi-keyword ("neeve" + "hey neeve") in
one detector, mapping Porcupine's numeric keyword index back to a label."""

from __future__ import annotations

import numpy as np
import pvporcupine


class WakeWordDetector:
    def __init__(self, access_key: str, keyword_paths: list[str], labels: list[str]):
        if len(keyword_paths) != len(labels):
            raise ValueError("keyword_paths and labels must be the same length")
        self._porcupine = pvporcupine.create(
            access_key=access_key, keyword_paths=keyword_paths
        )
        self._labels = labels

    @property
    def frame_length(self) -> int:
        return self._porcupine.frame_length

    @property
    def sample_rate(self) -> int:
        return self._porcupine.sample_rate

    def process(self, frame: np.ndarray) -> str | None:
        index = self._porcupine.process(frame)
        return self._labels[index] if index >= 0 else None

    def close(self) -> None:
        self._porcupine.delete()
