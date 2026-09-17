from __future__ import annotations

from agent.evidence import inspect_research, verification_prompt, verify_with_model


def _source(text: str) -> str:
    # Preenche com conteúdo real, pois inspect_research remove espaços nas bordas.
    return text + " conteúdo adicional para teste de evidência." * 8


def test_inspect_research_warns_when_there_are_too_few_usable_sources():
    report = inspect_research("FONTE 1\nconteúdo curto")

    assert report.sources == 1
    assert report.usable_sources == 0
    assert not report.reliable_enough
    assert report.warnings


def test_inspect_research_detects_unavailable_source():
    research = (
        _source("FONTE 1\nconteúdo válido")
        + "\n---\n"
        + "FONTE 2\nNão foi possível abrir esta fonte: indisponível"
    )

    report = inspect_research(research)

    assert report.sources == 2
    assert any("não puderam ser abertas" in warning for warning in report.warnings)


def test_inspect_research_flags_explicit_conflict_without_deciding_winner():
    research = (
        _source("FONTE A\nA primeira fonte diz uma coisa")
        + "\n---\n"
        + _source("FONTE B\nPorém, a segunda fonte apresenta informação diferente")
    )

    report = inspect_research(research)

    assert report.usable_sources == 2
    assert report.conflicts
    assert not report.reliable_enough


def test_verification_prompt_contains_structural_warnings_and_research():
    research = _source("FONTE A\nConteúdo para verificar")
    report = inspect_research(research)
    prompt = verification_prompt(research, report)

    assert "VERIFICAÇÃO DE EVIDÊNCIAS" in prompt
    assert "Fontes encontradas: 1" in prompt
    assert "Compare as fontes individualmente" in prompt
    assert research in prompt


def test_verify_with_model_returns_text_and_structural_report():
    captured = []

    def fake_model(messages):
        captured.extend(messages)
        return "Verificação concluída."

    result = verify_with_model(_source("FONTE A\nConteúdo verificável"), fake_model)
    report = inspect_research(_source("FONTE A\nConteúdo verificável"))

    assert result == "Verificação concluída."
    assert report.sources == 1
    assert not report.reliable_enough
    assert len(captured) == 2
    assert captured[0]["role"] == "system"
    assert captured[1]["role"] == "user"
    assert "MATERIAL PESQUISADO" in captured[1]["content"]
