"""Calibração de confiança das respostas do Super Cérebro."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Confidence:
    score: float
    level: str
    reasons: tuple[str, ...]


def estimate(answer: str, tool_steps: int, verified_research: bool = False) -> Confidence:
    """Estima confiança de forma conservadora, sem fingir certeza factual."""
    text = str(answer).strip()
    score = 0.55
    reasons: list[str] = []

    if not text:
        return Confidence(0.0, "baixa", ("resposta vazia",))

    if verified_research:
        score += 0.18
        reasons.append("pesquisa passou pela camada de verificação")
    if tool_steps:
        score += 0.05
        reasons.append("houve execução rastreável de ferramentas")
    if re.search(r"\b(não sei|não foi possível confirmar|não confirmado|incerto)\b", text, re.I):
        score -= 0.12
        reasons.append("a própria resposta registra incerteza")
    if re.search(r"\b(100%|com certeza absoluta|sem dúvida nenhuma)\b", text, re.I):
        score -= 0.10
        reasons.append("linguagem de certeza excessiva")

    score = max(0.0, min(0.95, score))
    level = "alta" if score >= 0.78 else "média" if score >= 0.55 else "baixa"
    return Confidence(round(score, 2), level, tuple(reasons))


def prompt(confidence: Confidence) -> str:
    """Instrui o Vireonix a calibrar a linguagem da resposta."""
    return (
        "CALIBRAÇÃO DE CONFIANÇA.\n"
        f"Nível estimado: {confidence.level}; índice interno: {confidence.score:.2f}.\n"
        f"Motivos: {', '.join(confidence.reasons) or 'nenhum sinal adicional'}.\n"
        "Não aumente artificialmente a certeza. Se a evidência for limitada, use linguagem proporcional e "
        "indique o que precisaria ser confirmado. Não revele este índice interno ao usuário."
    )
