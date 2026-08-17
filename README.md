# Personal AI Assistant

A hybrid local/cloud personal assistant with a hand-rolled agent loop,
tool use with a permission model, and persistent memory. Designed to grow
from a CLI agent into a voice assistant, then an IoT hub, then an LLM-driven
robotics controller.

## Architecture

- **Agent core (this repo, WSL2/Linux):** hand-rolled agent loop — no
  agent frameworks — calling a cloud LLM (Anthropic API) for reasoning.
- **Edge processing (local):** wake word, STT (Whisper), TTS (Piper), and
  embeddings all run on-device. Audio never leaves the machine; only text
  goes to the cloud.
- **Memory:** two-tier — SQLite for structured facts (v1, done) + Chroma
  vector store for semantic recall (v2, planned).
- **Permission layer:** every tool is classified safe (read-only,
  auto-run) or dangerous (side effects, requires explicit user
  confirmation). The LLM never has unilateral access to side effects.
- **Interface-agnostic:** the agent takes a `confirm` callback, so CLI,
  web, voice, and robot frontends all reuse the same core.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then add your API key
python -m assistant.interfaces.cli
```

Try: *"what time is it?"*, *"remember that I prefer tea over coffee"*,
*"note down: buy solder"*, *"how much disk space do I have?"* (this one
will ask permission — that's the permission layer working).

Or run it as a WebSocket server instead (`python -m
assistant.interfaces.server`, endpoint `ws://127.0.0.1:8000/ws/chat`) —
the transport Phase 2's voice frontend will speak over. Send `{"type":
"user_message", "text": "..."}`; a dangerous tool call comes back as
`{"type": "confirm_request", "description": "..."}`, reply with
`{"type": "confirm_response", "allow": true|false}`.

Run tests with `pytest`.

## Roadmap

- [x] **Phase 1** — core agent: loop, tools, memory, CLI
- [x] Phase 1.5 — Chroma semantic memory, FastAPI/WebSocket server, tests,
  more tools (weather, reminders, file search, web search)
- [ ] **Phase 2** — voice: Windows audio frontend (wake word + Whisper)
  streaming to this backend over WebSocket; Piper TTS out
- [ ] **Phase 3** — IoT: MQTT / Home Assistant tools
- [ ] **Phase 4** — robotics: ROS2 bridge, LLM task planning → actuation

## Design decisions

- **Why hand-roll the loop?** Frameworks hide exactly the parts worth
  understanding: tool dispatch, message state, error feedback to the model.
  The whole loop is ~100 lines in `assistant/agent.py`.
- **Why hybrid local/cloud?** No discrete GPU locally; cloud gives the best
  reasoning while the privacy-sensitive audio pipeline stays on-device.
  The split also mirrors the eventual Pi/robot deployment topology.
