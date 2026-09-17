"""Memória persistente de experiências e caminhos de resolução."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any


class ExperienceMemory:
    """Guarda estratégias executadas para reutilização em tarefas semelhantes."""

    def __init__(self, db_path: str | Path = "data/memory.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.db_path)
        db.row_factory = sqlite3.Row
        return db

    def _init_db(self) -> None:
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS task_experiences (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task TEXT NOT NULL,
                strategy TEXT NOT NULL,
                result TEXT NOT NULL,
                success INTEGER NOT NULL,
                uses INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")

    @staticmethod
    def _terms(text: str) -> set[str]:
        return {w.lower() for w in re.findall(r"[\wÀ-ÿ]+", str(text)) if len(w) >= 4}

    @classmethod
    def _similarity(cls, a: str, b: str) -> float:
        left, right = cls._terms(a), cls._terms(b)
        if not left or not right:
            return 0.0
        return len(left & right) / len(left | right)

    def record(self, task: str, strategy: str, result: str, success: bool) -> None:
        task = re.sub(r"\s+", " ", str(task).strip())[:600]
        strategy = re.sub(r"\s+", " ", str(strategy).strip())[:500]
        result = re.sub(r"\s+", " ", str(result).strip())[:800]
        if not task or not strategy:
            return
        with self._connect() as db:
            db.execute("""INSERT INTO task_experiences (task, strategy, result, success)
                VALUES (?, ?, ?, ?)""", (task, strategy, result, int(success)))
            db.execute("""DELETE FROM task_experiences
                WHERE id NOT IN (SELECT id FROM task_experiences ORDER BY id DESC LIMIT 500)""")

    def relevant(self, task: str, limit: int = 5) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("SELECT id, task, strategy, result, success, uses FROM task_experiences ORDER BY id DESC LIMIT 500").fetchall()
        ranked: list[tuple[float, dict[str, Any]]] = []
        for row in rows:
            item = dict(row)
            similarity = self._similarity(task, item["task"])
            if similarity <= 0:
                continue
            score = similarity * 10 + (2.0 if item["success"] else -1.5) + min(2.0, item["uses"] * 0.1)
            ranked.append((score, item))
        ranked.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in ranked[:max(1, limit)]]

    def context(self, task: str, limit: int = 5) -> str:
        items = self.relevant(task, limit)
        if not items:
            return ""
        lines = ["EXPERIÊNCIAS DE TAREFAS SEMELHANTES:"]
        for item in items:
            status = "SUCESSO" if item["success"] else "FALHA"
            lines.append(f"- [{status}] Estratégia: {item['strategy']} | Resultado: {item['result']}")
        lines.append("Use experiências anteriores apenas como orientação; confirme se a estratégia serve para a tarefa atual.")
        return "\n".join(lines)
