"""Reassemble a stream of arbitrarily-sized raw PCM chunks into the
fixed-length int16 frames wake-word/VAD engines require.

Neither the mic callback's chunk size nor the wake-word/VAD engines' frame
lengths are guaranteed to line up, so consumers can't just assume one
callback == one frame — this bridges that gap.
"""

from __future__ import annotations

import numpy as np


class FrameAccumulator:
    def __init__(self, frame_length: int):
        self._frame_length = frame_length
        self._frame_bytes = frame_length * 2  # int16 = 2 bytes/sample
        self._buffer = bytearray()

    def push(self, chunk: bytes) -> list[np.ndarray]:
        """Append raw int16 bytes; return as many complete frames as are
        now available, leaving any partial remainder buffered."""
        self._buffer.extend(chunk)
        frames = []
        while len(self._buffer) >= self._frame_bytes:
            frame_bytes = bytes(self._buffer[: self._frame_bytes])
            del self._buffer[: self._frame_bytes]
            frames.append(np.frombuffer(frame_bytes, dtype=np.int16))
        return frames

    def reset(self) -> None:
        self._buffer.clear()
