from agent.evidence import inspect_research


def _block(text: str) -> str:
    return text + " fonte: https://example.com"


def test_one_weak_source_is_not_reliable():
    report = inspect_research("fonte curta")
    assert report.reliable_enough is False
    assert report.sources == 1
    assert report.usable_sources == 0


def test_two_substantial_sources_without_conflict_are_reliable_enough():
    research = _block("A" * 150) + "\n---\n" + _block("B" * 150)
    report = inspect_research(research)
    assert report.sources == 2
    assert report.usable_sources == 2
    assert report.conflicts == ()
    assert report.reliable_enough is True


def test_explicit_divergence_blocks_reliable_enough():
    research = _block("A" * 150) + "\n---\n" + _block("Porém, a segunda fonte diverge dos dados anteriores. " + "B" * 150)
    report = inspect_research(research)
    assert report.conflicts
    assert report.reliable_enough is False


def test_failed_source_is_warning_not_automatic_consensus():
    research = "Não foi possível abrir esta fonte" + "\n---\n" + _block("C" * 150)
    report = inspect_research(research)
    assert report.warnings
    assert report.reliable_enough is False
