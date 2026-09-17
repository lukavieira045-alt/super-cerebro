from agent.memory import Memory


def test_relevant_increments_only_selected_duplicate_memory(tmp_path):
    memory = Memory(tmp_path / "memory.db")
    memory.add("user", "projeto duplicado", importance=1)
    memory.add("assistant", "projeto duplicado", importance=1)

    selected = memory.relevant("projeto", limit=1)

    assert len(selected) == 1
    with memory._connect() as db:
        rows = db.execute(
            "SELECT id, access_count FROM memories ORDER BY id"
        ).fetchall()

    assert [row["access_count"] for row in rows].count(1) == 1
    assert [row["access_count"] for row in rows].count(0) == 1


def test_relevant_does_not_change_unselected_memory_access(tmp_path):
    memory = Memory(tmp_path / "memory.db")
    memory.add("user", "primeira memória", importance=1)
    memory.add("user", "segunda memória", importance=1)

    memory.relevant("memória", limit=1)

    with memory._connect() as db:
        rows = db.execute(
            "SELECT content, access_count FROM memories ORDER BY id"
        ).fetchall()

    assert sum(row["access_count"] for row in rows) == 1
