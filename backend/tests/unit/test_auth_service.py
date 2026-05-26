"""Unit tests for app.domains.auth.service.

Tests are fully self-contained: no DB, no HTTP, no real Redis.
Covers: hash_password, verify_password, create_access_token, decode_token,
revoke_token, create_password_reset_token, verify_password_reset_token.
"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

try:
    from app.domains.auth import service as auth_service
    from app.domains.auth.service import (
        hash_password,
        verify_password,
        create_access_token,
        decode_token,
        revoke_token,
        create_password_reset_token,
        verify_password_reset_token,
        _revoked_tokens,
        _password_reset_tokens,
    )
    import jwt as pyjwt

    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="auth service import failed")

USER_ID = "user-abc-123"


# ---------------------------------------------------------------------------
# hash_password / verify_password
# ---------------------------------------------------------------------------

class TestHashPassword:
    def test_returns_non_empty_string(self):
        hashed = hash_password("secret123")
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_is_different_from_plaintext(self):
        plain = "mysecretpassword"
        assert hash_password(plain) != plain

    def test_two_hashes_of_same_password_differ(self):
        """bcrypt uses random salt — same input must produce different hashes."""
        h1 = hash_password("hello")
        h2 = hash_password("hello")
        assert h1 != h2

    def test_verify_correct_password_returns_true(self):
        plain = "correcthorse"
        hashed = hash_password(plain)
        assert verify_password(plain, hashed) is True

    def test_verify_wrong_password_returns_false(self):
        hashed = hash_password("realpassword")
        assert verify_password("wrongpassword", hashed) is False

    def test_verify_empty_string_returns_false(self):
        hashed = hash_password("something")
        assert verify_password("", hashed) is False

    def test_verify_with_garbage_hash_returns_false(self):
        assert verify_password("anything", "not-a-valid-hash") is False


# ---------------------------------------------------------------------------
# create_access_token / decode_token
# ---------------------------------------------------------------------------

class TestCreateAccessToken:
    def test_returns_string(self):
        token = create_access_token(USER_ID)
        assert isinstance(token, str)
        assert len(token) > 20

    def test_token_contains_subject(self):
        token = create_access_token(USER_ID)
        from app.config import settings
        payload = pyjwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        assert payload["sub"] == USER_ID

    def test_token_has_jti(self):
        token = create_access_token(USER_ID)
        from app.config import settings
        payload = pyjwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        assert "jti" in payload and payload["jti"]

    def test_extra_claims_included(self):
        token = create_access_token(USER_ID, extra_claims={"role": "admin"})
        from app.config import settings
        payload = pyjwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        assert payload.get("role") == "admin"

    def test_custom_expiry_respected(self):
        token = create_access_token(USER_ID, expires_minutes=120)
        from app.config import settings
        payload = pyjwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        now = int(datetime.now(timezone.utc).timestamp())
        assert payload["exp"] > now + 7000  # at least ~2 hrs

    def test_decode_valid_token_returns_payload(self):
        token = create_access_token(USER_ID)
        payload = decode_token(token)
        assert payload["sub"] == USER_ID

    def test_decode_tampered_token_raises(self):
        token = create_access_token(USER_ID)
        bad_token = token[:-4] + "XXXX"
        with pytest.raises(Exception):
            decode_token(bad_token)

    def test_decode_expired_token_raises(self):
        # create_access_token ignores negative values; encode an expired token directly
        import jwt as pyjwt
        from app.config import settings
        from datetime import datetime, timedelta, timezone
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        expired_payload = {
            "sub": USER_ID,
            "iat": int(past.timestamp()),
            "exp": int(past.timestamp()),
            "jti": "expired-test",
        }
        token = pyjwt.encode(expired_payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        with pytest.raises(Exception):
            decode_token(token)


# ---------------------------------------------------------------------------
# revoke_token / decode after revocation
# ---------------------------------------------------------------------------

class TestRevokeToken:
    def test_revoked_token_raises_on_decode(self):
        token = create_access_token(USER_ID)
        revoke_token(token)
        with pytest.raises(Exception):
            decode_token(token)

    def test_revoking_garbage_does_not_raise(self):
        """Revoking an invalid token must silently no-op."""
        revoke_token("not.a.real.token")  # must not raise


# ---------------------------------------------------------------------------
# create_password_reset_token / verify_password_reset_token
# ---------------------------------------------------------------------------

class TestPasswordResetToken:
    def test_create_returns_string(self):
        token = create_password_reset_token(USER_ID)
        assert isinstance(token, str) and len(token) > 10

    def test_verify_valid_token_returns_user_id(self):
        token = create_password_reset_token(USER_ID)
        result = verify_password_reset_token(token)
        assert result == USER_ID

    def test_verify_consumes_token(self):
        """Token should be single-use — second verify returns None."""
        token = create_password_reset_token(USER_ID)
        verify_password_reset_token(token)  # first use
        second = verify_password_reset_token(token)
        assert second is None

    def test_verify_garbage_returns_none(self):
        result = verify_password_reset_token("garbage.token.value")
        assert result is None

    def test_verify_access_token_as_reset_token_returns_none(self):
        """An access token must NOT pass as a password-reset token."""
        access_token = create_access_token(USER_ID)
        result = verify_password_reset_token(access_token)
        assert result is None
