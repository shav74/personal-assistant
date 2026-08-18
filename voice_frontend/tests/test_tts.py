import json
from types import SimpleNamespace

import numpy as np

import voice_frontend.tts as tts_module
from voice_frontend.tts import PiperSpeaker


def make_speaker(tmp_path, monkeypatch, sample_rate=22050):
    exe = tmp_path / "piper.exe"
    exe.write_text("")  # not actually executed, subprocess.run is mocked
    voice_model = tmp_path / "voice.onnx"
    voice_model.write_text("")
    sidecar = tmp_path / "voice.onnx.json"
    sidecar.write_text(json.dumps({"audio": {"sample_rate": sample_rate}}))
    return PiperSpeaker(exe, voice_model)


def test_reads_sample_rate_from_sidecar(tmp_path, monkeypatch):
    speaker = make_speaker(tmp_path, monkeypatch, sample_rate=24000)
    assert speaker._sample_rate == 24000


def test_synthesize_parses_raw_pcm_stdout(tmp_path, monkeypatch):
    speaker = make_speaker(tmp_path, monkeypatch)
    expected = np.array([1, -1, 32000, -32000], dtype=np.int16)

    captured = {}

    def fake_run(cmd, input=None, stdout=None, stderr=None, check=None):
        captured["cmd"] = cmd
        captured["input"] = input
        return SimpleNamespace(stdout=expected.tobytes())

    monkeypatch.setattr(tts_module.subprocess, "run", fake_run)
    pcm = speaker.synthesize("hello there")

    assert list(pcm) == list(expected)
    assert captured["input"] == b"hello there"
    assert "--output-raw" in captured["cmd"]


def test_speak_plays_at_the_sidecar_sample_rate(tmp_path, monkeypatch):
    speaker = make_speaker(tmp_path, monkeypatch, sample_rate=24000)
    monkeypatch.setattr(
        tts_module.subprocess, "run",
        lambda *a, **k: SimpleNamespace(stdout=np.array([0], dtype=np.int16).tobytes()),
    )
    play_calls = []
    monkeypatch.setattr(
        tts_module.sd, "play",
        lambda pcm, samplerate=None, device=None: play_calls.append((samplerate, device)),
    )
    monkeypatch.setattr(tts_module.sd, "wait", lambda: None)

    speaker.speak("hi", device="my-speaker")

    assert play_calls == [(24000, "my-speaker")]
