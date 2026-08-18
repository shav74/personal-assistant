"""Voice frontend entry point.

Continuous mic capture -> openWakeWord wake word ("neeve" / "hey neeve") ->
beep acknowledgment -> Silero-VAD-bounded recording -> faster-whisper
transcription -> send to the backend over WebSocket -> speak the reply via
Piper. Permission confirmations are keyboard y/N in v1 (see confirm.py).

Run the backend first (in WSL2):  python -m assistant.interfaces.server
Then, in a Windows venv:           python -m voice_frontend.main
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import numpy as np
from websockets.exceptions import ConnectionClosed

from .audio.capture import MicCapture
from .audio.framing import FrameAccumulator
from .audio.tones import generate_beep, play_blocking
from .backend_client import BackendClient, BackendError
from .config import settings
from .confirm import keyboard_confirm
from .stt import Transcriber
from .tts import PiperSpeaker
from .vad import EndOfSpeechDetector
from .wakeword import WakeWordDetector

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def record_utterance(
    mic: MicCapture, vad_acc: FrameAccumulator, vad: EndOfSpeechDetector
) -> np.ndarray | None:
    """VAD-driven recording: stops on end-of-speech, a no-speech timeout,
    or a hard max-duration cap, whichever comes first."""
    vad.reset()
    vad_acc.reset()
    frames: list[np.ndarray] = []
    start = time.monotonic()

    while True:
        elapsed = time.monotonic() - start
        if elapsed > settings.max_utterance_seconds:
            break
        if not vad.heard_speech and elapsed > settings.no_speech_timeout_seconds:
            break

        chunk = mic.next_chunk(timeout=0.5)
        if chunk is None:
            continue

        for frame in vad_acc.push(chunk):
            frames.append(frame)
            if vad.update(frame):
                return np.concatenate(frames)

    return np.concatenate(frames) if vad.heard_speech and frames else None


def handle_wake(
    label: str,
    mic: MicCapture,
    vad_acc: FrameAccumulator,
    vad: EndOfSpeechDetector,
    transcriber: Transcriber,
    backend: BackendClient,
    speaker: PiperSpeaker,
) -> None:
    log.info("wake word detected: %s", label)
    with mic.paused():
        play_blocking(generate_beep(), sample_rate=16000, device=settings.output_device)

    pcm = record_utterance(mic, vad_acc, vad)
    if pcm is None:
        with mic.paused():
            speaker.speak("Sorry, I didn't catch that.", device=settings.output_device)
        return

    text = transcriber.transcribe(pcm)
    if not text:
        with mic.paused():
            speaker.speak("Sorry, I didn't catch that.", device=settings.output_device)
        return
    print(f"you> {text}")

    try:
        reply = backend.send_command(text, on_confirm=keyboard_confirm)
    except (BackendError, ConnectionClosed) as exc:
        log.error("backend error: %s", exc)
        with mic.paused():
            speaker.speak("Sorry, something went wrong.", device=settings.output_device)
        return

    print(f"assistant> {reply}")
    with mic.paused():
        speaker.speak(reply, device=settings.output_device)


def run() -> None:
    if not settings.wake_model_paths:
        print("Set WAKE_MODEL_PATHS in your .env file first.")
        return

    wake = WakeWordDetector(list(settings.wake_model_paths), settings.wake_threshold)
    vad = EndOfSpeechDetector(settings.silence_hangover_ms, settings.vad_voice_threshold)
    transcriber = Transcriber(
        settings.whisper_model_size, settings.whisper_device, settings.whisper_compute_type
    )
    speaker = PiperSpeaker(Path(settings.piper_exe_path), Path(settings.piper_voice_model_path))
    backend = BackendClient(settings.backend_ws_url)

    print(f"Connecting to backend at {settings.backend_ws_url} ...")
    backend.connect()
    print(f"Listening for: {', '.join(settings.wake_model_paths)}. Ctrl+C to exit.")

    mic = MicCapture(
        sample_rate=wake.sample_rate, blocksize=wake.frame_length, device=settings.input_device
    )
    mic.start()
    wake_acc = FrameAccumulator(wake.frame_length)
    vad_acc = FrameAccumulator(vad.frame_length)

    try:
        while True:
            chunk = mic.next_chunk(timeout=1.0)
            if chunk is None:
                continue
            for frame in wake_acc.push(chunk):
                label = wake.process(frame)
                if label is not None:
                    handle_wake(label, mic, vad_acc, vad, transcriber, backend, speaker)
                    wake_acc.reset()
                    break
    except KeyboardInterrupt:
        print()
    finally:
        mic.stop()
        wake.close()
        vad.close()
        backend.close()


if __name__ == "__main__":
    run()
