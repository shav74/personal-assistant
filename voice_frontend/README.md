# Voice frontend

Wake word ("neeve" / "hey neeve") → record your command → transcribe locally
via Whisper → send to the backend over WebSocket → speak the reply back via
Piper. A separate, Windows-native sub-project — it only talks to the backend
over the network, no shared code or venv with `assistant/`.

Permission confirmations are keyboard `y/N` in this version — everything
else is voice. Full voice confirmations are a deliberately deferred
follow-up.

## 1. Prerequisites

- Windows 10/11
- Python 3.11+ from [python.org](https://python.org) (not the Microsoft
  Store version — it has historically had issues with native-extension
  packages like this project depends on)
- The backend already set up and runnable (see the main repo's README)

## 2. Picovoice setup (wake word + VAD)

1. Create a free account at [console.picovoice.ai](https://console.picovoice.ai).
2. Copy your **AccessKey** into `.env` as `PICOVOICE_ACCESS_KEY`.
3. Under **Wake Word**, train two custom models — type the text exactly:
   - `Neeve`
   - `hey Neeve`

   **Not "Niamh"** — that's the assistant's name, but it's Gaelic spelling
   (pronounced "neeve") that an English text→phoneme model would mispronounce.
   Training on the phonetic spelling "Neeve" gets you a model that correctly
   fires on how it's actually said; the assistant still introduces itself as
   "Niamh" everywhere else.
4. Target platform: **Windows**. Training takes seconds, no audio recording
   required.
5. Download both `.ppn` files into `voice_frontend/models/`.

No separate step is needed for Cobra (the end-of-speech detector) — it's a
general-purpose model included with the same AccessKey, no Console training.

## 3. Piper TTS setup

1. Download the prebuilt Windows release from the
   [Piper releases page](https://github.com/rhasspy/piper/releases) and
   extract it somewhere, e.g. `C:\tools\piper`.
2. Download a voice — e.g. `en_US-lessac-medium` — from the
   [Piper voices repo](https://github.com/rhasspy/piper/blob/master/VOICES.md).
   You need both the `.onnx` file and its `.onnx.json` sidecar.
3. Set `PIPER_EXE_PATH` and `PIPER_VOICE_MODEL_PATH` in `.env` to point at these.

## 4. Python environment

```powershell
py -3.11 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 5. Configure `.env`

```powershell
copy .env.example .env
```

Fill in `PICOVOICE_ACCESS_KEY`, the wake-word `.ppn` paths, and the Piper
paths from steps 2–3. `BACKEND_WS_URL` normally doesn't need changing —
`ws://localhost:8000/ws/chat` reaches the WSL2-hosted backend directly via
WSL2's mirrored networking.

`faster-whisper` downloads its model automatically on first use (~140 MB for
the default `base.en`) — needs internet once.

## 6. Run it

In WSL2, start the backend first:
```bash
python -m assistant.interfaces.server
```

Then, in your Windows venv:
```powershell
python -m voice_frontend.main
```

Say "neeve" or "hey neeve", wait for the chime, then speak your command.

## Troubleshooting

- **No `.ppn` file found / AccessKey errors**: double-check the platform
  selected when training was "Windows", and that the AccessKey in `.env`
  matches the account you trained the models under.
- **Nothing happens when you speak**: list available input devices (`import
  sounddevice; sounddevice.query_devices()`) and set `INPUT_DEVICE` in
  `.env` if the wrong mic is picked by default.
- **No audio comes out**: check `PIPER_EXE_PATH`/`PIPER_VOICE_MODEL_PATH`
  are correct — Piper writes nothing to stderr on a silent failure with a
  bad path, it just produces no audio.
- **It keeps triggering on its own voice**: there's no acoustic echo
  cancellation in v1 — the mic is paused during playback as a mitigation,
  but a very loud speaker or an open mic right next to it can still bleed
  through. Lower the speaker volume or increase physical distance.

## Known v1 limitations

- Permission confirmations are keyboard-only (`y/N`), not spoken.
- No real echo cancellation, only pausing the mic during playback.
- Single fixed wake-acknowledgment beep, no visual/other feedback.
