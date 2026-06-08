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
    from app.infra.database import get_db
    from app.infra.models import User

    _IMPORT_OK = True
except Exception:
    _IMPORT_OK = False


def _mock_user():
    u = MagicMock(spec=User)
    # Geçerli UUID — RBAC sorgularında "user_id::UUID" cast'i hatasız çalışsın.
    u.id = "550e8400-e29b-41d4-a716-446655440000"
    u.email = "test@example.com"
    u.tenant_id = "00000000-0000-0000-0000-000000000001"
    # Admin yetkisi — automation run authorization (project membership) bypass eder.
    admin_perm = MagicMock()
    admin_perm.permission = "admin.*"
    admin_role = MagicMock()
    admin_role.permissions = [admin_perm]
    u.roles = [admin_role]
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


# ---------------------------------------------------------------------------
# IDOR / project membership authorization (NON-admin user)
#
# _mock_user() above grants "admin.*", so all preceding tests take the admin
# bypass branch in _require_run_access / list_automation_runs. The user below
# has roles=[] (no permissions), forcing the real membership check that queries
# the DB via db.scalar() / db.scalars().
# ---------------------------------------------------------------------------


def _mock_nonadmin_user():
    """User with no roles → no permissions → membership check is enforced."""
    u = MagicMock(spec=User)
    u.id = "550e8400-e29b-41d4-a716-446655440000"
    u.email = "member@example.com"
    u.tenant_id = "00000000-0000-0000-0000-000000000001"
    u.roles = []
    return u


def _app_nonadmin(mock_db) -> TestClient:
    """App wired to a non-admin user and a mocked DB session via dependency_overrides."""
    app = FastAPI()
    app.dependency_overrides[get_current_user] = _mock_nonadmin_user
    app.dependency_overrides[get_db] = lambda: mock_db
    app.include_router(automation_router, prefix="/api/v1")
    return TestClient(app, raise_server_exceptions=False)


def test_get_run_non_member_forbidden_403() -> None:
    """GET run → 403 when the non-admin user is not a member of the run's project."""
    mock_db = MagicMock()
    mock_db.scalar.return_value = 0  # not a member
    client = _app_nonadmin(mock_db)

    run = _fake_run("run-100")
    mock_service = MagicMock()
    mock_service.get_run.return_value = run

    with patch("app.domains.automation.router.AutomationBrainService", return_value=mock_service), \
         patch("app.domains.automation.router.SqlAlchemyAutomationRunStore", return_value=MagicMock()):
        r = client.get("/api/v1/automation/runs/run-100")
    assert r.status_code == 403


def test_get_run_member_allowed_200() -> None:
    """GET run → 200 when the non-admin user IS a member of the run's project."""
    mock_db = MagicMock()
    mock_db.scalar.return_value = 1  # is a member
    client = _app_nonadmin(mock_db)

    run = _fake_run("run-101")
    mock_service = MagicMock()
    mock_service.get_run.return_value = run

    with patch("app.domains.automation.router.AutomationBrainService", return_value=mock_service), \
         patch("app.domains.automation.router.SqlAlchemyAutomationRunStore", return_value=MagicMock()):
        r = client.get("/api/v1/automation/runs/run-101")
    assert r.status_code == 200


def test_cancel_run_non_member_forbidden_403() -> None:
    """POST cancel → 403 when the non-admin user is not a member of the run's project."""
    mock_db = MagicMock()
    mock_db.scalar.return_value = 0  # not a member
    client = _app_nonadmin(mock_db)

    run = _fake_run("run-102")
    mock_service = MagicMock()
    mock_service.get_run.return_value = run

    with patch("app.domains.automation.router.AutomationBrainService", return_value=mock_service), \
         patch("app.domains.automation.router.SqlAlchemyAutomationRunStore", return_value=MagicMock()):
        r = client.post("/api/v1/automation/runs/run-102/cancel")
    assert r.status_code == 403
    # Membership is rejected before cancellation is attempted.
    mock_service.cancel_run.assert_not_called()


def test_list_runs_project_id_not_member_forbidden_403() -> None:
    """GET /runs?project_id=proj-1 → 403 when proj-1 is not in the user's member projects."""
    mock_db = MagicMock()
    mock_db.scalars.return_value = []  # user is a member of no projects
    client = _app_nonadmin(mock_db)

    mock_service = MagicMock()

    with patch("app.domains.automation.router.AutomationBrainService", return_value=mock_service), \
         patch("app.domains.automation.router.SqlAlchemyAutomationRunStore", return_value=MagicMock()):
        r = client.get("/api/v1/automation/runs", params={"project_id": "proj-1"})
    assert r.status_code == 403
    # Access is denied before any runs are listed.
    mock_service.list_runs.assert_not_called()
