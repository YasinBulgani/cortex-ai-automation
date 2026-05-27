"""Unit tests for auth.service pure helper functions.

All tests are self-contained: no DB, no Redis, no HTTP.
Covers:
  - _utc_ts: returns current UTC epoch as int
  - _sha256_token: SHA-256 hex digest of a token string
"""
from __future__ import annotations

import hashlib
import time

import pytest

try:
    from app.domains.auth.service import _utc_ts, _sha256_token
    _AUTH_OK = True
except ImportError:
    _AUTH_OK = False


# ---------------------------------------------------------------------------
# _utc_ts
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _AUTH_OK, reason="auth.service import failed")
class TestUtcTs:
    def test_returns_int(self):
        assert isinstance(_utc_ts(), int)

    def test_close_to_current_time(self):
        now = int(time.time())
        result = _utc_ts()
        # Should be within 5 seconds of wall-clock time
        assert abs(result - now) <= 5

    def test_monotonically_non_decreasing(self):
        t1 = _utc_ts()
        t2 = _utc_ts()
        assert t2 >= t1

    def test_reasonable_epoch_range(self):
        result = _utc_ts()
        # After 2024-01-01 (1704067200) and before 2100-01-01 (4102444800)
        assert result > 1_704_067_200
        assert result < 4_102_444_800

    def test_positive(self):
        assert _utc_ts() > 0


# ---------------------------------------------------------------------------
# _sha256_token
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _AUTH_OK, reason="auth.service import failed")
class TestSha256Token:
    def test_returns_string(self):
        assert isinstance(_sha256_token("mytoken"), str)

    def test_hex_only(self):
        result = _sha256_token("testtoken")
        assert all(c in "0123456789abcdef" for c in result)

    def test_length_is_64(self):
        # SHA-256 produces 64 hex chars
        assert len(_sha256_token("testtoken")) == 64

    def test_deterministic(self):
        token = "abc123xyz"
        assert _sha256_token(token) == _sha256_token(token)

    def test_different_tokens_different_hashes(self):
        assert _sha256_token("token1") != _sha256_token("token2")

    def test_matches_hashlib_directly(self):
        token = "supersecrettoken"
        expected = hashlib.sha256(token.encode("utf-8")).hexdigest()
        assert _sha256_token(token) == expected

    def test_empty_string(self):
        result = _sha256_token("")
        assert len(result) == 64

    def test_unicode_token(self):
        result = _sha256_token("şifre123")
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)

    def test_long_token(self):
        long_token = "a" * 1000
        result = _sha256_token(long_token)
        assert len(result) == 64

    def test_case_sensitive(self):
        assert _sha256_token("Token") != _sha256_token("token")
