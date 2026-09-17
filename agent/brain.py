"""Núcleo de inteligência do Super Cérebro usando somente Vireonix."""

from __future__ import annotations

import json
import requests

from .intelligence import build_system_prompt
from .memory import Memory
from .tools import TOOL_DESCRIPTIONS, execute_tool

VIREONIX_URL = "https://vireonix.ai/v1/chat/completions"
MODEL = "auto"
MAX_TOOL_STEPS = 4


class SuperCerebro:
    """Vireonix + memória persistente + execução controlada de ferramentas."""

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
            context.append({"role": "system", "content": "Memórias de longo prazo confirmadas:\n" + "\n".join(f"[{item['category']}] {item['fact']}" for item in facts)})
        if relevant_unique:
            context.append({"role": "system", "content": "Conversas anteriores relevantes:\n" + "\n".join(f"{item['role']}: {item['content']}" for item in relevant_unique)})
        context.extend(recent)
        context.append({"role": "user", "content": text})
        return context

    def _call_vireonix(self, messages: list[dict[str, str]]) -> str:
        try:
            response = requests.post(
                VIREONIX_URL,
                headers={"Content-Type": "application/json"},
                json={"model": MODEL, "messages": messages},
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except requests.RequestException as exc:
            raise RuntimeError(f"Falha ao conectar ao Vireonix: {exc}") from exc
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise RuntimeError("Resposta inválida recebida do Vireonix.") from exc

    @staticmethod
    def _parse_tool_request(answer: str) -> dict | None:
        text = answer.strip()
        if not text.startswith("{") or not text.endswith("}"):
            return None
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return None
        if not isinstance(data, dict) or not isinstance(data.get("tool"), str):
            return None
        if not isinstance(data.get("arguments", {}), dict):
            return None
        return data

    def _extract_facts(self, user_text: str, answer: str) -> None:
        prompt = (
            "Extraia somente fatos duradouros e úteis para futuras conversas. "
            "Não invente nada e não salve senhas, tokens, chaves, dados bancários "
            "ou informações extremamente sensíveis. Responda SOMENTE com JSON em "
            "uma lista, no formato [{\"category\":\"...\",\"fact\":\"...\",\"importance\":1}]. "
            "Se não houver fatos úteis, responda [].\n\n"
            f"Usuário: {user_text}\nResposta: {answer}"
        )
        try:
            content = self._call_vireonix([
                {"role": "system", "content": "Você é um extrator de memória. Seja conservador."},
                {"role": "user", "content": prompt},
            ])
            facts = json.loads(content)
            if not isinstance(facts, list):
                return
            for item in facts[:5]:
                if isinstance(item, dict) and item.get("fact"):
                    self.memory.remember_fact(str(item.get("category", "geral")), str(item["fact"]), int(item.get("importance", 2)))
        except (RuntimeError, KeyError, IndexError, TypeError, ValueError):
            return

    def ask(self, text: str) -> str:
        """Resolve a tarefa e executa ferramentas locais quando necessário."""
        messages: list[dict[str, str]] = [
            {"role": "system", "content": build_system_prompt(TOOL_DESCRIPTIONS)},
            *self._build_context(text),
        ]

        answer = self._call_vireonix(messages)
        for _ in range(MAX_TOOL_STEPS):
            request = self._parse_tool_request(answer)
            if request is None:
                break
            try:
                result = execute_tool(request["tool"], request["arguments"])
            except Exception as exc:
                result = f"ERRO DA FERRAMENTA: {exc}"
            messages.extend([
                {"role": "assistant", "content": answer},
                {"role": "system", "content": f"Resultado da ferramenta {request['tool']}:\n{result}\nAgora continue e responda ao usuário. Se outra ferramenta for necessária, use o JSON exigido."},
            ])
            answer = self._call_vireonix(messages)

        self.messages = messages + [{"role": "assistant", "content": answer}]
        self.memory.add("user", text)
        self.memory.add("assistant", answer)
        self._extract_facts(text, answer)
        return answer


def build_agent() -> SuperCerebro:
    """Cria o núcleo do Super Cérebro."""
    return SuperCerebro()
