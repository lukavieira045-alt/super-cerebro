"""Proveniência das informações armazenadas pelo Super Cérebro."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any


class Provenance:
    """Registra de onde veio uma informação para evitar tratar inferência como fato."""

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
            db.execute("""CREATE TABLE IF NOT EXISTS provenance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                claim TEXT NOT NULL,
                source_type TEXT NOT NULL,
                source_ref TEXT NOT NULL DEFAULT '',
                confidence REAL NOT NULL DEFAULT 0.5,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")

    @staticmethod
    def _clean(value: str, limit: int = 500) -> str:
        return re.sub(r"\s+", " ", str(value).strip())[:limit]

    def record(self, subject: str, claim: str, source_type: str, source_ref: str = "", confidence: float = 0.5) -> None:
        subject, claim, source_type, source_ref = self._clean(subject, 180), self._clean(claim), self._clean(source_type, 80), self._clean(source_ref, 500)
        if not subject or not claim or not source_type:
            return
        confidence = max(0.0, min(1.0, float(confidence)))
        with self._connect() as db:
            db.execute("INSERT INTO provenance (subject, claim, source_type, source_ref, confidence) VALUES (?, ?, ?, ?, ?)", (subject, claim, source_type, source_ref, confidence))
            db.execute("DELETE FROM provenance WHERE id NOT IN (SELECT id FROM provenance ORDER BY id DESC LIMIT 1500)")

    def relevant(self, query: str, limit: int = 8) -> list[dict[str, Any]]:
        terms = {w.lower() for w in re.findall(r"[\wÀ-ÿ]+", str(query)) if len(w) >= 4}
        if not terms:
            return []
        with self._connect() as db:
            rows = db.execute("SELECT subject, claim, source_type, source_ref, confidence, created_at FROM provenance ORDER BY id DESC LIMIT 800").fetchall()
        ranked = []
        for row in rows:
            item = dict(row)
            haystack = f"{item['subject']} {item['claim']}".lower()
            overlap = sum(1 for term in terms if term in haystack)
            if overlap:
                score = overlap * 3 + float(item['confidence'])
                ranked.append((score, item))
        ranked.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in ranked[:max(1, limit)]]

    def context(self, query: str, limit: int = 6) -> str:
        items = self.relevant(query, limit)
        if not items:
            return ""
        lines = ["PROVENIÊNCIA DAS INFORMAÇÕES RELEVANTES:"]
        for item in items:
            ref = f" ({item['source_ref']})" if item["source_ref"] else ""
            lines.append(f"- {item['subject']}: {item['claim']} | origem: {item['source_type']}{ref} | confiança registrada: {item['confidence']:.2f}")
        lines.append("Não trate inferências do modelo como fatos confirmados. Considere a origem e a confiança antes de reutilizar uma informação.")
        return "\n".join(lines)
