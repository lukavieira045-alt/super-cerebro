"""Super Cérebro agent package."""

# Mantém o núcleo existente intacto e aplica o orçamento seguro de contexto
# assim que a classe principal é carregada.
from .brain import MAX_CONTEXT_CHARS, SuperCerebro
from .context_budget import bound_messages


def _safe_bounded_messages(cls, messages, limit=MAX_CONTEXT_CHARS):
    return bound_messages(messages, limit, cls._clip)


SuperCerebro._bounded_messages = classmethod(_safe_bounded_messages)
