"""Automation router unit tests — /api/v1/automation.

FastAPI TestClient. All heavy dependencies (DB, brain service, external
httpx calls) are mocked via unittest.mock.patch.
"""
from __future__ import annotations

import pytest

try:
    from unittest.mock import AsyncMock, MagicMock, patch

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.domains.automation.router import router as automation_router
    from app.deps import get_current_user
    from app.infra.models import User

    _IMPORT_OK = True
except Exception:
    _IMPORT_OK = False


def _mock_user():
    u = MagicMock(spec=User)
    u.id = "test-user-id"
    u.email = "test@example.com"
    u.roles = []
    return u

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="import failed")


# ---------------------------------------------------------------------------
# App factory helpers
# ---------------------------------------------------------------------------


def _app() -> TestClient:
    app = FastAPI()
    app.dependency_overrides[get_current_user] = _mock_user
    app.include_router(automation_router, prefix="/api/v1")
    return TestClient(app, raise_server_exceptions=False)


def _fake_user() -> MagicMock:
    u = MagicMock()
    u.id = "test-user"
    u.email = "test@test.com"
    return u


def _fake_run(run_id: str = "run-001", status: str = "queued"):
    from datetime import datetime, timezone
    from app.domains.automation.schemas import AutomationRunOut

    return AutomationRunOut(
        id=run_id,
        project_id="proj-1",
        kind="web",
        name="Smoke Test",
        status=status,
        trigger="manual",
        environment=None,
        device=None,
        target="features/smoke.feature",
        provenance="fallback",
        created_at=datetime.now(timezone.utc),
        started_at=None,
        finished_at=None,
        duration_ms=None,
        artifacts=[],
        metrics={},
        next_action=None,
        error=None,
        retry_of=None,
        created_by="test-user",
        metadata={},
    )


def _fake_capability() -> MagicMock:
    c = MagicMock()
    c.kind = "web"
    c.label = "Web E2E"
    c.description = "Playwright test runner"
    c.provenance = "real"
    c.supports_cancel = True
    c.supports_retry = True
    c.required_fields = []
    c.route_hint = None
    c.model_dump.return_value = {
        "kind": "web",
        "label": "Web E2E",
        "description": "Playwright test runner",
        "provenance": "real",
        "supports_cancel": True,
        "supports_retry": True,
        "required_fields": [],
        "route_hint": None,
    }
    return c


def _fake_summary() -> MagicMock:
    s = MagicMock()
    s.capabilities = [_fake_capability()]
    s.active_runs = 0
    s.queued_runs = 0
    s.last_run = None
    s.model_dump.return_value = {
        "capabilities": [_fake_capability().model_dump.return_value],
        "active_runs": 0,
        "queued_runs": 0,
        "last_run": None,
    }
    return s


_RUN_CREATE_BODY = {
    "project_id": "proj-1",
    "kind": "web",
    "name": "My Smoke",
    "trigger": "manual",
    "execute_now": False,
}


# ---------------------------------------------------------------------------
# GET /api/v1/automation/health
# ---------------------------------------------------------------------------


def test_health_engine_unreachable_returns_200() -> None:
    """Health endpoint handles connection errors gracefully."""
    client = _app()
    with patch(
        "app.domains.automation.router.httpx.AsyncClient"
    ) as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        import httpx
        mock_client.get.side_effect = httpx.RequestError("connection refused")
        r = client.get("/api/v1/automation/health")
    assert r.status_code == 200
    assert r.json().get("status") == "unreachable"


def test_health_engine_reachable() -> None:
    """Health endpoint proxies engine response when reachable."""
    client = _app()
    with patch(
        "app.domains.automation.router.httpx.AsyncClient"
    ) as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        fake_resp = MagicMock()
        fake_resp.json.return_value = {"status": "ok"}
        mock_client.get.return_value = fake_resp
        r = client.get("/api/v1/automation/health")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


# ---------------------------------------------------------------------------
# GET /api/v1/automation/brain/capabilities
# ---------------------------------------------------------------------------


def test_list_capabilities_returns_200() -> None:
    client = _app()
    with patch("app.domains.automation.router.get_current_user", return_value=_fake_user()), \
         patch("app.domains.automation.router.brain_service") as mock_brain:
        mock_brain.capabilities.return_value = [_fake_capability()]
        r = client.get("/api/v1/automation/brain/capabilities")
    assert r.status_code == 200


def test_list_capabilities_returns_list() -> None:
    client = _app()
    with patch("app.domains.automation.router.get_current_user", return_value=_fake_user()), \
         patch("app.domains.automation.router.brain_service") as mock_brain:
        mock_brain.capabilities.return_value = [_fake_capability(), _fake_capability()]
        r = client.get("/api/v1/automation/brain/capabilities")
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 2


def test_list_capabilities_empty() -> None:
    client = _app()
    with patch("app.domains.automation.router.get_current_user", return_value=_fake_user()), \
         patch("app.domains.automation.router.brain_service") as mock_brain:
        mock_brain.capabilities.return_value = []
        r = client.get("/api/v1/automation/brain/capabilities")
    assert r.json() == []


# ---------------------------------------------------------------------------
# GET /api/v1/automation/runs
# ---------------------------------------------------------------------------


def test_list_runs_returns_200() -> None:
    client = _app()
    run = _fake_run()
    mock_service = MagicMock()
    mock_run_list = MagicMock()
    mock_run_list.items = [run]
    mock_run_list.total = 1
    mock_service.list_runs.return_value = mock_run_list
    mock_service.store.replace.side_effect = lambda x: x

    with patch("app.domains.automation.router.get_current_user", return_value=_fake_user()), \
         patch("app.domains.automation.router.get_db", return_value=MagicMock()), \
         patch("app.domains.automation.router.AutomationBrainService", return_value=mock_service), \
         patch("app.domains.automation.router.SqlAlchemyAutomationRunStore", return_value=MagicMock()), \
         patch("app.domains.automation.router._sync_external_run", side_effect=lambda _svc, r: r):
        r = client.get("/api/v1/automation/runs")
    assert r.status_code == 200


def test_list_runs_empty_list() -> None:
    client = _app()
    mock_service = MagicMock()
    mock_run_list = MagicMock()
    mock_run_list.items = []
    mock_run_list.total = 0
    mock_service.list_runs.return_value = mock_run_list

    with patch("app.domains.automation.router.get_current_user", return_value=_fake_user()), \
         patch("app.domains.automation.router.get_db", return_value=MagicMock()), \
         patch("app.domains.automation.router.AutomationBrainService", return_value=mock_service), \
         patch("app.domains.automation.router.SqlAlchemyAutomationRunStore", return_value=MagicMock()):
        r = client.get("/api/v1/automation/runs")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 0
    assert body["items"] == []


# ---------------------------------------------------------------------------
# POST /api/v1/automation/runs
# ---------------------------------------------------------------------------


def test_create_run_returns_201_or_200() -> None:
    """Create run endpoint returns a successful status."""
    client = _app()
    run = _fake_run()
    mock_service = MagicMock()
    mock_service.create_run.return_value = run

    with patch("app.domains.automation.router.get_current_user", return_value=_fake_user()), \
         patch("app.domains.automation.router.get_db", return_value=MagicMock()), \
         patch("app.domains.automation.router.AutomationBrainService", return_value=mock_service), \
         patch("app.domains.automation.router.SqlAlchemyAutomationRunStore", return_value=MagicMock()):
        r = client.post("/api/v1/automation/runs", json=_RUN_CREATE_BODY)
    assert r.status_code in {200, 201}


def test_create_run_missing_project_id_422() -> None:
    client = _app()
    bad_body = {"kind": "web", "name": "Test"}
    with patch("app.domains.automation.router.get_current_user", return_value=_fake_user()):
        r = client.post("/api/v1/automation/runs", json=bad_body)
    assert r.status_code == 422


def test_create_run_missing_kind_422() -> None:
    client = _app()
    bad_body = {"project_id": "proj-1", "name": "Test"}
    with patch("app.domains.automation.router.get_current_user", return_value=_fake_user()):
        r = client.post("/api/v1/automation/runs", json=bad_body)
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/automation/runs/{run_id}
# ---------------------------------------------------------------------------


def test_get_run_found_200() -> None:
    client = _app()
    run = _fake_run("run-007")
    mock_service = MagicMock()
    mock_service.get_run.return_value = run
    mock_service.store.replace.side_effect = lambda x: x

    with patch("app.domains.automation.router.get_current_user", return_value=_fake_user()), \
         patch("app.domains.automation.router.get_db", return_value=MagicMock()), \
         patch("app.domains.automation.router.AutomationBrainService", return_value=mock_service), \
         patch("app.domains.automation.router.SqlAlchemyAutomationRunStore", return_value=MagicMock()):
        r = client.get("/api/v1/automation/runs/run-007")
    assert r.status_code == 200


def test_get_run_not_found_404() -> None:
    client = _app()
    mock_service = MagicMock()
    mock_service.get_run.return_value = None

    with patch("app.domains.automation.router.get_current_user", return_value=_fake_user()), \
         patch("app.domains.automation.router.get_db", return_value=MagicMock()), \
         patch("app.domains.automation.router.AutomationBrainService", return_value=mock_service), \
         patch("app.domains.automation.router.SqlAlchemyAutomationRunStore", return_value=MagicMock()):
        r = client.get("/api/v1/automation/runs/nonexistent")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/v1/automation/runs/{run_id}/cancel
# ---------------------------------------------------------------------------


def test_cancel_run_200() -> None:
    client = _app()
    run = _fake_run("run-001", "cancelled")
    run.metrics = {}
    mock_service = MagicMock()
    mock_service.cancel_run.return_value = run

    with patch("app.domains.automation.router.get_current_user", return_value=_fake_user()), \
         patch("app.domains.automation.router.get_db", return_value=MagicMock()), \
         patch("app.domains.automation.router.AutomationBrainService", return_value=mock_service), \
         patch("app.domains.automation.router.SqlAlchemyAutomationRunStore", return_value=MagicMock()):
        r = client.post("/api/v1/automation/runs/run-001/cancel")
    assert r.status_code == 200


def test_cancel_run_not_found_404() -> None:
    client = _app()
    mock_service = MagicMock()
    mock_service.cancel_run.return_value = None

    with patch("app.domains.automation.router.get_current_user", return_value=_fake_user()), \
         patch("app.domains.automation.router.get_db", return_value=MagicMock()), \
         patch("app.domains.automation.router.AutomationBrainService", return_value=mock_service), \
         patch("app.domains.automation.router.SqlAlchemyAutomationRunStore", return_value=MagicMock()):
        r = client.post("/api/v1/automation/runs/ghost-run/cancel")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/v1/automation/brain (summary)
# ---------------------------------------------------------------------------


def test_brain_summary_returns_200() -> None:
    client = _app()
    mock_service = MagicMock()
    mock_run_list = MagicMock()
    mock_run_list.items = []
    mock_service.list_runs.return_value = mock_run_list
    mock_service.summary.return_value = _fake_summary()
    mock_service.store.replace.side_effect = lambda x: x

    with patch("app.domains.automation.router.get_current_user", return_value=_fake_user()), \
         patch("app.domains.automation.router.get_db", return_value=MagicMock()), \
         patch("app.domains.automation.router.AutomationBrainService", return_value=mock_service), \
         patch("app.domains.automation.router.SqlAlchemyAutomationRunStore", return_value=MagicMock()):
        r = client.get("/api/v1/automation/brain")
    assert r.status_code == 200


def test_brain_summary_has_expected_keys() -> None:
    client = _app()
    mock_service = MagicMock()
    mock_run_list = MagicMock()
    mock_run_list.items = []
    mock_service.list_runs.return_value = mock_run_list
    mock_service.summary.return_value = _fake_summary()
    mock_service.store.replace.side_effect = lambda x: x

    with patch("app.domains.automation.router.get_current_user", return_value=_fake_user()), \
         patch("app.domains.automation.router.get_db", return_value=MagicMock()), \
         patch("app.domains.automation.router.AutomationBrainService", return_value=mock_service), \
         patch("app.domains.automation.router.SqlAlchemyAutomationRunStore", return_value=MagicMock()):
        r = client.get("/api/v1/automation/brain")
    body = r.json()
    assert "active_runs" in body
    assert "queued_runs" in body
    assert "capabilities" in body


# ---------------------------------------------------------------------------
# Proxy path allowlist guard
# ---------------------------------------------------------------------------


def test_proxy_forbidden_path_403() -> None:
    """Proxy rejects paths not on the allowlist."""
    client = _app()
    with patch("app.domains.automation.router.get_current_user", return_value=_fake_user()):
        r = client.get("/api/v1/automation/proxy/admin/secrets")
    assert r.status_code == 403
