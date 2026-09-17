"""Objetivos persistentes do Super Cérebro."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any


class Goals:
    """Mantém objetivos ativos entre mensagens usando o mesmo SQLite da memória."""

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
            db.execute("""CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                progress TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r"\s+", " ", str(text).strip())[:500]

    def create(self, title: str) -> int:
        title = self._normalize(title)
        if not title:
            raise ValueError("objetivo vazio")
        with self._connect() as db:
            row = db.execute(
                "SELECT id FROM goals WHERE status = 'active' AND lower(title) = lower(?) ORDER BY id DESC LIMIT 1",
                (title,),
            ).fetchone()
            if row:
                return int(row["id"])
            cursor = db.execute("INSERT INTO goals (title) VALUES (?)", (title,))
            return int(cursor.lastrowid)

    def active(self, limit: int = 5) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT id, title, status, progress, created_at, updated_at FROM goals WHERE status = 'active' ORDER BY updated_at DESC, id DESC LIMIT ?",
                (max(1, min(int(limit), 20)),),
            ).fetchall()
        return [dict(row) for row in rows]

    def update(self, goal_id: int, progress: str, status: str | None = None) -> None:
        progress = self._normalize(progress)
        with self._connect() as db:
            if status is None:
                db.execute("UPDATE goals SET progress = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (progress, goal_id))
            else:
                if status not in {"active", "paused", "completed", "cancelled"}:
                    raise ValueError("status de objetivo inválido")
                db.execute("UPDATE goals SET progress = ?, status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (progress, status, goal_id))

    def complete(self, goal_id: int, progress: str = "Concluído.") -> None:
        self.update(goal_id, progress, "completed")

    def context(self, limit: int = 5) -> str:
        goals = self.active(limit)
        if not goals:
            return ""
        lines = ["OBJETIVOS PERSISTENTES ATIVOS:"]
        for goal in goals:
            progress = f" — progresso: {goal['progress']}" if goal["progress"] else ""
            lines.append(f"- #{goal['id']}: {goal['title']}{progress}")
        return "\n".join(lines)

    def active_for(self, text: str, limit: int = 3) -> list[dict[str, Any]]:
        """Encontra objetivos ativos relacionados à mensagem atual por termos compartilhados."""
        words = {w.lower() for w in re.findall(r"[\wÀ-ÿ]+", str(text)) if len(w) >= 4}
        if not words:
            return []
        candidates = self.active(20)
        scored: list[tuple[int, int, dict[str, Any]]] = []
        for goal in candidates:
            goal_words = {w.lower() for w in re.findall(r"[\wÀ-ÿ]+", goal["title"]) if len(w) >= 4}
            overlap = len(words & goal_words)
            if overlap:
                scored.append((overlap, int(goal["id"]), goal))
        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [goal for _, _, goal in scored[:limit]]
