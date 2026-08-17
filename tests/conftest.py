"""Shared pytest fixtures.

`isolated_settings` is autouse: every test gets its own throwaway data
directory, so nothing here ever reads or writes the real ~/.assistant
store (which has real seeded facts in it).
"""

from __future__ import annotations

import pytest

import assistant.agent as agent_module
from assistant.config import Settings
from assistant.memory.store import MemoryStore
from assistant.reminders.store import ReminderStore
from assistant.tools import builtin as builtin_tools


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path, monkeypatch):
    fake_settings = Settings(
        anthropic_api_key="test-api-key",
        model="test-model",
        assistant_name="TestBot",
        data_dir=tmp_path,
    )
    monkeypatch.setattr(builtin_tools, "settings", fake_settings)
    monkeypatch.setattr(builtin_tools, "_memory", MemoryStore(fake_settings.db_path))
    monkeypatch.setattr(
        builtin_tools, "_reminders", ReminderStore(fake_settings.reminders_db_path)
    )
    monkeypatch.setattr(agent_module, "settings", fake_settings)
    return fake_settings
