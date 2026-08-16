"""Built-in starter tools.

Safe tools run automatically; dangerous ones go through the permission
layer. Notice `run_shell` is dangerous while `get_time` is not — this
classification is the whole point of the permission model.
"""

from __future__ import annotations

import subprocess
from datetime import datetime

from ..config import settings
from ..memory.store import MemoryStore
from .base import tool

_memory = MemoryStore(settings.db_path)


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
    dangerous=True,  # writes to disk
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
    dangerous=True,  # arbitrary execution — always confirmed by the user
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
