"""Planejamento determinístico para tarefas complexas do Super Cérebro."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Plan:
    """Plano simples e verificável antes da execução."""

    complex: bool
    steps: tuple[str, ...]


_COMPLEX_MARKERS = {
    "pesquise", "pesquisar", "investigue", "investigar", "compare", "comparar",
    "analise", "analisar", "crie", "criar", "desenvolva", "desenvolver",
    "implemente", "implementar", "corrija", "corrigir", "encontre", "encontrar",
    "configure", "configurar",
}


def _terms(text: str) -> set[str]:
    return {word.lower() for word in re.findall(r"[\wÀ-ÿ]+", text) if len(word) >= 4}


def make_plan(text: str) -> Plan:
    """Classifica a tarefa e cria etapas genéricas sem substituir o Vireonix."""
    terms = _terms(text)
    complex_task = len(terms) >= 10 or bool(terms & _COMPLEX_MARKERS)
    if not complex_task:
        return Plan(False, ("entender e responder",))

    steps = ["entender objetivo e restrições"]
    if terms & {"pesquise", "pesquisar", "investigue", "investigar", "encontre", "encontrar"}:
        steps.append("pesquisar e reunir evidências")
    if terms & {"compare", "comparar", "analise", "analisar"}:
        steps.append("comparar e analisar as evidências")
    if terms & {"crie", "criar", "desenvolva", "desenvolver", "implemente", "implementar", "corrija", "corrigir", "configure", "configurar"}:
        steps.append("executar as ações necessárias")
    steps.append("verificar resultado e inconsistências")
    steps.append("entregar a resposta final")
    return Plan(True, tuple(dict.fromkeys(steps)))


def format_plan(plan: Plan) -> str:
    """Formata o plano para o contexto do modelo."""
    if not plan.complex:
        return "Tarefa simples: responda diretamente."
    return "Plano inicial (pode ser ajustado conforme os resultados):\n" + "\n".join(
        f"{index}. {step}" for index, step in enumerate(plan.steps, 1)
    )
