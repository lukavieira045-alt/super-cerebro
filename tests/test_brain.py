from __future__ import annotations

import json

import requests

from agent.brain import SuperCerebro
from agent.learning import Learning
from agent.memory import Memory


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


def _response(payload=None, status=200):
    response = requests.Response()
    response.status_code = status
    response.url = "https://vireonix.ai/v1/chat/completions"
    response._content = json.dumps(payload or {"choices": [{"message": {"content": "OK"}}]}).encode()
    return response


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


def test_brain_repeated_tool_request_is_not_executed_twice(tmp_path):
    tool_request = json.dumps({"tool": "calculator", "arguments": {"expression": "2+2"}})
    brain = FakeBrain([tool_request, tool_request, "Já temos o resultado: 4."], tmp_path)

    answer = brain.ask("Calcule 2+2 e não repita a etapa")

    assert answer == "Já temos o resultado: 4."
    assert len(brain.task_engine.steps) == 1
    assert brain.task_engine.steps[0].result == "4"
    repeated_notice = "não repita a mesma etapa"
    assert any(repeated_notice in call[-1]["content"].lower() for call in brain.calls if call and call[-1]["role"] == "system")


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


def test_brain_records_successful_strategy_in_learning_and_experience(tmp_path):
    tool_request = json.dumps({"tool": "calculator", "arguments": {"expression": "6*7"}})
    brain = FakeBrain([tool_request, "O resultado é 42."], tmp_path)

    brain.ask("Calcule 6*7")

    learned = brain.learning.relevant("Calcule 6*7")
    assert learned
    assert learned[0]["successes"] >= 1
    assert learned[0]["failures"] == 0

    experiences = brain.experiences.relevant("Calcule 6*7")
    assert experiences
    assert experiences[0]["success"] == 1


def test_brain_records_failed_strategy_in_learning_and_experience(tmp_path):
    tool_request = json.dumps({"tool": "calculator", "arguments": {"expression": "1/0"}})
    brain = FakeBrain([tool_request, "O cálculo falhou."], tmp_path)

    brain.ask("Calcule 1/0")

    learned = brain.learning.relevant("Calcule 1/0")
    assert learned
    assert learned[0]["failures"] >= 1
    assert learned[0]["success"] == 0

    experiences = brain.experiences.relevant("Calcule 1/0")
    assert experiences
    assert experiences[0]["success"] == 0


def test_brain_uses_learned_strategy_in_vireonix_context(tmp_path):
    brain = SuperCerebro(memory=Memory(tmp_path / "memory.db"))
    brain.learning.record("pesquisa web", "buscar fontes oficiais", True)
    brain.learning.record_experience("pesquisa web", "usar uma única fonte", False, "não foi possível confirmar a informação")

    context = brain._build_context("pesquisa web sobre um assunto atual")
    system_text = "\n\n".join(item["content"] for item in context if item["role"] == "system")

    assert "buscar fontes oficiais" in system_text
    assert "usar uma única fonte" in system_text
    assert "Use essas experiências como referência, não como verdade absoluta" in system_text


def test_brain_carries_related_goal_progress_into_vireonix_context(tmp_path):
    brain = SuperCerebro(memory=Memory(tmp_path / "memory.db"))
    goal_id = brain.goals.create("Pesquisar e verificar inteligência artificial")
    brain.goals.update(goal_id, "Pesquisa inicial concluída")

    context = brain._build_context("pesquisar inteligência artificial")
    system_text = "\n\n".join(item["content"] for item in context if item["role"] == "system")

    assert f"#{goal_id}" in system_text
    assert "Pesquisa inicial concluída" in system_text
    assert "MODO AUTÔNOMO ATIVO" in system_text


def test_brain_continues_related_goal_after_follow_up_wording_changes(tmp_path):
    brain = SuperCerebro(memory=Memory(tmp_path / "memory.db"))
    goal_id = brain.goals.create("Pesquisar fontes oficiais sobre inteligência artificial")
    brain.goals.update(goal_id, "2 fontes verificadas")

    context = brain._build_context("continue a investigação das fontes oficiais de IA")
    system_text = "\n\n".join(item["content"] for item in context if item["role"] == "system")

    assert f"#{goal_id}" in system_text
    assert "2 fontes verificadas" in system_text


def test_brain_respects_maximum_tool_steps(tmp_path):
    tool_request = json.dumps({"tool": "calculator", "arguments": {"expression": "1+1"}})
    brain = FakeBrain([tool_request] * 20, tmp_path)

    brain.ask("Execute várias etapas de cálculo")

    assert len(brain.task_engine.steps) == 1
    assert all(step.ok for step in brain.task_engine.steps)


def test_brain_evaluator_failure_is_non_fatal(tmp_path, monkeypatch):
    brain = FakeBrain(["Resposta que deve continuar disponível."], tmp_path)

    def fail_judge(*args, **kwargs):
        raise RuntimeError("avaliador indisponível")

    monkeypatch.setattr("agent.brain.judge_with_vireonix", fail_judge)

    answer = brain.ask("Pergunta simples")

    assert answer == "Resposta que deve continuar disponível."


def test_brain_research_verification_returns_text_and_sets_structural_flag(tmp_path, monkeypatch):
    brain = FakeBrain(["Análise verificada."], tmp_path)
    source_a = "FONTE A\n" + ("conteúdo verificável " * 20)
    source_b = "FONTE B\n" + ("outro conteúdo verificável " * 20)
    research = source_a + "\n---\n" + source_b

    monkeypatch.setattr("agent.brain.verify_with_model", lambda research, call_model: "Análise verificada.")

    result = brain._verify_research(research)

    assert isinstance(result, str)
    assert result == "Análise verificada."
    assert brain._research_verified is True


def test_vireonix_retries_connection_error_then_succeeds(monkeypatch, tmp_path):
    brain = SuperCerebro(timeout=3, memory=Memory(tmp_path / "memory.db"))
    calls = []

    def fake_post(*args, **kwargs):
        calls.append(kwargs)
        if len(calls) < 3:
            raise requests.ConnectionError("rede temporariamente indisponível")
        return _response()

    monkeypatch.setattr("agent.brain.requests.post", fake_post)
    monkeypatch.setattr("agent.brain.time.sleep", lambda _: None)

    assert brain._call_vireonix([{"role": "user", "content": "teste"}]) == "OK"
    assert len(calls) == 3
    assert all(call["timeout"] == 3 for call in calls)


def test_vireonix_retries_transient_http_error(monkeypatch, tmp_path):
    brain = SuperCerebro(memory=Memory(tmp_path / "memory.db"))
    calls = []

    def fake_post(*args, **kwargs):
        calls.append(1)
        if len(calls) < 2:
            response = _response({"error": "temporário"}, status=503)
            raise requests.HTTPError("503", response=response)
        return _response()

    monkeypatch.setattr("agent.brain.requests.post", fake_post)
    monkeypatch.setattr("agent.brain.time.sleep", lambda _: None)

    assert brain._call_vireonix([{"role": "user", "content": "teste"}]) == "OK"
    assert len(calls) == 2


def test_vireonix_invalid_response_is_controlled_and_not_retried(monkeypatch, tmp_path):
    brain = SuperCerebro(memory=Memory(tmp_path / "memory.db"))
    calls = []

    def fake_post(*args, **kwargs):
        calls.append(1)
        return _response({"choices": []})

    monkeypatch.setattr("agent.brain.requests.post", fake_post)
    monkeypatch.setattr("agent.brain.time.sleep", lambda _: None)

    try:
        brain._call_vireonix([{"role": "user", "content": "teste"}])
    except RuntimeError as exc:
        assert "Resposta inválida do Vireonix" in str(exc)
    else:
        raise AssertionError("A resposta inválida deveria gerar RuntimeError")

    assert len(calls) == 1
