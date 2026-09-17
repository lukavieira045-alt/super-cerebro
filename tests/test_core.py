from agent.confidence import estimate
from agent.contradictions import detect
from agent.evidence import inspect_research
from agent.knowledge_graph import KnowledgeGraph
from agent.memory import Memory
from agent.planner import make_plan
from agent.source_memory import SourceMemory
from agent.source_reliability import score
from agent.task_engine import TaskEngine
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


def test_memory_and_knowledge_persist(tmp_path):
    db = tmp_path / "memory.db"
    memory = Memory(db)
    memory.add("user", "O projeto usa Vireonix")
    memory.remember_fact("projeto", "O projeto usa Vireonix", 4)
    assert memory.relevant_facts("projeto Vireonix")
    graph = KnowledgeGraph(db)
    graph.add("Projeto", "usa", "Vireonix", 0.9)
    assert graph.related("Projeto Vireonix")


def test_source_memory_uses_structural_score(tmp_path):
    db = tmp_path / "memory.db"
    sources = SourceMemory(db)
    sources.record("teste", "https://example.gov.br/fonte", "Fonte oficial", "conteudo " * 30, 0.6)
    item = sources.relevant("teste")[0]
    assert item["confidence"] > 0.6


def test_reliability_is_bounded():
    result = score("https://example.gov.br", "Fonte", "conteudo " * 30)
    assert 0.0 <= result.score <= 0.9


def test_contradictions_are_flagged_as_possible_only():
    found = detect([
        {"fact": "O projeto usa Vireonix"},
        {"fact": "O projeto não usa Vireonix"},
    ])
    assert found


def test_confidence_stays_conservative():
    result = estimate("Não foi possível confirmar este dado.", 0, False)
    assert result.level == "baixa"
    assert result.score < 0.55


def test_workspace_blocks_escape(tmp_path, monkeypatch):
    from agent import tools
    monkeypatch.setattr(tools, "WORKSPACE", tmp_path.resolve())
    assert _safe_path("arquivo.txt").parent == tmp_path.resolve()
    try:
        _safe_path("../fora.txt")
    except ValueError:
        pass
    else:
        raise AssertionError("path traversal não foi bloqueado")
