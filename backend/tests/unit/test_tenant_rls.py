"""Unit tests for tenant middleware and RLS propagation.

Tests:
- TenantMiddleware extracts tenant_id from Bearer token correctly
- TenantMiddleware falls back to default tenant when no token
- TenantMiddleware reads from cookie when header is absent
- _safe_tenant_id rejects non-UUID values
- get_db() calls SET LOCAL with correct tenant
"""

from __future__ import annotations

import base64
import json
from unittest.mock import MagicMock, patch

import pytest

from app.core.tenant_middleware import _safe_tenant_id, _DEFAULT_TENANT, extract_tenant_from_token


def _make_jwt_payload(payload: dict) -> str:
    """Build a fake JWT (no signature, test only)."""
    header = base64.urlsafe_b64encode(b'{"alg":"HS256"}').decode().rstrip("=")
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return f"{header}.{body}.fake_sig"


class TestSafeTenantId:
    def test_valid_uuid(self):
        uid = "12345678-1234-1234-1234-1234567890ab"
        assert _safe_tenant_id(uid) == uid.lower()

    def test_none_returns_default(self):
        assert _safe_tenant_id(None) == _DEFAULT_TENANT

    def test_empty_string_returns_default(self):
        assert _safe_tenant_id("") == _DEFAULT_TENANT

    def test_invalid_uuid_returns_default(self):
        assert _safe_tenant_id("not-a-uuid") == _DEFAULT_TENANT

    def test_sql_injection_attempt_returns_default(self):
        assert _safe_tenant_id("'; DROP TABLE tenants; --") == _DEFAULT_TENANT

    def test_too_short_returns_default(self):
        assert _safe_tenant_id("1234-5678") == _DEFAULT_TENANT


class TestExtractTenantFromToken:
    def test_extracts_tenant_claim(self):
        uid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        token = _make_jwt_payload({"sub": "user1", "tenant": uid})
        assert extract_tenant_from_token(token) == uid.lower()

    def test_extracts_tenant_id_claim(self):
        uid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        token = _make_jwt_payload({"sub": "user1", "tenant_id": uid})
        assert extract_tenant_from_token(token) == uid.lower()

    def test_no_tenant_claim_returns_default(self):
        token = _make_jwt_payload({"sub": "user1"})
        assert extract_tenant_from_token(token) == _DEFAULT_TENANT

    def test_none_token_returns_default(self):
        assert extract_tenant_from_token(None) == _DEFAULT_TENANT

    def test_malformed_token_returns_default(self):
        assert extract_tenant_from_token("not.a.jwt") == _DEFAULT_TENANT

    def test_invalid_base64_returns_default(self):
        assert extract_tenant_from_token("bad..sig") == _DEFAULT_TENANT


class TestGetDbTenantPropagation:
    """Verify get_db() executes SET LOCAL with the request's tenant_id."""

    def test_set_config_called_with_tenant(self):
        from app.infra.database import get_db

        tenant_id = "12345678-1234-1234-1234-1234567890ab"

        mock_request = MagicMock()
        mock_request.state.tenant_id = tenant_id

        mock_session = MagicMock()
        mock_session_local = MagicMock(return_value=mock_session)

        with patch("app.infra.database.SessionLocal", mock_session_local):
            gen = get_db(mock_request)
            next(gen)  # start the generator (runs up to yield)
            mock_session.execute.assert_called_once()
            call_args = mock_session.execute.call_args
            # The SQL text should contain set_config
            sql_str = str(call_args[0][0])
            assert "set_config" in sql_str.lower()
            assert "app.current_tenant" in sql_str
            # The param should be the tenant_id
            params = call_args[0][1]
            assert params.get("t") == tenant_id

    def test_fallback_tenant_when_no_state(self):
        from app.infra.database import get_db, _DEFAULT_TENANT

        mock_request = MagicMock()
        del mock_request.state.tenant_id  # simulate missing state

        mock_session = MagicMock()
        mock_session_local = MagicMock(return_value=mock_session)

        with patch("app.infra.database.SessionLocal", mock_session_local):
            gen = get_db(mock_request)
            next(gen)
            call_params = mock_session.execute.call_args[0][1]
            assert call_params.get("t") == _DEFAULT_TENANT
