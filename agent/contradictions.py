"""Detecção conservadora de possíveis contradições na memória."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Contradiction:
    older: str
    newer: str
    reason: str


def _terms(text: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[\wÀ-ÿ]+", str(text)) if len(w) >= 4}


def detect(items: list[dict], limit: int = 8) -> list[Contradiction]:
    """Sinaliza mudanças aparentes para o modelo revisar, sem decidir qual é verdadeira."""
    results: list[Contradiction] = []
    normalized = [str(item.get("fact", item.get("content", ""))).strip() for item in items]
    normalized = [x for x in normalized if x]
    for index, older in enumerate(normalized):
        for newer in normalized[index + 1:]:
            left, right = _terms(older), _terms(newer)
            if not left or not right:
                continue
            overlap = len(left & right) / max(1, len(left | right))
            if overlap < 0.35:
                continue
            negative_change = bool(re.search(r"\b(não|nao|nunca|deixou|parou|acabou|mudou)\b", newer, re.I)) != bool(re.search(r"\b(não|nao|nunca|deixou|parou|acabou|mudou)\b", older, re.I))
            if negative_change or overlap >= 0.65:
                results.append(Contradiction(older, newer, "há sobreposição de assunto e possível mudança de estado"))
                if len(results) >= limit:
                    return results
    return results


def context(items: list[dict], limit: int = 8) -> str:
    found = detect(items, limit)
    if not found:
        return ""
    lines = ["POSSÍVEIS CONTRADIÇÕES NA MEMÓRIA:"]
    for item in found:
        lines.append(f"- Registro A: {item.older}\n  Registro B: {item.newer}\n  Sinal: {item.reason}")
    lines.append("Não escolha automaticamente entre registros conflitantes. Priorize evidência mais recente e verificável, ou peça confirmação quando necessário.")
    return "\n".join(lines)
