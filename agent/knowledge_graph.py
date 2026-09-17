"""Grafo local de relações aprendidas pelo Super Cérebro."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any


class KnowledgeGraph:
    """Mantém entidades e relações simples entre conceitos importantes."""

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
            db.execute("""CREATE TABLE IF NOT EXISTS knowledge_edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                relation TEXT NOT NULL,
                object TEXT NOT NULL,
                confidence REAL NOT NULL DEFAULT 0.5,
                uses INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(subject, relation, object)
            )""")

    @staticmethod
    def _clean(value: str, limit: int = 180) -> str:
        return re.sub(r"\s+", " ", str(value).strip())[:limit]

    def add(self, subject: str, relation: str, obj: str, confidence: float = 0.7) -> None:
        subject, relation, obj = self._clean(subject), self._clean(relation, 100), self._clean(obj)
        if not subject or not relation or not obj:
            return
        confidence = max(0.0, min(1.0, float(confidence)))
        with self._connect() as db:
            db.execute("""INSERT INTO knowledge_edges (subject, relation, object, confidence)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(subject, relation, object) DO UPDATE SET
                    confidence = MAX(knowledge_edges.confidence, excluded.confidence),
                    uses = knowledge_edges.uses + 1,
                    updated_at = CURRENT_TIMESTAMP""", (subject, relation, obj, confidence))

    def related(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        terms = {w.lower() for w in re.findall(r"[\wÀ-ÿ]+", str(query)) if len(w) >= 4}
        if not terms:
            return []
        with self._connect() as db:
            rows = db.execute("SELECT subject, relation, object, confidence, uses FROM knowledge_edges ORDER BY updated_at DESC LIMIT 1000").fetchall()
        ranked: list[tuple[float, dict[str, Any]]] = []
        for row in rows:
            item = dict(row)
            text = f"{item['subject']} {item['relation']} {item['object']}".lower()
            overlap = sum(1 for term in terms if term in text)
            if overlap:
                score = overlap * 3 + item["confidence"] + min(2.0, item["uses"] * 0.1)
                ranked.append((score, item))
        ranked.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in ranked[:max(1, limit)]]

    def context(self, query: str, limit: int = 8) -> str:
        edges = self.related(query, limit)
        if not edges:
            return ""
        lines = ["RELAÇÕES CONHECIDAS RELEVANTES:"]
        for edge in edges:
            lines.append(f"- {edge['subject']} — {edge['relation']} — {edge['object']}")
        lines.append("Essas relações são memória auxiliar; confirme-as quando a tarefa exigir precisão factual.")
        return "\n".join(lines)
