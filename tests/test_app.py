import app


class DummyBrain:
    def ask(self, text):
        return f"resposta: {text}"


def test_cli_health_command_runs_without_calling_brain(monkeypatch, capsys):
    monkeypatch.setattr(app, "build_agent", lambda: DummyBrain())

    class Report:
        def text(self):
            return "SAÚDE DO SISTEMA: SAUDÁVEL"

    monkeypatch.setattr(app, "run_health_checks", lambda: Report())
    inputs = iter(["saude", "sair"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))

    app.main()

    output = capsys.readouterr().out
    assert "SAÚDE DO SISTEMA: SAUDÁVEL" in output
