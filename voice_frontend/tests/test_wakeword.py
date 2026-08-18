import numpy as np

import voice_frontend.wakeword as wakeword_module
from voice_frontend.wakeword import WakeWordDetector

from .fakes import FakeOpenWakeWordModel


def make_detector(monkeypatch, script, threshold=0.5):
    fake = FakeOpenWakeWordModel(script=script)
    monkeypatch.setattr(wakeword_module, "Model", lambda **kwargs: fake)
    detector = WakeWordDetector(
        model_paths=["neeve.onnx", "hey_neeve.onnx"], threshold=threshold
    )
    return detector, fake


def test_process_returns_label_when_score_crosses_threshold(monkeypatch):
    detector, _fake = make_detector(
        monkeypatch,
        script=[
            {"neeve": 0.1, "hey_neeve": 0.05},
            {"neeve": 0.9, "hey_neeve": 0.05},
            {"neeve": 0.1, "hey_neeve": 0.8},
        ],
    )
    frame = np.zeros(1280, dtype=np.int16)

    assert detector.process(frame) is None
    assert detector.process(frame) == "neeve"
    assert detector.process(frame) == "hey_neeve"


def test_process_returns_none_when_no_score_meets_threshold(monkeypatch):
    detector, _fake = make_detector(monkeypatch, script=[{"neeve": 0.4}])
    frame = np.zeros(1280, dtype=np.int16)
    assert detector.process(frame) is None


def test_custom_threshold_applied(monkeypatch):
    detector, _fake = make_detector(monkeypatch, script=[{"neeve": 0.6}], threshold=0.7)
    frame = np.zeros(1280, dtype=np.int16)
    assert detector.process(frame) is None  # 0.6 < 0.7 threshold


def test_frame_length_and_sample_rate_properties(monkeypatch):
    detector, _fake = make_detector(monkeypatch, script=[])
    assert detector.frame_length == 1280
    assert detector.sample_rate == 16000


def test_model_constructed_with_given_paths(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        wakeword_module,
        "Model",
        lambda **kwargs: captured.update(kwargs) or FakeOpenWakeWordModel(**kwargs),
    )
    WakeWordDetector(model_paths=["a.onnx", "b.onnx"])
    assert captured["wakeword_model_paths"] == ["a.onnx", "b.onnx"]
