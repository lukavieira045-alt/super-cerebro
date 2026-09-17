from agent.goals import Goals


def test_completion_requires_explicit_intent():
    assert Goals.is_explicit_completion("continue o projeto") is False
    assert Goals.is_explicit_completion("terminei de analisar os dados") is False
    assert Goals.is_explicit_completion("pode finalizar esse objetivo") is True
    assert Goals.is_explicit_completion("objetivo está concluído") is True


def test_complete_active_closes_related_goal(tmp_path):
    goals = Goals(tmp_path / "goals.db")
    goal_id = goals.create("Pesquisar fontes oficiais")

    completed = goals.complete_active("pode finalizar esse objetivo")

    assert completed == goal_id
    assert goals.active() == []


def test_complete_active_does_not_close_on_ambiguous_message(tmp_path):
    goals = Goals(tmp_path / "goals.db")
    goal_id = goals.create("Pesquisar fontes oficiais")

    completed = goals.complete_active("continue pesquisando as fontes")

    assert completed is None
    assert goals.active()[0]["id"] == goal_id


def test_completed_goal_is_not_reused(tmp_path):
    goals = Goals(tmp_path / "goals.db")
    goal_id = goals.create("Finalizar projeto")
    goals.complete_active("finalize esse objetivo")

    assert goals.active_for("finalizar projeto") == []
    row = goals._connect()
    try:
        status = row.execute("SELECT status FROM goals WHERE id = ?", (goal_id,)).fetchone()["status"]
    finally:
        row.close()
    assert status == "completed"
