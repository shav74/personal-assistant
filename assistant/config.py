"""Configuration, loaded from environment / .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    # Sonnet is a good default brain; drop to Haiku for cheap/fast turns.
    model: str = os.getenv("ASSISTANT_MODEL", "claude-sonnet-5")
    assistant_name: str = os.getenv("ASSISTANT_NAME", "Niamh")
    data_dir: Path = Path(os.getenv("ASSISTANT_DATA_DIR", "~/.assistant")).expanduser()
    server_host: str = os.getenv("ASSISTANT_SERVER_HOST", "127.0.0.1")
    server_port: int = int(os.getenv("ASSISTANT_SERVER_PORT", "8000"))
    # Optional — web_search tool returns an instructive error until this is set.
    # Free tier: https://brave.com/search/api/
    brave_search_api_key: str = os.getenv("BRAVE_SEARCH_API_KEY", "")
    # Optional — Google Calendar sync for reminders. See
    # assistant/integrations/google_calendar.py for setup steps.
    google_calendar_id: str = os.getenv("GOOGLE_CALENDAR_ID", "primary")

    @property
    def db_path(self) -> Path:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return self.data_dir / "memory.db"

    @property
    def notes_path(self) -> Path:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return self.data_dir / "notes.md"

    @property
    def reminders_db_path(self) -> Path:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return self.data_dir / "reminders.db"

    @property
    def google_credentials_path(self) -> Path:
        override = os.getenv("GOOGLE_CREDENTIALS_PATH")
        if override:
            return Path(override).expanduser()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return self.data_dir / "google_credentials.json"

    @property
    def google_token_path(self) -> Path:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return self.data_dir / "google_token.json"


settings = Settings()
