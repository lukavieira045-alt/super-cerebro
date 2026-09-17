import pytest

from agent.task_engine import TaskEngine


def test_max_steps_is_clamped():
    assert TaskEngine(100).max_steps == 12
    assert TaskEngine(0).max_steps == 1


def test_repeated_request_is_detected_after_argument_key_reordering():
    engine = TaskEngine(3)
    runner = lambda tool, args: "ok"

    engine.execute("calculator", {"b": 2, "a": 1}, runner)

    assert engine.has_repeated_request("calculator", {"a": 1, "b": 2})


def test_failed_step_counts_toward_limit_and_is_not_reported_as_success():
    engine = TaskEngine(1)

    def failing_runner(tool, args):
        raise RuntimeError("falhou")

    result = engine.execute("calculator", {}, failing_runner)

    assert result.startswith("ERRO DA FERRAMENTA:")
    assert len(engine.steps) == 1
    assert engine.all_successful() is False
    with pytest.raises(RuntimeError, match="limite"):
        engine.execute("calculator", {}, lambda *_: "ok")
