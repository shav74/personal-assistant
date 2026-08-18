"""WebSocket client for the backend's /ws/chat endpoint — the same protocol
`assistant/interfaces/ws_client.py` speaks, pulled out here as a reusable,
mockable class instead of inline stdin/stdout code, since main.py drives it
from speech instead of a terminal prompt."""

from __future__ import annotations

import json
from typing import Callable

from websockets.sync.client import connect


class BackendError(Exception):
    """Raised when the server reports an error instead of a reply."""


class BackendClient:
    def __init__(self, url: str):
        self._url = url
        self._ws = None

    def connect(self) -> None:
        self._ws = connect(self._url)

    def close(self) -> None:
        if self._ws is not None:
            self._ws.close()
            self._ws = None

    def send_command(self, text: str, on_confirm: Callable[[str], bool]) -> str:
        """Send one user message and drive the response loop to completion,
        answering as many confirm_request rounds as the agent's tool loop
        needs, and returning the final assistant_message text."""
        self._ws.send(json.dumps({"type": "user_message", "text": text}))

        while True:
            message = json.loads(self._ws.recv())
            msg_type = message.get("type")

            if msg_type == "confirm_request":
                allow = on_confirm(message["description"])
                self._ws.send(json.dumps({"type": "confirm_response", "allow": allow}))
                continue

            if msg_type == "assistant_message":
                return message["text"]

            raise BackendError(message.get("detail", str(message)))
