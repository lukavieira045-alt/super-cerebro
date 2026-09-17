from __future__ import annotations

import requests

from agent.brain import SuperCerebro
from agent.memory import Memory
from agent.learning import Learning


class FakeResponse:
    def __init__(self, payload=None, status_code=200):
        self._payload = payload or {"choices": [{"message": {"content": "ok"}}]}
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            error = requests.HTTPError(f"HTTP {self.status_code}")
            error.response = self
            raise error

    def json(self):
        return self._payload


def make_brain(tmp_path):
    return SuperCerebro(
        memory=Memory(tmp_path / "memory.db"),
        learning=Learning(tmp_path / "memory.db"),
        timeout=1,
    )


def test_vireonix_retries_timeout_then_succeeds(tmp_path, monkeypatch):
    brain = make_brain(tmp_path)
    calls = []
    sleeps = []

    def fake_post(*args, **kwargs):
        calls.append(kwargs)
        if len(calls) < 3:
            raise requests.Timeout("tempo esgotado")
        return FakeResponse()

    monkeypatch.setattr("agent.brain.requests.post", fake_post)
    monkeypatch.setattr("agent.brain.time.sleep", sleeps.append)

    assert brain._call_vireonix([{"role": "user", "content": "teste"}]) == "ok"
    assert len(calls) == 3
    assert sleeps == [0.5, 1.0]


def test_vireonix_retries_transient_http_status(tmp_path, monkeypatch):
    brain = make_brain(tmp_path)
    calls = []

    def fake_post(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            return FakeResponse(status_code=503)
        return FakeResponse()

    monkeypatch.setattr("agent.brain.requests.post", fake_post)
    monkeypatch.setattr("agent.brain.time.sleep", lambda _: None)

    assert brain._call_vireonix([{"role": "user", "content": "teste"}]) == "ok"
    assert len(calls) == 2


def test_vireonix_does_not_retry_permanent_http_error(tmp_path, monkeypatch):
    brain = make_brain(tmp_path)
    calls = []

    def fake_post(*args, **kwargs):
        calls.append(1)
        return FakeResponse(status_code=400)

    monkeypatch.setattr("agent.brain.requests.post", fake_post)
    monkeypatch.setattr("agent.brain.time.sleep", lambda _: None)

    try:
        brain._call_vireonix([{"role": "user", "content": "teste"}])
        assert False, "era esperado RuntimeError"
    except RuntimeError as exc:
        assert "Falha ao conectar ao Vireonix" in str(exc)

    assert len(calls) == 1


def test_vireonix_exhausted_retries_return_controlled_error(tmp_path, monkeypatch):
    brain = make_brain(tmp_path)
    calls = []

    def fake_post(*args, **kwargs):
        calls.append(1)
        raise requests.ConnectionError("sem conexão")

    monkeypatch.setattr("agent.brain.requests.post", fake_post)
    monkeypatch.setattr("agent.brain.time.sleep", lambda _: None)

    try:
        brain._call_vireonix([{"role": "user", "content": "teste"}])
        assert False, "era esperado RuntimeError"
    except RuntimeError as exc:
        assert "Falha ao conectar ao Vireonix" in str(exc)

    assert len(calls) == 3
