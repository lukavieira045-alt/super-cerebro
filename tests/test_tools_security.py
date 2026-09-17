import pytest

from agent.tools import _validate_public_url, calculate


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
