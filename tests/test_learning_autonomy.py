from __future__ import annotations

from agent.autonomy import build_autonomy_context
from agent.goals import Goals
from agent.learning import Learning
from agent.planner import make_plan


def test_learning_context_exposes_success_and_failure_for_future_tasks(tmp_path):
    learning = Learning(tmp_path / "learning.db")
    learning.record("pesquisa web", "buscar fontes oficiais", True)
    learning.record("pesquisa web", "buscar fontes oficiais", True)
    learning.record_experience("pesquisa web", "usar uma única fonte", False, "a fonte não pôde ser confirmada")

    context = learning.context("pesquisa web")

    assert "ESTRATÉGIAS COM MAIOR EVIDÊNCIA DE SUCESSO" in context
    assert "buscar fontes oficiais" in context
    assert "ESTRATÉGIAS QUE DEVEM SER REAVALIADAS OU EVITADAS" in context
    assert "usar uma única fonte" in context


def test_learning_best_strategy_prefers_higher_success_rate(tmp_path):
    learning = Learning(tmp_path / "learning.db")
    learning.record("tarefa", "estrategia fraca", False)
    learning.record("tarefa", "estrategia forte", True)
    learning.record("tarefa", "estrategia forte", True)

    best = learning.best_strategies("tarefa", limit=1)

    assert best
    assert best[0]["strategy"] == "estrategia forte"


def test_autonomy_context_activates_for_complex_plan():
    plan = make_plan("pesquise, compare e verifique fontes sobre inteligência artificial")

    context = build_autonomy_context(plan, None, 8)

    assert plan.complex
    assert "MODO AUTÔNOMO ATIVO" in context
    assert "8 etapas de ferramenta" in context
    assert "Não invente resultados" in context


def test_autonomy_context_identifies_persistent_goal():
    plan = make_plan("organize um projeto complexo")

    context = build_autonomy_context(plan, 42, 8)

    assert "objetivo persistente #42" in context


def test_goal_progress_persists_for_follow_up(tmp_path):
    goals = Goals(tmp_path / "goals.db")
    goal_id = goals.create("Pesquisar e verificar um tema")
    goals.update(goal_id, "Pesquisa inicial concluída")

    active = goals.active()

    assert active
    assert active[0]["id"] == goal_id
    assert active[0]["progress"] == "Pesquisa inicial concluída"
