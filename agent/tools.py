"""Ferramentas locais e de pesquisa do Super Cérebro."""

from __future__ import annotations

import ast
import html
import ipaddress
import operator
import socket
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

import requests

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
SEARCH_URL = "https://html.duckduckgo.com/html/"
MAX_PAGE_BYTES = 200_000
MAX_EXPRESSION_LENGTH = 2_000
MAX_PATH_LENGTH = 500
MAX_CONTENT_LENGTH = 100_000
MAX_QUERY_LENGTH = 1_000
MAX_URL_LENGTH = 4_000
MAX_TOOL_ARGUMENTS = 12


def calculate(expression: str) -> float | int:
    """Calcula aritmética básica sem usar eval()."""
    expression = str(expression).strip()
    if not expression:
        raise ValueError("expressão vazia")
    if len(expression) > MAX_EXPRESSION_LENGTH:
        raise ValueError("expressão muito grande")
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
    relative_path = str(relative_path).strip()
    if not relative_path:
        raise ValueError("caminho vazio")
    if len(relative_path) > MAX_PATH_LENGTH:
        raise ValueError("caminho muito grande")
    path = (WORKSPACE / relative_path).resolve()
    if path != WORKSPACE and WORKSPACE not in path.parents:
        raise ValueError("caminho fora do workspace permitido")
    return path


def read_file(relative_path: str) -> str:
    """Lê somente arquivos dentro de workspace/."""
    path = _safe_path(relative_path)
    if not path.is_file():
        raise FileNotFoundError(f"arquivo não encontrado: {relative_path}")
    return path.read_text(encoding="utf-8")[:MAX_CONTENT_LENGTH]


def write_file(relative_path: str, content: str) -> str:
    """Cria ou substitui um arquivo de texto dentro de workspace/."""
    path = _safe_path(relative_path)
    content = str(content)
    if len(content) > MAX_CONTENT_LENGTH:
        raise ValueError("conteúdo muito grande")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"arquivo salvo: {relative_path}"


class _SearchParser(HTMLParser):
    """Extrai resultados da página HTML do DuckDuckGo."""

    def __init__(self) -> None:
        super().__init__()
        self.results: list[dict[str, str]] = []
        self._current: dict[str, str] | None = None
        self._capture_title = False
        self._capture_snippet = False
        self._title_parts: list[str] = []
        self._snippet_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        classes = set((attributes.get("class") or "").split())
        if tag == "a" and "result__a" in classes:
            self._current = {"url": self._clean_url(attributes.get("href") or "")}
            self._capture_title = True
            self._title_parts = []
        elif tag in {"a", "div"} and "result__snippet" in classes and self._current:
            self._capture_snippet = True
            self._snippet_parts = []

    def handle_data(self, data: str) -> None:
        if self._capture_title:
            self._title_parts.append(data)
        if self._capture_snippet:
            self._snippet_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._capture_title and self._current:
            self._current["title"] = html.unescape("".join(self._title_parts)).strip()
            self._capture_title = False
        if self._capture_snippet and tag in {"a", "div"} and self._current:
            self._current["snippet"] = html.unescape(" ".join(self._snippet_parts)).strip()
            self._capture_snippet = False
            if self._current.get("title") and self._current.get("url"):
                self.results.append(self._current)
                self._current = None

    @staticmethod
    def _clean_url(url: str) -> str:
        parsed = urlparse(url)
        if parsed.path.startswith("/l/"):
            target = parse_qs(parsed.query).get("uddg", [""])[0]
            if target:
                return unquote(target)
        return url


class _PageParser(HTMLParser):
    """Converte HTML de uma página em texto legível."""

    def __init__(self) -> None:
        super().__init__()
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self._title = False
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "title":
            self._title = True
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip += 1

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._title = False
        if tag in {"script", "style", "noscript", "svg"} and self._skip:
            self._skip -= 1

    def handle_data(self, data: str) -> None:
        value = html.unescape(" ".join(data.split())).strip()
        if not value or self._skip:
            return
        if self._title:
            self.title_parts.append(value)
        else:
            self.text_parts.append(value)


def _validate_public_url(url: str) -> str:
    url = str(url).strip()
    if not url or len(url) > MAX_URL_LENGTH:
        raise ValueError("URL vazia ou muito grande")
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("URL deve usar http ou https")
    host = parsed.hostname.lower().rstrip(".")
    if host in {"localhost", "localhost.localdomain"}:
        raise ValueError("host local não permitido")
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, None)}
    except socket.gaierror as exc:
        raise ValueError("não foi possível resolver o host") from exc
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if not ip.is_global:
            raise ValueError("endereço privado ou reservado não permitido")
    return parsed.geturl()


def open_webpage(url: str) -> str:
    """Abre uma página pública e devolve título + texto, com limite de tamanho."""
    safe_url = _validate_public_url(url)
    response = requests.get(
        safe_url,
        headers={"User-Agent": "SuperCerebro/1.0"},
        timeout=20,
        stream=True,
    )
    response.raise_for_status()
    content_type = response.headers.get("content-type", "").lower()
    if "text/html" not in content_type and "text/plain" not in content_type:
        raise ValueError("o recurso não é uma página de texto/HTML")
    chunks: list[bytes] = []
    total = 0
    for chunk in response.iter_content(chunk_size=16_384):
        if not chunk:
            continue
        total += len(chunk)
        if total > MAX_PAGE_BYTES:
            break
        chunks.append(chunk)
    raw = b"".join(chunks)
    encoding = response.encoding or "utf-8"
    text = raw.decode(encoding, errors="replace")
    if "text/plain" in content_type:
        body = text
        title = ""
    else:
        parser = _PageParser()
        parser.feed(text)
        title = " ".join(parser.title_parts)
        body = " ".join(parser.text_parts)
    body = body[:12_000]
    return f"Título: {title or '(sem título)'}\nURL: {safe_url}\nConteúdo:\n{body}"


def search_web(query: str, limit: int = 5) -> str:
    """Pesquisa a web e retorna títulos, URLs e trechos dos resultados."""
    query = str(query).strip()
    if not query:
        raise ValueError("consulta vazia")
    if len(query) > MAX_QUERY_LENGTH:
        raise ValueError("consulta muito grande")
    limit = max(1, min(int(limit), 8))
    response = requests.get(
        SEARCH_URL,
        params={"q": query, "kl": "br-pt"},
        headers={"User-Agent": "SuperCerebro/1.0"},
        timeout=20,
    )
    response.raise_for_status()
    parser = _SearchParser()
    parser.feed(response.text)
    results = parser.results[:limit]
    if not results:
        return "Nenhum resultado encontrado."
    lines = []
    for index, item in enumerate(results, 1):
        lines.append(f"{index}. {item['title']}\nURL: {item['url']}\nTrecho: {item.get('snippet', '')}")
    return "\n\n".join(lines)


def execute_tool(name: str, arguments: dict[str, Any]) -> str:
    """Despacha somente ferramentas explicitamente permitidas."""
    if not isinstance(arguments, dict):
        raise ValueError("argumentos inválidos")
    if len(arguments) > MAX_TOOL_ARGUMENTS:
        raise ValueError("quantidade de argumentos excedida")
    if name == "calculator":
        return str(calculate(str(arguments.get("expression", ""))))
    if name == "datetime":
        return current_datetime()
    if name == "read_file":
        return read_file(str(arguments.get("path", "")))
    if name == "write_file":
        return write_file(str(arguments.get("path", "")), str(arguments.get("content", "")))
    if name == "web_search":
        return search_web(str(arguments.get("query", "")), int(arguments.get("limit", 5)))
    if name == "open_webpage":
        return open_webpage(str(arguments.get("url", "")))
    raise ValueError(f"ferramenta não permitida: {name}")


TOOL_DESCRIPTIONS = """
Ferramentas disponíveis:
- calculator: cálculos matemáticos. Argumentos: {"expression":"2*(3+4)"}
- datetime: data/hora local do dispositivo. Argumentos: {}
- read_file: lê texto dentro de workspace/. Argumentos: {"path":"arquivo.txt"}
- write_file: grava texto dentro de workspace/. Argumentos: {"path":"arquivo.txt","content":"..."}
- web_search: pesquisa informações atuais na web. Argumentos: {"query":"sua pesquisa","limit":5}
- open_webpage: abre e lê uma página pública encontrada na web. Argumentos: {"url":"https://exemplo.com"}

Para usar uma ferramenta, responda SOMENTE com JSON válido neste formato:
{"tool":"open_webpage","arguments":{"url":"https://exemplo.com"}}
Nunca invente o resultado de uma ferramenta. Para resposta normal, não use esse formato.
""".strip()
