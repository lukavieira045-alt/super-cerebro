from __future__ import annotations

from agent import research


def test_deep_research_deduplicates_urls_and_collects_sources(monkeypatch):
    opened = []

    def fake_search(query, limit=5):
        assert query == "teste"
        assert limit == 7
        return (
            "TITULO: Fonte A\nURL: https://example.com/a\nRESUMO: A\n"
            "TITULO: Fonte A duplicada\nURL: https://example.com/a\nRESUMO: A2\n"
            "TITULO: Fonte B\nURL: https://example.com/b\nRESUMO: B"
        )

    def fake_open(url):
        opened.append(url)
        return f"Conteúdo de {url}"

    monkeypatch.setattr(research, "search_web", fake_search)
    monkeypatch.setattr(research, "open_webpage", fake_open)

    result = research.deep_research("teste", sources=4)

    assert opened == ["https://example.com/a", "https://example.com/b"]
    assert result.count("FONTE 1") == 1
    assert result.count("FONTE 2") == 1
    assert "Conteúdo de https://example.com/a" in result
    assert "Conteúdo de https://example.com/b" in result


def test_deep_research_keeps_going_when_a_source_fails(monkeypatch):
    def fake_search(query, limit=5):
        return (
            "URL: https://example.com/falha\n"
            "URL: https://example.com/ok"
        )

    def fake_open(url):
        if url.endswith("falha"):
            raise RuntimeError("fonte indisponível")
        return "Fonte disponível"

    monkeypatch.setattr(research, "search_web", fake_search)
    monkeypatch.setattr(research, "open_webpage", fake_open)

    result = research.deep_research("teste", sources=2)

    assert "Não foi possível abrir esta fonte" in result
    assert "Fonte disponível" in result


def test_deep_research_rejects_empty_query(monkeypatch):
    called = False

    def fake_search(*args, **kwargs):
        nonlocal called
        called = True
        return ""

    monkeypatch.setattr(research, "search_web", fake_search)

    try:
        research.deep_research("   ")
    except ValueError as exc:
        assert "consulta vazia" in str(exc)
    else:
        raise AssertionError("consulta vazia deveria gerar ValueError")

    assert called is False


def test_deep_research_clamps_requested_sources(monkeypatch):
    limits = []
    opened = []

    def fake_search(query, limit=5):
        limits.append(limit)
        return "\n".join(f"URL: https://example.com/{i}" for i in range(10))

    def fake_open(url):
        opened.append(url)
        return "conteúdo"

    monkeypatch.setattr(research, "search_web", fake_search)
    monkeypatch.setattr(research, "open_webpage", fake_open)

    research.deep_research("teste", sources=99)

    assert limits == [8]
    assert len(opened) == 5


def test_deep_research_enforces_minimum_source_request(monkeypatch):
    limits = []

    def fake_search(query, limit=5):
        limits.append(limit)
        return "URL: https://example.com/a\nURL: https://example.com/b"

    monkeypatch.setattr(research, "search_web", fake_search)
    monkeypatch.setattr(research, "open_webpage", lambda url: "conteúdo")

    research.deep_research("teste", sources=1)

    assert limits == [5]
