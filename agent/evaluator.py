"""Juiz interno e autocorreção das respostas do Super Cérebro."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class Evaluation:
    score: int
    issues: tuple[str, ...]
    needs_revision: bool


def local_check(question: str, answer: str, had_tools: bool = False) -> Evaluation:
    """Checagem rápida e determinística antes do juiz do Vireonix."""
    text = str(answer).strip()
    issues: list[str] = []
    if not text:
        issues.append("resposta vazia")
    if len(text) < 12:
        issues.append("resposta curta demais")
    if had_tools and re.search(r"\bsegundo (eu|minha) pesquisa\b", text, re.IGNORECASE):
        issues.append("evidência descrita de forma vaga")
    score = max(0, 100 - len(issues) * 30)
    return Evaluation(score, tuple(issues), score < 70)


def judge_with_vireonix(question: str, answer: str, call_model: Callable[[list[dict[str, str]]], str]) -> Evaluation:
    """Usa o próprio Vireonix como juiz, sem adicionar outro modelo."""
    prompt = (
        "Avalie rigorosamente a resposta. Considere atendimento ao pedido, correção, "
        "coerência, completude, evidências e ausência de invenções. "
        "Responda SOMENTE JSON válido no formato "
        '{"score":0,"approved":true,"issues":[]}.\n\n'
        f"PEDIDO:\n{question}\n\nRESPOSTA:\n{answer}"
    )
    try:
        raw = call_model([
            {"role": "system", "content": "Você é o juiz interno de qualidade do Super Cérebro. Seja rigoroso e conservador."},
            {"role": "user", "content": prompt},
        ])
        data = json.loads(raw)
        score = max(0, min(100, int(data.get("score", 0))))
        approved = bool(data.get("approved", score >= 80))
        raw_issues = data.get("issues", [])
        issues = tuple(str(item) for item in raw_issues[:6]) if isinstance(raw_issues, list) else ()
        return Evaluation(score, issues, not approved or score < 80)
    except (RuntimeError, TypeError, ValueError, json.JSONDecodeError, AttributeError):
        return Evaluation(100, (), False)


def revision_instruction(evaluation: Evaluation) -> str:
    if not evaluation.needs_revision:
        return ""
    issues = "\n".join(f"- {issue}" for issue in evaluation.issues) or "- qualidade insuficiente segundo a avaliação interna"
    return (
        "AUTOCORREÇÃO NECESSÁRIA. Revise a resposta preliminar.\n"
        f"Problemas detectados pelo juiz interno:\n{issues}\n"
        "Reescreva usando somente as informações e evidências disponíveis. "
        "Corrija os problemas sem inventar dados. Entregue somente a versão final corrigida."
    )
