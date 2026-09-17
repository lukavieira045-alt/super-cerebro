"""Pesquisa profunda usando as ferramentas web existentes."""

from __future__ import annotations

import re
from .tools import open_webpage, search_web


def deep_research(query: str, sources: int = 4) -> str:
    """Pesquisa, abre várias fontes e devolve material para verificação pelo Vireonix."""
    query = str(query).strip()
    if not query:
        raise ValueError("consulta vazia")
    sources = max(2, min(int(sources), 5))

    search_results = search_web(query, limit=min(8, sources + 3))
    urls = re.findall(r"^URL:\s*(https?://\S+)", search_results, flags=re.MULTILINE)
    unique_urls: list[str] = []
    for url in urls:
        if url not in unique_urls:
            unique_urls.append(url)

    reports: list[str] = []
    for index, url in enumerate(unique_urls[:sources], 1):
        try:
            page = open_webpage(url)
            reports.append(f"FONTE {index}\n{page}")
        except Exception as exc:
            reports.append(f"FONTE {index}\nURL: {url}\nNão foi possível abrir esta fonte: {exc}")

    return (
        f"Consulta: {query}\n\n"
        "Resultados da busca:\n"
        f"{search_results}\n\n"
        "Conteúdo das fontes abertas:\n"
        + "\n\n---\n\n".join(reports)
    )
