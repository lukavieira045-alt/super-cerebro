"""Núcleo de inteligência do Super Cérebro usando somente Vireonix."""

from __future__ import annotations

import json
import requests

from .autonomy import build_autonomy_context
from .confidence import estimate, prompt as confidence_prompt
from .evaluator import judge_with_vireonix, local_check, revision_instruction
from .evidence import verify_with_model
from .goals import Goals
from .intelligence import build_system_prompt
from .learning import Learning
from .memory import Memory
from .planner import format_plan, make_plan
from .research import deep_research
from .self_improvement import SelfImprovement
from .semantic_memory import expand_query
from .task_engine import TaskEngine
from .tools import TOOL_DESCRIPTIONS, execute_tool

VIREONIX_URL = "https://vireonix.ai/v1/chat/completions"
MODEL = "auto"
MAX_TOOL_STEPS = 8


class SuperCerebro:
    """Vireonix + memória semântica + objetivos + autonomia + aprendizado + evidências."""

    def __init__(self, timeout: int = 120, memory: Memory | None = None, learning: Learning | None = None) -> None:
        self.timeout = timeout
        self.memory = memory or Memory()
        self.learning = learning or Learning(self.memory.db_path)
        self.goals = Goals(self.memory.db_path)
        self.improvement = SelfImprovement(self.learning)
        self.messages: list[dict[str, str]] = []
        self.task_engine = TaskEngine(MAX_TOOL_STEPS)
        self._research_verified = False

    def _build_context(self, text: str) -> list[dict[str, str]]:
        recent = self.memory.recent(limit=12)
        try:
            memory_query = expand_query(text, self._call_vireonix)
        except RuntimeError:
            memory_query = text
        memory_context = self.memory.memory_context(memory_query, limit=8)
        learned = self.learning.context(text, limit=5)
        goal_context = self.goals.context(limit=5)
        related_goals = self.goals.active_for(text, limit=3)
        plan = make_plan(text)
        context: list[dict[str, str]] = [{"role": "system", "content": format_plan(plan)}]
        if goal_context:
            context.append({"role": "system", "content": goal_context})
        if related_goals:
            context.append({"role": "system", "content": "OBJETIVOS RELACIONADOS À MENSAGEM ATUAL:\n" + "\n".join(f"- #{goal['id']}: {goal['title']} — {goal['progress'] or 'sem progresso registrado'}" for goal in related_goals)})
        autonomy = build_autonomy_context(plan, int(related_goals[0]["id"]) if related_goals else None, MAX_TOOL_STEPS)
        if autonomy:
            context.append({"role": "system", "content": autonomy})
        if memory_context:
            context.append({"role": "system", "content": memory_context})
        if learned:
            context.append({"role": "system", "content": learned + "\nUse essas experiências como referência, não como verdade absoluta. Reavalie tudo na tarefa atual."})
        context.extend(recent)
        context.append({"role": "user", "content": text})
        return context

    def _call_vireonix(self, messages: list[dict[str, str]]) -> str:
        try:
            response = requests.post(VIREONIX_URL, headers={"Content-Type": "application/json"}, json={"model": MODEL, "messages": messages}, timeout=self.timeout)
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
        if not isinstance(data, dict) or not isinstance(data.get("tool"), str) or not isinstance(data.get("arguments", {}), dict):
            return None
        return data

    def _run_tool(self, tool: str, arguments: dict) -> str:
        if tool == "deep_research":
            return deep_research(arguments.get("query", ""), arguments.get("sources", 4))
        return execute_tool(tool, arguments)

    def _extract_facts(self, user_text: str, answer: str) -> None:
        prompt = ("Extraia somente fatos duradouros e úteis para futuras conversas. Não invente nada e não salve senhas, tokens, chaves, dados bancários ou informações extremamente sensíveis. Responda SOMENTE com JSON em uma lista, no formato [{\"category\":\"...\",\"fact\":\"...\",\"importance\":1}]. Se não houver fatos úteis, responda [].\n\n" f"Usuário: {user_text}\nResposta: {answer}")
        try:
            facts = json.loads(self._call_vireonix([{"role": "system", "content": "Você é um extrator de memória. Seja conservador."}, {"role": "user", "content": prompt}]))
            if not isinstance(facts, list):
                return
            for item in facts[:5]:
                if isinstance(item, dict) and item.get("fact"):
                    self.memory.remember_fact(str(item.get("category", "geral")), str(item["fact"]), int(item.get("importance", 2)))
        except (RuntimeError, KeyError, IndexError, TypeError, ValueError):
            return

    def _verify_final(self, messages: list[dict[str, str]], answer: str) -> str:
        trace = self.task_engine.trace_text()
        verification = ("VERIFICAÇÃO FINAL DA TAREFA.\nRevise a resposta usando somente o histórico e resultados das ferramentas. Corrija afirmações sem suporte, contradições, cálculos errados e conclusões sem evidência. Não invente dados. Entregue diretamente a resposta final.\n\n" f"ETAPAS EXECUTADAS:\n{trace}\n\nRESPOSTA A REVISAR:\n{answer}")
        try:
            checked = self._call_vireonix(messages + [{"role": "system", "content": verification}])
            return checked.strip() or answer
        except RuntimeError:
            return answer

    def _quality_check(self, messages: list[dict[str, str]], question: str, answer: str) -> str:
        quick = local_check(question, answer, bool(self.task_engine.steps))
        if quick.needs_revision:
            try:
                revised = self._call_vireonix(messages + [{"role": "system", "content": revision_instruction(quick)}])
                answer = revised.strip() or answer
            except RuntimeError:
                pass
        evaluation = judge_with_vireonix(question, answer, self._call_vireonix)
        if not evaluation.needs_revision:
            return answer
        try:
            revised = self._call_vireonix(messages + [{"role": "assistant", "content": answer}, {"role": "system", "content": revision_instruction(evaluation)}])
            return revised.strip() or answer
        except RuntimeError:
            return answer

    def _verify_research(self, research: str) -> str:
        try:
            verified = verify_with_model(research, self._call_vireonix)
            self._research_verified = True
            return verified
        except RuntimeError:
            self._research_verified = False
            return research

    def _calibrate(self, question: str, answer: str) -> str:
        confidence = estimate(answer, len(self.task_engine.steps), self._research_verified)
        try:
            calibrated = self._call_vireonix([
                {"role": "system", "content": "Você calibra a linguagem de uma resposta sem alterar fatos sustentados."},
                {"role": "user", "content": f"Pergunta: {question}\n\nResposta:\n{answer}\n\n{confidence_prompt(confidence)}\nReescreva somente se necessário para que o grau de certeza da linguagem seja proporcional às evidências."},
            ])
            return calibrated.strip() or answer
        except RuntimeError:
            return answer

    def _update_goals(self, text: str, answer: str) -> None:
        plan = make_plan(text)
        related = self.goals.active_for(text, limit=1)
        goal_id = int(related[0]["id"]) if related else None
        if plan.complex and goal_id is None:
            goal_id = self.goals.create(text)
        if goal_id is None:
            return
        strategy = self.task_engine.strategy_summary()
        progress = (f"Última execução: {strategy}. Resultado: {'sucesso' if self.task_engine.all_successful() else 'houve falha em uma ou mais etapas'}." if strategy else "Etapa de análise/resposta concluída; objetivo permanece ativo para continuidade.")
        self.goals.update(goal_id, progress)

    def ask(self, text: str) -> str:
        self.task_engine.reset()
        self._research_verified = False
        tool_descriptions = TOOL_DESCRIPTIONS + ('\n- deep_research: pesquisa várias fontes e reúne conteúdo para comparação. Argumentos: {"query":"tema a investigar","sources":4}\n\nPara tarefas complexas, siga o plano inicial, mas ajuste-o conforme os resultados. Depois de cada ferramenta, verifique se a próxima etapa é necessária. Em modo autônomo, continue executando etapas úteis até concluir ou atingir o limite.')
        messages: list[dict[str, str]] = [{"role": "system", "content": build_system_prompt(tool_descriptions)}, *self._build_context(text)]
        answer = self._call_vireonix(messages)
        for _ in range(MAX_TOOL_STEPS):
            request = self._parse_tool_request(answer)
            if request is None:
                break
            tool = request["tool"]
            arguments = request["arguments"]
            result = self.task_engine.execute(tool, arguments, self._run_tool)
            if tool == "deep_research" and result:
                evidence = self._verify_research(result)
                result = result + "\n\nVERIFICAÇÃO DAS EVIDÊNCIAS:\n" + evidence
            messages.extend([{ "role": "assistant", "content": answer}, {"role": "system", "content": f"Resultado da ferramenta {tool}:\n{result}\n\nHistórico:\n{self.task_engine.trace_text()}\n\nContinue seguindo ou ajustando o plano. Verifique o resultado antes da próxima etapa."}])
            answer = self._call_vireonix(messages)

        if self.task_engine.steps:
            answer = self._verify_final(messages, answer)
        answer = self._quality_check(messages, text, answer)
        answer = self._calibrate(text, answer)

        strategy = self.task_engine.strategy_summary()
        if strategy:
            success = self.task_engine.all_successful()
            failures = [step for step in self.task_engine.steps if not step.ok]
            reason = "Todas as etapas terminaram com sucesso." if not failures else "; ".join(f"{step.tool}: {step.result[:180]}" for step in failures)
            improvement = self.improvement.analyze(text, [step.__dict__ for step in self.task_engine.steps], success, reason)
            self.improvement.apply(text, strategy, improvement)

        self._update_goals(text, answer)
        self.messages = messages + [{"role": "assistant", "content": answer}]
        self.memory.add("user", text)
        self.memory.add("assistant", answer)
        self._extract_facts(text, answer)
        return answer


def build_agent() -> SuperCerebro:
    return SuperCerebro()
