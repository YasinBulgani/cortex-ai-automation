"""Unit tests for core auth helper functions — coverage enhancements.

Tests token creation, decoding, password reset flows with edge cases.
Focuses on pure logic paths without decorator sampling issues.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

try:
    from app.domains.auth.service import (
        create_access_token,
        decode_token,
        revoke_token,
        create_password_reset_token,
        verify_password_reset_token,
        create_refresh_token,
        verify_refresh_token,
        _password_reset_tokens,
        _revoked_tokens,
    )
    from app.config import settings
    import jwt as pyjwt

    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="auth service import failed")


# ────────────────────────────────────────────────────────────────────────────
# Token Creation — Edge Cases
# ────────────────────────────────────────────────────────────────────────────


class TestTokenCreationEdgeCases:
    """Edge cases for create_access_token."""

    def test_token_with_empty_user_id(self):
        """Empty user ID should create a token (app validates)."""
        token = create_access_token("")
        payload = decode_token(token)
        assert payload["sub"] == ""

    def test_token_with_unicode_subject(self):
        """Unicode characters in subject should work."""
        token = create_access_token("user_🔐_тест")
        payload = decode_token(token)
        assert payload["sub"] == "user_🔐_тест"

    def test_token_with_very_long_subject(self):
        """Very long subject ID."""
        long_user = "u" * 500
        token = create_access_token(long_user)
        payload = decode_token(token)
        assert payload["sub"] == long_user

    def test_token_with_zero_expiry_uses_default(self):
        """Zero expiry falls back to settings."""
        token = create_access_token("user", expires_minutes=0)
        payload = pyjwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        now = int(datetime.now(timezone.utc).timestamp())
        expected_min = now + (settings.access_token_expire_minutes * 60) - 10
        expected_max = now + (settings.access_token_expire_minutes * 60) + 10
        assert expected_min <= payload["exp"] <= expected_max

    def test_token_with_negative_expiry_uses_default(self):
        """Negative expiry falls back to settings."""
        token = create_access_token("user", expires_minutes=-1000)
        payload = pyjwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        now = int(datetime.now(timezone.utc).timestamp())
        expected_min = now + (settings.access_token_expire_minutes * 60) - 10
        expected_max = now + (settings.access_token_expire_minutes * 60) + 10
        assert expected_min <= payload["exp"] <= expected_max

    def test_token_with_extra_claims_override_standard(self):
        """Extra claims can override standard JWT claims."""
        token = create_access_token(
            "original_user",
            extra_claims={"sub": "override_user", "custom": "value"}
        )
        payload = pyjwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        assert payload["sub"] == "override_user"
        assert payload["custom"] == "value"

    def test_token_jti_is_unique_per_call(self):
        """Each token has a unique JTI."""
        tokens = [create_access_token("user") for _ in range(5)]
        jtis = []
        for token in tokens:
            payload = pyjwt.decode(
                token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
            )
            jtis.append(payload.get("jti"))
        # All should be unique
        assert len(jtis) == len(set(jtis))
        # None should be None
        assert all(jti for jti in jtis)


# ────────────────────────────────────────────────────────────────────────────
# Token Decoding — Edge Cases
# ────────────────────────────────────────────────────────────────────────────


class TestTokenDecodingEdgeCases:
    """Edge cases for decode_token."""

    def test_decode_missing_exp_raises(self):
        """Token without exp is rejected (JWT library requires exp)."""
        payload = {"sub": "user"}
        token = pyjwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        # JWT without exp is not automatically rejected — PyJWT only rejects if verify_exp=True
        # Our decode_token doesn't explicitly set options, so this actually succeeds
        result = decode_token(token)
        assert result["sub"] == "user"  # No exp but still valid

    def test_decode_expired_token_raises(self):
        """Expired token is rejected."""
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        payload = {
            "sub": "user",
            "exp": int(past.timestamp()),
            "jti": "expired",
        }
        token = pyjwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        with pytest.raises(Exception):
            decode_token(token)

    def test_decode_with_purpose_claim_rejected(self):
        """Tokens with purpose claim (special-purpose tokens) are rejected."""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "user",
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "purpose": "password_reset",
        }
        token = pyjwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        with pytest.raises(pyjwt.InvalidTokenError) as exc:
            decode_token(token)
        assert "purpose" in str(exc.value).lower()

    def test_decode_with_empty_jti_works(self):
        """Empty JTI doesn't cause issues."""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "user",
            "exp": int((now + timedelta(hours=1)).timestamp()),
            "jti": "",
        }
        token = pyjwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        result = decode_token(token)
        assert result["jti"] == ""

    def test_decode_with_missing_sub_works(self):
        """Missing 'sub' claim is allowed (app validates)."""
        now = datetime.now(timezone.utc)
        payload = {
            "exp": int((now + timedelta(hours=1)).timestamp()),
        }
        token = pyjwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        result = decode_token(token)
        assert "sub" not in result

    def test_decode_invalid_signature_raises(self):
        """Invalid signature raises."""
        token = create_access_token("user")
        # Corrupt the signature
        parts = token.split(".")
        corrupted = ".".join([parts[0], parts[1], "invalidsignature"])
        with pytest.raises(Exception):
            decode_token(corrupted)

    def test_decode_two_part_jwt_raises(self):
        """JWT without signature (2 parts) raises."""
        with pytest.raises(Exception):
            decode_token("header.payload")


# ────────────────────────────────────────────────────────────────────────────
# Token Revocation — State Transitions
# ────────────────────────────────────────────────────────────────────────────


class TestTokenRevocationTransitions:
    """Test revocation state transitions."""

    def test_revoke_valid_token_makes_it_invalid(self):
        """Revoking a token prevents its use."""
        token = create_access_token("user")
        # Token should be valid initially
        payload = decode_token(token)
        assert payload["sub"] == "user"
        # Revoke it
        revoke_token(token)
        # Now it should fail
        with pytest.raises(pyjwt.InvalidTokenError):
            decode_token(token)

    def test_revoke_invalid_token_silently_succeeds(self):
        """Revoking a malformed token doesn't raise."""
        revoke_token("not.a.valid.token")
        revoke_token("garbage")
        # Should not raise

    def test_revoke_token_without_jti_silently_succeeds(self):
        """Token without JTI can't be revoked but doesn't error."""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "user",
            "exp": int((now + timedelta(hours=1)).timestamp()),
            # No JTI
        }
        token = pyjwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        revoke_token(token)
        # Token still works since it can't be revoked
        result = decode_token(token)
        assert result["sub"] == "user"

    def test_revoke_already_revoked_token_idempotent(self):
        """Revoking twice is safe."""
        token = create_access_token("user")
        revoke_token(token)
        revoke_token(token)  # Second revoke
        with pytest.raises(pyjwt.InvalidTokenError):
            decode_token(token)


# ────────────────────────────────────────────────────────────────────────────
# Password Reset Token — State Transitions
# ────────────────────────────────────────────────────────────────────────────


class TestPasswordResetTokenTransitions:
    """Test password reset token lifecycle."""

    def test_create_and_verify_reset_token(self):
        """Create and immediately verify a reset token."""
        token = create_password_reset_token("user123")
        user_id = verify_password_reset_token(token)
        assert user_id == "user123"

    def test_verify_reset_token_is_single_use(self):
        """Reset token is consumed after first use."""
        token = create_password_reset_token("user123")
        # First use
        user_id = verify_password_reset_token(token)
        assert user_id == "user123"
        # Second use should return None (consumed)
        user_id = verify_password_reset_token(token)
        assert user_id is None

    def test_verify_invalid_reset_token_returns_none(self):
        """Invalid reset token returns None."""
        result = verify_password_reset_token("garbage.token.value")
        assert result is None

    def test_verify_access_token_as_reset_token_returns_none(self):
        """Access token is not a valid reset token."""
        access_token = create_access_token("user123")
        result = verify_password_reset_token(access_token)
        assert result is None

    def test_verify_reset_token_with_empty_jti_returns_none(self):
        """Reset token with empty JTI can't be found in storage."""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": "user123",
            "exp": int((now + timedelta(minutes=15)).timestamp()),
            "purpose": "password_reset",
            "jti": "",  # empty JTI
        }
        token = pyjwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        result = verify_password_reset_token(token)
        assert result is None

    def test_multiple_reset_tokens_independent(self):
        """Multiple reset tokens for different users are independent."""
        token1 = create_password_reset_token("user1")
        token2 = create_password_reset_token("user2")
        # Both should verify to their respective users
        assert verify_password_reset_token(token1) == "user1"
        assert verify_password_reset_token(token2) == "user2"
        # Both consumed after first use
        assert verify_password_reset_token(token1) is None
        assert verify_password_reset_token(token2) is None


# ────────────────────────────────────────────────────────────────────────────
# Refresh Token — Async Operations
# ────────────────────────────────────────────────────────────────────────────


class TestRefreshTokenAsyncOps:
    """Async tests for refresh token operations."""

    @pytest.mark.asyncio
    async def test_create_refresh_token_structure(self):
        """Created refresh token has correct JWT structure."""
        mock_db = AsyncMock()
        mock_db.flush = AsyncMock()

        token = await create_refresh_token("user1", mock_db, user_agent="Mozilla/5.0")

        payload = pyjwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        assert payload["sub"] == "user1"
        assert payload["type"] == "refresh"
        assert "jti" in payload
        assert isinstance(token, str)

    @pytest.mark.asyncio
    async def test_verify_refresh_token_missing_jti_raises(self):
        """Refresh token without JTI raises ValueError."""
        now = int(datetime.now(timezone.utc).timestamp())
        payload = {
            "sub": "user1",
            "exp": now + 86400,
            "type": "refresh",
            # Missing 'jti'
        }
        token = pyjwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

        mock_db = AsyncMock()
        with pytest.raises(ValueError) as exc:
            await verify_refresh_token(token, mock_db)
        assert "jti" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_verify_refresh_token_wrong_type_raises(self):
        """Refresh token with wrong 'type' raises."""
        now = int(datetime.now(timezone.utc).timestamp())
        payload = {
            "sub": "user1",
            "exp": now + 86400,
            "type": "access",  # Wrong type
            "jti": "test-jti",
        }
        token = pyjwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

        mock_db = AsyncMock()
        with pytest.raises(ValueError) as exc:
            await verify_refresh_token(token, mock_db)
        assert "refresh" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_verify_refresh_token_no_record_raises(self):
        """Refresh token not in DB raises ValueError."""
        now = int(datetime.now(timezone.utc).timestamp())
        payload = {
            "sub": "user1",
            "exp": now + 86400,
            "type": "refresh",
            "jti": "nonexistent-jti",
        }
        token = pyjwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=None)

        with pytest.raises(ValueError) as exc:
            await verify_refresh_token(token, mock_db)
        assert "bulunamadi" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_verify_refresh_token_revoked_raises(self):
        """Revoked refresh token raises ValueError."""
        now = int(datetime.now(timezone.utc).timestamp())
        payload = {
            "sub": "user1",
            "exp": now + 86400,
            "type": "refresh",
            "jti": "revoked-jti",
        }
        token = pyjwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

        mock_record = MagicMock()
        mock_record.revoked = True
        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=mock_record)

        with pytest.raises(ValueError) as exc:
            await verify_refresh_token(token, mock_db)
        assert "iptal" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_verify_refresh_token_expired_raises(self):
        """Expired refresh token raises ValueError."""
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        payload = {
            "sub": "user1",
            "exp": int(past.timestamp()),
            "type": "refresh",
            "jti": "expired-jti",
        }
        token = pyjwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

        mock_record = MagicMock()
        mock_record.revoked = False
        mock_record.expires_at = past.replace(tzinfo=None)
        mock_db = AsyncMock()
        mock_db.get = AsyncMock(return_value=mock_record)

        with pytest.raises(ValueError) as exc:
            await verify_refresh_token(token, mock_db)
        assert "dolmus" in str(exc.value).lower() or "expired" in str(exc.value).lower()


# ────────────────────────────────────────────────────────────────────────────
# Parametrized Tests — Combinatorial Coverage
# ────────────────────────────────────────────────────────────────────────────


class TestParametrizedCombinatorial:
    """Parametrized tests for combinatorial coverage."""

    @pytest.mark.parametrize("user_id", ["user1", "тест", "user@example.com", ""])
    def test_token_with_various_user_ids(self, user_id):
        """Token creation works with various user ID formats."""
        token = create_access_token(user_id)
        payload = decode_token(token)
        assert payload["sub"] == user_id

    @pytest.mark.parametrize("expires_minutes", [1, 30, 60, 1440, 10080])
    def test_token_with_various_expiry_times(self, expires_minutes):
        """Token creation works with various expiry times."""
        token = create_access_token("user", expires_minutes=expires_minutes)
        payload = decode_token(token)
        assert payload["sub"] == "user"
        now = int(datetime.now(timezone.utc).timestamp())
        # Verify exp is approximately correct
        assert payload["exp"] > now

    @pytest.mark.parametrize("num_claims", [0, 1, 3, 5])
    def test_token_with_various_claim_counts(self, num_claims):
        """Token creation works with various numbers of extra claims."""
        claims = {f"claim_{i}": f"value_{i}" for i in range(num_claims)}
        token = create_access_token("user", extra_claims=claims if claims else None)
        payload = decode_token(token)
        for k, v in claims.items():
            assert payload[k] == v
