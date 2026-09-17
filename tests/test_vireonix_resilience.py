from __future__ import annotations

import requests
import pytest

import agent.brain as brain_module
from agent.brain import SuperCerebro


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self.payload = payload if payload is not None else {"choices": [{"message": {"content": "ok"}}]}

    def raise_for_status(self):
        if self.status_code >= 400:
            error = requests.HTTPError(f"HTTP {self.status_code}")
            error.response = self
            raise error

    def json(self):
        return self.payload


def test_vireonix_retries_transient_http_error(monkeypatch, tmp_path):
    brain = SuperCerebro(timeout=1)
    calls = []
    responses = [FakeResponse(503), FakeResponse(200)]

    def post(*args, **kwargs):
        calls.append((args, kwargs))
        return responses.pop(0)

    sleeps = []
    monkeypatch.setattr(brain_module.requests, "post", post)
    monkeypatch.setattr(brain_module.time, "sleep", lambda seconds: sleeps.append(seconds))

    assert brain._call_vireonix([{"role": "user", "content": "teste"}]) == "ok"
    assert len(calls) == 2
    assert sleeps == [0.5]


def test_vireonix_retries_connection_timeout(monkeypatch):
    brain = SuperCerebro(timeout=1)
    calls = []

    def post(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            raise requests.Timeout("tempo esgotado")
        return FakeResponse()

    monkeypatch.setattr(brain_module.requests, "post", post)
    monkeypatch.setattr(brain_module.time, "sleep", lambda _: None)

    assert brain._call_vireonix([]) == "ok"
    assert len(calls) == 2


def test_vireonix_gives_up_after_retries(monkeypatch):
    brain = SuperCerebro(timeout=1)
    calls = []

    def post(*args, **kwargs):
        calls.append(1)
        raise requests.ConnectionError("sem conexão")

    monkeypatch.setattr(brain_module.requests, "post", post)
    monkeypatch.setattr(brain_module.time, "sleep", lambda _: None)

    with pytest.raises(RuntimeError, match="Falha ao conectar ao Vireonix"):
        brain._call_vireonix([])

    assert len(calls) == 3


def test_vireonix_invalid_payload_is_not_retried(monkeypatch):
    brain = SuperCerebro(timeout=1)
    calls = []

    def post(*args, **kwargs):
        calls.append(1)
        return FakeResponse(payload={"choices": []})

    monkeypatch.setattr(brain_module.requests, "post", post)
    monkeypatch.setattr(brain_module.time, "sleep", lambda _: None)

    with pytest.raises(RuntimeError, match="Resposta inválida"):
        brain._call_vireonix([])

    assert len(calls) == 1
