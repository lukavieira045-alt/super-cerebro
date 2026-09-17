"""Verificação de evidências para pesquisas do Super Cérebro."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class EvidenceReport:
    sources: int
    usable_sources: int
    conflicts: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def reliable_enough(self) -> bool:
        return self.usable_sources >= 2 and not self.conflicts


def _source_blocks(research: str) -> list[str]:
    return re.split(r"\n---\n", str(research))


def inspect_research(research: str) -> EvidenceReport:
    """Faz uma checagem estrutural antes de o modelo interpretar a pesquisa."""
    blocks = [block.strip() for block in _source_blocks(research) if block.strip()]
    usable = [block for block in blocks if len(block) >= 120]
    warnings: list[str] = []
    conflicts: list[str] = []

    if len(usable) < 2:
        warnings.append("há poucas fontes com conteúdo suficiente para comparação")
    if any("Não foi possível abrir esta fonte" in block for block in blocks):
        warnings.append("uma ou mais fontes não puderam ser abertas")

    # Sinaliza divergências explícitas sem tentar decidir qual fonte está correta.
    if re.search(r"\b(?:porém|por outro lado|diverge|contradiz|diferente de)\b", research, re.I):
        conflicts.append("o material contém sinais de divergência entre fontes")

    return EvidenceReport(len(blocks), len(usable), tuple(conflicts), tuple(warnings))


def verification_prompt(research: str, report: EvidenceReport) -> str:
    """Gera instruções para o Vireonix comparar as evidências sem inventar consenso."""
    return (
        "VERIFICAÇÃO DE EVIDÊNCIAS.\n"
        f"Fontes encontradas: {report.sources}. Fontes utilizáveis: {report.usable_sources}.\n"
        f"Alertas: {', '.join(report.warnings) or 'nenhum alerta estrutural'}.\n"
        f"Conflitos detectados: {', '.join(report.conflicts) or 'nenhum conflito explícito detectado'}.\n\n"
        "Compare as fontes individualmente. Não trate quantidade de fontes como prova automática. "
        "Diferencie fato diretamente sustentado, interpretação e informação não confirmada. "
        "Quando houver conflito, mostre a divergência e atribua cada posição à sua fonte. "
        "Não invente uma fonte, data, número ou consenso.\n\n"
        f"MATERIAL PESQUISADO:\n{research}"
    )


def verify_with_model(
    research: str,
    call_model: Callable[[list[dict[str, str]]], str],
) -> str:
    """Entrega o material ao Vireonix para verificação final das evidências."""
    report = inspect_research(research)
    return call_model([
        {"role": "system", "content": "Você é um verificador de evidências. Seja rigoroso e não invente fontes."},
        {"role": "user", "content": verification_prompt(research, report)},
    ]).strip()
