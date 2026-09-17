from __future__ import annotations

import json

from agent.brain import SuperCerebro
from agent.memory import Memory
from agent.learning import Learning


class FakeBrain(SuperCerebro):
    def __init__(self, replies, tmp_path):
        super().__init__(
            memory=Memory(tmp_path / "memory.db"),
            learning=Learning(tmp_path / "memory.db"),
        )
        self.replies = list(replies)
        self.calls = []

    def _call_vireonix(self, messages):
        self.calls.append(messages)
        if not self.replies:
            return "Resposta simulada final."
        return self.replies.pop(0)

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


def test_brain_simple_question_persists_memory(tmp_path):
    brain = FakeBrain(["Olá! Resposta final."], tmp_path)
    answer = brain.ask("Olá")

    assert answer == "Olá! Resposta final."
    assert brain.memory.recent(limit=2)[-1]["content"] == answer
    assert len(brain.calls) >= 1


def test_brain_tool_flow_runs_calculator_and_returns_final_answer(tmp_path):
    tool_request = json.dumps({"tool": "calculator", "arguments": {"expression": "2*(3+4)"}})
    brain = FakeBrain([tool_request, "O resultado é 14."], tmp_path)

    answer = brain.ask("Calcule 2*(3+4)")

    assert answer == "O resultado é 14."
    assert brain.task_engine.steps
    assert brain.task_engine.steps[0].tool == "calculator"
    assert brain.task_engine.steps[0].ok is True
    assert "14" in brain.task_engine.steps[0].result
    assert len(brain.calls) >= 2


def test_brain_unknown_tool_is_tracked_as_failure_without_crash(tmp_path):
    tool_request = json.dumps({"tool": "tool_inexistente", "arguments": {}})
    brain = FakeBrain([tool_request, "Não foi possível executar essa ferramenta."], tmp_path)

    answer = brain.ask("Teste uma ferramenta inexistente")

    assert answer == "Não foi possível executar essa ferramenta."
    assert len(brain.task_engine.steps) == 1
    assert brain.task_engine.steps[0].ok is False
    assert "ERRO" in brain.task_engine.steps[0].result


def test_brain_tool_failure_does_not_stop_final_response(tmp_path):
    tool_request = json.dumps({"tool": "calculator", "arguments": {"expression": "1/0"}})
    brain = FakeBrain([tool_request, "O cálculo falhou e isso foi informado corretamente."], tmp_path)

    answer = brain.ask("Divida 1 por zero")

    assert answer == "O cálculo falhou e isso foi informado corretamente."
    assert brain.task_engine.steps[0].ok is False
    assert "ERRO" in brain.task_engine.steps[0].result


def test_brain_evaluator_failure_is_non_fatal(tmp_path, monkeypatch):
    brain = FakeBrain(["Resposta que deve continuar disponível."], tmp_path)

    def fail_judge(*args, **kwargs):
        raise RuntimeError("avaliador indisponível")

    monkeypatch.setattr("agent.brain.judge_with_vireonix", fail_judge)

    answer = brain.ask("Pergunta simples")

    assert answer == "Resposta que deve continuar disponível."
