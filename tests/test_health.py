from agent.health import run_health_checks


def test_health_checks_are_offline_and_healthy(tmp_path):
    report = run_health_checks(tmp_path / "health.db")
    assert report.ok, report.text()
    assert len(report.checks) >= 10
