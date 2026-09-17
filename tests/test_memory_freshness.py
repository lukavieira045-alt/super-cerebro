from datetime import datetime, timedelta, timezone

from agent.temporal_memory import TemporalMemory


def test_expired_temporal_fact_is_not_retrieved(tmp_path):
    memory = TemporalMemory(tmp_path / "memory.db")
    past = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    memory.record("produto", "preço antigo", valid_until=past)

    assert memory.relevant("produto preço") == []


def test_future_temporal_fact_is_retrieved_with_validity(tmp_path):
    memory = TemporalMemory(tmp_path / "memory.db")
    future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    memory.record("produto", "preço atual", valid_until=future)

    result = memory.relevant("produto preço")

    assert result
    assert result[0]["fact"] == "preço atual"
