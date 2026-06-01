"""Unit tests for MFA login step-up flow (POST /auth/login + POST /auth/mfa/login).

Tests the new LoginResponse schema and mfa_session_token verification logic.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ── LoginResponse schema ──────────────────────────────────────────────────────


class TestLoginResponseSchema:
    def test_no_mfa_response(self) -> None:
        from app.domains.auth.schemas import LoginResponse

        r = LoginResponse(
            access_token="eyJhbGci",
            refresh_token="eyJhbGci",
            expires_in=1800,
            mfa_required=False,
        )
        assert r.mfa_required is False
        assert r.access_token == "eyJhbGci"
        assert r.mfa_session_token is None

    def test_mfa_required_response(self) -> None:
        from app.domains.auth.schemas import LoginResponse

        r = LoginResponse(
            mfa_required=True,
            mfa_session_token="short-lived-jwt",
        )
        assert r.mfa_required is True
        assert r.access_token is None
        assert r.mfa_session_token == "short-lived-jwt"

    def test_default_mfa_required_is_false(self) -> None:
        from app.domains.auth.schemas import LoginResponse

        r = LoginResponse()
        assert r.mfa_required is False


class TestMfaLoginRequest:
    def test_requires_session_token_and_code(self) -> None:
        from pydantic import ValidationError
        from app.domains.auth.schemas import MfaLoginRequest

        with pytest.raises(ValidationError):
            MfaLoginRequest()  # missing both required fields

    def test_valid_request(self) -> None:
        from app.domains.auth.schemas import MfaLoginRequest

        req = MfaLoginRequest(session_token="jwt-token", code="123456")
        assert req.session_token == "jwt-token"
        assert req.code == "123456"
        assert req.remember_me is False

    def test_accepts_backup_code_length(self) -> None:
        from app.domains.auth.schemas import MfaLoginRequest

        req = MfaLoginRequest(session_token="jwt", code="ABCD1234")  # 8-char backup
        assert len(req.code) == 8


# ── mfa_service TOTP verification ─────────────────────────────────────────────


class TestMfaServiceComprehensive:
    """Additional edge-case tests for mfa_service."""

    def test_generate_totp_reproducible_in_same_window(self) -> None:
        """Two calls in the same 30-second window must produce the same code."""
        from app.domains.auth.mfa_service import generate_totp_secret, generate_totp
        import time

        secret = generate_totp_secret()
        ts = time.time()
        # Same timestamp → same code
        assert generate_totp(secret, ts=ts) == generate_totp(secret, ts=ts)

    def test_different_secrets_produce_different_codes(self) -> None:
        from app.domains.auth.mfa_service import generate_totp_secret, generate_totp
        import time

        ts = time.time()
        s1 = generate_totp_secret()
        s2 = generate_totp_secret()
        # With overwhelming probability, different secrets → different codes
        codes = {generate_totp(s, ts=ts) for s in [s1, s2]}
        # May occasionally collide (1/1M chance); skip if they do
        if len(codes) == 1:
            pytest.skip("Rare collision — re-run")
        assert len(codes) == 2

    def test_backup_code_case_insensitive(self) -> None:
        """Backup codes should match regardless of case."""
        from app.domains.auth.mfa_service import (
            generate_backup_codes, hash_backup_codes, verify_backup_code,
        )

        codes = generate_backup_codes()
        stored = hash_backup_codes(codes)
        # All codes are uppercase; try with lowercase
        matched, _ = verify_backup_code(stored, codes[0].lower())
        assert matched is True

    def test_all_backup_codes_usable(self) -> None:
        from app.domains.auth.mfa_service import (
            generate_backup_codes, hash_backup_codes, verify_backup_code,
        )

        codes = generate_backup_codes()
        stored = hash_backup_codes(codes)
        for code in codes:
            matched, stored = verify_backup_code(stored, code)
            assert matched is True, f"Backup code {code} should have matched"

        import json
        assert json.loads(stored) == []  # all used

    def test_empty_backup_codes_list(self) -> None:
        import json
        from app.domains.auth.mfa_service import verify_backup_code

        empty = json.dumps([])
        matched, _ = verify_backup_code(empty, "ANYCODE1")
        assert matched is False


# ── Auth router MFA endpoint surface ─────────────────────────────────────────


class TestAuthRouterMfaEndpoints:
    def test_mfa_endpoints_registered(self) -> None:
        from app.domains.auth.router import router

        paths = {route.path for route in router.routes}
        assert "/auth/mfa/status" in paths
        assert "/auth/mfa/setup" in paths
        assert "/auth/mfa/verify" in paths
        assert "/auth/mfa/disable" in paths
        assert "/auth/mfa/backup-codes/regenerate" in paths
        assert "/auth/mfa/login" in paths

    def test_login_endpoint_uses_login_response_model(self) -> None:
        from app.domains.auth.router import router
        from app.domains.auth.schemas import LoginResponse

        login_routes = [
            r for r in router.routes
            if r.path == "/auth/login"
        ]
        assert len(login_routes) >= 1
        route = login_routes[0]
        assert route.response_model is LoginResponse
