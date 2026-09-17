from __future__ import annotations

import json

from agent.brain import SuperCerebro
from agent.learning import Learning
from agent.memory import Memory


class ResearchBrain(SuperCerebro):
    def __init__(self, replies, tmp_path):
        super().__init__(
            memory=Memory(tmp_path / "memory.db"),
            learning=Learning(tmp_path / "memory.db"),
        )
        self.replies = list(replies)
        self.calls = []

    def _call_vireonix(self, messages):
        self.calls.append(messages)
        return self.replies.pop(0) if self.replies else "Resposta final simulada."

    def _build_context(self, text):
        return [{"role": "user", "content": text}]

    def _extract_facts(self, user_text, answer):
        return None

    def _extract_knowledge(self, user_text, answer):
        return None

    def _verify_final(self, messages, answer):
        return answer

    def _quality_check(self, messages, question, answer):
        return answer

    def _calibrate(self, question, answer):
        return answer


def test_brain_research_flows_through_evidence_and_source_memory(monkeypatch, tmp_path):
    tool_request = json.dumps({
        "tool": "deep_research",
        "arguments": {"query": "Vireonix", "sources": 2},
    })
    brain = ResearchBrain([tool_request, "Pesquisa concluída com base nas fontes verificadas."], tmp_path)

    research = (
        "FONTE 1\nURL: https://example.gov.br/a\n"
        + "Conteúdo oficial suficientemente longo para ser considerado utilizável. " * 4
        + "\n---\n"
        + "FONTE 2\nURL: https://example.org/b\n"
        + "Segundo conteúdo suficientemente longo para comparação e verificação. " * 4
    )

    monkeypatch.setattr("agent.brain.deep_research", lambda query, sources: research)
    monkeypatch.setattr("agent.brain.verify_with_model", lambda material, call_model: "As duas fontes foram comparadas sem conflito explícito.")

    answer = brain.ask("Pesquise Vireonix")

    assert answer == "Pesquisa concluída com base nas fontes verificadas."
    assert brain.task_engine.steps[0].tool == "deep_research"
    assert brain.task_engine.steps[0].ok is True
    assert brain._research_verified is True

    sources = brain.sources.relevant("Vireonix", limit=5)
    urls = {item["url"] for item in sources}
    assert "https://example.gov.br/a" in urls
    assert "https://example.org/b" in urls


def test_brain_keeps_research_result_when_evidence_verification_fails(monkeypatch, tmp_path):
    tool_request = json.dumps({
        "tool": "deep_research",
        "arguments": {"query": "teste", "sources": 2},
    })
    brain = ResearchBrain([tool_request, "Resultado preservado com aviso de verificação."], tmp_path)

    research = "FONTE 1\nURL: https://example.com/a\nConteúdo da pesquisa"
    monkeypatch.setattr("agent.brain.deep_research", lambda query, sources: research)

    def fail_verification(material, call_model):
        raise RuntimeError("verificador indisponível")

    monkeypatch.setattr("agent.brain.verify_with_model", fail_verification)

    answer = brain.ask("Pesquise teste")

    assert answer == "Resultado preservado com aviso de verificação."
    assert brain.task_engine.steps[0].ok is True
    assert brain._research_verified is False
    assert brain.sources.relevant("teste", limit=5)
