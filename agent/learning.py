"""Aprendizado local de estratégias e experiências do Super Cérebro."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any


class Learning:
    """Registra estratégias e experiências para reutilização futura."""

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
            db.execute("""CREATE TABLE IF NOT EXISTS strategies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_type TEXT NOT NULL,
                strategy TEXT NOT NULL,
                success INTEGER NOT NULL DEFAULT 1,
                uses INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(task_type, strategy)
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS experiences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_type TEXT NOT NULL,
                strategy TEXT NOT NULL,
                success INTEGER NOT NULL,
                reason TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r"\s+", " ", str(text).strip().lower())[:160]

    def record(self, task_type: str, strategy: str, success: bool = True) -> None:
        task_type = self._normalize(task_type) or "geral"
        strategy = str(strategy).strip()
        if not strategy:
            return
        with self._connect() as db:
            db.execute("""INSERT INTO strategies (task_type, strategy, success, uses)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(task_type, strategy) DO UPDATE SET
                    success = CASE WHEN excluded.success = 1 THEN 1 ELSE strategies.success END,
                    uses = strategies.uses + 1,
                    updated_at = CURRENT_TIMESTAMP""",
                (task_type, strategy, int(success)))

    def record_experience(self, task_type: str, strategy: str, success: bool, reason: str = "") -> None:
        """Guarda uma experiência concreta: o caminho usado e o resultado observado."""
        task_type = self._normalize(task_type) or "geral"
        strategy = str(strategy).strip()[:500]
        reason = re.sub(r"\s+", " ", str(reason).strip())[:500]
        if not strategy:
            return
        with self._connect() as db:
            db.execute(
                "INSERT INTO experiences (task_type, strategy, success, reason) VALUES (?, ?, ?, ?)",
                (task_type, strategy, int(success), reason),
            )
            db.execute(
                "DELETE FROM experiences WHERE id NOT IN (SELECT id FROM experiences ORDER BY id DESC LIMIT 300)"
            )

    def relevant(self, task_type: str, limit: int = 5) -> list[dict[str, Any]]:
        key = self._normalize(task_type)
        words = [word for word in re.findall(r"[\wÀ-ÿ]+", key) if len(word) >= 4]
        with self._connect() as db:
            if words:
                clauses = " OR ".join("task_type LIKE ?" for _ in words)
                params = [f"%{word}%" for word in words]
                rows = db.execute(
                    f"SELECT task_type, strategy, success, uses FROM strategies WHERE {clauses} ORDER BY success DESC, uses DESC, updated_at DESC LIMIT ?",
                    (*params, limit),
                ).fetchall()
            else:
                rows = db.execute(
                    "SELECT task_type, strategy, success, uses FROM strategies ORDER BY success DESC, uses DESC, updated_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [dict(row) for row in rows]

    def relevant_experiences(self, task_type: str, limit: int = 5) -> list[dict[str, Any]]:
        """Recupera experiências semelhantes, incluindo sucessos e falhas recentes."""
        key = self._normalize(task_type)
        words = [word for word in re.findall(r"[\wÀ-ÿ]+", key) if len(word) >= 4]
        with self._connect() as db:
            if words:
                clauses = " OR ".join("task_type LIKE ?" for _ in words)
                params = [f"%{word}%" for word in words]
                rows = db.execute(
                    f"SELECT task_type, strategy, success, reason FROM experiences WHERE {clauses} ORDER BY id DESC LIMIT ?",
                    (*params, limit),
                ).fetchall()
            else:
                rows = db.execute(
                    "SELECT task_type, strategy, success, reason FROM experiences ORDER BY id DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [dict(row) for row in rows]

    def context(self, task_type: str, limit: int = 5) -> str:
        items = self.relevant(task_type, limit)
        experiences = self.relevant_experiences(task_type, limit)
        parts: list[str] = []
        if items:
            parts.append("Estratégias aprendidas de tarefas anteriores:\n" + "\n".join(
                f"- {item['strategy']} (usada {item['uses']}x; sucesso={bool(item['success'])})"
                for item in items
            ))
        if experiences:
            parts.append("Experiências recentes semelhantes:\n" + "\n".join(
                f"- {'SUCESSO' if item['success'] else 'FALHA'}: {item['strategy']}"
                + (f" — {item['reason']}" if item['reason'] else "")
                for item in experiences
            ))
        return "\n\n".join(parts)

    @staticmethod
    def summarize_trace(trace: list[dict[str, Any]]) -> str:
        """Converte o histórico de ferramentas em uma estratégia compacta."""
        parts = []
        for step in trace:
            tool = str(step.get("tool", ""))
            status = "ok" if step.get("ok") else "erro"
            if tool:
                parts.append(f"{tool}={status}")
        return " -> ".join(parts)
