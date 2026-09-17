from agent.brain import SuperCerebro
from agent.memory import Memory
from agent.task_engine import TaskStep


def test_brain_explicit_completion_closes_goal(tmp_path):
    brain = SuperCerebro(memory=Memory(tmp_path / "brain.db"))
    goal_id = brain.goals.create("Pesquisar fontes oficiais")

    brain._update_goals("pode finalizar esse objetivo", "Tarefa concluída.")

    assert brain.goals.active() == []
    row = brain.goals._connect()
    try:
        status = row.execute("SELECT status FROM goals WHERE id = ?", (goal_id,)).fetchone()["status"]
    finally:
        row.close()
    assert status == "completed"


def test_brain_keeps_goal_active_after_failed_tool_step(tmp_path):
    brain = SuperCerebro(memory=Memory(tmp_path / "brain.db"))
    goal_id = brain.goals.create("Pesquisar fontes oficiais")
    brain.task_engine.steps.append(TaskStep(1, "web_search", {"query": "fontes"}, "falhou", False))

    brain._update_goals("pode finalizar esse objetivo", "Não consegui concluir todas as etapas.")

    active = brain.goals.active()
    assert active
    assert active[0]["id"] == goal_id


def test_brain_does_not_complete_on_ambiguous_message(tmp_path):
    brain = SuperCerebro(memory=Memory(tmp_path / "brain.db"))
    goal_id = brain.goals.create("Pesquisar fontes oficiais")

    brain._update_goals("terminei de analisar as fontes", "Análise concluída.")

    assert brain.goals.active()[0]["id"] == goal_id
