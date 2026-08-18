"""Continuous microphone capture, decoupled from any single consumer's
frame size via a background callback feeding a queue."""

from __future__ import annotations

import contextlib
import queue
from typing import Iterator

import sounddevice as sd


class MicCapture:
    def __init__(self, sample_rate: int, blocksize: int, device: str | None = None):
        self._sample_rate = sample_rate
        self._blocksize = blocksize
        self._device = device
        self._queue: queue.Queue[bytes] = queue.Queue()
        self._stream: sd.RawInputStream | None = None

    def _callback(self, indata, frames, time_info, status) -> None:  # noqa: ANN001
        self._queue.put(bytes(indata))

    def start(self) -> None:
        self._stream = sd.RawInputStream(
            samplerate=self._sample_rate,
            blocksize=self._blocksize,
            device=self._device,
            channels=1,
            dtype="int16",
            callback=self._callback,
        )
        self._stream.start()

    def stop(self) -> None:
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def next_chunk(self, timeout: float | None = None) -> bytes | None:
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def _drain(self) -> None:
        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

    @contextlib.contextmanager
    def paused(self) -> Iterator[None]:
        """Stop capturing around playback — no echo cancellation in v1, so
        this is the mitigation against the mic picking up our own output."""
        was_running = self._stream is not None
        if was_running:
            self.stop()
            self._drain()
        try:
            yield
        finally:
            if was_running:
                self._drain()
                self.start()
