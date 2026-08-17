"""Terminal chat client for the WebSocket server (assistant/interfaces/server.py).

Same interactive experience as the CLI, but talking to a running server
over the network instead of driving an in-process Agent directly — useful
for testing the server, and a stand-in for what a real remote frontend
(voice, web) will eventually do.

Run the server first:  python -m assistant.interfaces.server
Then, in another terminal:  python -m assistant.interfaces.ws_client
"""

from __future__ import annotations

import json

from websockets.sync.client import connect

from ..config import settings

BOLD = "\033[1m"
DIM = "\033[2m"
YELLOW = "\033[33m"
RESET = "\033[0m"


def main() -> None:
    url = f"ws://{settings.server_host}:{settings.server_port}/ws/chat"
    print(f"{DIM}Connecting to {url} ...{RESET}")

    with connect(url) as ws:
        print(f"{BOLD}{settings.assistant_name}{RESET} ready. "
              f"{DIM}Type 'quit' to exit.{RESET}\n")

        while True:
            try:
                user_input = input(f"{BOLD}you>{RESET} ").strip()
            except (KeyboardInterrupt, EOFError):
                print()
                break
            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit"):
                break

            ws.send(json.dumps({"type": "user_message", "text": user_input}))

            while True:
                message = json.loads(ws.recv())
                msg_type = message.get("type")

                if msg_type == "confirm_request":
                    print(f"\n{YELLOW}⚠ Permission required{RESET}\n{message['description']}")
                    answer = input(f"{YELLOW}Allow? [y/N]{RESET} ").strip().lower()
                    ws.send(json.dumps({
                        "type": "confirm_response",
                        "allow": answer in ("y", "yes"),
                    }))
                    continue

                if msg_type == "assistant_message":
                    print(f"\n{BOLD}{settings.assistant_name.lower()}>{RESET} {message['text']}\n")
                    break

                print(f"\n{YELLOW}(server error){RESET} {message}\n")
                break


if __name__ == "__main__":
    main()
