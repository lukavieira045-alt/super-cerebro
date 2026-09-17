"""Limitação inteligente do contexto enviado ao modelo."""

from __future__ import annotations

from typing import Mapping


def bound_messages(messages: list[Mapping[str, str]], limit: int, clip) -> list[dict[str, str]]:
    """Preserva instruções iniciais e a mensagem atual, descartando contexto antigo primeiro."""
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

    # Sempre reserva uma parte do orçamento para a mensagem atual.
    last_reserve = min(len(last["content"]), max(1, limit // 4))
    first_budget = max(0, limit - last_reserve)
    first_content = clip(first["content"], first_budget)
    remaining = limit - len(first_content)

    last_budget = min(len(last["content"]), remaining)
    last_content = clip(last["content"], last_budget)
    remaining -= len(last_content)

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
