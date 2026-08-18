"""Shared fakes for testing without real hardware or the Picovoice/Piper/
Whisper SDKs actually doing anything."""

from __future__ import annotations


class FakePorcupine:
    def __init__(self, frame_length=512, sample_rate=16000, script=None):
        self.frame_length = frame_length
        self.sample_rate = sample_rate
        self._script = list(script or [])
        self.deleted = False

    def process(self, frame):
        return self._script.pop(0) if self._script else -1

    def delete(self):
        self.deleted = True


class FakeCobra:
    def __init__(self, frame_length=512, sample_rate=16000, script=None):
        self.frame_length = frame_length
        self.sample_rate = sample_rate
        self._script = list(script or [])
        self.deleted = False

    def process(self, frame):
        return self._script.pop(0) if self._script else 0.0

    def delete(self):
        self.deleted = True


class FakeWS:
    """script: values recv() returns in order (already-JSON-encoded strings)."""

    def __init__(self, script):
        self._script = list(script)
        self.sent = []
        self.closed = False

    def send(self, message):
        self.sent.append(message)

    def recv(self):
        return self._script.pop(0)

    def close(self):
        self.closed = True


class FakeSegment:
    def __init__(self, text):
        self.text = text


class FakeWhisperModel:
    def __init__(self, *args, segments=(), **kwargs):
        self._segments = [FakeSegment(t) for t in segments]

    def transcribe(self, audio, language=None, beam_size=None):
        return self._segments, object()
