import numpy as np

import voice_frontend.stt as stt_module
from voice_frontend.stt import Transcriber

from .fakes import FakeWhisperModel


def make_transcriber(monkeypatch, segments):
    monkeypatch.setattr(
        stt_module, "WhisperModel", lambda *a, **k: FakeWhisperModel(segments=segments)
    )
    return Transcriber(model_size="base.en")


def test_transcribe_joins_segments(monkeypatch):
    transcriber = make_transcriber(monkeypatch, segments=["what's ", " the weather", " today"])
    pcm = np.zeros(1600, dtype=np.int16)
    assert transcriber.transcribe(pcm) == "what's the weather today"


def test_transcribe_strips_segment_whitespace(monkeypatch):
    transcriber = make_transcriber(monkeypatch, segments=["  hello  ", "world  "])
    pcm = np.zeros(1600, dtype=np.int16)
    assert transcriber.transcribe(pcm) == "hello world"


def test_transcribe_empty_segments_returns_empty_string(monkeypatch):
    transcriber = make_transcriber(monkeypatch, segments=[])
    pcm = np.zeros(1600, dtype=np.int16)
    assert transcriber.transcribe(pcm) == ""


def test_transcribe_normalizes_int16_to_float32_range(monkeypatch):
    captured = {}

    class CapturingFakeModel(FakeWhisperModel):
        def transcribe(self, audio, language=None, beam_size=None):
            captured["audio"] = audio
            return super().transcribe(audio, language, beam_size)

    monkeypatch.setattr(stt_module, "WhisperModel", lambda *a, **k: CapturingFakeModel(segments=[]))
    transcriber = Transcriber(model_size="base.en")

    pcm = np.array([32767, -32768, 0], dtype=np.int16)
    transcriber.transcribe(pcm)

    assert captured["audio"].dtype == np.float32
    assert captured["audio"].max() <= 1.0
    assert captured["audio"].min() >= -1.0
