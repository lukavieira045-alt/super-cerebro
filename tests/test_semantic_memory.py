from agent.semantic_memory import expand_query


def test_semantic_expansion_preserves_original_query():
    calls = []

    def model(messages):
        calls.append(messages)
        return "sinônimo relacionado"

    result = expand_query("preço atual", model)

    assert result.startswith("preço atual ")
    assert "sinônimo relacionado" in result
    assert len(calls) == 1


def test_semantic_expansion_is_bounded():
    def model(messages):
        return "x" * 10000

    result = expand_query("consulta", model)

    assert result.startswith("consulta ")
    assert len(result) <= 2000


def test_semantic_expansion_failure_is_propagated_for_brain_fallback():
    def model(messages):
        raise RuntimeError("vireonix indisponível")

    try:
        expand_query("consulta", model)
    except RuntimeError as exc:
        assert "indisponível" in str(exc)
    else:
        raise AssertionError("a falha deveria ser propagada")
