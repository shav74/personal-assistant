import numpy as np

import voice_frontend.vad as vad_module
from voice_frontend.vad import EndOfSpeechDetector

from .fakes import FakeOpenWakeWordVAD


def make_detector(monkeypatch, script, silence_hangover_ms=100, voice_threshold=0.5):
    # frame_length=512, sample_rate=16000 -> 32ms/frame; 100ms hangover -> ~3 frames
    fake = FakeOpenWakeWordVAD(script=script)
    monkeypatch.setattr(vad_module, "VAD", lambda: fake)
    detector = EndOfSpeechDetector(
        silence_hangover_ms=silence_hangover_ms, voice_threshold=voice_threshold
    )
    return detector, fake


def test_never_fires_on_silence_only(monkeypatch):
    detector, _fake = make_detector(monkeypatch, script=[0.0] * 20)
    frame = np.zeros(512, dtype=np.int16)
    results = [detector.update(frame) for _ in range(20)]
    assert not any(results)
    assert detector.heard_speech is False


def test_fires_after_speech_then_enough_silent_frames(monkeypatch):
    # 100ms hangover at 512-sample/16kHz frames rounds to 3 frames.
    detector, _fake = make_detector(monkeypatch, script=[0.9, 0.9, 0.0, 0.0, 0.0])
    frame = np.zeros(512, dtype=np.int16)

    assert detector.update(frame) is False  # speech frame 1
    assert detector.update(frame) is False  # speech frame 2
    assert detector.update(frame) is False  # silent frame 1
    assert detector.update(frame) is False  # silent frame 2
    assert detector.update(frame) is True  # silent frame 3 -> hangover reached


def test_silence_run_resets_on_renewed_speech(monkeypatch):
    detector, _fake = make_detector(monkeypatch, script=[0.9, 0.0, 0.0, 0.9, 0.0, 0.0, 0.0])
    frame = np.zeros(512, dtype=np.int16)

    for _ in range(6):
        assert detector.update(frame) is False
    assert detector.update(frame) is True  # only now has a full 3-frame silent run


def test_reset_clears_state_and_calls_reset_states(monkeypatch):
    detector, fake = make_detector(monkeypatch, script=[0.9])
    frame = np.zeros(512, dtype=np.int16)
    detector.update(frame)
    assert detector.heard_speech is True

    detector.reset()
    assert detector.heard_speech is False
    assert fake.reset_calls == 1
