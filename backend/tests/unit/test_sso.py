"""Unit tests for the SSO domain router — 8 test classes (13 test methods).

Tests cover:
  - Google OIDC callback success
  - Azure AD OIDC callback success
  - Invalid state parameter returns 400
  - Disabled/unconfigured provider returns 404/503
  - Missing code query param returns 422
  - Auto-provision creates a new user
  - Existing user login skips provision
  - Allowed-domains filter blocks/allows by email domain

All DB calls, httpx requests, and token creation functions are mocked.
No real database or network connections required.

Settings are patched via ``patch("app.domains.sso.router.settings")`` so
Pydantic's read-only field restriction is bypassed entirely.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

try:
    from app.domains.sso.router import (
        router,
        _email_domain_allowed,
        _state_store,
    )

    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="sso router import failed")


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_client(db_user=None):
    """Build a TestClient with a mock DB session injected via dependency override."""
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


def _inject_state(state: str, provider: str = "google") -> None:
    """Seed the in-memory state store so the callback sees the state as valid."""
    _state_store[state] = {"provider": provider}


def _clear_state(state: str) -> None:
    _state_store.pop(state, None)


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
    """Return a MagicMock that mimics ``app.config.settings`` for SSO fields."""
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
    """Synchronous httpx.Client context-manager mock."""
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


# ---------------------------------------------------------------------------
# 1. Google OIDC callback success
# ---------------------------------------------------------------------------


class TestGoogleOidcCallbackSuccess:
    """Successful Google OIDC callback returns 302 redirect with sso=success."""

    def test_google_oidc_callback_success(self):
        state = "google-success-state"
        _inject_state(state, "google")

        existing_user = MagicMock()
        existing_user.mfa_enabled = False
        existing_user.id = 42
        client, _ = _make_client(db_user=existing_user)

        mock_settings = _make_settings()
        httpx_mock = _build_httpx_mock(
            token_data={"access_token": "goog-access-token"},
            userinfo_data={"email": "user@example.com", "name": "Test User"},
        )

        with (
            patch("app.domains.sso.router.settings", mock_settings),
            patch("app.domains.sso.router.httpx.Client", return_value=httpx_mock),
            patch("app.domains.sso.router.create_access_token", return_value="jwt-access"),
            patch("app.domains.sso.router.create_refresh_token", return_value="jwt-refresh"),
            patch("app.domains.sso.router.log_audit"),
        ):
            resp = client.get(f"/sso/google/callback?code=auth-code&state={state}")

        _clear_state(state)

        assert resp.status_code in (302, 307)
        assert "sso=success" in resp.headers.get("location", "")


# ---------------------------------------------------------------------------
# 2. Azure AD OIDC callback success
# ---------------------------------------------------------------------------


class TestAzureOidcCallbackSuccess:
    """Successful Azure AD OIDC callback returns 302 redirect with sso=success."""

    def test_azure_oidc_callback_success(self):
        state = "azure-success-state"
        _inject_state(state, "azure")

        existing_user = MagicMock()
        existing_user.mfa_enabled = False
        existing_user.id = 99
        client, _ = _make_client(db_user=existing_user)

        mock_settings = _make_settings(
            google_id="",
            google_secret="",
            azure_id="azure-client-id",
            azure_secret="azure-secret",
            azure_tenant="my-tenant",
        )
        httpx_mock = _build_httpx_mock(
            token_data={"access_token": "azure-access-token"},
            userinfo_data={"email": "user@corp.com", "name": "Corp User"},
        )

        with (
            patch("app.domains.sso.router.settings", mock_settings),
            patch("app.domains.sso.router.httpx.Client", return_value=httpx_mock),
            patch("app.domains.sso.router.create_access_token", return_value="jwt-access"),
            patch("app.domains.sso.router.create_refresh_token", return_value="jwt-refresh"),
            patch("app.domains.sso.router.log_audit"),
        ):
            resp = client.get(f"/sso/azure/callback?code=auth-code&state={state}")

        _clear_state(state)

        assert resp.status_code in (302, 307)
        assert "sso=success" in resp.headers.get("location", "")


# ---------------------------------------------------------------------------
# 3. Invalid state returns 400
# ---------------------------------------------------------------------------


class TestSsoInvalidStateReturns400:
    """Tampered or absent state token is rejected with 400 (CSRF protection)."""

    def test_sso_invalid_state_returns_400(self):
        client, _ = _make_client()
        mock_settings = _make_settings()

        with patch("app.domains.sso.router.settings", mock_settings):
            resp = client.get(
                "/sso/google/callback?code=abc&state=totally-invalid-state-xyz"
            )

        assert resp.status_code == 400
        detail = resp.json().get("detail", "").lower()
        assert "state" in detail or "csrf" in detail


# ---------------------------------------------------------------------------
# 4. Disabled / unconfigured provider returns 404 / 503
# ---------------------------------------------------------------------------


class TestSsoDisabledProviderReturns404:
    """Unknown provider → 404; unconfigured Google credentials → 503."""

    def test_unknown_provider_returns_404(self):
        state = "unknown-provider-state"
        _inject_state(state, "unknown")
        client, _ = _make_client()
        mock_settings = _make_settings()

        with patch("app.domains.sso.router.settings", mock_settings):
            resp = client.get(f"/sso/unknown/callback?code=abc&state={state}")

        _clear_state(state)
        assert resp.status_code == 404

    def test_unconfigured_google_returns_503(self):
        state = "disabled-google-state"
        _inject_state(state, "google")
        client, _ = _make_client()

        # Empty credentials → _provider_config raises HTTPException(503)
        mock_settings = _make_settings(google_id="", google_secret="")

        with patch("app.domains.sso.router.settings", mock_settings):
            resp = client.get(f"/sso/google/callback?code=abc&state={state}")

        _clear_state(state)
        assert resp.status_code == 503


# ---------------------------------------------------------------------------
# 5. Missing code parameter returns 422 / error param returns 400
# ---------------------------------------------------------------------------


class TestSsoMissingCodeReturns400:
    """Missing required query param → FastAPI 422; provider error param → 400."""

    def test_sso_missing_code_returns_422(self):
        """FastAPI raises 422 Unprocessable Entity when ``code`` is absent."""
        state = "no-code-state"
        _inject_state(state, "google")
        client, _ = _make_client()
        mock_settings = _make_settings()

        with patch("app.domains.sso.router.settings", mock_settings):
            resp = client.get(f"/sso/google/callback?state={state}")

        _clear_state(state)
        # FastAPI validates required query params at the request level → 422
        assert resp.status_code == 422

    def test_sso_error_param_returns_400(self):
        """Provider returning ?error=access_denied triggers our 400 guard."""
        state = "error-param-state"
        _inject_state(state, "google")
        client, _ = _make_client()
        mock_settings = _make_settings()

        with patch("app.domains.sso.router.settings", mock_settings):
            resp = client.get(
                f"/sso/google/callback?code=x&state={state}&error=access_denied"
            )

        _clear_state(state)
        assert resp.status_code == 400
        assert "access_denied" in resp.json().get("detail", "")


# ---------------------------------------------------------------------------
# 6. Auto-provision creates a new user
# ---------------------------------------------------------------------------


class TestSsoAutoProvisionCreatesUser:
    """When no user exists and sso_auto_provision=True, a new User row is added."""

    def test_sso_auto_provision_creates_user(self):
        state = "provision-state"
        _inject_state(state, "google")

        # db returns None → no existing user → provision path
        client, mock_session = _make_client(db_user=None)

        mock_settings = _make_settings(auto_provision=True)
        httpx_mock = _build_httpx_mock(
            token_data={"access_token": "goog-token"},
            userinfo_data={"email": "new@example.com", "name": "New User"},
        )

        with (
            patch("app.domains.sso.router.settings", mock_settings),
            patch("app.domains.sso.router.httpx.Client", return_value=httpx_mock),
            patch("app.domains.sso.router.create_access_token", return_value="jwt-access"),
            patch("app.domains.sso.router.create_refresh_token", return_value="jwt-refresh"),
            patch("app.domains.sso.router.log_audit") as mock_audit,
            patch("app.domains.sso.router.hash_password", return_value="hashed-pw"),
        ):
            # Patch flush to assign a fake id to the newly created user
            def _flush_side_effect():
                # Find the User instance that was added and give it an id
                if mock_session.add.call_args:
                    added = mock_session.add.call_args[0][0]
                    added.id = 7

            mock_session.flush.side_effect = _flush_side_effect
            resp = client.get(f"/sso/google/callback?code=auth-code&state={state}")

        _clear_state(state)

        # A new User instance must have been added to the session
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called()

        # sso.provision audit event must be logged
        provision_calls = [
            c for c in mock_audit.call_args_list
            if c.kwargs.get("action") == "sso.provision"
        ]
        assert len(provision_calls) == 1
        assert resp.status_code in (302, 307)


# ---------------------------------------------------------------------------
# 7. Existing user login skips provision
# ---------------------------------------------------------------------------


class TestSsoExistingUserLogin:
    """Known email skips provision; sso.login audit event is recorded."""

    def test_sso_existing_user_login(self):
        state = "existing-user-state"
        _inject_state(state, "google")

        existing_user = MagicMock()
        existing_user.mfa_enabled = False
        existing_user.id = 55
        client, mock_session = _make_client(db_user=existing_user)

        mock_settings = _make_settings()
        httpx_mock = _build_httpx_mock(
            token_data={"access_token": "goog-token"},
            userinfo_data={"email": "existing@example.com", "name": "Existing User"},
        )

        with (
            patch("app.domains.sso.router.settings", mock_settings),
            patch("app.domains.sso.router.httpx.Client", return_value=httpx_mock),
            patch("app.domains.sso.router.create_access_token", return_value="jwt-access"),
            patch("app.domains.sso.router.create_refresh_token", return_value="jwt-refresh"),
            patch("app.domains.sso.router.log_audit") as mock_audit,
        ):
            resp = client.get(f"/sso/google/callback?code=auth-code&state={state}")

        _clear_state(state)

        # No new user row should be created
        mock_session.add.assert_not_called()

        # sso.login audit event must be recorded
        login_calls = [
            c for c in mock_audit.call_args_list
            if c.kwargs.get("action") == "sso.login"
        ]
        assert len(login_calls) == 1
        assert resp.status_code in (302, 307)


# ---------------------------------------------------------------------------
# 8. Allowed-domains filter
# ---------------------------------------------------------------------------


class TestSsoAllowedDomainsFilter:
    """_email_domain_allowed() and end-to-end 403 for blocked domains."""

    def test_allowed_domain_passes(self):
        with patch("app.domains.sso.router.settings") as s:
            s.sso_allowed_email_domains = "example.com,corp.io"
            assert _email_domain_allowed("user@example.com") is True
            assert _email_domain_allowed("admin@corp.io") is True

    def test_blocked_domain_is_rejected(self):
        with patch("app.domains.sso.router.settings") as s:
            s.sso_allowed_email_domains = "example.com"
            assert _email_domain_allowed("attacker@evil.com") is False

    def test_empty_allowlist_permits_all(self):
        with patch("app.domains.sso.router.settings") as s:
            s.sso_allowed_email_domains = ""
            assert _email_domain_allowed("anyone@anydomain.xyz") is True

    def test_blocked_domain_callback_returns_403(self):
        """End-to-end: callback with a blocked email domain returns 403."""
        state = "blocked-domain-state"
        _inject_state(state, "google")

        client, _ = _make_client(db_user=None)
        mock_settings = _make_settings(allowed_domains="allowed.com")
        httpx_mock = _build_httpx_mock(
            token_data={"access_token": "goog-token"},
            userinfo_data={"email": "user@blocked.com", "name": "Blocked User"},
        )

        with (
            patch("app.domains.sso.router.settings", mock_settings),
            patch("app.domains.sso.router.httpx.Client", return_value=httpx_mock),
        ):
            resp = client.get(f"/sso/google/callback?code=auth-code&state={state}")

        _clear_state(state)

        assert resp.status_code == 403
        detail = resp.json().get("detail", "").lower()
        assert "izinli" in detail or "domain" in detail or "email" in detail
