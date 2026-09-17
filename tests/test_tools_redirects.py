import ipaddress
import pytest

from agent.tools import MAX_REDIRECTS, open_webpage


class FakeResponse:
    def __init__(self, status_code=200, headers=None, body=b"<title>OK</title>conteudo"):
        self.status_code = status_code
        self.headers = headers or {"content-type": "text/html; charset=utf-8"}
        self.encoding = "utf-8"
        self._body = body

    @property
    def is_redirect(self):
        return 300 <= self.status_code < 400

    @property
    def is_permanent_redirect(self):
        return self.status_code in {308}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def iter_content(self, chunk_size=16_384):
        yield self._body


def test_redirect_to_private_address_is_rejected(monkeypatch):
    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse(302, {"location": "http://127.0.0.1/admin"})

    def fake_addrinfo(host, *args, **kwargs):
        address = "127.0.0.1" if host == "127.0.0.1" else "93.184.216.34"
        return [(0, 0, 0, "", (address, 0))]

    monkeypatch.setattr("agent.tools.requests.get", fake_get)
    monkeypatch.setattr("agent.tools.socket.getaddrinfo", fake_addrinfo)

    with pytest.raises(ValueError, match="privado|reservado"):
        open_webpage("https://example.com")

    assert len(calls) == 1


def test_redirect_chain_is_limited(monkeypatch):
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        return FakeResponse(302, {"location": "https://example.com/next"})

    monkeypatch.setattr("agent.tools.requests.get", fake_get)
    monkeypatch.setattr("agent.tools.socket.getaddrinfo", lambda *args, **kwargs: [(0, 0, 0, "", ("93.184.216.34", 0))])

    with pytest.raises(ValueError, match="redirecionamentos"):
        open_webpage("https://example.com")

    assert len(calls) == MAX_REDIRECTS + 1


def test_safe_redirect_is_followed(monkeypatch):
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        if len(calls) == 1:
            return FakeResponse(302, {"location": "/final"})
        return FakeResponse()

    monkeypatch.setattr("agent.tools.requests.get", fake_get)
    monkeypatch.setattr("agent.tools.socket.getaddrinfo", lambda *args, **kwargs: [(0, 0, 0, "", ("93.184.216.34", 0))])

    result = open_webpage("https://example.com/start")

    assert calls == ["https://example.com/start", "https://example.com/final"]
    assert "conteudo" in result
