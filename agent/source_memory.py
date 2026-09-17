"""Memória persistente de fontes e evidências externas."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any

from .source_reliability import score


class SourceMemory:
    """Guarda fontes usadas em pesquisas para permitir rastreabilidade futura."""

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
            db.execute("""CREATE TABLE IF NOT EXISTS source_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                url TEXT NOT NULL,
                title TEXT NOT NULL DEFAULT '',
                summary TEXT NOT NULL DEFAULT '',
                confidence REAL NOT NULL DEFAULT 0.5,
                uses INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(query, url)
            )""")

    @staticmethod
    def _clean(value: str, limit: int) -> str:
        return re.sub(r"\s+", " ", str(value).strip())[:limit]

    def record(self, query: str, url: str, title: str = "", summary: str = "", confidence: float = 0.7) -> None:
        query = self._clean(query, 300)
        url = self._clean(url, 1000)
        title = self._clean(title, 300)
        summary = self._clean(summary, 1000)
        if not query or not url:
            return
        structural = score(url, title, summary)
        confidence = max(0.0, min(1.0, float(confidence)))
        confidence = round((confidence + structural.score) / 2, 2)
        with self._connect() as db:
            db.execute("""INSERT INTO source_memory (query, url, title, summary, confidence)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(query, url) DO UPDATE SET
                    title = CASE WHEN excluded.title != '' THEN excluded.title ELSE source_memory.title END,
                    summary = CASE WHEN excluded.summary != '' THEN excluded.summary ELSE source_memory.summary END,
                    confidence = MAX(source_memory.confidence, excluded.confidence),
                    uses = source_memory.uses + 1,
                    updated_at = CURRENT_TIMESTAMP""", (query, url, title, summary, confidence))
            db.execute("DELETE FROM source_memory WHERE id NOT IN (SELECT id FROM source_memory ORDER BY id DESC LIMIT 1000)")

    def relevant(self, query: str, limit: int = 6) -> list[dict[str, Any]]:
        terms = {w.lower() for w in re.findall(r"[\wÀ-ÿ]+", str(query)) if len(w) >= 4}
        with self._connect() as db:
            rows = db.execute("SELECT query, url, title, summary, confidence, uses, updated_at FROM source_memory ORDER BY updated_at DESC LIMIT 1000").fetchall()
        ranked: list[tuple[float, dict[str, Any]]] = []
        for row in rows:
            item = dict(row)
            haystack = f"{item['query']} {item['title']} {item['summary']}".lower()
            overlap = sum(1 for term in terms if term in haystack)
            if not overlap:
                continue
            score_value = overlap * 3 + float(item['confidence']) + min(2.0, item['uses'] * 0.1)
            ranked.append((score_value, item))
        ranked.sort(key=lambda pair: pair[0], reverse=True)
        return [item for _, item in ranked[:max(1, limit)]]

    def context(self, query: str, limit: int = 6) -> str:
        items = self.relevant(query, limit)
        if not items:
            return ""
        lines = ["FONTES CONHECIDAS RELEVANTES:"]
        for item in items:
            label = item["title"] or item["url"]
            lines.append(f"- {label} | {item['url']} | confiança estrutural registrada: {item['confidence']:.2f}")
            if item["summary"]:
                lines.append(f"  Resumo: {item['summary']}")
        lines.append("A pontuação é apenas um sinal estrutural. Não trate domínio ou pontuação como prova automática. Fontes antigas são pistas e informações sensíveis ao tempo devem ser confirmadas.")
        return "\n".join(lines)
