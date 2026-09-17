"""Aprendizado local de estratégias para o Super Cérebro.

O Vireonix continua sendo o único cérebro. Esta camada apenas registra
quais ferramentas e sequências funcionaram bem, para que o agente possa
reutilizar estratégias em tarefas futuras.
"""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any


class Learning:
    """Memória de estratégias bem-sucedidas armazenada localmente."""

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

    def context(self, task_type: str, limit: int = 5) -> str:
        items = self.relevant(task_type, limit)
        if not items:
            return ""
        return "Estratégias aprendidas de tarefas anteriores:\n" + "\n".join(
            f"- {item['strategy']} (usada {item['uses']}x; sucesso={bool(item['success'])})"
            for item in items
        )

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
