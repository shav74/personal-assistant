"""Built-in starter tools.

Safe tools run automatically; dangerous ones go through the permission
layer. `run_shell` decides per-call via `is_dangerous` — a plain, unchained
read-only command (see `_SAFE_SHELL_COMMANDS`) auto-runs, anything else
requires confirmation.
"""

from __future__ import annotations

import os
import shlex
import subprocess
from datetime import datetime
from pathlib import Path

import requests

from ..config import settings
from ..integrations.google_calendar import GoogleCalendarUnavailable
from ..integrations.google_calendar import create_event as gcal_create_event
from ..integrations.google_calendar import delete_event as gcal_delete_event
from ..memory.store import MemoryStore
from ..reminders.store import ReminderStore
from .base import tool

_memory = MemoryStore(settings.db_path)
_reminders = ReminderStore(settings.reminders_db_path)

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


_FILE_SEARCH_SKIP_DIRS = {"__pycache__", "node_modules", ".venv", "venv", ".cache"}
_MAX_SEARCH_RESULTS = 30
_MAX_FILE_READ_CHARS = 20_000


@tool(
    "search_files",
    "Search for files by filename (case-insensitive substring match) under "
    "a directory. Defaults to the user's home directory if no root is given.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Substring to match against filenames."},
            "root": {
                "type": "string",
                "description": "Directory to search under. Defaults to the home directory.",
            },
        },
        "required": ["query"],
    },
)
def search_files(query: str, root: str | None = None) -> str:
    base = Path(root).expanduser() if root else Path.home()
    if not base.is_dir():
        return f"'{base}' is not a directory."

    query_lower = query.lower()
    matches: list[str] = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [
            d for d in dirnames if d not in _FILE_SEARCH_SKIP_DIRS and not d.startswith(".")
        ]
        for name in filenames:
            if query_lower in name.lower():
                matches.append(str(Path(dirpath) / name))
                if len(matches) >= _MAX_SEARCH_RESULTS:
                    break
        if len(matches) >= _MAX_SEARCH_RESULTS:
            break

    if not matches:
        return f"No files matching '{query}' found under {base}."
    suffix = " (truncated, more matches exist)" if len(matches) >= _MAX_SEARCH_RESULTS else ""
    return "\n".join(matches) + suffix


@tool(
    "read_file",
    "Read a text file's contents by path.",
    input_schema={
        "type": "object",
        "properties": {"path": {"type": "string"}},
        "required": ["path"],
    },
)
def read_file(path: str) -> str:
    file_path = Path(path).expanduser()
    if not file_path.is_file():
        return f"'{file_path}' is not a file."
    try:
        content = file_path.read_text(errors="replace")
    except OSError as exc:
        return f"Couldn't read '{file_path}': {exc}"
    if len(content) > _MAX_FILE_READ_CHARS:
        return content[:_MAX_FILE_READ_CHARS] + f"\n... (truncated, {len(content)} chars total)"
    return content


_WMO_WEATHER_CODES = {
    0: "clear sky", 1: "mainly clear", 2: "partly cloudy", 3: "overcast",
    45: "fog", 48: "depositing rime fog",
    51: "light drizzle", 53: "moderate drizzle", 55: "dense drizzle",
    61: "slight rain", 63: "moderate rain", 65: "heavy rain",
    71: "slight snow", 73: "moderate snow", 75: "heavy snow",
    80: "slight rain showers", 81: "moderate rain showers", 82: "violent rain showers",
    95: "thunderstorm", 96: "thunderstorm with slight hail", 99: "thunderstorm with heavy hail",
}


def _geocode(location: str) -> list[dict]:
    geo = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": location, "count": 1},
        timeout=10,
    ).json()
    return geo.get("results") or []


@tool(
    "get_weather",
    "Get current weather conditions for a location (city name or place).",
    input_schema={
        "type": "object",
        "properties": {"location": {"type": "string"}},
        "required": ["location"],
    },
)
def get_weather(location: str) -> str:
    results = _geocode(location)
    if not results and "," in location:
        # Open-Meteo's geocoder matches on bare place names — "Plymouth, UK"
        # finds nothing where "Plymouth" does, so retry with just that part.
        results = _geocode(location.split(",")[0].strip())
    if not results:
        return f"Couldn't find a location matching '{location}'."
    place = results[0]

    forecast = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
            "timezone": "auto",
        },
        timeout=10,
    ).json()
    current = forecast.get("current")
    if not current:
        return f"Couldn't fetch weather for {place.get('name', location)}."

    condition = _WMO_WEATHER_CODES.get(current.get("weather_code"), "unknown conditions")
    place_name = ", ".join(
        part for part in [place.get("name"), place.get("admin1"), place.get("country")] if part
    )
    return (
        f"{place_name}: {current['temperature_2m']}°C, {condition}, "
        f"humidity {current['relative_humidity_2m']}%, "
        f"wind {current['wind_speed_10m']} km/h"
    )


@tool(
    "add_reminder",
    "Add a reminder for the user, and create a matching Google Calendar "
    "event if a due date/time is given. Use when they ask to be reminded "
    "of something.",
    input_schema={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "What to remind the user about."},
            "due_at": {
                "type": "string",
                "description": (
                    "When it's due, ISO 8601 (e.g. 2026-08-20T09:00:00). "
                    "Omit if there's no specific time — calendar sync needs a "
                    "time, so reminders without one stay local-only."
                ),
            },
        },
        "required": ["text"],
    },
)
def add_reminder(text: str, due_at: str | None = None) -> str:
    google_event_id = None
    calendar_note = ""
    if due_at:
        try:
            google_event_id = gcal_create_event(text, due_at)
        except GoogleCalendarUnavailable as exc:
            calendar_note = f" (calendar sync skipped: {exc})"
    reminder_id = _reminders.add(text, due_at, google_event_id)
    return f"Added reminder #{reminder_id}.{calendar_note}"


@tool(
    "list_reminders",
    "List the user's pending reminders, soonest due first. Set include_done "
    "to true to also show completed ones.",
    input_schema={
        "type": "object",
        "properties": {"include_done": {"type": "boolean"}},
        "required": [],
    },
)
def list_reminders(include_done: bool = False) -> str:
    reminders = _reminders.list(include_done=include_done)
    if not reminders:
        return "(no reminders)"
    lines = []
    for id_, text, due_at, done in reminders:
        marker = "[done] " if done else ""
        due = f" (due {due_at})" if due_at else ""
        lines.append(f"#{id_} {marker}{text}{due}")
    return "\n".join(lines)


@tool(
    "complete_reminder",
    "Mark a reminder as done by its ID.",
    input_schema={
        "type": "object",
        "properties": {"reminder_id": {"type": "integer"}},
        "required": ["reminder_id"],
    },
)
def complete_reminder(reminder_id: int) -> str:
    if _reminders.complete(reminder_id):
        return f"Marked reminder #{reminder_id} as done."
    return f"No reminder with ID {reminder_id} found."


@tool(
    "delete_reminder",
    "Delete a reminder by its ID. Also removes its Google Calendar event, "
    "if it had one.",
    input_schema={
        "type": "object",
        "properties": {"reminder_id": {"type": "integer"}},
        "required": ["reminder_id"],
    },
)
def delete_reminder(reminder_id: int) -> str:
    existing = _reminders.get(reminder_id)
    if existing is None:
        return f"No reminder with ID {reminder_id} found."
    _, _, _, _, google_event_id = existing
    if google_event_id:
        try:
            gcal_delete_event(google_event_id)
        except GoogleCalendarUnavailable:
            pass  # best-effort — the local reminder still gets deleted
    _reminders.delete(reminder_id)
    return f"Deleted reminder #{reminder_id}."


@tool(
    "web_search",
    "Search the web and return brief result summaries.",
    input_schema={
        "type": "object",
        "properties": {"query": {"type": "string"}},
        "required": ["query"],
    },
)
def web_search(query: str) -> str:
    if not settings.brave_search_api_key:
        return (
            "Web search isn't configured — set BRAVE_SEARCH_API_KEY in .env "
            "(free tier: https://brave.com/search/api/)."
        )
    response = requests.get(
        "https://api.search.brave.com/res/v1/web/search",
        headers={
            "Accept": "application/json",
            "X-Subscription-Token": settings.brave_search_api_key,
        },
        params={"q": query, "count": 5},
        timeout=10,
    )
    response.raise_for_status()
    results = response.json().get("web", {}).get("results", [])[:5]
    if not results:
        return "No results found."
    return "\n\n".join(
        f"{r.get('title', '')}\n{r.get('url', '')}\n{r.get('description', '')}"
        for r in results
    )
