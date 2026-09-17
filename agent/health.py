"""Diagnóstico local das camadas do Super Cérebro.

O health check é deliberadamente offline: ele valida componentes locais sem
fazer uma chamada automática ao Vireonix.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .confidence import estimate
from .contradictions import detect
from .goals import Goals
from .knowledge_graph import KnowledgeGraph
from .learning import Learning
from .memory import Memory
from .planner import make_plan
from .source_memory import SourceMemory
from .source_reliability import score
from .task_engine import TaskEngine
from .temporal_memory import TemporalMemory
from .tools import execute_tool


@dataclass(frozen=True)
class HealthCheck:
    name: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class HealthReport:
    checks: tuple[HealthCheck, ...]

    @property
    def ok(self) -> bool:
        return all(check.ok for check in self.checks)

    def text(self) -> str:
        status = "SAUDÁVEL" if self.ok else "ATENÇÃO"
        lines = [f"SAÚDE DO SISTEMA: {status}"]
        for check in self.checks:
            lines.append(f"- [{'OK' if check.ok else 'ERRO'}] {check.name}: {check.detail}")
        return "\n".join(lines)


def _check(name: str, fn) -> HealthCheck:
    try:
        detail = str(fn())
        return HealthCheck(name, True, detail or "funcionando")
    except Exception as exc:
        return HealthCheck(name, False, f"{type(exc).__name__}: {exc}")


def run_health_checks(db_path: str | Path = "data/health_check.db") -> HealthReport:
    """Executa verificações rápidas e isoladas das camadas locais."""
    db_path = Path(db_path)
    checks = [
        _check("SQLite/memória", lambda: _memory_check(db_path)),
        _check("Aprendizado", lambda: _learning_check(db_path)),
        _check("Objetivos", lambda: _goals_check(db_path)),
        _check("Grafo de conhecimento", lambda: _graph_check(db_path)),
        _check("Memória temporal", lambda: _temporal_check(db_path)),
        _check("Fontes", lambda: _source_check(db_path)),
        _check("Planejador", lambda: _planner_check()),
        _check("Contradições", lambda: _contradiction_check()),
        _check("Confiança", lambda: _confidence_check()),
        _check("Task engine", lambda: _task_engine_check()),
        _check("Ferramenta de cálculo", lambda: _calculator_check()),
    ]
    return HealthReport(tuple(checks))


def _memory_check(path: Path) -> str:
    memory = Memory(path)
    memory.add("system", "health-check", importance=1)
    return f"SQLite OK ({path})"


def _learning_check(path: Path) -> str:
    learning = Learning(path)
    learning.record("health check", "diagnóstico local", True)
    return "estratégias OK"


def _goals_check(path: Path) -> str:
    goals = Goals(path)
    goal_id = goals.create("health check")
    goals.update(goal_id, "verificado")
    return "objetivos OK"


def _graph_check(path: Path) -> str:
    graph = KnowledgeGraph(path)
    graph.add("health", "estado", "ok", 1.0)
    return "relações OK"


def _temporal_check(path: Path) -> str:
    temporal = TemporalMemory(path)
    temporal.record("health", "verificado", 1.0)
    return "tempo OK"


def _source_check(path: Path) -> str:
    sources = SourceMemory(path)
    sources.record("health", "https://example.org", "health", "conteúdo de teste", 0.5)
    structural = score("https://example.org", "health", "conteúdo de teste")
    return f"fontes OK ({structural.score:.2f})"


def _planner_check() -> str:
    plan = make_plan("pesquisar e analisar um problema complexo")
    if not plan.complex:
        raise AssertionError("planejador não reconheceu tarefa complexa")
    return "plano complexo reconhecido"


def _contradiction_check() -> str:
    result = detect([{"fact": "o sistema está ativo"}, {"fact": "o sistema não está ativo"}])
    return f"detector OK ({len(result)} sinal(is))"


def _confidence_check() -> str:
    confidence = estimate("resposta de teste", 1)
    if not 0.0 <= confidence.score <= 1.0:
        raise AssertionError("confiança fora do intervalo")
    return f"confiança OK ({confidence.level})"


def _task_engine_check() -> str:
    engine = TaskEngine(2)
    result = engine.execute("calculator", {"expression": "2+2"}, execute_tool)
    if result.strip() != "4":
        raise AssertionError(f"resultado inesperado: {result}")
    return "execução rastreável OK"


def _calculator_check() -> str:
    result = execute_tool("calculator", {"expression": "(2 + 3) * 4"})
    if result.strip() != "20":
        raise AssertionError(f"cálculo inesperado: {result}")
    return "cálculo seguro OK"
