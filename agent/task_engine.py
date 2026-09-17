"""Orquestrador de tarefas compostas do Super Cérebro."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class TaskStep:
    """Registro de uma etapa executada pelo agente."""

    number: int
    tool: str
    arguments: dict[str, Any]
    result: str
    ok: bool


class TaskEngine:
    """Executa uma cadeia limitada de ferramentas e mantém seu histórico."""

    def __init__(self, max_steps: int = 8) -> None:
        self.max_steps = max(1, min(int(max_steps), 12))
        self.steps: list[TaskStep] = []

    def reset(self) -> None:
        self.steps.clear()

    def has_repeated_request(self, tool: str, arguments: dict[str, Any]) -> bool:
        """Detecta uma solicitação idêntica já executada para evitar loops improdutivos."""
        try:
            target = json.dumps(arguments, sort_keys=True, ensure_ascii=False)
        except (TypeError, ValueError):
            target = repr(arguments)
        for step in self.steps:
            try:
                previous = json.dumps(step.arguments, sort_keys=True, ensure_ascii=False)
            except (TypeError, ValueError):
                previous = repr(step.arguments)
            if step.tool == tool and previous == target:
                return True
        return False

    def execute(
        self,
        tool: str,
        arguments: dict[str, Any],
        runner: Callable[[str, dict[str, Any]], str],
    ) -> str:
        """Executa uma ferramenta, registra a etapa e retorna seu resultado."""
        if len(self.steps) >= self.max_steps:
            raise RuntimeError("limite de etapas da tarefa atingido")

        number = len(self.steps) + 1
        try:
            result = runner(tool, arguments)
            self.steps.append(TaskStep(number, tool, arguments, str(result), True))
            return str(result)
        except Exception as exc:
            result = f"ERRO DA FERRAMENTA: {exc}"
            self.steps.append(TaskStep(number, tool, arguments, result, False))
            return result

    def trace_text(self) -> str:
        """Resume as etapas para o Vireonix verificar o trabalho realizado."""
        if not self.steps:
            return "Nenhuma ferramenta foi executada."
        lines = []
        for step in self.steps:
            status = "OK" if step.ok else "ERRO"
            lines.append(f"ETAPA {step.number} [{status}] {step.tool}: {step.result}")
        return "\n\n".join(lines)

    def strategy_summary(self) -> str:
        """Produz uma sequência compacta reutilizável como experiência."""
        return " -> ".join(f"{step.tool}={'ok' if step.ok else 'erro'}" for step in self.steps)

    def all_successful(self) -> bool:
        """Indica se todas as ferramentas executadas terminaram sem erro."""
        return bool(self.steps) and all(step.ok for step in self.steps)
