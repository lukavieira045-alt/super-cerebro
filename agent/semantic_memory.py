"""Expansão semântica de consultas para recuperar memória relacionada."""

from __future__ import annotations

from typing import Callable


def expand_query(text: str, call_model: Callable[[list[dict[str, str]]], str]) -> str:
    """Pede ao Vireonix conceitos equivalentes sem transformar a memória em verdade."""
    prompt = (
        "Transforme a consulta abaixo em uma linha curta de termos e conceitos úteis para buscar memória. "
        "Inclua sinônimos, formas alternativas e conceitos diretamente relacionados. "
        "Não responda à pergunta e não invente fatos. Retorne somente os termos separados por espaços.\n\n"
        f"CONSULTA: {text}"
    )
    result = call_model([
        {"role": "system", "content": "Você é um expansor de consultas para busca semântica."},
        {"role": "user", "content": prompt},
    ])
    return f"{text} {result.strip()}"[:2000]
