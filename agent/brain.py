"""Vireonix-powered intelligence core for Super Cérebro."""

from __future__ import annotations

import json
import requests

from .intelligence import build_system_prompt
from .memory import Memory

VIREONIX_URL = "https://vireonix.ai/v1/chat/completions"
MODEL = "auto"


class SuperCerebro:
    """Interface para o Vireonix com memória persistente e aprendizado estruturado."""

    def __init__(self, timeout: int = 120, memory: Memory | None = None) -> None:
        self.timeout = timeout
        self.memory = memory or Memory()
        self.messages: list[dict[str, str]] = []

    def _build_context(self, text: str) -> list[dict[str, str]]:
        recent = self.memory.recent(limit=12)
        relevant = self.memory.relevant(text, limit=6)
        facts = self.memory.relevant_facts(text, limit=8)

        seen = {(item["role"], item["content"]) for item in recent}
        relevant_unique = [item for item in relevant if (item["role"], item["content"]) not in seen]

        context: list[dict[str, str]] = []
        if facts:
            context.append({
                "role": "system",
                "content": "Memórias de longo prazo confirmadas:\n"
                + "\n".join(f"[{item['category']}] {item['fact']}" for item in facts),
            })
        if relevant_unique:
            context.append({
                "role": "system",
                "content": "Conversas anteriores relevantes:\n"
                + "\n".join(f"{item['role']}: {item['content']}" for item in relevant_unique),
            })
        context.extend(recent)
        context.append({"role": "user", "content": text})
        return context

    def _extract_facts(self, user_text: str, answer: str) -> None:
        """Ask Vireonix for durable facts in a small structured pass."""
        prompt = (
            "Extraia somente fatos duradouros e úteis para futuras conversas. "
            "Não invente nada e não salve senhas, tokens, chaves, dados bancários "
            "ou informações extremamente sensíveis. Responda SOMENTE com JSON em "
            "uma lista, no formato [{\"category\":\"...\",\"fact\":\"...\",\"importance\":1}]. "
            "Se não houver fatos úteis, responda [].\n\n"
            f"Usuário: {user_text}\nResposta: {answer}"
        )
        try:
            response = requests.post(
                VIREONIX_URL,
                headers={"Content-Type": "application/json"},
                json={
                    "model": MODEL,
                    "messages":[
                        {"role": "system", "content": "Você é um extrator de memória. Seja conservador."},
                        {"role": "user", "content": prompt},
                    ],
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            facts = json.loads(content)
            if not isinstance(facts, list):
                return
            for item in facts[:5]:
                if isinstance(item, dict) and item.get("fact"):
                    self.memory.remember_fact(
                        str(item.get("category", "geral")),
                        str(item["fact"]),
                        int(item.get("importance", 2)),
                    )
        except (requests.RequestException, KeyError, IndexError, TypeError, ValueError):
            # Memory extraction must never prevent the main answer.
            return

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
        self._extract_facts(text, answer)
        return answer


def build_agent() -> SuperCerebro:
    """Cria o núcleo de inteligência do Super Cérebro."""
    return SuperCerebro()
