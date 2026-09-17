from agent.brain import SuperCerebro
from agent.context_budget import bound_messages


def clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit] + "[TRUNCADO]"


def test_context_budget_preserves_current_message():
    messages = [
        {"role": "system", "content": "SYSTEM"},
        {"role": "system", "content": "older context " * 20},
        {"role": "user", "content": "pedido atual que não pode desaparecer"},
    ]
    bounded = bound_messages(messages, 40, clip)
    assert bounded[-1]["content"] == "pedido atual que não pode desaparecer"
    assert sum(len(item["content"]) for item in bounded) <= 40


def test_context_budget_discards_old_middle_context_first():
    messages = [
        {"role": "system", "content": "SYSTEM"},
        {"role": "system", "content": "OLD " * 30},
        {"role": "assistant", "content": "RECENT " * 30},
        {"role": "user", "content": "CURRENT"},
    ]
    bounded = bound_messages(messages, 30, clip)
    combined = "".join(item["content"] for item in bounded)
    assert bounded[-1]["content"] == "CURRENT"
    assert "OLD" not in combined
    assert len(combined) <= 30


def test_context_budget_keeps_user_when_system_message_exceeds_limit():
    messages = [
        {"role": "system", "content": "S" * 1000},
        {"role": "user", "content": "PEDIDO_ATUAL"},
    ]
    bounded = bound_messages(messages, 20, clip)
    assert bounded[-1]["content"] == "PEDIDO_ATUAL"
    assert len("".join(item["content"] for item in bounded)) <= 20


def test_context_budget_strictly_clips_when_callback_adds_marker():
    messages = [
        {"role": "system", "content": "S" * 1000},
        {"role": "user", "content": "PEDIDO_ATUAL_MUITO_LONGO"},
    ]
    bounded = bound_messages(messages, 10, clip)
    assert bounded[-1]["content"] == "PEDIDO_ATU"
    assert len("".join(item["content"] for item in bounded)) <= 10


def test_brain_uses_safe_context_budget():
    messages = [
        {"role": "system", "content": "S" * 1000},
        {"role": "assistant", "content": "contexto antigo"},
        {"role": "user", "content": "PEDIDO_ATUAL"},
    ]
    bounded = SuperCerebro._bounded_messages(messages, 40)
    assert bounded[-1]["content"] == "PEDIDO_ATUAL"
    assert sum(len(item["content"]) for item in bounded) <= 40
