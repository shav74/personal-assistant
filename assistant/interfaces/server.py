"""WebSocket API exposing the agent over the network.

One WebSocket connection = one conversation with one Agent. This is the
transport Phase 2 (voice) is meant to speak over — a wake-word/STT
frontend streams recognized text in, gets replies (and TTS-able text)
back, over the same socket.

Confirmation needs special handling here: `Agent.chat()` is synchronous
and blocking (it's a plain network call plus a blocking `confirm()`
callback — the same contract the CLI uses), but FastAPI's WebSocket I/O
is async. `_ConfirmBridge` bridges the two: `agent.chat()` runs in a
worker thread; when it needs confirmation, the bridge schedules a
`confirm_request` send on the event loop and blocks the worker thread on
a `threading.Event` until the client's `confirm_response` arrives and
resolves it.

Run with:  python -m assistant.interfaces.server
"""

from __future__ import annotations

import asyncio
import contextlib
import threading

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from ..agent import Agent
from ..config import settings

app = FastAPI(title=f"{settings.assistant_name} API")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "assistant": settings.assistant_name}


class _ConfirmBridge:
    """Bridges Agent's synchronous confirm() callback to async WS I/O."""

    def __init__(self, websocket: WebSocket, loop: asyncio.AbstractEventLoop):
        self._websocket = websocket
        self._loop = loop
        self._answer = False
        self._answered = threading.Event()

    def confirm(self, description: str) -> bool:
        """Called from the agent's worker thread; blocks until answered."""
        self._answered.clear()
        future = asyncio.run_coroutine_threadsafe(
            self._websocket.send_json(
                {"type": "confirm_request", "description": description}
            ),
            self._loop,
        )
        # Must consume the future — if the scheduled send is cancelled or
        # errors (e.g. connection torn down mid-flight), that exception has
        # to surface here, not linger unretrieved on an abandoned Future.
        future.result(timeout=10)
        self._answered.wait()
        return self._answer

    def resolve(self, allow: bool) -> None:
        """Called from the event loop thread when confirm_response arrives."""
        self._answer = allow
        self._answered.set()


@app.websocket("/ws/chat")
async def chat_socket(websocket: WebSocket) -> None:
    """One connection, one Agent.

    Reading and chat-processing run as two concurrent tasks, not one
    sequential loop: while `agent.chat()` blocks in a worker thread
    waiting on a confirmation, something still has to be calling
    `receive_json()` to actually receive that confirm_response off the
    wire, or the two sides deadlock waiting on each other.
    """
    await websocket.accept()
    loop = asyncio.get_running_loop()
    bridge = _ConfirmBridge(websocket, loop)
    agent = Agent(confirm=bridge.confirm)
    user_messages: asyncio.Queue[str] = asyncio.Queue()

    async def reader() -> None:
        while True:
            message = await websocket.receive_json()
            msg_type = message.get("type")
            if msg_type == "confirm_response":
                bridge.resolve(bool(message.get("allow")))
            elif msg_type == "user_message":
                await user_messages.put(message.get("text", ""))
            else:
                await websocket.send_json(
                    {"type": "error", "detail": f"unknown message type {msg_type!r}"}
                )

    async def responder() -> None:
        while True:
            text = await user_messages.get()
            reply = await asyncio.to_thread(agent.chat, text)
            await websocket.send_json({"type": "assistant_message", "text": reply})

    tasks = [asyncio.create_task(reader()), asyncio.create_task(responder())]
    try:
        done, _pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            exc = task.exception()
            if exc is not None and not isinstance(exc, WebSocketDisconnect):
                raise exc
    except asyncio.CancelledError:
        pass  # the connection itself is being torn down — nothing to do
    finally:
        for task in tasks:
            task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await asyncio.gather(*tasks, return_exceptions=True)


def main() -> None:
    import uvicorn

    if not settings.anthropic_api_key:
        print("Set ANTHROPIC_API_KEY in your .env file first.")
        return

    uvicorn.run(app, host=settings.server_host, port=settings.server_port)


if __name__ == "__main__":
    main()
