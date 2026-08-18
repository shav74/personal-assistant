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

## 2. Wake word setup (openWakeWord)

Fully local, free, no account needed at all — a plain `pip install
openwakeword` (already in `requirements.txt`) gets you the engine. The
end-of-speech detector (Silero VAD) is bundled inside `openwakeword` too, so
there's nothing separate to install or configure for that.

You still need to **train** two custom wake-word models, since "neeve"/"hey
neeve" aren't in openWakeWord's small set of pre-trained example words. The
reliable free way to do that:

1. Open the official training notebook: [openWakeWord's Google Colab
   notebook](https://github.com/dscripka/openWakeWord/blob/main/notebooks/training_models.ipynb)
   (needs only the Google account you already have — no new signup).
2. Run it once for the wake phrase **"Neeve"**, once for **"hey Neeve"**.

   **Not "Niamh"** — that's the assistant's name, but it's Gaelic spelling
   (pronounced "neeve") that an English text→phoneme model would mispronounce.
   Training on the phonetic spelling "Neeve" gets you a model that correctly
   fires on how it's actually said; the assistant still introduces itself as
   "Niamh" everywhere else.
3. Download the resulting `.onnx` files, and name them after what they
   detect — openWakeWord reads the *label* from the filename, so name them
   `neeve.onnx` and `hey_neeve.onnx` (underscore, not space) to match
   `WAKE_MODEL_PATHS` in `.env.example`.
4. Put both files in `voice_frontend/models/`.

(There's also a newer hosted trainer at `openwakeword.com/train` — steer
clear of it for now. Whether it's still actually free wasn't something I
could confirm, and this project has already been burned twice by "free"
services quietly going commercial. The Colab notebook is the verified-free
path.)

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

Fill in the wake-word `.onnx` paths and the Piper paths from steps 2–3.
`BACKEND_WS_URL` normally doesn't need changing —
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

- **No `.onnx` file found / wake word never fires**: double-check
  `WAKE_MODEL_PATHS` in `.env` points at the actual downloaded files, and
  that the filenames (used as the detection label) don't have typos.
- **`UserWarning: Specified provider 'CUDAExecutionProvider' is not in
  available provider names`**: harmless — openWakeWord probes for a CUDA
  provider and falls back to CPU automatically. Expected on a CPU-only
  machine, doesn't affect anything.
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
