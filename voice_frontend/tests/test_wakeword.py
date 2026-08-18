import numpy as np
import pytest

import voice_frontend.wakeword as wakeword_module
from voice_frontend.wakeword import WakeWordDetector

from .fakes import FakePorcupine


def make_detector(monkeypatch, script):
    fake = FakePorcupine(script=script)
    monkeypatch.setattr(wakeword_module.pvporcupine, "create", lambda **kwargs: fake)
    detector = WakeWordDetector(
        access_key="test-key",
        keyword_paths=["neeve.ppn", "hey-neeve.ppn"],
        labels=["neeve", "hey neeve"],
    )
    return detector, fake


def test_process_maps_index_to_label(monkeypatch):
    detector, _fake = make_detector(monkeypatch, script=[-1, 0, -1, 1])
    frame = np.zeros(512, dtype=np.int16)

    assert detector.process(frame) is None
    assert detector.process(frame) == "neeve"
    assert detector.process(frame) is None
    assert detector.process(frame) == "hey neeve"


def test_frame_length_and_sample_rate_passthrough(monkeypatch):
    detector, fake = make_detector(monkeypatch, script=[])
    assert detector.frame_length == fake.frame_length
    assert detector.sample_rate == fake.sample_rate


def test_close_deletes_underlying_porcupine(monkeypatch):
    detector, fake = make_detector(monkeypatch, script=[])
    detector.close()
    assert fake.deleted is True


def test_mismatched_paths_and_labels_raises():
    with pytest.raises(ValueError):
        WakeWordDetector(access_key="k", keyword_paths=["a.ppn", "b.ppn"], labels=["only-one"])
