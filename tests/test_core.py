from datetime import datetime, timedelta, timezone

from agent.confidence import estimate
from agent.contradictions import detect
from agent.knowledge_graph import KnowledgeGraph
from agent.learning import Learning
from agent.memory import Memory
from agent.planner import make_plan
from agent.source_memory import SourceMemory
from agent.source_reliability import score
from agent.task_engine import TaskEngine
from agent.temporal_memory import TemporalMemory
from agent.tools import _safe_path, calculate


def test_calculator_is_safe_and_correct():
    assert calculate("2*(3+4)") == 14


def test_planner_detects_research_task():
    plan = make_plan("pesquise e compare duas fontes sobre memória artificial")
    assert plan.complex
    assert "pesquisar e reunir evidências" in plan.steps


def test_task_engine_records_failure_without_crashing():
    engine = TaskEngine(2)
    result = engine.execute("x", {}, lambda *_: (_ for _ in ()).throw(ValueError("falhou")))
    assert "ERRO DA FERRAMENTA" in result
    assert not engine.all_successful()


def test_task_engine_detects_repeated_request():
    engine = TaskEngine(4)
    engine.execute("x", {"value": 1, "other": "a"}, lambda *_: "ok")
    assert engine.has_repeated_request("x", {"other": "a", "value": 1})
    assert not engine.has_repeated_request("x", {"value": 2})


def test_memory_and_knowledge_persist(tmp_path):
    db = tmp_path / "memory.db"
    memory = Memory(db)
    memory.add("user", "O projeto usa Vireonix")
    memory.remember_fact("projeto", "O projeto usa Vireonix", 4)
    assert memory.relevant_facts("projeto Vireonix")
    graph = KnowledgeGraph(db)
    graph.add("Projeto", "usa", "Vireonix", 0.9)
    assert graph.related("Projeto Vireonix")


def test_learning_tracks_success_and_failure_history(tmp_path):
    db = tmp_path / "learning.db"
    learning = Learning(db)
    learning.record("pesquisa web", "buscar fontes oficiais", True)
    learning.record("pesquisa web", "buscar fontes oficiais", False)
    learning.record("pesquisa web", "buscar fontes oficiais", True)
    item = learning.relevant("pesquisa web")[0]
    assert item["uses"] == 3
    assert item["successes"] == 2
    assert item["failures"] == 1
    assert learning.best_strategies("pesquisa web")


def test_learning_failure_can_change_strategy_status(tmp_path):
    db = tmp_path / "learning.db"
    learning = Learning(db)
    learning.record("tarefa", "estrategia", True)
    learning.record("tarefa", "estrategia", False)
    item = learning.relevant("tarefa")[0]
    assert item["success"] == 0
    assert item["successes"] == 1
    assert item["failures"] == 1


def test_source_memory_uses_structural_score(tmp_path):
    db = tmp_path / "memory.db"
    sources = SourceMemory(db)
    sources.record("teste", "https://example.gov.br/fonte", "Fonte oficial", "conteudo " * 30, 0.6)
    item = sources.relevant("teste")[0]
    assert item["confidence"] > 0.6


def test_reliability_is_bounded():
    result = score("https://example.gov.br", "Fonte", "conteudo " * 30)
    assert 0.0 <= result.score <= 0.9
