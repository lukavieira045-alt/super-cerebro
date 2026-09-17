"""Aprendizado local adaptativo do Super Cérebro."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any


STOPWORDS = {"para", "como", "isso", "essa", "esse", "esta", "este", "mais", "menos", "muito", "menos", "tambem", "porque", "quando", "onde", "qual", "quais", "uma", "umas", "dos", "das", "com", "sem", "sobre", "por", "pra"}


class Learning:
    """Registra experiências e escolhe estratégias pelo histórico de sucesso."""

    def __init__(self, db_path: str | Path = "data/memory.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    @staticmethod
    def _ensure_column(db: sqlite3.Connection, table: str, column: str, definition: str) -> bool:
        columns = {row[1] for row in db.execute(f"PRAGMA table_info({table})").fetchall()}
        if column in columns:
            return False
        db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
        return True

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
            added_successes = self._ensure_column(db, "strategies", "successes", "INTEGER NOT NULL DEFAULT 0")
            added_failures = self._ensure_column(db, "strategies", "failures", "INTEGER NOT NULL DEFAULT 0")
            if added_successes or added_failures:
                db.execute("""
                    UPDATE strategies
                    SET successes = CASE WHEN success = 1 THEN uses ELSE 0 END,
                        failures = CASE WHEN success = 0 THEN uses ELSE 0 END
                """)

    @staticmethod
    def _normalize(text: str) -> str:
        return re.sub(r"\s+", " ", str(text).strip().lower())[:160]

    @staticmethod
    def _terms(text: str) -> set[str]:
        return {w.lower() for w in re.findall(r"[\wÀ-ÿ]+", str(text)) if len(w) >= 4 and w.lower() not in STOPWORDS}

    @classmethod
    def _similarity(cls, a: str, b: str) -> float:
        left, right = cls._terms(a), cls._terms(b)
        if not left or not right:
            return 0.0
        return len(left & right) / max(1, len(left | right))

    @staticmethod
    def _success_rate(item: dict[str, Any]) -> float:
        successes = int(item.get("successes", 0))
        failures = int(item.get("failures", 0))
        total = successes + failures
        if total <= 0:
            return 1.0 if item.get("success") else 0.0
        return successes / total

    def record(self, task_type: str, strategy: str, success: bool = True) -> None:
        task_type = self._normalize(task_type) or "geral"
        strategy = str(strategy).strip()
        if not strategy:
            return
        with self._connect() as db:
            db.execute("""INSERT INTO strategies (
                    task_type, strategy, success, uses, successes, failures
                ) VALUES (?, ?, ?, 1, ?, ?)
                ON CONFLICT(task_type, strategy) DO UPDATE SET
                    success = excluded.success,
                    uses = strategies.uses + 1,
                    successes = strategies.successes + CASE WHEN excluded.success = 1 THEN 1 ELSE 0 END,
                    failures = strategies.failures + CASE WHEN excluded.success = 0 THEN 1 ELSE 0 END,
                    updated_at = CURRENT_TIMESTAMP""",
                (task_type, strategy, int(success), int(success), int(not success)))

    def record_experience(self, task_type: str, strategy: str, success: bool, reason: str = "") -> None:
        task_type = self._normalize(task_type) or "geral"
        strategy = str(strategy).strip()[:500]
        reason = re.sub(r"\s+", " ", str(reason).strip())[:500]
        if not strategy:
            return
        with self._connect() as db:
            db.execute("INSERT INTO experiences (task_type, strategy, success, reason) VALUES (?, ?, ?, ?)", (task_type, strategy, int(success), reason))
            db.execute("DELETE FROM experiences WHERE id NOT IN (SELECT id FROM experiences ORDER BY id DESC LIMIT 300)")

    def relevant(self, task_type: str, limit: int = 5) -> list[dict[str, Any]]:
        """Busca estratégias por semelhança e usa a taxa histórica de sucesso."""
        with self._connect() as db:
            rows = db.execute("SELECT task_type, strategy, success, uses, successes, failures FROM strategies ORDER BY updated_at DESC LIMIT 500").fetchall()
        ranked = []
        for row in rows:
            item = dict(row)
            similarity = self._similarity(task_type, item["task_type"])
            if similarity > 0 or self._normalize(task_type) == item["task_type"]:
                success_rate = self._success_rate(item)
                rate_bonus = (success_rate - 0.5) * 4.0
                # A quantidade de usos é informativa, mas não deve superar a taxa
                # real de sucesso. A evidência histórica é o sinal principal.
                evidence_bonus = min(0.5, item["uses"] * 0.02)
                ranked.append((similarity * 10 + rate_bonus + evidence_bonus, item))
        ranked.sort(key=lambda pair: pair[0], reverse=True)
        return [item for _, item in ranked[:max(1, limit)]]

    def relevant_experiences(self, task_type: str, limit: int = 5) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute("SELECT task_type, strategy, success, reason FROM experiences ORDER BY id DESC LIMIT 500").fetchall()
        ranked = []
        for row in rows:
            item = dict(row)
            similarity = self._similarity(task_type, item["task_type"])
            if similarity > 0:
                ranked.append((similarity * 10 + (1.5 if item["success"] else 0), item))
        ranked.sort(key=lambda pair: pair[0], reverse=True)
        return [item for _, item in ranked[:max(1, limit)]]

    def best_strategies(self, task_type: str, limit: int = 3) -> list[dict[str, Any]]:
        """Retorna caminhos aprendidos com maior evidência de sucesso."""
        return [item for item in self.relevant(task_type, limit * 2) if self._success_rate(item) >= 0.5][:limit]

    def avoid_strategies(self, task_type: str, limit: int = 3) -> list[dict[str, Any]]:
        """Retorna caminhos que falharam para o agente evitar repetir cegamente."""
        experiences = self.relevant_experiences(task_type, limit * 3)
        return [item for item in experiences if not item["success"]][:limit]

    def context(self, task_type: str, limit: int = 5) -> str:
        items = self.relevant(task_type, limit)
        experiences = self.relevant_experiences(task_type, limit)
        best = self.best_strategies(task_type, 3)
        avoid = self.avoid_strategies(task_type, 3)
        parts: list[str] = []
        if best:
            parts.append("ESTRATÉGIAS COM MAIOR EVIDÊNCIA DE SUCESSO:\n" + "\n".join(f"- {item['strategy']} ({self._success_rate(item):.0%} de sucesso, {item['uses']} usos)" for item in best))
        if avoid:
            parts.append("ESTRATÉGIAS QUE DEVEM SER REAVALIADAS OU EVITADAS:\n" + "\n".join(f"- {item['strategy']} — {item['reason']}" for item in avoid))
        if experiences:
            parts.append("EXPERIÊNCIAS SEMELHANTES:\n" + "\n".join(f"- {'SUCESSO' if item['success'] else 'FALHA'}: {item['strategy']}" + (f" — {item['reason']}" if item['reason'] else "") for item in experiences))
        elif items:
            parts.append("ESTRATÉGIAS APRENDIDAS:\n" + "\n".join(f"- {item['strategy']}" for item in items))
        return "\n\n".join(parts)

    @staticmethod
    def summarize_trace(trace: list[dict[str, Any]]) -> str:
        parts = []
        for step in trace:
            tool = str(step.get("tool", ""))
            status = "ok" if step.get("ok") else "erro"
            if tool:
                parts.append(f"{tool}={status}")
        return " -> ".join(parts)
