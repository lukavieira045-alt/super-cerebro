"""Avaliação e autocorreção das respostas do Super Cérebro."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Evaluation:
    score: int
    issues: tuple[str, ...]
    needs_revision: bool


def evaluate(question: str, answer: str, had_tools: bool = False) -> Evaluation:
    """Faz uma checagem local barata antes da revisão pelo Vireonix."""
    text = str(answer).strip()
    issues: list[str] = []

    if not text:
        issues.append("resposta vazia")
    if len(text) < 12:
        issues.append("resposta curta demais para a tarefa")
    if re.search(r"\b(não sei|nao sei)\b", text, re.IGNORECASE) and len(question.split()) > 8:
        issues.append("resposta admite falta de informação sem tentar verificar")
    if had_tools and re.search(r"\bsegundo (eu|minha) pesquisa\b", text, re.IGNORECASE):
        issues.append("linguagem vaga sobre evidências")

    score = max(0, 100 - len(issues) * 25)
    return Evaluation(score, tuple(issues), score < 75)


def revision_instruction(evaluation: Evaluation) -> str:
    if not evaluation.needs_revision:
        return ""
    issues = "\n".join(f"- {issue}" for issue in evaluation.issues)
    return (
        "AUTOCORREÇÃO NECESSÁRIA. A resposta preliminar apresentou sinais de baixa qualidade.\n"
        f"Problemas detectados:\n{issues}\n"
        "Reescreva a resposta usando as evidências disponíveis, sem inventar informações. "
        "Entregue somente a versão corrigida."
    )
