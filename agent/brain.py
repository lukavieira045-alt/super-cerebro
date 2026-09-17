"""Núcleo de inteligência do Super Cérebro usando somente Vireonix."""

from __future__ import annotations

import json
import time
import requests

from .autonomy import build_autonomy_context
from .confidence import estimate, prompt as confidence_prompt
from .contradictions import context as contradiction_context
from .evaluator import judge_with_vireonix, local_check, revision_instruction
from .evidence import inspect_research, verify_with_model
from .experience_memory import ExperienceMemory
from .goals import Goals
from .health import HealthReport, run_health_checks
from .intelligence import build_system_prompt
from .knowledge_graph import KnowledgeGraph
from .learning import Learning
from .memory import Memory
from .planner import format_plan, make_plan
from .research import deep_research
from .self_improvement import SelfImprovement
from .semantic_memory import expand_query
from .source_memory import SourceMemory
from .task_engine import TaskEngine
from .temporal_memory import TemporalMemory
from .tools import TOOL_DESCRIPTIONS, execute_tool

VIREONIX_URL = "https://vireonix.ai/v1/chat/completions"
MODEL = "auto"
MAX_TOOL_STEPS = 8
VIREONIX_RETRIES = 2
MAX_CONTEXT_CHARS = 60_000
MAX_TOOL_RESULT_CHARS = 30_000
MAX_FINAL_INPUT_CHARS = 20_000


class SuperCerebro:
    """Vireonix + memória + experiências + fontes + grafo + tempo + contradições + autonomia."""

    def __init__(self, timeout: int = 120, memory: Memory | None = None, learning: Learning | None = None) -> None:
        self.timeout = timeout
        self.memory = memory or Memory()
        self.learning = learning or Learning(self.memory.db_path)
        self.experiences = ExperienceMemory(self.memory.db_path)
        self.knowledge = KnowledgeGraph(self.memory.db_path)
        self.temporal = TemporalMemory(self.memory.db_path)
        self.sources = SourceMemory(self.memory.db_path)
        self.goals = Goals(self.memory.db_path)
        self.improvement = SelfImprovement(self.learning)
        self.messages: list[dict[str, str]] = []
        self.task_engine = TaskEngine(MAX_TOOL_STEPS)
        self._research_verified = False

    def health_check(self) -> HealthReport:
        return run_health_checks(self.memory.db_path)

    @staticmethod
    def _clip(text: str, limit: int) -> str:
        value = str(text)
        if len(value) <= limit:
            return value
        return value[:limit] + "\n[conteúdo truncado para preservar o contexto do modelo]"

    @classmethod
    def _bounded_messages(cls, messages: list[dict[str, str]], limit: int = MAX_CONTEXT_CHARS) -> list[dict[str, str]]:
        total = 0
        bounded: list[dict[str, str]] = []
        for message in messages:
            role = str(message.get("role", "system"))
            content = str(message.get("content", ""))
            remaining = limit - total
            if remaining <= 0:
                break
            content = cls._clip(content, remaining)
            bounded.append({"role": role, "content": content})
            total += len(content)
        return bounded

    def _build_context(self, text: str) -> list[dict[str, str]]:
        recent = self.memory.recent(limit=12)
        try:
            memory_query = expand_query(text, self._call_vireonix)
        except RuntimeError:
            memory_query = text
        memory_context = self.memory.memory_context(memory_query, limit=8)
        learned = self.learning.context(text, limit=5)
        experience_context = self.experiences.context(text, limit=5)
        knowledge_context = self.knowledge.context(text, limit=8)
        temporal_context = self.temporal.context(text, limit=6)
        source_context = self.sources.context(text, limit=5)
        goal_context = self.goals.context(limit=5)
        related_goals = self.goals.active_for(text, limit=3)
        try:
            facts_context = contradiction_context(self.memory.facts(), limit=6)
        except (AttributeError, TypeError):
            facts_context = ""
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
        if experience_context:
            context.append({"role": "system", "content": experience_context})
        if knowledge_context:
            context.append({"role": "system", "content": knowledge_context})
        if temporal_context:
            context.append({"role": "system", "content": temporal_context})
        if source_context:
            context.append({"role": "system", "content": source_context})
        if facts_context:
            context.append({"role": "system", "content": facts_context})
        context.extend(recent)
        context.append({"role": "user", "content": text})
        return self._bounded_messages(context)

    def _call_vireonix(self, messages: list[dict[str, str]]) -> str:
        last_error: Exception | None = None
        safe_messages = self._bounded_messages(messages)
        for attempt in range(VIREONIX_RETRIES + 1):
            try:
                response = requests.post(VIREONIX_URL, headers={"Content-Type": "application/json"}, json={"model": MODEL, "messages": safe_messages}, timeout=self.timeout)
                response.raise_for_status()
                try:
                    payload = response.json()
                    content = payload["choices"][0]["message"]["content"]
                except (ValueError, KeyError, IndexError, TypeError) as exc:
                    raise RuntimeError(f"Resposta inválida do Vireonix: {exc}") from exc
                if not isinstance(content, str) or not content.strip():
                    raise RuntimeError("Resposta inválida do Vireonix: conteúdo vazio")
                return content
            except requests.HTTPError as exc:
                last_error = exc
                status = exc.response.status_code if exc.response is not None else None
                if status not in {429, 500, 502, 503, 504} or attempt >= VIREONIX_RETRIES:
                    raise RuntimeError(f"Falha ao conectar ao Vireonix: {exc}") from exc
            except (requests.Timeout, requests.ConnectionError) as exc:
                last_error = exc
                if attempt >= VIREONIX_RETRIES:
                    raise RuntimeError(f"Falha ao conectar ao Vireonix: {exc}") from exc
            except requests.RequestException as exc:
                raise RuntimeError(f"Falha ao conectar ao Vireonix: {exc}") from exc
            except RuntimeError:
                raise
            if attempt < VIREONIX_RETRIES:
                time.sleep(0.5 * (2 ** attempt))
        raise RuntimeError(f"Falha ao conectar ao Vireonix: {last_error}")

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

    def _extract_knowledge(self, user_text: str, answer: str) -> None:
        prompt = ("Extraia somente relações factuais duradouras e úteis. Não invente. Não extraia opiniões, senhas, tokens, chaves, dados bancários ou informações extremamente sensíveis. Responda SOMENTE JSON em uma lista no formato [{\"subject\":\"...\",\"relation\":\"...\",\"object\":\"...\",\"confidence\":0.8}]. Se não houver relações úteis, responda [].\n\n" f"Mensagem: {user_text}\nResposta: {answer}")
        try:
            edges = json.loads(self._call_vireonix([{"role": "system", "content": "Você é um extrator conservador de relações de conhecimento."}, {"role": "user", "content": prompt}]))
            if not isinstance(edges, list):
                return
            for item in edges[:8]:
                if isinstance(item, dict) and item.get("subject") and item.get("relation") and item.get("object"):
                    self.knowledge.add(str(item["subject"]), str(item["relation"]), str(item["object"]), float(item.get("confidence", 0.7)))
                    self.temporal.record(str(item["subject"]), f"{item['relation']} = {item['object']}", float(item.get("confidence", 0.7)))
        except (RuntimeError, KeyError, IndexError, TypeError, ValueError):
            return

    def _remember_sources(self, research: str, query: str) -> None:
        import re
        blocks = re.split(r"\n---\n", str(research))
        for block in blocks[:8]:
            urls = re.findall(r"https?://[^\s]+", block)
            if not urls:
                continue
            url = urls[0].rstrip(").,;\"")
            lines = [line.strip() for line in block.splitlines() if line.strip()]
            title = lines[0][:300] if lines else ""
            summary = " ".join(lines[1:3])[:1000] if len(lines) > 1 else ""
            self.sources.record(query, url, title, summary, 0.6)

    def _verify_final(self, messages: list[dict[str, str]], answer: str) -> str:
        trace = self.task_engine.trace_text()
        verification = ("VERIFICAÇÃO FINAL DA TAREFA.\nRevise a resposta usando somente o histórico e resultados das ferramentas. Corrija afirmações sem suporte, contradições, cálculos errados e conclusões sem evidência. Não invente dados. Entregue diretamente a resposta final.\n\n" f"ETAPAS EXECUTADAS:\n{trace}\n\nRESPOSTA A REVISAR:\n{self._clip(answer, MAX_FINAL_INPUT_CHARS)}")
        try:
            checked = self._call_vireonix(self._bounded_messages(messages + [{"role": "system", "content": verification}]))
            return checked.strip() or answer
        except RuntimeError:
            return answer

    def _quality_check(self, messages: list[dict[str, str]], question: str, answer: str) -> str:
        quick = local_check(question, answer, bool(self.task_engine.steps))
        if quick.needs_revision:
            try:
                revised = self._call_vireonix(self._bounded_messages(messages + [{"role": "system", "content": revision_instruction(quick)}]))
                answer = revised.strip() or answer
            except RuntimeError:
                pass
        try:
            evaluation = judge_with_vireonix(question, answer, self._call_vireonix)
        except RuntimeError:
            return answer
        if not evaluation.needs_revision:
            return answer
        try:
            revised = self._call_vireonix(self._bounded_messages(messages + [{"role": "assistant", "content": self._clip(answer, MAX_FINAL_INPUT_CHARS)}, {"role": "system", "content": revision_instruction(evaluation)}]))
            return revised.strip() or answer
        except RuntimeError:
            return answer

    def _verify_research(self, research: str) -> str:
        try:
            verified = verify_with_model(research, self._call_vireonix)
            report = inspect_research(research)
            self._research_verified = report.reliable_enough
            return verified
        except RuntimeError:
            self._research_verified = False
            return research

    def _calibrate(self, question: str, answer: str) -> str:
        confidence = estimate(answer, len(self.task_engine.steps), self._research_verified)
        try:
            calibrated = self._call_vireonix([{"role": "system", "content": "Você calibra a linguagem de uma resposta sem alterar fatos sustentados."}, {"role": "user", "content": f"Pergunta: {self._clip(question, MAX_FINAL_INPUT_CHARS)}\n\nResposta:\n{self._clip(answer, MAX_FINAL_INPUT_CHARS)}\n\n{confidence_prompt(confidence)}\nReescreva somente se necessário para que o grau de certeza da linguagem seja proporcional às evidências."}])
            return calibrated.strip() or answer
        except RuntimeError:
            return answer

    def _update_goals(self, text: str, answer: str) -> None:
        if self.goals.is_explicit_completion(text):
            if self.task_engine.steps and not self.task_engine.all_successful():
                return
            completed = self.goals.complete_active(text, "Concluído após a verificação da tarefa.")
            if completed is not None:
                return
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
        messages: list[dict[str, str]] = self._bounded_messages([{"role": "system", "content": build_system_prompt(tool_descriptions)}, *self._build_context(text)])
        answer = self._call_vireonix(messages)
        for _ in range(MAX_TOOL_STEPS):
            request = self._parse_tool_request(answer)
            if request is None:
                break
            tool = request["tool"]
            arguments = request["arguments"]
            if self.task_engine.has_repeated_request(tool, arguments):
                messages.extend([{"role": "assistant", "content": self._clip(answer, MAX_FINAL_INPUT_CHARS)}, {"role": "system", "content": f"A ferramenta {tool} com esses mesmos argumentos já foi executada. Não repita a mesma etapa. Escolha uma etapa diferente, use o resultado existente ou conclua a tarefa."}])
                messages = self._bounded_messages(messages)
                answer = self._call_vireonix(messages)
                continue
            result = self.task_engine.execute(tool, arguments, self._run_tool)
            if tool == "deep_research" and result:
                self._remember_sources(result, arguments.get("query", text))
                evidence = self._verify_research(result)
                result = result + "\n\nVERIFICAÇÃO DAS EVIDÊNCIAS:\n" + evidence
            messages.extend([
                {"role": "assistant", "content": self._clip(answer, MAX_FINAL_INPUT_CHARS)},
                {"role": "system", "content": f"Resultado da ferramenta {tool}:\n{self._clip(result, MAX_TOOL_RESULT_CHARS)}\n\nHistórico:\n{self.task_engine.trace_text()}\n\nContinue seguindo ou ajustando o plano. Verifique o resultado antes da próxima etapa."},
            ])
            messages = self._bounded_messages(messages)
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
            self.experiences.record(text, strategy, reason, success)
        self._update_goals(text, answer)
        self.messages = messages + [{"role": "assistant", "content": answer}]
        self.memory.add("user", text)
        self.memory.add("assistant", answer)
        self._extract_facts(text, answer)
        self._extract_knowledge(text, answer)
        self.memory.retain()
        return answer
