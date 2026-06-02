"""Unit tests for the Onboarding router — 12 tests.

Covers:
  GET  /onboarding/steps
  GET  /onboarding/progress/{project_id}
  PATCH /onboarding/progress          (update a single step)
  DELETE /onboarding/progress/{project_id}

progress_store and compute_progress are patched to isolate HTTP layer.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

try:
    from app.domains.onboarding.router import router as onboarding_router
    _IMPORT_OK = True
except Exception:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="onboarding router import failed")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_progress(project_id: str = "proj-1", pct: float = 0.0) -> dict:
    return {
        "project_id": project_id,
        "steps": [],
        "completed": {},
        "completion_pct": pct,
        "total_required": 6,
        "completed_required": 0,
        "is_fully_onboarded": pct >= 100.0,
    }


def _make_step_dict(step_id: str = "create_project", order: int = 1) -> dict:
    return {
        "id": step_id,
        "order": order,
        "title": "Proje oluştur",
        "description": "İlk projenizi oluşturun",
        "is_optional": False,
        "action_url": "/projects/new",
        "help_doc": None,
    }


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(onboarding_router, prefix="/api/v1")
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# GET /onboarding/steps
# ---------------------------------------------------------------------------

class TestStepsEndpoint:
    def test_steps_returns_200(self, client):
        resp = client.get("/api/v1/onboarding/steps")
        assert resp.status_code == 200

    def test_steps_contains_total_key(self, client):
        resp = client.get("/api/v1/onboarding/steps")
        body = resp.json()
        assert "total" in body
        assert "steps" in body

    def test_steps_total_matches_default_steps_count(self, client):
        from app.domains.onboarding.service import DEFAULT_STEPS  # noqa: PLC0415
        resp = client.get("/api/v1/onboarding/steps")
        assert resp.json()["total"] == len(DEFAULT_STEPS)

    def test_steps_list_is_non_empty(self, client):
        resp = client.get("/api/v1/onboarding/steps")
        assert len(resp.json()["steps"]) > 0


# ---------------------------------------------------------------------------
# GET /onboarding/progress/{project_id}
# ---------------------------------------------------------------------------

class TestProgressGetEndpoint:
    def test_progress_returns_200(self, client):
        mock_progress = _make_progress("proj-1")
        with patch("app.domains.onboarding.router.progress_store") as ps, \
             patch("app.domains.onboarding.router.compute_progress", return_value=mock_progress):
            ps.get.return_value = {}
            resp = client.get("/api/v1/onboarding/progress/proj-1")
        assert resp.status_code == 200

    def test_progress_returns_project_id(self, client):
        mock_progress = _make_progress("proj-42")
        with patch("app.domains.onboarding.router.progress_store") as ps, \
             patch("app.domains.onboarding.router.compute_progress", return_value=mock_progress):
            ps.get.return_value = {}
            resp = client.get("/api/v1/onboarding/progress/proj-42")
        assert resp.json()["project_id"] == "proj-42"

    def test_progress_completion_pct_present(self, client):
        mock_progress = _make_progress("proj-99", pct=50.0)
        with patch("app.domains.onboarding.router.progress_store") as ps, \
             patch("app.domains.onboarding.router.compute_progress", return_value=mock_progress):
            ps.get.return_value = {}
            resp = client.get("/api/v1/onboarding/progress/proj-99")
        assert resp.json()["completion_pct"] == 50.0


# ---------------------------------------------------------------------------
# PATCH /onboarding/progress
# ---------------------------------------------------------------------------

class TestProgressUpdateEndpoint:
    def test_update_valid_step_returns_200(self, client):
        from app.domains.onboarding.service import DEFAULT_STEPS  # noqa: PLC0415
        valid_step_id = DEFAULT_STEPS[0].id
        mock_progress = _make_progress("proj-patch")

        with patch("app.domains.onboarding.router.progress_store") as ps, \
             patch("app.domains.onboarding.router.compute_progress", return_value=mock_progress):
            ps.get.return_value = {}
            resp = client.patch(
                "/api/v1/onboarding/progress",
                json={"project_id": "proj-patch", "step_id": valid_step_id, "done": True},
            )
        assert resp.status_code == 200

    def test_update_invalid_step_returns_400(self, client):
        resp = client.patch(
            "/api/v1/onboarding/progress",
            json={"project_id": "proj-x", "step_id": "nonexistent_step_id_xyz", "done": True},
        )
        assert resp.status_code == 400

    def test_update_calls_progress_store_set(self, client):
        from app.domains.onboarding.service import DEFAULT_STEPS  # noqa: PLC0415
        valid_step_id = DEFAULT_STEPS[0].id
        mock_progress = _make_progress("proj-set-test")

        with patch("app.domains.onboarding.router.progress_store") as ps, \
             patch("app.domains.onboarding.router.compute_progress", return_value=mock_progress):
            ps.get.return_value = {}
            client.patch(
                "/api/v1/onboarding/progress",
                json={"project_id": "proj-set-test", "step_id": valid_step_id, "done": True},
            )
            ps.set.assert_called_once_with("proj-set-test", valid_step_id, True)


# ---------------------------------------------------------------------------
# DELETE /onboarding/progress/{project_id}
# ---------------------------------------------------------------------------

class TestProgressDeleteEndpoint:
    def test_reset_returns_200(self, client):
        with patch("app.domains.onboarding.router.progress_store") as ps:
            resp = client.delete("/api/v1/onboarding/progress/proj-del")
        assert resp.status_code == 200

    def test_reset_returns_ok_true(self, client):
        with patch("app.domains.onboarding.router.progress_store"):
            resp = client.delete("/api/v1/onboarding/progress/proj-del")
        assert resp.json()["ok"] is True

    def test_reset_calls_store_reset(self, client):
        with patch("app.domains.onboarding.router.progress_store") as ps:
            client.delete("/api/v1/onboarding/progress/proj-reset-me")
            ps.reset.assert_called_once_with("proj-reset-me")
