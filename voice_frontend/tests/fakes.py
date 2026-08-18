"""Shared fakes for testing without real hardware or the openWakeWord/Piper/
Whisper SDKs actually doing anything."""

from __future__ import annotations


class FakeOpenWakeWordModel:
    """Stands in for openwakeword.Model — .predict() returns a scripted
    {label: score} dict per call, same shape the real Model returns."""

    def __init__(self, wakeword_model_paths=None, script=None):
        self.wakeword_model_paths = wakeword_model_paths or []
        self._script = list(script or [])

    def predict(self, frame):
        return self._script.pop(0) if self._script else {}


class FakeOpenWakeWordVAD:
    """Stands in for openwakeword.VAD — .predict() returns a scripted
    probability per call."""

    def __init__(self, script=None):
        self._script = list(script or [])
        self.reset_calls = 0

    def predict(self, frame, frame_size=None):
        return self._script.pop(0) if self._script else 0.0

    def reset_states(self):
        self.reset_calls += 1


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
