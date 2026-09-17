"""Camada temporal para conhecimento persistente do Super Cérebro."""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class TemporalMemory:
    """Registra quando uma informação foi observada e respeita sua validade."""

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

    @staticmethod
    def _parse_time(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except (TypeError, ValueError):
            return None

    def record(self, subject: str, fact: str, confidence: float = 0.7, valid_until: str | None = None) -> None:
        subject, fact = self._clean(subject, 160), self._clean(fact)
        if not subject or not fact:
            return
        confidence = max(0.0, min(1.0, float(confidence)))
        if valid_until is not None:
            valid_until = self._clean(valid_until, 64)
            if self._parse_time(valid_until) is None:
                raise ValueError("valid_until deve ser uma data ISO-8601 válida")
        observed = datetime.now(timezone.utc).isoformat()
        with self._connect() as db:
            db.execute(
                "INSERT INTO temporal_facts (subject, fact, observed_at, valid_until, confidence) VALUES (?, ?, ?, ?, ?)",
                (subject, fact, observed, valid_until, confidence),
            )
            db.execute("DELETE FROM temporal_facts WHERE id NOT IN (SELECT id FROM temporal_facts ORDER BY id DESC LIMIT 1000)")

    def relevant(self, query: str, limit: int = 6) -> list[dict[str, Any]]:
        terms = {w.lower() for w in re.findall(r"[\wÀ-ÿ]+", str(query)) if len(w) >= 4}
        with self._connect() as db:
            rows = db.execute(
                "SELECT subject, fact, observed_at, valid_until, confidence FROM temporal_facts ORDER BY id DESC LIMIT 500"
            ).fetchall()
        ranked: list[tuple[float, dict[str, Any]]] = []
        now = datetime.now(timezone.utc)
        for row in rows:
            item = dict(row)
            expires = self._parse_time(item.get("valid_until"))
            if expires is not None and expires <= now:
                continue
            haystack = f"{item['subject']} {item['fact']}".lower()
            overlap = sum(1 for term in terms if term in haystack)
            if not overlap:
                continue
            observed = self._parse_time(item["observed_at"])
            if observed is None:
                continue
            age_days = max(0.0, (now - observed).total_seconds() / 86400)
            freshness = 1.0 / (1.0 + age_days / 30.0)
            score = overlap * 3 + float(item["confidence"]) + freshness
            ranked.append((score, item))
        ranked.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in ranked[:max(1, limit)]]

    def context(self, query: str, limit: int = 6) -> str:
        items = self.relevant(query, limit)
        if not items:
            return ""
        lines = ["MEMÓRIA TEMPORAL RELEVANTE:"]
        for item in items:
            expiry = f"; válido até {item['valid_until']}" if item.get("valid_until") else ""
            lines.append(f"- [{item['observed_at']}] {item['subject']}: {item['fact']}{expiry}")
        lines.append("Considere a data de observação e validade. Informação temporalmente sensível deve ser confirmada quando necessário.")
        return "\n".join(lines)
