from agent.learning import Learning
from agent.self_improvement import SelfImprovement


def test_failed_strategy_is_not_promoted_to_best(tmp_path):
    learning = Learning(tmp_path / "memory.db")
    learning.record("pesquisar fontes", "buscar na fonte A", False)

    assert learning.best_strategies("pesquisar fontes") == []
    avoided = learning.avoid_strategies("pesquisar fontes")
    assert avoided
    assert avoided[0]["success"] is False


def test_mixed_history_uses_real_success_rate(tmp_path):
    learning = Learning(tmp_path / "memory.db")
    for _ in range(4):
        learning.record("pesquisar fontes", "estrategia", False)
    learning.record("pesquisar fontes", "estrategia", True)

    best = learning.best_strategies("pesquisar fontes")
    assert best == []
    assert learning.relevant("pesquisar fontes")[0]["failures"] == 4
    assert learning.relevant("pesquisar fontes")[0]["successes"] == 1


def test_self_improvement_records_failure_as_avoidance(tmp_path):
    learning = Learning(tmp_path / "memory.db")
    improvement = SelfImprovement(learning).analyze(
        "pesquisar fontes",
        [{"tool": "deep_research", "ok": False}],
        False,
        "fonte indisponível",
    )
    SelfImprovement(learning).apply("pesquisar fontes", "deep_research=erro", improvement)

    assert learning.best_strategies("pesquisar fontes") == []
    assert learning.avoid_strategies("pesquisar fontes")[0]["strategy"] == "deep_research=erro"
