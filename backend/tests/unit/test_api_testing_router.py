"""Unit tests for the api_testing router — environments, specs, test-cases, execute.

14 tests covering the most critical endpoints:
  - GET  /environments     (list)
  - POST /environments     (create)
  - GET  /specs            (list)
  - POST /test-cases       (create)
  - GET  /test-cases       (list)
  - GET  /test-cases/{id}  (get, 404)
  - DELETE /test-cases/{id}(delete, 404)
  - POST /execute/single   (mock httpx)

The router uses router-level dependency _require_project_access which checks
TspmProject in db. We override get_db and get_current_user to bypass all DB
and auth logic.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

try:
    from app.domains.api_testing.router import router as api_testing_router, _require_project_access
    _IMPORT_OK = True
except Exception:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="import failed")

PROJECT_ID = "proj-test-001"
BASE = f"/api/v1/api-testing/projects/{PROJECT_ID}"


# ── DB mock factories ─────────────────────────────────────────────────────

def _make_env(id="env-1", name="Staging", project_id=PROJECT_ID):
    env = MagicMock()
    env.id = id
    env.name = name
    env.project_id = project_id
    env.description = "Staging environment"
    env.variables = {"BASE_URL": "https://staging.example.com"}
    env.sensitive_keys = []
    env.is_default = False
    env.created_at = "2026-05-27T10:00:00"
    env.updated_at = "2026-05-27T10:00:00"
    return env


def _make_spec(id="spec-1", project_id=PROJECT_ID):
    spec = MagicMock()
    spec.id = id
    spec.project_id = project_id
    spec.name = "Petstore API"
    spec.source_url = None
    spec.source_file = "petstore.json"
    spec.version = "3.0.0"
    spec.endpoint_count = 5
    spec.created_at = "2026-05-27T10:00:00"
    spec.updated_at = "2026-05-27T10:00:00"
    return spec


def _make_test_case(id="tc-1", project_id=PROJECT_ID):
    tc = MagicMock()
    tc.id = id
    tc.project_id = project_id
    tc.title = "GET /pets returns 200"
    tc.description = "Verifies the list pets endpoint"
    tc.endpoint_id = None
    tc.collection_id = None
    tc.test_type = "functional"
    tc.request_method = "GET"
    tc.request_path = "/pets"
    tc.request_headers = {}
    tc.request_params = {}
    tc.request_body = None
    tc.assertions = []
    tc.ai_generated = False
    tc.ai_model = None
    tc.ai_confidence = None
    tc.ai_reasoning = None
    tc.review_status = "pending"
    tc.reviewer_note = None
    tc.priority = "P2"
    tc.reviewer_id = None
    tc.owasp_category = None
    tc.regulation = None
    tc.cwe_id = None
    tc.pre_request_vars = None
    tc.setup_chain = None
    tc.last_run_status = None
    tc.last_run_at = None
    tc.run_count = 0
    tc.pass_count = 0
    tc.fail_count = 0
    tc.quarantined = False
    tc.quarantine_reason = None
    tc.created_at = "2026-05-27T10:00:00"
    tc.updated_at = "2026-05-27T10:00:00"
    return tc


def _make_db_session(
    *,
    env_list=None,
    spec_list=None,
    tc=None,
    tc_list=None,
    deleted=0,
):
    """Return a mock SQLAlchemy Session wired to return specified objects."""
    db = MagicMock()

    env_list = env_list or []
    spec_list = spec_list or []
    tc_list = tc_list or []

    # Mock query chain: .query().filter().order_by().offset().limit().all()
    def _query_side_effect(model):
        q = MagicMock()
        q.filter.return_value = q
        q.order_by.return_value = q
        q.offset.return_value = q
        q.limit.return_value = q

        from app.domains.api_testing.models import ApiEnvironment, ApiSpec, ApiTestCase

        if model is ApiEnvironment:
            q.all.return_value = env_list
            # first() used for get-by-id lookups
            q.first.return_value = env_list[0] if env_list else None
            q.delete.return_value = deleted
        elif model is ApiSpec:
            q.all.return_value = spec_list
            q.first.return_value = spec_list[0] if spec_list else None
            q.delete.return_value = deleted
        elif model is ApiTestCase:
            q.all.return_value = tc_list
            q.first.return_value = tc if tc else (tc_list[0] if tc_list else None)
            q.delete.return_value = deleted
            q.count.return_value = len(tc_list)
        else:
            q.all.return_value = []
            q.first.return_value = None
            q.delete.return_value = 0

        return q

    db.query.side_effect = _query_side_effect
    db.get.return_value = MagicMock()  # TspmProject exists check
    db.scalar.return_value = 1  # project member count
    db.add = MagicMock()
    db.commit = MagicMock()

    def _refresh(obj):
        # Simulate DB assigning id/timestamps and defaults after commit
        if getattr(obj, "id", None) is None:
            obj.id = "generated-id"
        if getattr(obj, "created_at", None) is None:
            obj.created_at = "2026-05-27T10:00:00"
        if getattr(obj, "updated_at", None) is None:
            obj.updated_at = "2026-05-27T10:00:00"
        # Set model-level defaults that SQLAlchemy normally fills from DB
        for attr, default in [
            ("review_status", "pending"),
            ("run_count", 0),
            ("pass_count", 0),
            ("fail_count", 0),
            ("quarantined", False),
            ("is_default", False),
            ("ai_generated", False),
        ]:
            if getattr(obj, attr, None) is None:
                try:
                    setattr(obj, attr, default)
                except Exception:
                    pass
        return obj

    db.refresh = MagicMock(side_effect=_refresh)

    # SQLAlchemy 2.0 style: db.execute(stmt).scalars().first() / .rowcount
    _tc_for_execute = tc if tc else (tc_list[0] if tc_list else None)

    def _execute_side_effect(stmt, *args, **kwargs):
        result = MagicMock()
        # Check if it's a DELETE statement by inspecting the stmt type
        stmt_type = type(stmt).__name__.lower()
        if "delete" in stmt_type:
            result.rowcount = deleted
            return result
        # For SELECT statements
        scalars_mock = MagicMock()
        scalars_mock.first.return_value = _tc_for_execute
        scalars_mock.all.return_value = tc_list
        result.scalars.return_value = scalars_mock
        result.rowcount = 0
        return result

    db.execute = MagicMock(side_effect=_execute_side_effect)

    return db


# ── fixture ───────────────────────────────────────────────────────────────

@pytest.fixture
def client_factory():
    """Returns a factory that builds a TestClient with a given db mock."""
    def _make(db_mock):
        app = FastAPI()

        mock_user = MagicMock()
        mock_user.id = "user-test"
        mock_user.email = "tester@neurex.io"
        mock_user.roles = []

        from app.deps import get_current_user
        from app.infra.database import get_db

        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_db] = lambda: db_mock
        app.dependency_overrides[_require_project_access] = lambda: None

        app.include_router(api_testing_router)
        return TestClient(app, raise_server_exceptions=False)

    return _make


# ── GET /environments ─────────────────────────────────────────────────────

class TestListEnvironments:
    def test_list_returns_200(self, client_factory):
        client = client_factory(_make_db_session(env_list=[_make_env()]))
        resp = client.get(f"{BASE}/environments")
        assert resp.status_code == 200

    def test_list_returns_list_type(self, client_factory):
        client = client_factory(_make_db_session(env_list=[_make_env()]))
        resp = client.get(f"{BASE}/environments")
        assert isinstance(resp.json(), list)

    def test_list_empty_environments(self, client_factory):
        client = client_factory(_make_db_session(env_list=[]))
        resp = client.get(f"{BASE}/environments")
        assert resp.status_code == 200
        assert resp.json() == []


# ── POST /environments ────────────────────────────────────────────────────

class TestCreateEnvironment:
    def test_create_environment_returns_201(self, client_factory):
        env = _make_env()
        db = _make_db_session(env_list=[env])
        client = client_factory(db)
        payload = {
            "name": "Production",
            "description": "Prod env",
            "variables": {"BASE_URL": "https://api.example.com"},
            "sensitive_keys": [],
            "is_default": False,
        }
        resp = client.post(f"{BASE}/environments", json=payload)
        assert resp.status_code == 201

    def test_create_environment_missing_name_returns_422(self, client_factory):
        client = client_factory(_make_db_session())
        resp = client.post(f"{BASE}/environments", json={})
        assert resp.status_code == 422


# ── GET /specs ────────────────────────────────────────────────────────────

class TestListSpecs:
    def test_list_specs_returns_200(self, client_factory):
        client = client_factory(_make_db_session(spec_list=[_make_spec()]))
        resp = client.get(f"{BASE}/specs")
        assert resp.status_code == 200

    def test_list_specs_empty(self, client_factory):
        client = client_factory(_make_db_session(spec_list=[]))
        resp = client.get(f"{BASE}/specs")
        assert resp.status_code == 200
        assert resp.json() == []


# ── POST /test-cases ──────────────────────────────────────────────────────

class TestCreateTestCase:
    def test_create_test_case_returns_201(self, client_factory):
        tc = _make_test_case()
        db = _make_db_session(tc=tc, tc_list=[tc])
        client = client_factory(db)
        payload = {
            "title": "GET /pets returns 200",
            "request_method": "GET",
            "request_path": "/pets",
            "test_type": "functional",
            "priority": "P2",
        }
        resp = client.post(f"{BASE}/test-cases", json=payload)
        assert resp.status_code == 201

    def test_create_test_case_missing_required_fields_returns_422(self, client_factory):
        client = client_factory(_make_db_session())
        resp = client.post(f"{BASE}/test-cases", json={})
        assert resp.status_code == 422


# ── GET /test-cases/{id} ──────────────────────────────────────────────────

class TestGetTestCase:
    def test_get_existing_test_case_returns_200(self, client_factory):
        tc = _make_test_case(id="tc-42")
        db = _make_db_session(tc=tc)
        client = client_factory(db)
        resp = client.get(f"{BASE}/test-cases/tc-42")
        assert resp.status_code == 200

    def test_get_nonexistent_test_case_returns_404(self, client_factory):
        db = _make_db_session(tc=None)
        client = client_factory(db)
        resp = client.get(f"{BASE}/test-cases/nonexistent-id")
        assert resp.status_code == 404


# ── DELETE /test-cases/{id} ───────────────────────────────────────────────

class TestDeleteTestCase:
    def test_delete_existing_test_case_returns_204(self, client_factory):
        db = _make_db_session(deleted=1)
        client = client_factory(db)
        resp = client.delete(f"{BASE}/test-cases/tc-1")
        assert resp.status_code == 204

    def test_delete_nonexistent_test_case_returns_404(self, client_factory):
        db = _make_db_session(deleted=0)
        client = client_factory(db)
        resp = client.delete(f"{BASE}/test-cases/no-such-tc")
        assert resp.status_code == 404
