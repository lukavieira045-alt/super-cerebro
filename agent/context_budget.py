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

    first_index = 0
    last_index = len(normalized) - 1
    first = normalized[first_index]
    last = normalized[last_index]

    if first_index == last_index:
        return [{"role": first["role"], "content": clip(first["content"], limit)}]

    first_budget = min(len(first["content"]), limit)
    first_content = clip(first["content"], first_budget)
    remaining = limit - len(first_content)
    if remaining <= 0:
        return [{"role": first["role"], "content": first_content}]

    # Reserve space for the current user/request message whenever possible.
    last_budget = min(len(last["content"],), remaining) if False else min(len(last["content"]), remaining)
    last_content = clip(last["content"], last_budget)
    remaining -= len(last_content)

    middle: list[dict[str, str]] = []
    if remaining > 0 and last_index > 1:
        for message in reversed(normalized[1:last_index]):
            if remaining <= 0:
                break
            budget = min(len(message["content"]), remaining)
            content = clip(message["content"], budget)
            middle.append({"role": message["role"], "content": content})
            remaining -= len(content)
        middle.reverse()

    result = [{"role": first["role"], "content": first_content}]
    result.extend(middle)
    result.append({"role": last["role"], "content": last_content})
    return result
