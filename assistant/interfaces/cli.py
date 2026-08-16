"""Terminal chat interface.

Run with:  python -m assistant.interfaces.cli
"""

from __future__ import annotations

from ..agent import Agent
from ..config import settings

BOLD = "\033[1m"
DIM = "\033[2m"
YELLOW = "\033[33m"
RESET = "\033[0m"


def confirm_in_terminal(description: str) -> bool:
    print(f"\n{YELLOW}⚠ Permission required{RESET}\n{description}")
    answer = input(f"{YELLOW}Allow? [y/N]{RESET} ").strip().lower()
    return answer in ("y", "yes")


def main() -> None:
    if not settings.anthropic_api_key:
        print("Set ANTHROPIC_API_KEY in your .env file first.")
        return

    agent = Agent(confirm=confirm_in_terminal)
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

        reply = agent.chat(user_input)
        print(f"\n{BOLD}{settings.assistant_name.lower()}>{RESET} {reply}\n")


if __name__ == "__main__":
    main()
