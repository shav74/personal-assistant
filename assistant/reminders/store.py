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
                google_event_id TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        # Migration: databases created before google_event_id existed won't
        # have picked it up from CREATE TABLE IF NOT EXISTS above.
        existing_columns = {row[1] for row in self.conn.execute("PRAGMA table_info(reminders)")}
        if "google_event_id" not in existing_columns:
            self.conn.execute("ALTER TABLE reminders ADD COLUMN google_event_id TEXT")
        self.conn.commit()

    def add(self, text: str, due_at: str | None = None, google_event_id: str | None = None) -> int:
        cur = self.conn.execute(
            "INSERT INTO reminders (text, due_at, google_event_id, created_at) VALUES (?, ?, ?, ?)",
            (text, due_at, google_event_id, datetime.now(timezone.utc).isoformat()),
        )
        self.conn.commit()
        return cur.lastrowid

    def get(self, reminder_id: int) -> tuple[int, str, str | None, bool, str | None] | None:
        cur = self.conn.execute(
            "SELECT id, text, due_at, done, google_event_id FROM reminders WHERE id = ?",
            (reminder_id,),
        )
        row = cur.fetchone()
        if row is None:
            return None
        id_, text, due_at, done, google_event_id = row
        return (id_, text, due_at, bool(done), google_event_id)

    def list(self, include_done: bool = False) -> list[tuple[int, str, str | None, bool]]:
        query = "SELECT id, text, due_at, done FROM reminders"
        if not include_done:
            query += " WHERE done = 0"
        query += " ORDER BY (due_at IS NULL), due_at, id"
        cur = self.conn.execute(query)
        return [(id_, text, due_at, bool(done)) for id_, text, due_at, done in cur.fetchall()]

    def set_google_event_id(self, reminder_id: int, google_event_id: str) -> bool:
        cur = self.conn.execute(
            "UPDATE reminders SET google_event_id = ? WHERE id = ?",
            (google_event_id, reminder_id),
        )
        self.conn.commit()
        return cur.rowcount > 0

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
