import pytest

from agent.tools import (
    MAX_CONTENT_LENGTH,
    MAX_EXPRESSION_LENGTH,
    MAX_QUERY_LENGTH,
    MAX_URL_LENGTH,
    _validate_public_url,
    calculate,
    execute_tool,
)


def test_private_ipv4_is_rejected(monkeypatch):
    monkeypatch.setattr("agent.tools.socket.getaddrinfo", lambda *args, **kwargs: [(0, 0, 0, "", ("192.168.1.10", 0))])
    with pytest.raises(ValueError, match="privado"):
        _validate_public_url("https://example.com")


def test_loopback_is_rejected(monkeypatch):
    monkeypatch.setattr("agent.tools.socket.getaddrinfo", lambda *args, **kwargs: [(0, 0, 0, "", ("127.0.0.1", 0))])
    with pytest.raises(ValueError, match="privado"):
        _validate_public_url("http://example.com")


def test_unsupported_scheme_is_rejected():
    with pytest.raises(ValueError, match="http ou https"):
        _validate_public_url("file:///etc/passwd")


def test_calculator_rejects_calls():
    with pytest.raises(ValueError):
        calculate("__import__('os').system('echo unsafe')")


def test_calculator_rejects_oversized_expression():
    with pytest.raises(ValueError, match="muito grande"):
        calculate("1+" + "1" * MAX_EXPRESSION_LENGTH)


def test_public_url_rejects_oversized_input():
    with pytest.raises(ValueError, match="muito grande"):
        _validate_public_url("https://example.com/" + "a" * MAX_URL_LENGTH)


def test_search_rejects_oversized_query():
    with pytest.raises(ValueError, match="muito grande"):
        execute_tool("web_search", {"query": "x" * (MAX_QUERY_LENGTH + 1)})


def test_write_rejects_oversized_content():
    with pytest.raises(ValueError, match="muito grande"):
        execute_tool("write_file", {"path": "limite.txt", "content": "x" * (MAX_CONTENT_LENGTH + 1)})


def test_execute_tool_rejects_non_mapping_arguments():
    with pytest.raises(ValueError, match="argumentos inválidos"):
        execute_tool("datetime", [])
