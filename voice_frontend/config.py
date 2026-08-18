"""Configuration for the voice frontend, loaded from environment / .env file.

Deliberately independent of assistant/config.py — this runs as a separate
Windows-native process talking to the backend only over the network, never
importing assistant/ directly.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _split_csv(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())


@dataclass(frozen=True)
class Settings:
    backend_ws_url: str = os.getenv("BACKEND_WS_URL", "ws://localhost:8000/ws/chat")
    picovoice_access_key: str = os.getenv("PICOVOICE_ACCESS_KEY", "")
    wake_keyword_paths: tuple[str, ...] = _split_csv(os.getenv("WAKE_KEYWORD_PATHS", ""))
    wake_keyword_labels: tuple[str, ...] = _split_csv(
        os.getenv("WAKE_KEYWORD_LABELS", "neeve,hey neeve")
    )
    whisper_model_size: str = os.getenv("WHISPER_MODEL_SIZE", "base.en")
    whisper_device: str = os.getenv("WHISPER_DEVICE", "cpu")
    whisper_compute_type: str = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
    piper_exe_path: str = os.getenv("PIPER_EXE_PATH", "")
    piper_voice_model_path: str = os.getenv("PIPER_VOICE_MODEL_PATH", "")
    silence_hangover_ms: int = int(os.getenv("SILENCE_HANGOVER_MS", "800"))
    vad_voice_threshold: float = float(os.getenv("VAD_VOICE_THRESHOLD", "0.5"))
    max_utterance_seconds: float = float(os.getenv("MAX_UTTERANCE_SECONDS", "15"))
    no_speech_timeout_seconds: float = float(os.getenv("NO_SPEECH_TIMEOUT_SECONDS", "4"))
    input_device: str | None = os.getenv("INPUT_DEVICE") or None
    output_device: str | None = os.getenv("OUTPUT_DEVICE") or None


settings = Settings()
