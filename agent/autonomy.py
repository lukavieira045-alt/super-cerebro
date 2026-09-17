"""Modo autônomo de execução do Super Cérebro."""

from __future__ import annotations

from dataclasses import dataclass

from .planner import Plan


@dataclass(frozen=True)
class AutonomyState:
    goal_id: int | None
    active: bool
    max_steps: int


def build_autonomy_context(plan: Plan, goal_id: int | None, max_steps: int) -> str:
    """Instrui o Vireonix a conduzir uma tarefa até onde as ferramentas permitirem."""
    if not plan.complex and goal_id is None:
        return ""
    objective = f"objetivo persistente #{goal_id}" if goal_id is not None else "tarefa atual"
    return (
        "MODO AUTÔNOMO ATIVO.\n"
        f"Você está conduzindo o {objective}.\n"
        f"Limite operacional: {max_steps} etapas de ferramenta.\n"
        "Não pare apenas porque uma primeira resposta é possível. Primeiro determine se ainda existe "
        "uma etapa necessária para cumprir o objetivo. Use as ferramentas disponíveis quando forem úteis. "
        "Após cada resultado, avalie se a etapa seguinte é necessária. Se uma ferramenta falhar, adapte a "
        "estratégia ou tente uma alternativa segura. Não invente resultados. Quando não houver mais nenhuma "
        "etapa útil disponível, entregue a melhor conclusão possível e deixe claro o que ficou pendente."
    )
