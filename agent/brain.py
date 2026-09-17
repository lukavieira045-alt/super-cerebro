"""Vireonix-powered intelligence core for Super Cérebro."""

from __future__ import annotations

import requests

from .intelligence import build_system_prompt

VIREONIX_URL = "https://vireonix.ai/v1/chat/completions"
MODEL = "auto"


class SuperCerebro:
    """Interface simples para o modelo Auto da Vireonix."""

    def __init__(self, timeout: int = 120) -> None:
        self.timeout = timeout
        self.messages: list[dict[str, str]] = [
            {"role": "system", "content": build_system_prompt()}
        ]

    def ask(self, text: str) -> str:
        """Envia uma mensagem mantendo o contexto da conversa."""
        self.messages.append({"role": "user", "content": text})

        try:
            response = requests.post(
                VIREONIX_URL,
                headers={"Content-Type": "application/json"},
                json={
                    "model": MODEL,
                    "messages": self.messages,
                },
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            answer = data["choices"][0]["message"]["content"]
        except requests.RequestException as exc:
            self.messages.pop()
            raise RuntimeError(f"Falha ao conectar ao Vireonix: {exc}") from exc
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            self.messages.pop()
            raise RuntimeError("Resposta inválida recebida do Vireonix.") from exc

        self.messages.append({"role": "assistant", "content": answer})
        return answer


def build_agent() -> SuperCerebro:
    """Cria o núcleo de inteligência do Super Cérebro."""
    return SuperCerebro()
