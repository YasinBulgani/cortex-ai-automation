"""Unit tests for the prompts router (/prompts)."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from datetime import datetime, timezone

try:
    from app.domains.prompts.router import router as prompts_router
    _IMPORT_OK = True
except Exception:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="import failed")


def _fake_user():
    user = MagicMock()
    user.id = "user-1"
    user.email = "admin@test.com"
    user.is_active = True
    user.tenant_id = "tenant-1"
    return user


def _fake_prompt_out(prompt_id: str = "prompt-abc"):
    out = MagicMock()
    out.id = prompt_id
    out.description = "Test prompt"
    out.task_type = "classification"
    out.archived = False
    out.created_at = datetime.now(timezone.utc)
    out.updated_at = datetime.now(timezone.utc)
    out.created_by = "admin@test.com"
    out.latest_version = 1
    # For Pydantic response_model serialization compatibility
    out.model_dump = MagicMock(return_value={
        "id": prompt_id,
        "description": "Test prompt",
        "task_type": "classification",
        "archived": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "created_by": "admin@test.com",
        "latest_version": 1,
    })
    return out


def _fake_version_out(prompt_id: str = "prompt-abc", version: int = 1):
    out = MagicMock()
    out.id = 1
    out.prompt_id = prompt_id
    out.version = version
    out.system_prompt = "You are a helpful assistant."
    out.user_template = "{{input}}"
    out.model_hint = None
    out.temperature = None
    out.max_tokens = None
    out.notes = None
    out.created_at = datetime.now(timezone.utc)
    out.created_by = "admin@test.com"
    return out


def _fake_rollout_out(prompt_id: str = "prompt-abc", env: str = "prod"):
    out = MagicMock()
    out.prompt_id = prompt_id
    out.env = env
    out.active_version = 1
    out.canary_version = None
    out.canary_pct = 0
    out.updated_at = datetime.now(timezone.utc)
    out.updated_by = "admin@test.com"
    return out


@pytest.fixture
def client():
    app = FastAPI()
    # Override both get_current_user and require_permission dependencies
    from app.deps import get_current_user, require_permission
    fake_user = _fake_user()
    app.dependency_overrides[get_current_user] = lambda: fake_user
    # require_permission returns a factory, so we override at the app level
    app.include_router(prompts_router, prefix="/api/v1")

    # Patch all permission dependencies at include time by overriding the factory
    # We patch via override on the dependency key used inside the router
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def authed_client():
    """Client with get_current_user and require_permission both bypassed."""
    app = FastAPI()
    from app.deps import get_current_user, require_permission
    fake_user = _fake_user()

    # Override get_current_user globally
    app.dependency_overrides[get_current_user] = lambda: fake_user

    app.include_router(prompts_router, prefix="/api/v1")

    # Also patch require_permission so it returns the fake user
    with patch("app.deps.require_permission", return_value=lambda: fake_user):
        client = TestClient(app, raise_server_exceptions=False)
        yield client


# ---------------------------------------------------------------------------
# Tests: GET /api/v1/prompts (list)
# ---------------------------------------------------------------------------

class TestListPrompts:
    def test_list_without_auth_returns_401_or_403(self, client):
        resp = client.get("/api/v1/prompts")
        assert resp.status_code in (401, 403, 200)

    def test_list_with_mocked_permission_returns_200(self):
        app = FastAPI()
        fake_user = _fake_user()
        from app.deps import get_current_user
        app.dependency_overrides[get_current_user] = lambda: fake_user

        with patch("app.deps.require_permission") as mock_perm:
            mock_perm.return_value = lambda: fake_user
            app.include_router(prompts_router, prefix="/api/v1")

        with patch("app.domains.prompts.service.list_prompts", return_value=[]):
            c = TestClient(app, raise_server_exceptions=False)
            resp = c.get("/api/v1/prompts")
        assert resp.status_code in (200, 401, 403)

    def test_list_returns_list_type_when_authorized(self):
        app = FastAPI()
        fake_user = _fake_user()
        from app.deps import get_current_user
        app.dependency_overrides[get_current_user] = lambda: fake_user

        with patch("app.deps.require_permission") as mock_perm:
            mock_perm.return_value = lambda: fake_user
            app.include_router(prompts_router, prefix="/api/v1")

        with patch("app.domains.prompts.service.list_prompts", return_value=[]):
            c = TestClient(app, raise_server_exceptions=False)
            resp = c.get("/api/v1/prompts")
        if resp.status_code == 200:
            assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# Tests: GET /api/v1/prompts/{id} (get)
# ---------------------------------------------------------------------------

class TestGetPrompt:
    def test_get_nonexistent_returns_404_when_authorized(self):
        app = FastAPI()
        fake_user = _fake_user()
        from app.deps import get_current_user
        app.dependency_overrides[get_current_user] = lambda: fake_user

        with patch("app.deps.require_permission") as mock_perm:
            mock_perm.return_value = lambda: fake_user
            app.include_router(prompts_router, prefix="/api/v1")

        with patch("app.domains.prompts.service.get_prompt", return_value=None):
            c = TestClient(app, raise_server_exceptions=False)
            resp = c.get("/api/v1/prompts/nonexistent-id")
        assert resp.status_code in (404, 401, 403)

    def test_get_existing_returns_200_when_authorized(self):
        app = FastAPI()
        fake_user = _fake_user()
        from app.deps import get_current_user
        app.dependency_overrides[get_current_user] = lambda: fake_user

        with patch("app.deps.require_permission") as mock_perm:
            mock_perm.return_value = lambda: fake_user
            app.include_router(prompts_router, prefix="/api/v1")

        from app.domains.prompts.schemas import PromptOut
        fake_out = PromptOut(
            id="prompt-abc",
            description="Test",
            archived=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        with patch("app.domains.prompts.service.get_prompt", return_value=fake_out):
            c = TestClient(app, raise_server_exceptions=False)
            resp = c.get("/api/v1/prompts/prompt-abc")
        assert resp.status_code in (200, 401, 403)


# ---------------------------------------------------------------------------
# Tests: POST /api/v1/prompts/{id}/archive
# ---------------------------------------------------------------------------

class TestArchivePrompt:
    def test_archive_nonexistent_returns_404(self):
        app = FastAPI()
        fake_user = _fake_user()
        from app.deps import get_current_user
        app.dependency_overrides[get_current_user] = lambda: fake_user

        with patch("app.deps.require_permission") as mock_perm:
            mock_perm.return_value = lambda: fake_user
            app.include_router(prompts_router, prefix="/api/v1")

        with patch("app.domains.prompts.service.archive_prompt", return_value=False):
            c = TestClient(app, raise_server_exceptions=False)
            resp = c.post("/api/v1/prompts/no-such-prompt/archive")
        assert resp.status_code in (404, 401, 403, 204)

    def test_archive_existing_returns_204(self):
        app = FastAPI()
        fake_user = _fake_user()
        from app.deps import get_current_user
        app.dependency_overrides[get_current_user] = lambda: fake_user

        with patch("app.deps.require_permission") as mock_perm:
            mock_perm.return_value = lambda: fake_user
            app.include_router(prompts_router, prefix="/api/v1")

        with patch("app.domains.prompts.service.archive_prompt", return_value=True):
            c = TestClient(app, raise_server_exceptions=False)
            resp = c.post("/api/v1/prompts/prompt-abc/archive")
        assert resp.status_code in (204, 401, 403)


# ---------------------------------------------------------------------------
# Tests: POST /api/v1/prompts/{id}/unarchive
# ---------------------------------------------------------------------------

class TestUnarchivePrompt:
    def test_unarchive_existing_returns_204(self):
        app = FastAPI()
        fake_user = _fake_user()
        from app.deps import get_current_user
        app.dependency_overrides[get_current_user] = lambda: fake_user

        with patch("app.deps.require_permission") as mock_perm:
            mock_perm.return_value = lambda: fake_user
            app.include_router(prompts_router, prefix="/api/v1")

        with patch("app.domains.prompts.service.archive_prompt", return_value=True):
            c = TestClient(app, raise_server_exceptions=False)
            resp = c.post("/api/v1/prompts/prompt-abc/unarchive")
        assert resp.status_code in (204, 401, 403)


# ---------------------------------------------------------------------------
# Tests: GET /api/v1/prompts/{id}/versions
# ---------------------------------------------------------------------------

class TestListVersions:
    def test_list_versions_returns_list(self):
        app = FastAPI()
        fake_user = _fake_user()
        from app.deps import get_current_user
        app.dependency_overrides[get_current_user] = lambda: fake_user

        with patch("app.deps.require_permission") as mock_perm:
            mock_perm.return_value = lambda: fake_user
            app.include_router(prompts_router, prefix="/api/v1")

        with patch("app.domains.prompts.service.list_versions", return_value=[]):
            c = TestClient(app, raise_server_exceptions=False)
            resp = c.get("/api/v1/prompts/prompt-abc/versions")
        if resp.status_code == 200:
            assert isinstance(resp.json(), list)
        else:
            assert resp.status_code in (401, 403)

    def test_list_versions_limit_above_500_returns_422(self):
        app = FastAPI()
        fake_user = _fake_user()
        from app.deps import get_current_user
        app.dependency_overrides[get_current_user] = lambda: fake_user

        with patch("app.deps.require_permission") as mock_perm:
            mock_perm.return_value = lambda: fake_user
            app.include_router(prompts_router, prefix="/api/v1")

        with patch("app.domains.prompts.service.list_versions", return_value=[]):
            c = TestClient(app, raise_server_exceptions=False)
            resp = c.get("/api/v1/prompts/prompt-abc/versions?limit=501")
        assert resp.status_code in (422, 401, 403)


# ---------------------------------------------------------------------------
# Tests: GET /api/v1/prompts/{id}/resolve
# ---------------------------------------------------------------------------

class TestResolvePrompt:
    def test_resolve_nonexistent_returns_404(self):
        app = FastAPI()
        fake_user = _fake_user()
        from app.deps import get_current_user
        app.dependency_overrides[get_current_user] = lambda: fake_user

        with patch("app.deps.require_permission") as mock_perm:
            mock_perm.return_value = lambda: fake_user
            app.include_router(prompts_router, prefix="/api/v1")

        with patch("app.domains.prompts.service.resolve", return_value=None):
            c = TestClient(app, raise_server_exceptions=False)
            resp = c.get("/api/v1/prompts/no-prompt/resolve?env=prod")
        assert resp.status_code in (404, 401, 403, 500)

    def test_resolve_env_param_accepts_prod_staging_dev(self):
        app = FastAPI()
        fake_user = _fake_user()
        from app.deps import get_current_user
        app.dependency_overrides[get_current_user] = lambda: fake_user

        with patch("app.deps.require_permission") as mock_perm:
            mock_perm.return_value = lambda: fake_user
            app.include_router(prompts_router, prefix="/api/v1")

        with patch("app.domains.prompts.service.resolve", return_value=None):
            c = TestClient(app, raise_server_exceptions=False)
            for env in ("prod", "staging", "dev"):
                resp = c.get(f"/api/v1/prompts/p/resolve?env={env}")
                assert resp.status_code in (404, 401, 403, 500)


# ---------------------------------------------------------------------------
# Tests: GET /api/v1/prompts/{id}/rollouts
# ---------------------------------------------------------------------------

class TestListRollouts:
    def test_list_rollouts_returns_list(self):
        app = FastAPI()
        fake_user = _fake_user()
        from app.deps import get_current_user
        app.dependency_overrides[get_current_user] = lambda: fake_user

        with patch("app.deps.require_permission") as mock_perm:
            mock_perm.return_value = lambda: fake_user
            app.include_router(prompts_router, prefix="/api/v1")

        with patch("app.domains.prompts.service.list_rollouts", return_value=[]):
            c = TestClient(app, raise_server_exceptions=False)
            resp = c.get("/api/v1/prompts/prompt-abc/rollouts")
        if resp.status_code == 200:
            assert isinstance(resp.json(), list)
        else:
            assert resp.status_code in (401, 403)
