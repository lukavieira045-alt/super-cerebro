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

    _GENERIC_TERMS = {
        "analisar", "analise", "análise", "criar", "crie", "corrigir", "corrija",
        "desenvolver", "desenvolva", "explicar", "explique", "encontrar", "encontre",
        "pesquisar", "pesquise", "pesquisa", "verificar", "verifique", "verificação",
        "objetivo", "tarefa", "fazer", "faça", "continuar", "continue",
    }

    @classmethod
    def _words(cls, text: str) -> set[str]:
        return {
            w.lower()
            for w in re.findall(r"[\wÀ-ÿ]+", str(text))
            if len(w) >= 4 and w.lower() not in cls._GENERIC_TERMS
        }

    @staticmethod
    def _stems(words: set[str]) -> set[str]:
        """Cria sinais simples para reconhecer pequenas variações morfológicas em português."""
        return {word[:6] for word in words if len(word) >= 6}

    @staticmethod
    def is_explicit_completion(text: str) -> bool:
        """Reconhece somente comandos claros de encerramento, evitando conclusão automática ambígua."""
        normalized = re.sub(r"\s+", " ", str(text).strip().lower())
        patterns = (
            r"\bobjetivo\s+(?:est[aá]|foi)\s+conclu[ií]d[oa]\b",
            r"\bobjetivo\s+conclu[ií]d[oa]\b",
            r"\b(?:pode|vamos)\s+(?:finalizar|encerrar|concluir)\s+(?:esse|este|o)\s+objetivo\b",
            r"\b(?:finalize|encerre|conclua)\s+(?:esse|este|o)\s+objetivo\b",
        )
        return any(re.search(pattern, normalized) for pattern in patterns)

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

    def complete_active(self, text: str, progress: str = "Concluído.") -> int | None:
        """Conclui o objetivo ativo relacionado à mensagem, somente com comando explícito."""
        if not self.is_explicit_completion(text):
            return None
        related = self.active_for(text, limit=1)
        if not related:
            active = self.active(limit=1)
            related = active[:1]
        if not related:
            return None
        goal_id = int(related[0]["id"])
        self.complete(goal_id, progress)
        return goal_id

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
        """Encontra objetivos relacionados mesmo com pequenas variações das palavras."""
        words = self._words(text)
        if not words:
            return []
        stems = self._stems(words)
        candidates = self.active(20)
        scored: list[tuple[int, int, dict[str, Any]]] = []
        for goal in candidates:
            goal_words = self._words(goal["title"])
            exact = len(words & goal_words)
            stem_overlap = len(stems & self._stems(goal_words))
            overlap = exact * 2 + stem_overlap
            if overlap:
                scored.append((overlap, int(goal["id"]), goal))
        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [goal for _, _, goal in scored[:limit]]
