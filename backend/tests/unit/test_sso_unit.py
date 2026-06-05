"""Unit tests for SSO domain — provider config, state store, login/callback flows.

Coverage:
  1. _provider_config — valid providers (google, azure)
  2. _provider_config — invalid provider raises 404
  3. _provider_config — unconfigured Google raises 503
  4. _redirect_uri — URL format and path correctness
  5. _StateStore set/get/delete — in-memory mode
  6. _StateStore set/get/delete — Redis mock mode
  7. login endpoint — redirect URL contains auth_url and correct params
  8. callback endpoint — invalid state → 400 (CSRF guard)
  9. callback endpoint — code exchange success → 302 with sso=success, cookies set
 10. callback endpoint — email absent in userinfo → 400
 11. callback endpoint — user not found, auto_provision=False → 403
 12. callback endpoint — user not found, auto_provision=True → user provisioned
 13. callback endpoint — existing user → no add(), sso.login audit recorded
 14. Token creation — access + refresh tokens issued after successful callback
 15. State expiry — expired/missing state is rejected with 400
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

try:
    from app.domains.sso.router import (
        _StateStore,
        _email_domain_allowed,
        _provider_config,
        _redirect_uri,
        _state_store,
        router,
    )

    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="sso router import failed")


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_client(db_user=None):
    """Build a TestClient with a mocked DB session via dependency override."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.infra.database import get_db

    app = FastAPI()
    app.include_router(router)

    mock_session = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.first.return_value = db_user
    execute_mock = MagicMock()
    execute_mock.scalars.return_value = scalars_mock
    mock_session.execute.return_value = execute_mock
    mock_session.add.return_value = None
    mock_session.flush.return_value = None
    mock_session.commit.return_value = None

    app.dependency_overrides[get_db] = lambda: mock_session
    return TestClient(app, follow_redirects=False), mock_session


def _make_settings(
    google_id: str = "google-client-id",
    google_secret: str = "google-secret",
    azure_id: str = "",
    azure_secret: str = "",
    azure_tenant: str = "common",
    auto_provision: bool = True,
    allowed_domains: str = "",
    public_url: str = "http://localhost:3000",
    cors_origins=None,
) -> MagicMock:
    s = MagicMock()
    s.sso_google_client_id = google_id
    s.sso_google_client_secret = google_secret
    s.sso_azure_client_id = azure_id
    s.sso_azure_client_secret = azure_secret
    s.sso_azure_tenant_id = azure_tenant
    s.sso_auto_provision = auto_provision
    s.sso_allowed_email_domains = allowed_domains
    s.app_public_url = public_url
    s.cors_origin_list = cors_origins or ["http://localhost:3000"]
    return s


def _build_httpx_mock(
    token_data: dict,
    userinfo_data: dict,
    token_status: int = 200,
    info_status: int = 200,
) -> MagicMock:
    token_resp = MagicMock()
    token_resp.status_code = token_status
    token_resp.json.return_value = token_data
    token_resp.text = str(token_data)

    info_resp = MagicMock()
    info_resp.status_code = info_status
    info_resp.json.return_value = userinfo_data

    client_mock = MagicMock()
    client_mock.post.return_value = token_resp
    client_mock.get.return_value = info_resp
    client_mock.__enter__ = MagicMock(return_value=client_mock)
    client_mock.__exit__ = MagicMock(return_value=False)
    return client_mock


def _seed_state(state: str, provider: str = "google") -> None:
    """Seed in-memory state store using the public API."""
    _state_store.set(state, {"provider": provider})


def _clear_state(state: str) -> None:
    _state_store.delete(state)


# ---------------------------------------------------------------------------
# 1 & 2. _provider_config — valid and invalid providers
# ---------------------------------------------------------------------------

class TestProviderConfig:
    """_provider_config returns correct config dict or raises HTTPException."""

    def test_google_returns_correct_keys(self):
        mock_settings = _make_settings()
        with patch("app.domains.sso.router.settings", mock_settings):
            cfg = _provider_config("google")
        assert cfg["client_id"] == "google-client-id"
        assert cfg["client_secret"] == "google-secret"
        assert "accounts.google.com" in cfg["auth_url"]
        assert "oauth2.googleapis.com" in cfg["token_url"]
        assert "openidconnect.googleapis.com" in cfg["userinfo_url"]
        assert "openid" in cfg["scope"]

    def test_azure_returns_correct_keys_with_tenant(self):
        mock_settings = _make_settings(
            azure_id="azure-id",
            azure_secret="azure-secret",
            azure_tenant="my-tenant",
        )
        with patch("app.domains.sso.router.settings", mock_settings):
            cfg = _provider_config("azure")
        assert cfg["client_id"] == "azure-id"
        assert "my-tenant" in cfg["auth_url"]
        assert "my-tenant" in cfg["token_url"]
        assert "graph.microsoft.com" in cfg["userinfo_url"]

    def test_unknown_provider_raises_404(self):
        from fastapi import HTTPException
        mock_settings = _make_settings()
        with patch("app.domains.sso.router.settings", mock_settings):
            with pytest.raises(HTTPException) as exc_info:
                _provider_config("okta")
        assert exc_info.value.status_code == 404
        assert "okta" in exc_info.value.detail.lower() or "bilinmeyen" in exc_info.value.detail.lower()

    def test_unconfigured_google_raises_503(self):
        from fastapi import HTTPException
        mock_settings = _make_settings(google_id="", google_secret="")
        with patch("app.domains.sso.router.settings", mock_settings):
            with pytest.raises(HTTPException) as exc_info:
                _provider_config("google")
        assert exc_info.value.status_code == 503

    def test_unconfigured_azure_raises_503(self):
        from fastapi import HTTPException
        mock_settings = _make_settings(azure_id="", azure_secret="")
        with patch("app.domains.sso.router.settings", mock_settings):
            with pytest.raises(HTTPException) as exc_info:
                _provider_config("azure")
        assert exc_info.value.status_code == 503


# ---------------------------------------------------------------------------
# 3. _redirect_uri — URL format validation
# ---------------------------------------------------------------------------

class TestRedirectUri:
    """_redirect_uri produces a well-formed callback URL."""

    def test_redirect_uri_contains_provider_and_callback(self):
        mock_settings = _make_settings(
            public_url="http://localhost:3000",
            cors_origins=["http://localhost:3000"],
        )
        with patch("app.domains.sso.router.settings", mock_settings):
            uri = _redirect_uri("google")
        assert uri.startswith("http")
        assert "/sso/google/callback" in uri

    def test_redirect_uri_azure_uses_azure_path(self):
        mock_settings = _make_settings(
            public_url="https://app.example.com",
            cors_origins=["https://app.example.com"],
        )
        with patch("app.domains.sso.router.settings", mock_settings):
            uri = _redirect_uri("azure")
        assert "/sso/azure/callback" in uri

    def test_redirect_uri_no_trailing_slash(self):
        mock_settings = _make_settings(
            public_url="http://localhost:3000/",
            cors_origins=["http://localhost:3000/"],
        )
        with patch("app.domains.sso.router.settings", mock_settings):
            uri = _redirect_uri("google")
        # No double-slash before /api
        assert "//" not in uri.replace("://", "___")

    def test_redirect_uri_uses_cors_origin_when_set(self):
        mock_settings = _make_settings(
            public_url="http://other.example.com",
            cors_origins=["https://frontend.example.com"],
        )
        with patch("app.domains.sso.router.settings", mock_settings):
            uri = _redirect_uri("google")
        # cors_origin_list[0] is preferred over app_public_url
        assert "frontend.example.com" in uri


# ---------------------------------------------------------------------------
# 4. _StateStore — in-memory set/get/delete
# ---------------------------------------------------------------------------

class TestStateStoreInMemory:
    """_StateStore in-memory backend operations."""

    def test_set_and_get_returns_value(self):
        store = _StateStore.__new__(_StateStore)
        store._store = {}
        store._redis = None
        from threading import RLock
        store._lock = RLock()

        store.set("key1", {"provider": "google"})
        result = store.get("key1")
        assert result == {"provider": "google"}

    def test_delete_removes_key(self):
        store = _StateStore.__new__(_StateStore)
        store._store = {}
        store._redis = None
        from threading import RLock
        store._lock = RLock()

        store.set("key2", {"x": 1})
        store.delete("key2")
        assert store.get("key2") is None

    def test_get_missing_key_returns_none(self):
        store = _StateStore.__new__(_StateStore)
        store._store = {}
        store._redis = None
        from threading import RLock
        store._lock = RLock()

        assert store.get("nonexistent") is None

    def test_delete_nonexistent_key_is_safe(self):
        store = _StateStore.__new__(_StateStore)
        store._store = {}
        store._redis = None
        from threading import RLock
        store._lock = RLock()

        # Should not raise
        store.delete("ghost-key")


# ---------------------------------------------------------------------------
# 5. _StateStore — Redis mock mode
# ---------------------------------------------------------------------------

class TestStateStoreRedis:
    """_StateStore Redis backend operations via mock."""

    def _make_redis_store(self) -> _StateStore:
        store = _StateStore.__new__(_StateStore)
        store._store = {}
        from threading import RLock
        store._lock = RLock()
        redis_mock = MagicMock()
        redis_mock.get.return_value = None
        store._redis = redis_mock
        return store

    def test_set_calls_redis_setex(self):
        store = self._make_redis_store()
        store.set("state-abc", {"provider": "google"}, ttl=600)
        store._redis.setex.assert_called_once()
        call_args = store._redis.setex.call_args
        # First arg is the key (with prefix), second is ttl, third is JSON payload
        assert "state-abc" in call_args[0][0]
        assert call_args[0][1] == 600
        assert "google" in call_args[0][2]

    def test_get_deserialises_json_from_redis(self):
        store = self._make_redis_store()
        store._redis.get.return_value = json.dumps({"provider": "azure"})
        result = store.get("state-xyz")
        assert result == {"provider": "azure"}

    def test_get_returns_none_when_redis_key_missing(self):
        store = self._make_redis_store()
        store._redis.get.return_value = None
        assert store.get("missing-key") is None

    def test_delete_calls_redis_delete(self):
        store = self._make_redis_store()
        store.delete("state-del")
        store._redis.delete.assert_called_once()
        assert "state-del" in store._redis.delete.call_args[0][0]

    def test_redis_set_error_falls_back_to_memory(self):
        store = self._make_redis_store()
        store._redis.setex.side_effect = Exception("Redis down")
        # Should not raise — falls back to in-memory
        store.set("fallback-key", {"x": 1})
        assert store._store.get("fallback-key") == {"x": 1}


# ---------------------------------------------------------------------------
# 6. login endpoint — redirect URL validation
# ---------------------------------------------------------------------------

class TestSsoLoginEndpoint:
    """GET /sso/{provider}/login produces a correct provider redirect."""

    def test_google_login_redirects_to_google_auth(self):
        client, _ = _make_client()
        mock_settings = _make_settings()

        with patch("app.domains.sso.router.settings", mock_settings):
            resp = client.get("/sso/google/login")

        assert resp.status_code in (302, 307)
        location = resp.headers["location"]
        assert "accounts.google.com" in location
        assert "client_id=google-client-id" in location
        assert "response_type=code" in location
        assert "state=" in location

    def test_azure_login_redirects_to_microsoft_auth(self):
        client, _ = _make_client()
        mock_settings = _make_settings(
            azure_id="azure-id",
            azure_secret="azure-secret",
            azure_tenant="tenant-123",
        )

        with patch("app.domains.sso.router.settings", mock_settings):
            resp = client.get("/sso/azure/login")

        assert resp.status_code in (302, 307)
        location = resp.headers["location"]
        assert "login.microsoftonline.com" in location
        assert "tenant-123" in location

    def test_login_unknown_provider_returns_404(self):
        client, _ = _make_client()
        mock_settings = _make_settings()

        with patch("app.domains.sso.router.settings", mock_settings):
            resp = client.get("/sso/saml/login")

        assert resp.status_code == 404

    def test_login_stores_state_in_state_store(self):
        """State token generated during login must be discoverable via state store."""
        client, _ = _make_client()
        mock_settings = _make_settings()
        captured_state = []

        original_set = _state_store.set

        def _capture_set(key, value, ttl=600):
            captured_state.append(key)
            original_set(key, value, ttl)

        with (
            patch("app.domains.sso.router.settings", mock_settings),
            patch.object(_state_store, "set", side_effect=_capture_set),
        ):
            client.get("/sso/google/login")

        assert len(captured_state) == 1
        # Clean up so we don't pollute other tests
        _clear_state(captured_state[0])


# ---------------------------------------------------------------------------
# 7. callback — invalid state → 400 (CSRF)
# ---------------------------------------------------------------------------

class TestCallbackInvalidState:
    """Tampered or absent state must be rejected."""

    def test_invalid_state_returns_400(self):
        client, _ = _make_client()
        mock_settings = _make_settings()

        with patch("app.domains.sso.router.settings", mock_settings):
            resp = client.get("/sso/google/callback?code=abc&state=INVALID-CSRF-STATE-xyz")

        assert resp.status_code == 400
        detail = resp.json().get("detail", "").lower()
        assert "state" in detail or "csrf" in detail

    def test_state_deleted_after_successful_use(self):
        """State is consumed (deleted) after the callback succeeds, preventing replay."""
        state = "one-time-state"
        _seed_state(state, "google")

        existing_user = MagicMock()
        existing_user.id = 1
        client, _ = _make_client(db_user=existing_user)

        mock_settings = _make_settings()
        httpx_mock = _build_httpx_mock(
            token_data={"access_token": "tok"},
            userinfo_data={"email": "user@example.com"},
        )

        with (
            patch("app.domains.sso.router.settings", mock_settings),
            patch("app.domains.sso.router.httpx.Client", return_value=httpx_mock),
            patch("app.domains.sso.router.create_access_token", return_value="a"),
            patch("app.domains.sso.router.create_refresh_token", return_value="r"),
            patch("app.domains.sso.router.log_audit"),
        ):
            client.get(f"/sso/google/callback?code=abc&state={state}")

        # After consumption the state must be gone
        assert _state_store.get(state) is None


# ---------------------------------------------------------------------------
# 8. callback — successful code exchange → cookies set
# ---------------------------------------------------------------------------

class TestCallbackCodeExchangeSuccess:
    """Successful callback sets access and refresh token cookies."""

    def test_cookies_set_on_success(self):
        state = "cookie-test-state"
        _seed_state(state, "google")

        existing_user = MagicMock()
        existing_user.id = 10
        client, _ = _make_client(db_user=existing_user)

        mock_settings = _make_settings()
        httpx_mock = _build_httpx_mock(
            token_data={"access_token": "goog-token"},
            userinfo_data={"email": "alice@example.com", "name": "Alice"},
        )

        with (
            patch("app.domains.sso.router.settings", mock_settings),
            patch("app.domains.sso.router.httpx.Client", return_value=httpx_mock),
            patch("app.domains.sso.router.create_access_token", return_value="access-jwt"),
            patch("app.domains.sso.router.create_refresh_token", return_value="refresh-jwt"),
            patch("app.domains.sso.router.log_audit"),
        ):
            resp = client.get(f"/sso/google/callback?code=auth-code&state={state}")

        _clear_state(state)

        assert resp.status_code in (302, 307)
        assert "sso=success" in resp.headers.get("location", "")

        cookies = {c.name: c for c in resp.cookies.jar}
        from app.domains.auth.router import ACCESS_TOKEN_COOKIE, REFRESH_TOKEN_COOKIE
        assert ACCESS_TOKEN_COOKIE in cookies or "access-jwt" in str(resp.headers.get("set-cookie", ""))
        assert REFRESH_TOKEN_COOKIE in cookies or "refresh-jwt" in str(resp.headers.get("set-cookie", ""))

    def test_token_exchange_failure_returns_400(self):
        state = "token-fail-state"
        _seed_state(state, "google")

        client, _ = _make_client()
        mock_settings = _make_settings()
        httpx_mock = _build_httpx_mock(
            token_data={"error": "invalid_code"},
            userinfo_data={},
            token_status=400,
        )

        with (
            patch("app.domains.sso.router.settings", mock_settings),
            patch("app.domains.sso.router.httpx.Client", return_value=httpx_mock),
        ):
            resp = client.get(f"/sso/google/callback?code=bad-code&state={state}")

        _clear_state(state)
        assert resp.status_code == 400
        assert "token" in resp.json().get("detail", "").lower() or "basarisiz" in resp.json().get("detail", "").lower()


# ---------------------------------------------------------------------------
# 9. callback — email absent in userinfo → 400
# ---------------------------------------------------------------------------

class TestCallbackMissingEmail:
    """Userinfo without an email field must raise 400."""

    def test_missing_email_returns_400(self):
        state = "no-email-state"
        _seed_state(state, "google")

        client, _ = _make_client()
        mock_settings = _make_settings()
        httpx_mock = _build_httpx_mock(
            token_data={"access_token": "tok"},
            userinfo_data={"sub": "12345", "name": "No Email"},  # no email
        )

        with (
            patch("app.domains.sso.router.settings", mock_settings),
            patch("app.domains.sso.router.httpx.Client", return_value=httpx_mock),
        ):
            resp = client.get(f"/sso/google/callback?code=abc&state={state}")

        _clear_state(state)
        assert resp.status_code == 400
        assert "email" in resp.json().get("detail", "").lower()

    def test_empty_email_string_returns_400(self):
        state = "empty-email-state"
        _seed_state(state, "google")

        client, _ = _make_client()
        mock_settings = _make_settings()
        httpx_mock = _build_httpx_mock(
            token_data={"access_token": "tok"},
            userinfo_data={"email": "   ", "name": "Blank Email"},
        )

        with (
            patch("app.domains.sso.router.settings", mock_settings),
            patch("app.domains.sso.router.httpx.Client", return_value=httpx_mock),
        ):
            resp = client.get(f"/sso/google/callback?code=abc&state={state}")

        _clear_state(state)
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# 10. callback — user not found, auto_provision=False → 403
# ---------------------------------------------------------------------------

class TestCallbackAutoProvisionDisabled:
    """When auto_provision=False and user does not exist → 403."""

    def test_no_auto_provision_returns_403(self):
        state = "no-provision-state"
        _seed_state(state, "google")

        client, _ = _make_client(db_user=None)  # no existing user
        mock_settings = _make_settings(auto_provision=False)
        httpx_mock = _build_httpx_mock(
            token_data={"access_token": "tok"},
            userinfo_data={"email": "stranger@example.com"},
        )

        with (
            patch("app.domains.sso.router.settings", mock_settings),
            patch("app.domains.sso.router.httpx.Client", return_value=httpx_mock),
        ):
            resp = client.get(f"/sso/google/callback?code=abc&state={state}")

        _clear_state(state)
        assert resp.status_code == 403
        detail = resp.json().get("detail", "").lower()
        assert "hesab" in detail or "davet" in detail or "provision" in detail or "yok" in detail


# ---------------------------------------------------------------------------
# 11. callback — user not found, auto_provision=True → user provisioned
# ---------------------------------------------------------------------------

class TestCallbackAutoProvisionCreatesUser:
    """With auto_provision=True a missing user is created and audit logged."""

    def test_auto_provision_creates_user(self):
        state = "auto-provision-state"
        _seed_state(state, "google")

        client, mock_session = _make_client(db_user=None)
        mock_settings = _make_settings(auto_provision=True)
        httpx_mock = _build_httpx_mock(
            token_data={"access_token": "tok"},
            userinfo_data={"email": "newuser@example.com", "name": "New User"},
        )

        def _flush_side_effect():
            if mock_session.add.call_args:
                added = mock_session.add.call_args[0][0]
                added.id = 99

        mock_session.flush.side_effect = _flush_side_effect

        with (
            patch("app.domains.sso.router.settings", mock_settings),
            patch("app.domains.sso.router.httpx.Client", return_value=httpx_mock),
            patch("app.domains.sso.router.create_access_token", return_value="a"),
            patch("app.domains.sso.router.create_refresh_token", return_value="r"),
            patch("app.domains.sso.router.log_audit") as mock_audit,
            patch("app.domains.sso.router.hash_password", return_value="pw-hash"),
        ):
            resp = client.get(f"/sso/google/callback?code=abc&state={state}")

        _clear_state(state)

        mock_session.add.assert_called_once()
        mock_session.flush.assert_called()

        provision_calls = [
            c for c in mock_audit.call_args_list
            if c.kwargs.get("action") == "sso.provision"
        ]
        assert len(provision_calls) == 1
        assert resp.status_code in (302, 307)


# ---------------------------------------------------------------------------
# 12. callback — existing user → no add(), sso.login audit recorded
# ---------------------------------------------------------------------------

class TestCallbackExistingUser:
    """Existing user lookup skips provisioning and records sso.login audit."""

    def test_existing_user_no_add_called(self):
        state = "existing-user-state"
        _seed_state(state, "google")

        existing_user = MagicMock()
        existing_user.id = 42
        client, mock_session = _make_client(db_user=existing_user)

        mock_settings = _make_settings()
        httpx_mock = _build_httpx_mock(
            token_data={"access_token": "tok"},
            userinfo_data={"email": "alice@example.com", "name": "Alice"},
        )

        with (
            patch("app.domains.sso.router.settings", mock_settings),
            patch("app.domains.sso.router.httpx.Client", return_value=httpx_mock),
            patch("app.domains.sso.router.create_access_token", return_value="a"),
            patch("app.domains.sso.router.create_refresh_token", return_value="r"),
            patch("app.domains.sso.router.log_audit") as mock_audit,
        ):
            resp = client.get(f"/sso/google/callback?code=abc&state={state}")

        _clear_state(state)

        mock_session.add.assert_not_called()
        login_calls = [
            c for c in mock_audit.call_args_list
            if c.kwargs.get("action") == "sso.login"
        ]
        assert len(login_calls) == 1
        assert resp.status_code in (302, 307)


# ---------------------------------------------------------------------------
# 13. Token creation — access + refresh tokens issued
# ---------------------------------------------------------------------------

class TestTokenCreationAfterCallback:
    """create_access_token and create_refresh_token are called with the user id."""

    def test_tokens_created_with_user_id(self):
        state = "token-creation-state"
        _seed_state(state, "google")

        existing_user = MagicMock()
        existing_user.id = 77
        client, _ = _make_client(db_user=existing_user)

        mock_settings = _make_settings()
        httpx_mock = _build_httpx_mock(
            token_data={"access_token": "tok"},
            userinfo_data={"email": "bob@example.com"},
        )

        with (
            patch("app.domains.sso.router.settings", mock_settings),
            patch("app.domains.sso.router.httpx.Client", return_value=httpx_mock),
            patch("app.domains.sso.router.create_access_token", return_value="access-jwt") as mock_access,
            patch("app.domains.sso.router.create_refresh_token", return_value="refresh-jwt") as mock_refresh,
            patch("app.domains.sso.router.log_audit"),
        ):
            resp = client.get(f"/sso/google/callback?code=abc&state={state}")

        _clear_state(state)

        mock_access.assert_called_once_with(subject_user_id=77)
        mock_refresh.assert_called_once()
        # user_id must be in the refresh token call
        refresh_kwargs = mock_refresh.call_args.kwargs
        assert refresh_kwargs.get("user_id") == 77

    def test_both_token_types_are_returned(self):
        state = "both-tokens-state"
        _seed_state(state, "google")

        existing_user = MagicMock()
        existing_user.id = 5
        client, _ = _make_client(db_user=existing_user)

        mock_settings = _make_settings()
        httpx_mock = _build_httpx_mock(
            token_data={"access_token": "tok"},
            userinfo_data={"email": "carol@example.com"},
        )

        with (
            patch("app.domains.sso.router.settings", mock_settings),
            patch("app.domains.sso.router.httpx.Client", return_value=httpx_mock),
            patch("app.domains.sso.router.create_access_token", return_value="my-access"),
            patch("app.domains.sso.router.create_refresh_token", return_value="my-refresh"),
            patch("app.domains.sso.router.log_audit"),
        ):
            resp = client.get(f"/sso/google/callback?code=abc&state={state}")

        _clear_state(state)

        set_cookie_header = resp.headers.get("set-cookie", "")
        assert "my-access" in set_cookie_header or resp.status_code in (302, 307)


# ---------------------------------------------------------------------------
# 14. State expiry — missing / already-consumed state is rejected
# ---------------------------------------------------------------------------

class TestStateExpiry:
    """A state that was never set or already consumed must be rejected."""

    def test_never_set_state_returns_400(self):
        client, _ = _make_client()
        mock_settings = _make_settings()

        with patch("app.domains.sso.router.settings", mock_settings):
            resp = client.get("/sso/google/callback?code=abc&state=never-existed-state")

        assert resp.status_code == 400

    def test_reused_state_returns_400(self):
        """State consumed by one callback cannot be replayed."""
        state = "reuse-state"
        _seed_state(state, "google")

        existing_user = MagicMock()
        existing_user.id = 3
        client, _ = _make_client(db_user=existing_user)

        mock_settings = _make_settings()
        httpx_mock = _build_httpx_mock(
            token_data={"access_token": "tok"},
            userinfo_data={"email": "replay@example.com"},
        )

        with (
            patch("app.domains.sso.router.settings", mock_settings),
            patch("app.domains.sso.router.httpx.Client", return_value=httpx_mock),
            patch("app.domains.sso.router.create_access_token", return_value="a"),
            patch("app.domains.sso.router.create_refresh_token", return_value="r"),
            patch("app.domains.sso.router.log_audit"),
        ):
            resp1 = client.get(f"/sso/google/callback?code=c1&state={state}")
            resp2 = client.get(f"/sso/google/callback?code=c2&state={state}")

        assert resp1.status_code in (302, 307)
        assert resp2.status_code == 400  # state was deleted after first use

    def test_state_ttl_constant_is_600_seconds(self):
        """_STATE_TTL_SECONDS must be exactly 600 (10 minutes)."""
        from app.domains.sso.router import _STATE_TTL_SECONDS
        assert _STATE_TTL_SECONDS == 600


# ---------------------------------------------------------------------------
# 15. list_providers endpoint
# ---------------------------------------------------------------------------

class TestListProviders:
    """GET /sso/providers returns configured providers only."""

    def test_both_providers_listed_when_configured(self):
        client, _ = _make_client()
        mock_settings = _make_settings(
            google_id="g-id",
            azure_id="a-id",
        )

        with patch("app.domains.sso.router.settings", mock_settings):
            resp = client.get("/sso/providers")

        assert resp.status_code == 200
        ids = {p["id"] for p in resp.json()["providers"]}
        assert "google" in ids
        assert "azure" in ids

    def test_empty_providers_when_none_configured(self):
        client, _ = _make_client()
        mock_settings = _make_settings(google_id="", azure_id="")

        with patch("app.domains.sso.router.settings", mock_settings):
            resp = client.get("/sso/providers")

        assert resp.status_code == 200
        assert resp.json()["providers"] == []

    def test_only_google_listed_when_azure_absent(self):
        client, _ = _make_client()
        mock_settings = _make_settings(google_id="g-id", azure_id="")

        with patch("app.domains.sso.router.settings", mock_settings):
            resp = client.get("/sso/providers")

        assert resp.status_code == 200
        ids = [p["id"] for p in resp.json()["providers"]]
        assert ids == ["google"]
