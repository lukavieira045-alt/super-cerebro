"""Persistent local memory for Super Cérebro."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Iterable


class Memory:
    """Lightweight SQLite memory with short history and long-term facts."""

    def __init__(self, db_path: str | Path = "data/memory.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                fact TEXT NOT NULL UNIQUE,
                importance INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")

    def add(self, role: str, content: str) -> None:
        with self._connect() as db:
            db.execute("INSERT INTO memories (role, content) VALUES (?, ?)", (role, content))

    def recent(self, limit: int = 12) -> list[dict[str, str]]:
        with self._connect() as db:
            rows = db.execute("SELECT role, content FROM memories ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(row) for row in reversed(rows)]

    def relevant(self, text: str, limit: int = 6) -> list[dict[str, str]]:
        words = [w.lower() for w in re.findall(r"[\wÀ-ÿ]+", text) if len(w) >= 4]
        if not words:
            return []
        clauses = " OR ".join("content LIKE ?" for _ in words)
        params: Iterable[str] = [f"%{word}%" for word in words]
        with self._connect() as db:
            rows = db.execute(f"SELECT role, content FROM memories WHERE {clauses} ORDER BY id DESC LIMIT ?", (*params, limit)).fetchall()
        return [dict(row) for row in reversed(rows)]

    def remember_fact(self, category: str, fact: str, importance: int = 2) -> None:
        with self._connect() as db:
            db.execute("""INSERT INTO facts (category, fact, importance)
                VALUES (?, ?, ?)
                ON CONFLICT(fact) DO UPDATE SET
                    category = excluded.category,
                    importance = MAX(facts.importance, excluded.importance),
                    updated_at = CURRENT_TIMESTAMP""",
                (category, fact.strip(), max(1, min(5, importance))))

    def facts(self, limit: int = 20) -> list[dict[str, str]]:
        with self._connect() as db:
            rows = db.execute("SELECT category, fact, importance FROM facts ORDER BY importance DESC, updated_at DESC LIMIT ?", (limit,)).fetchall()
        return [dict(row) for row in rows]

    def relevant_facts(self, text: str, limit: int = 8) -> list[dict[str, str]]:
        words = [w.lower() for w in re.findall(r"[\wÀ-ÿ]+", text) if len(w) >= 4]
        if not words:
            return self.facts(limit)
        clauses = " OR ".join("LOWER(fact) LIKE ?" for _ in words)
        params: Iterable[str] = [f"%{word}%" for word in words]
        with self._connect() as db:
            rows = db.execute(f"SELECT category, fact, importance FROM facts WHERE {clauses} ORDER BY importance DESC, updated_at DESC LIMIT ?", (*params, limit)).fetchall()
        return [dict(row) for row in rows]

    def clear(self) -> None:
        with self._connect() as db:
            db.execute("DELETE FROM memories")
            db.execute("DELETE FROM facts")
