from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.deps import get_current_user
from app.infra.database import get_db
from app.domains.automation.brain import AutomationRunStore
from app.domains.automation.router import router as automation_router


class _FakeUser:
    def __init__(self, user_id: str = "u1") -> None:
        self.id = user_id


def _client(monkeypatch) -> TestClient:
    app = FastAPI()
    store = AutomationRunStore()

    monkeypatch.setattr(
        "app.domains.automation.router.SqlAlchemyAutomationRunStore",
        lambda _db: store,
    )

    app.include_router(automation_router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: _FakeUser()
    app.dependency_overrides[get_db] = lambda: object()
    return TestClient(app)


def test_automation_brain_capabilities_and_run_lifecycle(monkeypatch) -> None:
    client = _client(monkeypatch)

    caps = client.get("/api/v1/automation/brain/capabilities")
    assert caps.status_code == 200
    kinds = {item["kind"] for item in caps.json()}
    assert {"web", "mobile", "api", "llm", "regression"}.issubset(kinds)

    created = client.post(
        "/api/v1/automation/runs",
        json={
            "project_id": "p1",
            "kind": "web",
            "name": "Login smoke",
            "target": "login.feature",
            "trigger": "manual",
            "environment": "local",
            "metadata": {"source_page": "automation_center"},
        },
    )
    assert created.status_code == 200
    run = created.json()
    assert run["status"] == "queued"
    assert run["next_action"]["href"].endswith("/p/p1/executions/new?feature=login.feature")

    listed = client.get("/api/v1/automation/runs?project_id=p1&limit=8")
    assert listed.status_code == 200
    body = listed.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == run["id"]

    summary = client.get("/api/v1/automation/brain?project_id=p1")
    assert summary.status_code == 200
    assert summary.json()["queued_runs"] == 1

    cancelled = client.post(f"/api/v1/automation/runs/{run['id']}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"

    retried = client.post(f"/api/v1/automation/runs/{run['id']}/retry")
    assert retried.status_code == 200
    assert retried.json()["retry_of"] == run["id"]
    assert retried.json()["trigger"] == "retry"


def test_automation_run_not_found_returns_404(monkeypatch) -> None:
    client = _client(monkeypatch)

    missing = client.get("/api/v1/automation/runs/arun_missing")
    assert missing.status_code == 404

    missing_cancel = client.post("/api/v1/automation/runs/arun_missing/cancel")
    assert missing_cancel.status_code == 404

    missing_retry = client.post("/api/v1/automation/runs/arun_missing/retry")
    assert missing_retry.status_code == 404


def test_web_run_can_execute_existing_suite_runner(monkeypatch) -> None:
    client = _client(monkeypatch)

    class _SuiteRun:
        run_id = "suite_123"
        status = "queued"

    async def _start_run(_req):
        return _SuiteRun()

    monkeypatch.setattr("app.domains.automation.router.suite_service.start_run", _start_run)
    monkeypatch.setattr("app.domains.automation.router.suite_service.get_run_status", lambda _run_id: None)

    created = client.post(
        "/api/v1/automation/runs",
        json={
            "project_id": "p1",
            "kind": "web",
            "name": "Login smoke",
            "target": "login.feature",
            "execute_now": True,
        },
    )

    assert created.status_code == 200
    run = created.json()
    assert run["status"] == "running"
    assert run["provenance"] == "real"
    assert run["metrics"]["external_runner"] == "automation_suite"
    assert run["metrics"]["external_run_id"] == "suite_123"


def test_mobile_run_can_execute_farm_runner(monkeypatch) -> None:
    client = _client(monkeypatch)

    class _MobileSession:
        def __init__(self, sid: str, device_id: str) -> None:
            self.id = sid
            self.device_id = device_id
            self.status = "running"
            self.started_at = datetime.now(timezone.utc)
            self.finished_at = None
            self.failure_message = None

    async def _start_suite(_req):
        return [_MobileSession("s_1", "pixel_7"), _MobileSession("s_2", "iphone_15")]

    monkeypatch.setattr("app.domains.automation.router.start_mobile_suite", _start_suite)

    created = client.post(
        "/api/v1/automation/runs",
        json={
            "project_id": "p1",
            "kind": "mobile",
            "name": "Mobile smoke",
            "execute_now": True,
            "metadata": {"parallel": 2, "mode": "simulation"},
        },
    )

    assert created.status_code == 200
    run = created.json()
    assert run["status"] == "running"
    assert run["provenance"] == "real"
    assert run["metrics"]["external_runner"] == "mobile_farm"
    assert run["metrics"]["external_session_ids"] == ["s_1", "s_2"]


def test_api_run_can_execute_test_cases(monkeypatch) -> None:
    client = _client(monkeypatch)

    async def _execute_test_cases(_db, project_id, test_case_ids, *, environment_id=None, stop_on_failure=False):
        assert project_id == "p1"
        assert test_case_ids == ["tc_1", "tc_2"]
        assert environment_id == "env_1"
        assert stop_on_failure is True
        return {
            "run_id": "api_run_123",
            "total": 2,
            "passed": 2,
            "failed": 0,
            "errors": 0,
            "duration_ms": 42.4,
            "results": [],
        }

    monkeypatch.setattr(
        "app.domains.automation.router.api_testing_service.execute_test_cases",
        _execute_test_cases,
    )

    created = client.post(
        "/api/v1/automation/runs",
        json={
            "project_id": "p1",
            "kind": "api",
            "name": "API smoke",
            "execute_now": True,
            "metadata": {
                "test_case_ids": ["tc_1", "tc_2"],
                "environment_id": "env_1",
                "stop_on_failure": True,
            },
        },
    )

    assert created.status_code == 200
    run = created.json()
    assert run["status"] == "passed"
    assert run["provenance"] == "real"
    assert run["metrics"]["external_runner"] == "api_testing"
    assert run["metrics"]["external_run_id"] == "api_run_123"
    assert run["metrics"]["passed"] == 2


def test_regression_run_can_generate_suggestions(monkeypatch) -> None:
    client = _client(monkeypatch)

    def _suggest(_db, project_id, body):
        assert project_id == "p1"
        assert "kritik" in body.extra_instructions
        return SimpleNamespace(
            sets=[
                {
                    "name": "Critical Smoke",
                    "description": "Kritik akışlar",
                    "scenario_ids": ["scn_1", "scn_2"],
                    "priority": "high",
                }
            ]
        )

    monkeypatch.setattr(
        "app.domains.automation.router.flow_regression_svc.suggest_regression_sets_for_project",
        _suggest,
    )

    created = client.post(
        "/api/v1/automation/runs",
        json={
            "project_id": "p1",
            "kind": "regression",
            "name": "Regression suggestion",
            "execute_now": True,
            "metadata": {"extra_instructions": "kritik akışları öne çıkar"},
        },
    )

    assert created.status_code == 200
    run = created.json()
    assert run["status"] == "passed"
    assert run["provenance"] == "real"
    assert run["metrics"]["external_runner"] == "regression_suggester"
    assert run["metrics"]["suggested_set_count"] == 1
    assert run["metrics"]["covered_scenario_count"] == 2
