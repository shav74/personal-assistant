"""Structured long-term memory (v1): a SQLite fact store.

Facts are short natural-language statements ("prefers meetings after 10am")
saved via the `remember` tool and injected into the system prompt each turn.

v2 (planned): add a Chroma vector store for semantic retrieval over
conversation history, so only *relevant* memories are injected instead of
all of them. The interface here is designed so that swap is additive.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class MemoryStore:
    def __init__(self, db_path: Path):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                created_at TEXT NOT NULL
            )
            """
        )
        self.conn.commit()

    def save_fact(self, content: str, category: str = "general") -> int:
        cur = self.conn.execute(
            "INSERT INTO facts (content, category, created_at) VALUES (?, ?, ?)",
            (content, category, datetime.now(timezone.utc).isoformat()),
        )
        self.conn.commit()
        return cur.lastrowid

    def all_facts(self) -> list[tuple[int, str, str]]:
        cur = self.conn.execute(
            "SELECT id, content, category FROM facts ORDER BY id"
        )
        return cur.fetchall()

    def delete_fact(self, fact_id: int) -> bool:
        cur = self.conn.execute("DELETE FROM facts WHERE id = ?", (fact_id,))
        self.conn.commit()
        return cur.rowcount > 0

    def format_for_prompt(self) -> str:
        facts = self.all_facts()
        return "\n".join(f"- [{cat}] {content}" for _, content, cat in facts)
