from __future__ import annotations

from pathlib import Path

from app.domains.agents import ops_agent as ops


def test_parse_targets_supports_multiple_delimiters() -> None:
    targets = ops.parse_targets(
        "backend=http://localhost:8000/health;engine=http://localhost:5001/health\nai=http://localhost:8080/ai/health"
    )
    assert [item["name"] for item in targets] == ["backend", "engine", "ai"]
    assert targets[1]["url"] == "http://localhost:5001/health"


def test_run_maintenance_cycle_writes_report(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        ops.settings,
        "ai_background_report_path",
        str(tmp_path / "latest.md"),
    )
    monkeypatch.setattr(
        ops,
        "collect_target_health",
        lambda: [
            {
                "name": "backend",
                "url": "http://localhost:8000/health",
                "ok": True,
                "status_code": 200,
                "latency_ms": 12,
                "summary": "ok",
                "payload": {"status": "ok"},
            },
            {
                "name": "engine",
                "url": "http://localhost:5001/health",
                "ok": False,
                "status_code": 503,
                "latency_ms": 45,
                "summary": "degraded",
                "payload": {"status": "degraded"},
            },
        ],
    )
    monkeypatch.setattr(
        ops,
        "generate_ai_summary",
        lambda results, trigger: "## Genel Durum\nServislerden biri sorunlu.",
    )

    status = ops.run_maintenance_cycle(trigger="test")

    assert status["last_status"] == "degraded"
    report_path = Path(status["last_report_path"])
    assert report_path.exists()
    assert "TestwrightAI AI Ops Report" in report_path.read_text(encoding="utf-8")


def test_read_last_report_returns_content(monkeypatch, tmp_path: Path) -> None:
    report = tmp_path / "latest.md"
    report.write_text("hello", encoding="utf-8")
    monkeypatch.setattr(ops, "ops_agent", ops.OpsAgentState())
    monkeypatch.setattr(ops.ops_agent, "last_report_path", str(report))

    result = ops.read_last_report()

    assert result["content"] == "hello"
