"""Core reasoning agent."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from .tools import calculate

load_dotenv()


def build_agent():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY não configurada. Crie um arquivo .env.")

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    llm = ChatOpenAI(model=model, temperature=0, api_key=api_key)

    return create_react_agent(
        llm,
        tools=[calculate],
        prompt=(
            "Você é o Super Cérebro, um agente de IA útil, cuidadoso e objetivo. "
            "Analise a tarefa antes de agir, use ferramentas quando forem úteis, "
            "não invente fatos e deixe claras as incertezas. "
            "Nunca revele chaves, segredos ou credenciais."
        ),
    )
