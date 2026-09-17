"""Limitação inteligente do contexto enviado ao modelo."""

from __future__ import annotations

from typing import Mapping


def bound_messages(messages: list[Mapping[str, str]], limit: int, clip) -> list[dict[str, str]]:
    """Preserva a mensagem atual sempre que ela couber e descarta contexto antigo primeiro."""
    limit = max(1, int(limit))
    normalized = [
        {"role": str(message.get("role", "system")), "content": str(message.get("content", ""))}
        for message in messages
    ]
    if not normalized:
        return []

    first = normalized[0]
    last = normalized[-1]
    if len(normalized) == 1:
        return [{"role": first["role"], "content": clip(first["content"], limit)}]

    # A mensagem atual tem prioridade máxima: se couber, preserva seu conteúdo inteiro.
    last_budget = min(len(last["content"]), limit)
    last_content = clip(last["content"], last_budget)
    remaining = limit - len(last_content)

    # Depois preserva as instruções iniciais, usando somente o espaço restante.
    first_budget = min(len(first["content"]), remaining)
    first_content = clip(first["content"], first_budget)
    remaining -= len(first_content)

    # Por fim, preenche o orçamento com o contexto intermediário mais recente.
    middle: list[dict[str, str]] = []
    if remaining > 0:
        for message in reversed(normalized[1:-1]):
            if remaining <= 0:
                break
            budget = min(len(message["content"]), remaining)
            content = clip(message["content"], budget)
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
