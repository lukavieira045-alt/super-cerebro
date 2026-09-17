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
    """Memória SQLite com histórico, fatos e retenção de longo prazo."""

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
                importance INTEGER NOT NULL DEFAULT 1,
                access_count INTEGER NOT NULL DEFAULT 0,
                last_accessed_at TEXT,
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
            self._ensure_column(db, "memories", "importance", "INTEGER NOT NULL DEFAULT 1")
            self._ensure_column(db, "memories", "access_count", "INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(db, "memories", "last_accessed_at", "TEXT")

    @staticmethod
    def _ensure_column(db: sqlite3.Connection, table: str, column: str, definition: str) -> None:
        columns = {row[1] for row in db.execute(f"PRAGMA table_info({table})").fetchall()}
        if column not in columns:
            db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    @staticmethod
    def _terms(text: str) -> set[str]:
        return {
            word.lower()
            for word in re.findall(r"[\wÀ-ÿ]+", str(text))
            if len(word) >= 4 and word.lower() not in STOPWORDS
        }

    @classmethod
    def _score(cls, query: str, content: str, importance: int = 0, access_count: int = 0) -> float:
        query_terms = cls._terms(query)
        content_terms = cls._terms(content)
        if not query_terms or not content_terms:
            return 0.0
        overlap = query_terms & content_terms
        if not overlap:
            return 0.0
        coverage = len(overlap) / len(query_terms)
        density = len(overlap) / max(1, len(content_terms))
        importance_bonus = max(0, min(5, int(importance))) * 0.5
        access_bonus = min(1.5, max(0, int(access_count)) * 0.1)
        return coverage * 10 + density * 2 + importance_bonus + access_bonus

    def add(self, role: str, content: str, importance: int = 1) -> None:
        with self._connect() as db:
            db.execute(
                "INSERT INTO memories (role, content, importance) VALUES (?, ?, ?)",
                (role, content, max(1, min(5, int(importance)))),
            )

    def recent(self, limit: int = 12) -> list[dict[str, str]]:
        with self._connect() as db:
            rows = db.execute("SELECT role, content FROM memories ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(row) for row in reversed(rows)]

    def relevant(self, text: str, limit: int = 6) -> list[dict[str, str]]:
        """Recupera lembranças por relevância e reforça memórias reutilizadas."""
        with self._connect() as db:
            rows = db.execute("SELECT id, role, content, importance, access_count FROM memories ORDER BY id DESC LIMIT 1000").fetchall()
        scored: list[tuple[float, int, dict[str, str]]] = []
        for row in rows:
            item = {"role": row["role"], "content": row["content"]}
            score = self._score(text, item["content"], row["importance"], row["access_count"])
            if score > 0:
                scored.append((score, int(row["id"]), item))
        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        selected = list(reversed([item for _, _, item in scored[:limit]]))
        if selected:
            contents = [item["content"] for item in selected]
            with self._connect() as db:
                for content in contents:
                    db.execute("UPDATE memories SET access_count = access_count + 1, last_accessed_at = CURRENT_TIMESTAMP WHERE content = ?", (content,))
        return selected

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

    def memory_context(self, text: str, limit: int = 8) -> str:
        """Monta um contexto compacto, priorizando fatos e lembranças relevantes."""
        facts = self.relevant_facts(text, limit=limit)
        memories = self.relevant(text, limit=limit)
        parts: list[str] = []
        if facts:
            parts.append("FATOS RELEVANTES:\n" + "\n".join(
                f"- [{item['category']}] {item['fact']} (importância {item['importance']})"
                for item in facts
            ))
        if memories:
            parts.append("LEMBRANÇAS RELEVANTES:\n" + "\n".join(
                f"- {item['role']}: {item['content']}" for item in memories
            ))
        return "\n\n".join(parts)

    def retain(self, max_memories: int = 3000) -> int:
        """Remove apenas memórias antigas e pouco úteis, preservando as importantes."""
        max_memories = max(100, int(max_memories))
        with self._connect() as db:
            count = int(db.execute("SELECT COUNT(*) AS total FROM memories").fetchone()["total"])
            if count <= max_memories:
                return 0
            excess = count - max_memories
            rows = db.execute("""SELECT id FROM memories
                ORDER BY (importance * 4 + MIN(access_count, 10) + CASE WHEN last_accessed_at IS NULL THEN 0 ELSE 2 END) ASC, id ASC
                LIMIT ?""", (excess,)).fetchall()
            ids = [int(row["id"]) for row in rows]
            if not ids:
                return 0
            db.executemany("DELETE FROM memories WHERE id = ?", [(item,) for item in ids])
            return len(ids)

    def clear(self) -> None:
        with self._connect() as db:
            db.execute("DELETE FROM memories")
            db.execute("DELETE FROM facts")
