"""Limitação inteligente do contexto enviado ao modelo."""

from __future__ import annotations

from typing import Mapping


def bound_messages(messages: list[Mapping[str, str]], limit: int, clip) -> list[dict[str, str]]:
    """Preserva a mensagem atual e mantém o orçamento estritamente limitado."""
    limit = max(1, int(limit))
    normalized = [
        {"role": str(message.get("role", "system")), "content": str(message.get("content", ""))}
        for message in messages
    ]
    if not normalized:
        return []

    def safe_clip(text: str, budget: int) -> str:
        budget = max(0, int(budget))
        if budget <= 0:
            return ""
        result = str(clip(text, budget))
        return result if len(result) <= budget else result[:budget]

    first = normalized[0]
    last = normalized[-1]
    if len(normalized) == 1:
        return [{"role": first["role"], "content": safe_clip(first["content"], limit)}]

    # A mensagem atual tem prioridade máxima. Se couber, ela é preservada inteira.
    last_budget = min(len(last["content"]), limit)
    last_content = safe_clip(last["content"], last_budget)
    remaining = limit - len(last_content)

    # Depois preservamos o início das instruções do sistema.
    first_budget = min(len(first["content"]), remaining)
    first_content = safe_clip(first["content"], first_budget)
    remaining -= len(first_content)

    # O espaço restante é preenchido pelo contexto intermediário mais recente.
    middle: list[dict[str, str]] = []
    if remaining > 0:
        for message in reversed(normalized[1:-1]):
            if remaining <= 0:
                break
            budget = min(len(message["content"]), remaining)
            content = safe_clip(message["content"], budget)
            if content:
                middle.append({"role": message["role"], "content": content})
                remaining -= len(content)
        middle.reverse()

    result: list[dict[str, str]] = []
    if first_content:
        result.append({"role": first["role"], "content": first_content})
    result.extend(middle)
    if last_content:
        result.append({"role": last["role"], "content": last_content})
    return result
