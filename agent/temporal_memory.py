"""Camada temporal para conhecimento persistente do Super Cérebro."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class TemporalMemory:
    """Registra quando uma informação foi observada e calcula sua atualidade."""

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
            db.execute("""CREATE TABLE IF NOT EXISTS temporal_facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                fact TEXT NOT NULL,
                observed_at TEXT NOT NULL,
                valid_until TEXT,
                confidence REAL NOT NULL DEFAULT 0.7,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")

    @staticmethod
    def _clean(value: str, limit: int = 500) -> str:
        return " ".join(str(value).strip().split())[:limit]

    def record(self, subject: str, fact: str, confidence: float = 0.7, valid_until: str | None = None) -> None:
        subject, fact = self._clean(subject, 160), self._clean(fact)
        if not subject or not fact:
            return
        confidence = max(0.0, min(1.0, float(confidence)))
        observed = datetime.now(timezone.utc).isoformat()
        with self._connect() as db:
            db.execute("INSERT INTO temporal_facts (subject, fact, observed_at, valid_until, confidence) VALUES (?, ?, ?, ?, ?)", (subject, fact, observed, valid_until, confidence))
            db.execute("DELETE FROM temporal_facts WHERE id NOT IN (SELECT id FROM temporal_facts ORDER BY id DESC LIMIT 1000)")

    def relevant(self, query: str, limit: int = 6) -> list[dict[str, Any]]:
        terms = {w.lower() for w in str(query).split() if len(w) >= 4}
        with self._connect() as db:
            rows = db.execute("SELECT subject, fact, observed_at, valid_until, confidence FROM temporal_facts ORDER BY id DESC LIMIT 500").fetchall()
        ranked = []
        now = datetime.now(timezone.utc)
        for row in rows:
            item = dict(row)
            haystack = f"{item['subject']} {item['fact']}".lower()
            overlap = sum(1 for term in terms if term in haystack)
            if not overlap:
                continue
            age_days = max(0.0, (now - datetime.fromisoformat(item['observed_at'])).total_seconds() / 86400)
            freshness = 1.0 / (1.0 + age_days / 30.0)
            score = overlap * 3 + float(item['confidence']) + freshness
            ranked.append((score, item))
        ranked.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in ranked[:max(1, limit)]]

    def context(self, query: str, limit: int = 6) -> str:
        items = self.relevant(query, limit)
        if not items:
            return ""
        lines = ["MEMÓRIA TEMPORAL RELEVANTE:"]
        for item in items:
            lines.append(f"- [{item['observed_at']}] {item['subject']}: {item['fact']}")
        lines.append("Considere a data de observação. Informação temporalmente sensível deve ser confirmada quando necessário.")
        return "\n".join(lines)
