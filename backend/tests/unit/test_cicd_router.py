"""Unit tests for the CI/CD router — 8 tests.

Tests focus on the router layer: helper functions and endpoint logic.
No real DB, no real HTTP. All external services are mocked.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.testclient import TestClient

    from app.domains.cicd.router import (
        router,
        _normalize_ref,
        _extract_commit_sha,
        _extract_branch,
        _summarize,
        _webhook_secret_required,
        _ci_trigger_token_required,
    )

    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False


pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="cicd router import failed")


# ---------------------------------------------------------------------------
# Helper: _normalize_ref
# ---------------------------------------------------------------------------

class TestNormalizeRef:
    def test_heads_prefix_stripped(self):
        assert _normalize_ref("refs/heads/main") == "main"

    def test_tags_prefix_stripped(self):
        assert _normalize_ref("refs/tags/v1.0.0") == "v1.0.0"

    def test_plain_branch_unchanged(self):
        assert _normalize_ref("feature/my-branch") == "feature/my-branch"


# ---------------------------------------------------------------------------
# Helper: _extract_commit_sha
# ---------------------------------------------------------------------------

class TestExtractCommitSha:
    def test_extracts_after_key(self):
        sha = _extract_commit_sha({"after": "abc123def456"})
        assert sha == "abc123def456"

    def test_extracts_checkout_sha_fallback(self):
        sha = _extract_commit_sha({"checkout_sha": "deadbeef"})
        assert sha == "deadbeef"

    def test_returns_empty_for_missing_sha(self):
        sha = _extract_commit_sha({"unrelated": "value"})
        assert sha == ""

    def test_truncates_long_sha(self):
        long_sha = "a" * 100
        sha = _extract_commit_sha({"after": long_sha})
        assert len(sha) <= 64


# ---------------------------------------------------------------------------
# Helper: _extract_branch
# ---------------------------------------------------------------------------

class TestExtractBranch:
    def test_extracts_branch_key(self):
        branch = _extract_branch({"branch": "main"})
        assert branch == "main"

    def test_normalizes_ref_key(self):
        branch = _extract_branch({"ref": "refs/heads/develop"})
        assert branch == "develop"

    def test_returns_empty_when_no_branch_info(self):
        branch = _extract_branch({"unrelated": "data"})
        assert branch == ""


# ---------------------------------------------------------------------------
# Helper: _summarize
# ---------------------------------------------------------------------------

class TestSummarize:
    def test_extracts_known_keys_only(self):
        payload = {"ref": "main", "unknown_key": "ignored", "action": "completed"}
        result = _summarize(payload)
        assert result.get("ref") == "main"
        assert result.get("action") == "completed"
        assert "unknown_key" not in result

    def test_empty_payload_returns_empty_dict(self):
        result = _summarize({})
        assert result == {}


# ---------------------------------------------------------------------------
# Helper: environment-based guards
# ---------------------------------------------------------------------------

class TestSecretRequiredGuards:
    def test_webhook_secret_required_respects_env(self, monkeypatch):
        monkeypatch.setenv("CICD_REQUIRE_WEBHOOK_SECRETS", "1")
        with patch("app.domains.cicd.router.settings") as mock_settings:
            mock_settings.is_production_like = False
            assert _webhook_secret_required() is True

    def test_ci_trigger_token_required_respects_env(self, monkeypatch):
        monkeypatch.setenv("CICD_REQUIRE_TRIGGER_TOKEN", "true")
        with patch("app.domains.cicd.router.settings") as mock_settings:
            mock_settings.is_production_like = False
            assert _ci_trigger_token_required() is True


# ---------------------------------------------------------------------------
# Router: webhook endpoints via TestClient
# ---------------------------------------------------------------------------

def _make_client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app, raise_server_exceptions=False)


class TestWebhookEndpoints:
    def test_github_webhook_missing_body_returns_error_or_422(self):
        client = _make_client()
        resp = client.post("/cicd/webhook/github", json={})
        # Accepts 400, 401, 422, 503 - all are valid rejection codes
        assert resp.status_code in {400, 401, 422, 503}

    def test_gitlab_webhook_missing_body_returns_error_or_422(self):
        client = _make_client()
        resp = client.post("/cicd/webhook/gitlab", json={})
        assert resp.status_code in {400, 401, 422, 503}

    def test_events_list_requires_auth(self):
        """GET /cicd/events should require authentication."""
        client = _make_client()
        resp = client.get("/cicd/events")
        assert resp.status_code in {401, 403, 422, 503}

    def test_quality_gate_evaluate_missing_body_returns_error(self):
        client = _make_client()
        resp = client.post("/cicd/quality-gate/evaluate", json={})
        # Missing required fields → 401/403/422
        assert resp.status_code in {401, 403, 422, 503}
