"""Piper TTS wrapper — shells out to the official prebuilt binary rather
than a Python ONNX binding, to sidestep Windows wheel/DLL issues those
packages have had. Uses --output-raw (raw PCM to stdout) to skip WAV
parsing, and reads the voice's actual sample rate from its .onnx.json
sidecar rather than hardcoding it."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
import sounddevice as sd


class PiperSpeaker:
    def __init__(self, piper_exe: Path, voice_model: Path):
        self._exe = piper_exe
        self._model = voice_model
        sidecar = Path(f"{voice_model}.json")
        self._sample_rate = json.loads(sidecar.read_text())["audio"]["sample_rate"]

    def synthesize(self, text: str) -> np.ndarray:
        result = subprocess.run(
            [str(self._exe), "--model", str(self._model), "--output-raw"],
            input=text.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        return np.frombuffer(result.stdout, dtype=np.int16)

    def speak(self, text: str, device: str | None = None) -> None:
        pcm = self.synthesize(text)
        sd.play(pcm, samplerate=self._sample_rate, device=device)
        sd.wait()
