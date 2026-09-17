"""Vireonix-powered intelligence core for Super Cérebro."""

from __future__ import annotations

import requests

from .intelligence import build_system_prompt
from .memory import Memory

VIREONIX_URL = "https://vireonix.ai/v1/chat/completions"
MODEL = "auto"


class SuperCerebro:
    """Interface para o Vireonix com memória persistente local."""

    def __init__(self, timeout: int = 120, memory: Memory | None = None) -> None:
        self.timeout = timeout
        self.memory = memory or Memory()
        self.messages: list[dict[str, str]] = [
            {"role": "system", "content": build_system_prompt()}
        ]

    def _build_context(self, text: str) -> list[dict[str, str]]:
        recent = self.memory.recent(limit=12)
        relevant = self.memory.relevant(text, limit=6)

        seen = {(item["role"], item["content"]) for item in recent}
        relevant_unique = [item for item in relevant if (item["role"], item["content"]) not in seen]

        context: list[dict[str, str]] = []
        if relevant_unique:
            context.append({
                "role": "system",
                "content": "Memórias relevantes de conversas anteriores:\n"
                + "\n".join(f"{item['role']}: {item['content']}" for item in relevant_unique),
            })
        context.extend(recent)
        context.append({"role": "user", "content": text})
        return context

    def ask(self, text: str) -> str:
        """Envia uma mensagem usando contexto atual e memória persistente."""
        self.messages = [
            {"role": "system", "content": build_system_prompt()},
            *self._build_context(text),
        ]

        try:
            response = requests.post(
                VIREONIX_URL,
                headers={"Content-Type": "application/json"},
                json={"model": MODEL, "messages": self.messages},
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            answer = data["choices"][0]["message"]["content"]
        except requests.RequestException as exc:
            raise RuntimeError(f"Falha ao conectar ao Vireonix: {exc}") from exc
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise RuntimeError("Resposta inválida recebida do Vireonix.") from exc

        self.memory.add("user", text)
        self.memory.add("assistant", answer)
        return answer


def build_agent() -> SuperCerebro:
    """Cria o núcleo de inteligência do Super Cérebro."""
    return SuperCerebro()
