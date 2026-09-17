"""Avaliação estrutural da confiabilidade de fontes."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class SourceScore:
    score: float
    reasons: tuple[str, ...]


def score(url: str, title: str = "", summary: str = "") -> SourceScore:
    """Gera um sinal conservador de qualidade; não trata o domínio como prova."""
    parsed = urlparse(str(url))
    value = 0.45
    reasons: list[str] = []
    host = (parsed.hostname or "").lower()

    if parsed.scheme == "https":
        value += 0.08
        reasons.append("usa HTTPS")
    if host.endswith(".gov.br") or host.endswith(".gov"):
        value += 0.12
        reasons.append("domínio governamental")
    elif host.endswith(".edu") or host.endswith(".edu.br"):
        value += 0.10
        reasons.append("domínio educacional")
    elif host.endswith(".org"):
        value += 0.03
        reasons.append("domínio organizacional")
    if title.strip():
        value += 0.04
        reasons.append("possui título identificado")
    if len(summary.strip()) >= 120:
        value += 0.08
        reasons.append("há conteúdo suficiente para inspeção")
    return SourceScore(round(max(0.0, min(0.9, value)), 2), tuple(reasons))
