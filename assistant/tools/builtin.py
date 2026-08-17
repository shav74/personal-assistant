"""Built-in starter tools.

Safe tools run automatically; dangerous ones go through the permission
layer. `run_shell` decides per-call via `is_dangerous` — a plain, unchained
read-only command (see `_SAFE_SHELL_COMMANDS`) auto-runs, anything else
requires confirmation.
"""

from __future__ import annotations

import shlex
import subprocess
from datetime import datetime

from ..config import settings
from ..memory.store import MemoryStore
from .base import tool

_memory = MemoryStore(settings.db_path)

# Read-only / informational commands that run without confirmation. Matched
# on the first word only, and only when the command has no shell
# metacharacters — pipes, redirects, substitution, or chaining (`;`, `&&`)
# can hide a mutating command behind a safe-looking prefix (e.g.
# `ls; rm -rf ~` or `echo hi > ~/.bashrc`), so any of those still asks.
_SAFE_SHELL_COMMANDS = {
    "ls", "cat", "pwd", "whoami", "date", "df", "du", "ps", "uname",
    "echo", "which", "uptime", "free", "hostname", "id", "env",
}
_SHELL_METACHARACTERS = set("|&;$`<>()")


def _shell_command_is_dangerous(tool_input: dict) -> bool:
    command = tool_input.get("command", "")
    if any(ch in command for ch in _SHELL_METACHARACTERS):
        return True
    try:
        parts = shlex.split(command)
    except ValueError:
        return True  # unparsable (e.g. unmatched quote) — ask to be safe
    return not parts or parts[0] not in _SAFE_SHELL_COMMANDS


@tool(
    "get_time",
    "Get the current local date and time.",
)
def get_time() -> str:
    return datetime.now().strftime("%A %d %B %Y, %H:%M:%S")


@tool(
    "remember",
    "Save a fact about the user to long-term memory. Use when the user "
    "shares a lasting preference, detail, or instruction worth remembering.",
    input_schema={
        "type": "object",
        "properties": {
            "fact": {"type": "string", "description": "The fact to remember, phrased in third person."},
            "category": {
                "type": "string",
                "description": "One of: preference, personal, work, project, general",
            },
        },
        "required": ["fact"],
    },
)
def remember(fact: str, category: str = "general") -> str:
    fact_id = _memory.save_fact(fact, category)
    return f"Saved fact #{fact_id}."


@tool(
    "list_memories",
    "List every fact currently remembered about the user, with its ID and "
    "category. Use this to see what's stored — e.g. before calling forget, "
    "or when asked what you know about the user.",
)
def list_memories() -> str:
    facts = _memory.all_facts()
    if not facts:
        return "(nothing remembered yet)"
    return "\n".join(f"#{id_} [{cat}] {content}" for id_, content, cat in facts)


@tool(
    "forget",
    "Delete a previously remembered fact by its ID. Use list_memories first "
    "if you don't already know the ID. Only touches the assistant's own "
    "memory store, so no confirmation is required.",
    input_schema={
        "type": "object",
        "properties": {
            "fact_id": {
                "type": "integer",
                "description": "The ID of the fact to delete, from list_memories.",
            },
        },
        "required": ["fact_id"],
    },
)
def forget(fact_id: int) -> str:
    if _memory.delete_fact(fact_id):
        return f"Forgot fact #{fact_id}."
    return f"No fact with ID {fact_id} found."


@tool(
    "read_notes",
    "Read the user's notes file.",
)
def read_notes() -> str:
    if not settings.notes_path.exists():
        return "(notes file is empty)"
    return settings.notes_path.read_text()


@tool(
    "append_note",
    "Append a line to the user's notes file.",
    input_schema={
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    },
    # Only touches the assistant's own notes file — low blast radius,
    # trivially reversible, so no confirmation needed.
)
def append_note(text: str) -> str:
    with settings.notes_path.open("a") as f:
        f.write(f"- {text}  ({datetime.now():%Y-%m-%d %H:%M})\n")
    return "Note added."


@tool(
    "run_shell",
    "Run a shell command on the user's machine and return its output. "
    "Use for system info, file listings, or tasks the user asks for. "
    "Prefer read-only commands.",
    input_schema={
        "type": "object",
        "properties": {"command": {"type": "string"}},
        "required": ["command"],
    },
    # A fixed allowlist of plain, unchained read-only commands runs without
    # asking; anything else (mutating, or using shell metacharacters that
    # could hide a mutating command) still requires confirmation.
    is_dangerous=_shell_command_is_dangerous,
)
def run_shell(command: str) -> str:
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    output = (result.stdout + result.stderr).strip()
    return output[:5000] or "(no output)"
