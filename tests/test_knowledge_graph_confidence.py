from agent.knowledge_graph import KnowledgeGraph


def test_confidence_is_clamped(tmp_path):
    graph = KnowledgeGraph(tmp_path / "memory.db")
    graph.add("A", "rel", "B", 3.0)
    graph.add("C", "rel", "D", -2.0)

    rows = graph.related("A C", limit=10)

    by_subject = {row["subject"]: row for row in rows}
    assert by_subject["A"]["confidence"] == 1.0
    assert by_subject["C"]["confidence"] == 0.0


def test_duplicate_edge_keeps_highest_confidence(tmp_path):
    graph = KnowledgeGraph(tmp_path / "memory.db")
    graph.add("A", "rel", "B", 0.8)
    graph.add("A", "rel", "B", 0.2)

    rows = graph.related("A B")

    assert len(rows) == 1
    assert rows[0]["confidence"] == 0.8
    assert rows[0]["uses"] == 2
