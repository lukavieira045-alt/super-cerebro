"""Ferramentas locais seguras do Super Cérebro."""

from __future__ import annotations

import ast
import operator
from datetime import datetime
from pathlib import Path
from typing import Any


_BIN_OPS: dict[type[ast.operator], Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}
_UNARY_OPS: dict[type[ast.unaryop], Any] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

WORKSPACE = Path("workspace").resolve()


def calculate(expression: str) -> float | int:
    """Calcula aritmética básica sem usar eval()."""
    tree = ast.parse(expression, mode="eval")

    def visit(node: ast.AST) -> float | int:
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
            left = visit(node.left)
            right = visit(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 100:
                raise ValueError("expoente muito grande")
            return _BIN_OPS[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
            return _UNARY_OPS[type(node.op)](visit(node.operand))
        raise ValueError("expressão não permitida")

    return visit(tree)


def current_datetime() -> str:
    """Retorna data e hora local do dispositivo que executa o agente."""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _safe_path(relative_path: str) -> Path:
    path = (WORKSPACE / relative_path).resolve()
    if path != WORKSPACE and WORKSPACE not in path.parents:
        raise ValueError("caminho fora do workspace permitido")
    return path


def read_file(relative_path: str) -> str:
    """Lê somente arquivos dentro de workspace/."""
    path = _safe_path(relative_path)
    if not path.is_file():
        raise FileNotFoundError(f"arquivo não encontrado: {relative_path}")
    return path.read_text(encoding="utf-8")


def write_file(relative_path: str, content: str) -> str:
    """Cria ou substitui um arquivo de texto dentro de workspace/."""
    path = _safe_path(relative_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"arquivo salvo: {relative_path}"


def execute_tool(name: str, arguments: dict[str, Any]) -> str:
    """Despacha uma ferramenta explicitamente permitida."""
    if name == "calculator":
        return str(calculate(str(arguments.get("expression", ""))))
    if name == "datetime":
        return current_datetime()
    if name == "read_file":
        return read_file(str(arguments.get("path", "")))
    if name == "write_file":
        return write_file(str(arguments.get("path", "")), str(arguments.get("content", "")))
    raise ValueError(f"ferramenta não permitida: {name}")


TOOL_DESCRIPTIONS = """
Ferramentas disponíveis:
- calculator: cálculos matemáticos. Argumentos: {"expression":"2*(3+4)"}
- datetime: data/hora local do dispositivo. Argumentos: {}
- read_file: lê texto dentro de workspace/. Argumentos: {"path":"arquivo.txt"}
- write_file: grava texto dentro de workspace/. Argumentos: {"path":"arquivo.txt","content":"..."}

Nunca invente o resultado de uma ferramenta. Para usar uma, responda SOMENTE com JSON válido neste formato:
{"tool":"calculator","arguments":{"expression":"2+2"}}
Para resposta normal, não use esse formato.
""".strip()
