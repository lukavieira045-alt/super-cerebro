from agent.evidence import inspect_research


def test_single_source_discourse_does_not_count_as_cross_source_conflict():
    source = ("FONTE ÚNICA\n" + "O relatório apresenta uma hipótese, porém também descreve limitações. " * 8)
    report = inspect_research(source)
    assert report.sources == 1
    assert report.conflicts == ()


def test_later_source_with_conflict_marker_is_flagged():
    source_a = "FONTE A\n" + "informação verificável " * 30
    source_b = "FONTE B\n" + "porém a segunda fonte apresenta informação diferente " * 30
    report = inspect_research(source_a + "\n---\n" + source_b)
    assert report.conflicts
