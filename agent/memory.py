"""Persistent local memory for Super Cérebro."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any


STOPWORDS = {
    "para", "como", "isso", "essa", "esse", "esta", "este", "mais", "menos",
    "muito", "muita", "tambem", "porque", "quando", "onde", "qual", "quais",
    "que", "uma", "umas", "um", "uns", "dos", "das", "com", "sem", "sobre",
    "por", "pra", "nos", "nas", "nosso", "nossa", "seu", "sua", "meu", "minha",
}


class Memory:
    """Memória SQLite com histórico, fatos e recuperação contextual ponderada."""

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

    @staticmethod
    def _terms(text: str) -> set[str]:
        return {
            word.lower()
            for word in re.findall(r"[\wÀ-ÿ]+", str(text))
            if len(word) >= 4 and word.lower() not in STOPWORDS
        }

    @classmethod
    def _score(cls, query: str, content: str, importance: int = 0) -> float:
        query_terms = cls._terms(query)
        content_terms = cls._terms(content)
        if not query_terms or not content_terms:
            return 0.0
        overlap = query_terms & content_terms
        if not overlap:
            return 0.0
        coverage = len(overlap) / len(query_terms)
        density = len(overlap) / max(1, len(content_terms))
        return coverage * 10 + density * 2 + max(0, min(5, int(importance))) * 0.5

    def add(self, role: str, content: str) -> None:
        with self._connect() as db:
            db.execute("INSERT INTO memories (role, content) VALUES (?, ?)", (role, content))

    def recent(self, limit: int = 12) -> list[dict[str, str]]:
        with self._connect() as db:
            rows = db.execute("SELECT role, content FROM memories ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(row) for row in reversed(rows)]

    def relevant(self, text: str, limit: int = 6) -> list[dict[str, str]]:
        """Recupera lembranças por relevância lexical, não apenas por uma palavra igual."""
        with self._connect() as db:
            rows = db.execute("SELECT id, role, content FROM memories ORDER BY id DESC LIMIT 500").fetchall()
        scored: list[tuple[float, int, dict[str, str]]] = []
        for row in rows:
            item = {"role": row["role"], "content": row["content"]}
            score = self._score(text, item["content"])
            if score > 0:
                scored.append((score, int(row["id"]), item))
        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        selected = [item for _, _, item in scored[:limit]]
        return list(reversed(selected))

    def remember_fact(self, category: str, fact: str, importance: int = 2) -> None:
        fact = fact.strip()
        if not fact:
            return
        with self._connect() as db:
            db.execute("""INSERT INTO facts (category, fact, importance)
                VALUES (?, ?, ?)
                ON CONFLICT(fact) DO UPDATE SET
                    category = excluded.category,
                    importance = MAX(facts.importance, excluded.importance),
                    updated_at = CURRENT_TIMESTAMP""",
                (category, fact, max(1, min(5, importance))))

    def facts(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("SELECT category, fact, importance FROM facts ORDER BY importance DESC, updated_at DESC LIMIT ?", (limit,)).fetchall()
        return [dict(row) for row in rows]

    def relevant_facts(self, text: str, limit: int = 8) -> list[dict[str, Any]]:
        """Prioriza fatos pelo quanto ajudam a explicar a tarefa atual."""
        with self._connect() as db:
            rows = db.execute("SELECT category, fact, importance FROM facts ORDER BY importance DESC, updated_at DESC LIMIT 500").fetchall()
        scored: list[tuple[float, int, dict[str, Any]]] = []
        for row in rows:
            item = dict(row)
            score = self._score(text, f"{item['category']} {item['fact']}", item["importance"])
            if score > 0:
                scored.append((score, int(item["importance"]), item))
        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [item for _, _, item in scored[:limit]]

    def clear(self) -> None:
        with self._connect() as db:
            db.execute("DELETE FROM memories")
            db.execute("DELETE FROM facts")
