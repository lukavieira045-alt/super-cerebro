from agent.planner import make_plan


def test_explanation_request_does_not_create_complex_autonomy_by_itself():
    plan = make_plan("explique o que é inteligência artificial")

    assert plan.complex is False
    assert plan.steps == ("entender e responder",)


def test_verification_request_does_not_create_complex_autonomy_by_itself():
    plan = make_plan("verifique esta informação")

    assert plan.complex is False


def test_research_request_remains_complex():
    plan = make_plan("pesquise fontes oficiais sobre inteligência artificial")

    assert plan.complex is True
    assert "pesquisar e reunir evidências" in plan.steps
