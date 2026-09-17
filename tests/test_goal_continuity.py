from agent.goals import Goals


def test_related_goal_matches_morphological_variation(tmp_path):
    goals = Goals(tmp_path / "goals.db")
    goal_id = goals.create("Pesquisar fontes e verificar resultados")

    related = goals.active_for("pesquisa fontes verificadas")

    assert related
    assert related[0]["id"] == goal_id


def test_completed_goal_is_not_reused(tmp_path):
    goals = Goals(tmp_path / "goals.db")
    goal_id = goals.create("Concluir tarefa de pesquisa")
    goals.complete(goal_id)

    assert goals.active_for("continuar pesquisa") == []
