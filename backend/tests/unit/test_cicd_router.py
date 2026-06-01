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
        _extract_author,
        _serialize_json,
        _keywords_from_path,
        _verify_github_signature,
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
    from app.infra.database import get_db
    mock_db = MagicMock()
    mock_db.get.return_value = None
    mock_db.commit.return_value = None
    mock_db.rollback.return_value = None
    app = FastAPI()
    app.dependency_overrides[get_db] = lambda: mock_db
    app.include_router(router)
    return TestClient(app, raise_server_exceptions=False)


class TestWebhookEndpoints:
    def test_github_webhook_empty_body_is_accepted_or_rejected(self):
        """GitHub webhook with empty body should not crash (200 ok, or error if signature required)."""
        client = _make_client()
        resp = client.post("/cicd/webhook/github", json={})
        # Webhook is idempotent — accepts empty payload (200) or rejects for
        # signature/config reasons (400/401/503); never 500
        assert resp.status_code in {200, 400, 401, 422, 503}

    def test_gitlab_webhook_empty_body_is_accepted_or_rejected(self):
        """GitLab webhook with empty body should not crash."""
        client = _make_client()
        resp = client.post("/cicd/webhook/gitlab", json={})
        assert resp.status_code in {200, 400, 401, 422, 503}

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


# ---------------------------------------------------------------------------
# Helper: _extract_author
# ---------------------------------------------------------------------------

class TestExtractAuthor:
    def test_extracts_sender_login_github(self):
        author = _extract_author({"sender": {"login": "octocat"}})
        assert author == "octocat"

    def test_extracts_user_username_gitlab(self):
        author = _extract_author({"user_username": "gitlab_user"})
        assert author == "gitlab_user"

    def test_extracts_user_name(self):
        author = _extract_author({"user_name": "john"})
        assert author == "john"

    def test_extracts_pusher_name(self):
        author = _extract_author({"pusher": {"name": "janedoe"}})
        assert author == "janedoe"

    def test_extracts_author_name(self):
        author = _extract_author({"author": {"name": "alice"}})
        assert author == "alice"

    def test_returns_empty_for_missing(self):
        author = _extract_author({})
        assert author == ""

    def test_truncates_long_names(self):
        long_name = "a" * 300
        author = _extract_author({"user_username": long_name})
        assert len(author) <= 256

    def test_prefers_sender_over_pusher(self):
        """sender.login has higher priority than pusher.name."""
        author = _extract_author({
            "sender": {"login": "sender_user"},
            "pusher": {"name": "pusher_user"},
        })
        assert author == "sender_user"


# ---------------------------------------------------------------------------
# Helper: _serialize_json
# ---------------------------------------------------------------------------

class TestSerializeJson:
    def test_simple_dict(self):
        result = _serialize_json({"key": "value"})
        import json
        assert json.loads(result) == {"key": "value"}

    def test_nested_structure(self):
        result = _serialize_json({"nested": {"a": 1}})
        import json
        assert json.loads(result)["nested"]["a"] == 1

    def test_datetime_is_serialized(self):
        from datetime import datetime
        dt = datetime(2026, 1, 1, 12, 0, 0)
        result = _serialize_json({"time": dt})
        assert "2026" in result  # datetime converted to string

    def test_list_serialized(self):
        result = _serialize_json([1, 2, 3])
        import json
        assert json.loads(result) == [1, 2, 3]


# ---------------------------------------------------------------------------
# Helper: _keywords_from_path
# ---------------------------------------------------------------------------

class TestKeywordsFromPath:
    def test_extracts_meaningful_keywords(self):
        kws = _keywords_from_path("src/auth/login.py")
        assert "auth" in kws
        assert "login" in kws

    def test_skips_common_words(self):
        kws = _keywords_from_path("src/utils/helpers.py")
        assert "src" not in kws
        assert "utils" not in kws
        assert "helpers" not in kws
        assert "py" not in kws

    def test_handles_backslash(self):
        kws = _keywords_from_path("src\\auth\\login.ts")
        assert "auth" in kws
        assert "login" in kws

    def test_empty_path_returns_empty(self):
        kws = _keywords_from_path("")
        assert kws == []

    def test_skips_short_parts(self):
        kws = _keywords_from_path("a/bb/auth.py")
        assert "a" not in kws
        assert "bb" not in kws
        assert "auth" in kws

    def test_lowercase_output(self):
        kws = _keywords_from_path("src/Auth/Login.py")
        assert all(k == k.lower() for k in kws)


# ---------------------------------------------------------------------------
# Helper: _verify_github_signature
# ---------------------------------------------------------------------------

class TestVerifyGithubSignature:
    def test_empty_signature_returns_false(self):
        assert _verify_github_signature(b"body", "") is False
        assert _verify_github_signature(b"body", None) is False  # type: ignore

    def test_no_secret_returns_true(self):
        """When GITHUB_SECRET is not set, any signature is accepted."""
        with patch("app.domains.cicd.router.GITHUB_SECRET", ""):
            result = _verify_github_signature(b"body", "sha256=anysig")
        assert result is True

    def test_valid_signature_returns_true(self):
        import hmac as _hmac
        import hashlib
        secret = "mysecret"
        body = b"test payload"
        sig = "sha256=" + _hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        with patch("app.domains.cicd.router.GITHUB_SECRET", secret):
            result = _verify_github_signature(body, sig)
        assert result is True

    def test_invalid_signature_returns_false(self):
        with patch("app.domains.cicd.router.GITHUB_SECRET", "mysecret"):
            result = _verify_github_signature(b"test payload", "sha256=deadbeef")
        assert result is False
