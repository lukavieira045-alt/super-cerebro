"""Autoaperfeiçoamento local do Super Cérebro."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .learning import Learning


@dataclass(frozen=True)
class Improvement:
    """Diagnóstico simples e acionável de uma execução."""

    success: bool
    strengths: tuple[str, ...]
    weaknesses: tuple[str, ...]
    actions: tuple[str, ...]


class SelfImprovement:
    """Transforma resultados de tarefas em ajustes reutilizáveis de estratégia."""

    def __init__(self, learning: Learning) -> None:
        self.learning = learning

    @staticmethod
    def _clean(text: str, limit: int = 240) -> str:
        return re.sub(r"\s+", " ", str(text).strip())[:limit]

    def analyze(self, task_type: str, trace: list[dict[str, Any]], success: bool, reason: str = "") -> Improvement:
        strengths: list[str] = []
        weaknesses: list[str] = []
        actions: list[str] = []

        if success:
            strengths.append("a execução terminou sem falhas registradas")
            actions.append("reutilizar a estratégia como candidata em tarefas semelhantes")
        else:
            weaknesses.append("a execução apresentou pelo menos uma falha")
            actions.append("evitar repetir cegamente o mesmo caminho")

        failed_tools = [str(step.get("tool")) for step in trace if not step.get("ok")]
        if failed_tools:
            weaknesses.append("falha nas ferramentas: " + ", ".join(failed_tools))
            actions.append("tentar uma alternativa segura antes de repetir a ferramenta que falhou")
        if len(trace) >= 7:
            weaknesses.append("a tarefa consumiu muitas etapas")
            actions.append("procurar uma sequência mais curta em tarefas futuras")
        elif trace:
            strengths.append("a estratégia usou ferramentas de forma rastreável")

        if reason and not success:
            weaknesses.append(self._clean(reason))

        return Improvement(success, tuple(strengths), tuple(weaknesses), tuple(dict.fromkeys(actions)))

    def apply(self, task_type: str, strategy: str, improvement: Improvement) -> None:
        """Registra o diagnóstico para influenciar futuras execuções."""
        self.learning.record(task_type, strategy, improvement.success)
        reason = "; ".join(improvement.weaknesses)
        self.learning.record_experience(task_type, strategy, improvement.success, reason)

    @staticmethod
    def context(improvement: Improvement) -> str:
        parts: list[str] = []
        if improvement.strengths:
            parts.append("Pontos que funcionaram:\n" + "\n".join(f"- {x}" for x in improvement.strengths))
        if improvement.weaknesses:
            parts.append("Pontos a corrigir:\n" + "\n".join(f"- {x}" for x in improvement.weaknesses))
        if improvement.actions:
            parts.append("Ajustes para próximas tarefas:\n" + "\n".join(f"- {x}" for x in improvement.actions))
        return "\n\n".join(parts)
