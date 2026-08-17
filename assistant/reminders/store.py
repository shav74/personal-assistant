"""Reminder storage: a small SQLite table, separate from the fact memory.

Reminders and remembered facts are different kinds of data (one-off,
time-bound tasks vs. lasting facts about the user) so they get their own
store rather than being shoehorned into MemoryStore's `facts` table.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class ReminderStore:
    def __init__(self, db_path: Path):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT NOT NULL,
                due_at TEXT,
                done INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
            """
        )
        self.conn.commit()

    def add(self, text: str, due_at: str | None = None) -> int:
        cur = self.conn.execute(
            "INSERT INTO reminders (text, due_at, created_at) VALUES (?, ?, ?)",
            (text, due_at, datetime.now(timezone.utc).isoformat()),
        )
        self.conn.commit()
        return cur.lastrowid

    def list(self, include_done: bool = False) -> list[tuple[int, str, str | None, bool]]:
        query = "SELECT id, text, due_at, done FROM reminders"
        if not include_done:
            query += " WHERE done = 0"
        query += " ORDER BY (due_at IS NULL), due_at, id"
        cur = self.conn.execute(query)
        return [(id_, text, due_at, bool(done)) for id_, text, due_at, done in cur.fetchall()]

    def complete(self, reminder_id: int) -> bool:
        cur = self.conn.execute(
            "UPDATE reminders SET done = 1 WHERE id = ?", (reminder_id,)
        )
        self.conn.commit()
        return cur.rowcount > 0

    def delete(self, reminder_id: int) -> bool:
        cur = self.conn.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
        self.conn.commit()
        return cur.rowcount > 0
