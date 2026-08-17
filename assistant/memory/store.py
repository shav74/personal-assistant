"""Structured long-term memory: SQLite fact store + Chroma semantic recall.

Facts are short natural-language statements ("prefers meetings after 10am")
saved via the `remember` tool. SQLite is the source of truth (id, content,
category, timestamp); Chroma indexes the same facts by embedding (v2) so
that once there are more facts than fit comfortably in a prompt, only the
ones *relevant* to the current message get injected instead of all of them.
Embeddings run on-device via Chroma's bundled ONNX model — no data leaves
the machine for this step.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import chromadb

# Below this many stored facts, just include everything in the prompt —
# semantic filtering only helps once there's enough volume to filter down.
RECALL_THRESHOLD = 20
RECALL_TOP_K = 8


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

        chroma_client = chromadb.PersistentClient(
            path=str(db_path.parent / "chroma")
        )
        self.collection = chroma_client.get_or_create_collection("facts")

    def save_fact(self, content: str, category: str = "general") -> int:
        cur = self.conn.execute(
            "INSERT INTO facts (content, category, created_at) VALUES (?, ?, ?)",
            (content, category, datetime.now(timezone.utc).isoformat()),
        )
        self.conn.commit()
        fact_id = cur.lastrowid
        self.collection.upsert(
            ids=[str(fact_id)],
            documents=[content],
            metadatas=[{"category": category}],
        )
        return fact_id

    def all_facts(self) -> list[tuple[int, str, str]]:
        cur = self.conn.execute(
            "SELECT id, content, category FROM facts ORDER BY id"
        )
        return cur.fetchall()

    def delete_fact(self, fact_id: int) -> bool:
        cur = self.conn.execute("DELETE FROM facts WHERE id = ?", (fact_id,))
        self.conn.commit()
        deleted = cur.rowcount > 0
        if deleted:
            self.collection.delete(ids=[str(fact_id)])
        return deleted

    def recall(
        self, query: str, n_results: int = RECALL_TOP_K
    ) -> list[tuple[int, str, str]]:
        """Semantic search over stored facts, ranked by relevance to `query`."""
        count = self.collection.count()
        if count == 0:
            return []
        results = self.collection.query(
            query_texts=[query], n_results=min(n_results, count)
        )
        return [
            (int(id_), doc, meta.get("category", "general"))
            for id_, doc, meta in zip(
                results["ids"][0], results["documents"][0], results["metadatas"][0]
            )
        ]

    def format_for_prompt(self, query: str | None = None) -> str:
        facts = self.all_facts()
        if query and len(facts) > RECALL_THRESHOLD:
            facts = self.recall(query)
        return "\n".join(f"- [{cat}] {content}" for _, content, cat in facts)
