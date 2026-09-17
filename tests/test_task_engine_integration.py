from agent.task_engine import TaskEngine


def test_failure_is_preserved_in_trace_and_blocks_success_claim():
    engine = TaskEngine(3)
    calls = []

    def runner(tool, args):
        calls.append(tool)
        if tool == "first":
            raise RuntimeError("falha controlada")
        return "ok"

    assert engine.execute("first", {}, runner).startswith("ERRO DA FERRAMENTA:")
    assert engine.execute("second", {}, runner) == "ok"

    trace = engine.trace_text()
    assert "ETAPA 1 [ERRO] first" in trace
    assert "ETAPA 2 [OK] second" in trace
    assert engine.all_successful() is False
    assert calls == ["first", "second"]


def test_successful_chain_has_compact_strategy_summary():
    engine = TaskEngine(3)
    engine.execute("search", {"q": "x"}, lambda *_: "found")
    engine.execute("calculator", {"x": 2}, lambda *_: "4")

    assert engine.strategy_summary() == "search=ok -> calculator=ok"
