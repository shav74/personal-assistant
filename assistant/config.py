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
    model: str = os.getenv("ASSISTANT_MODEL", "claude-sonnet-4-6")
    assistant_name: str = os.getenv("ASSISTANT_NAME", "Aria")
    data_dir: Path = Path(os.getenv("ASSISTANT_DATA_DIR", "~/.assistant")).expanduser()

    @property
    def db_path(self) -> Path:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return self.data_dir / "memory.db"

    @property
    def notes_path(self) -> Path:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return self.data_dir / "notes.md"


settings = Settings()
