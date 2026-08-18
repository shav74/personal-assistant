"""openWakeWord wrapper — multi-keyword ("neeve" + "hey neeve") in one
detector. Fully local, free, no account/API key (unlike Porcupine, which
this replaced after Picovoice moved its free tier to commercial-only).

The label returned by process() comes from the model's own name (derived
from its filename), which is why the wake-word .onnx files should be named
after what they detect (e.g. neeve.onnx, hey_neeve.onnx).
"""

from __future__ import annotations

import numpy as np
from openwakeword import Model

SAMPLE_RATE = 16000
FRAME_LENGTH = 1280  # 80ms @ 16kHz -- openWakeWord's recommended chunk size


class WakeWordDetector:
    def __init__(self, model_paths: list[str], threshold: float = 0.5):
        self._model = Model(wakeword_model_paths=model_paths)
        self._threshold = threshold

    @property
    def frame_length(self) -> int:
        return FRAME_LENGTH

    @property
    def sample_rate(self) -> int:
        return SAMPLE_RATE

    def process(self, frame: np.ndarray) -> str | None:
        predictions = self._model.predict(frame)
        for label, score in predictions.items():
            if score >= self._threshold:
                return label
        return None

    def close(self) -> None:
        pass  # no explicit teardown needed
