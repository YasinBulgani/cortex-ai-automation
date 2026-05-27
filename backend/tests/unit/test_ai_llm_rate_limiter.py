"""Unit tests for app.domains.ai.llm_rate_limiter — in-memory rate limiting.

Tests are fully self-contained: no Redis (mocked to None), no DB, no HTTP.
Covers: _parse_token_member, record_llm_usage, get_user_usage,
check_llm_rate_limit (in-memory fallback path).
"""
from __future__ import annotations

import pytest
from unittest.mock import patch

try:
    from app.domains.ai.llm_rate_limiter import (
        record_llm_usage,
        get_user_usage,
        check_llm_rate_limit,
        _parse_token_member,
        _token_member,
        MAX_REQUESTS_PER_MINUTE,
        MAX_TOKENS_PER_HOUR,
        MAX_TOKENS_PER_DAY,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="llm_rate_limiter import failed")


# ---------------------------------------------------------------------------
# Fixture: isolate in-memory state between tests
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clear_state():
    """Reset in-memory usage state before and after each test."""
    import app.domains.ai.llm_rate_limiter as mod
    mod._usage_log.clear()
    mod._minute_counters.clear()
    yield
    mod._usage_log.clear()
    mod._minute_counters.clear()


@pytest.fixture(autouse=True)
def _no_redis():
    """Force in-memory fallback by patching Redis client to return None."""
    with patch("app.domains.ai.llm_rate_limiter._get_redis_client", return_value=None):
        yield


# ---------------------------------------------------------------------------
# _parse_token_member / _token_member
# ---------------------------------------------------------------------------

class TestTokenMemberHelpers:
    def test_token_member_returns_string(self):
        result = _token_member(100)
        assert isinstance(result, str)

    def test_token_member_contains_token_count(self):
        result = _token_member(500)
        parsed = _parse_token_member(result)
        assert parsed == 500

    def test_parse_token_member_extracts_count(self):
        assert _parse_token_member("100|abc123") == 100

    def test_parse_token_member_invalid_returns_zero(self):
        assert _parse_token_member("notanumber|abc") == 0

    def test_parse_token_member_empty_returns_zero(self):
        assert _parse_token_member("|abc") == 0

    def test_token_member_negative_clamped_to_zero(self):
        result = _token_member(-50)
        parsed = _parse_token_member(result)
        assert parsed == 0


# ---------------------------------------------------------------------------
# record_llm_usage — in-memory path
# ---------------------------------------------------------------------------

class TestRecordLlmUsage:
    def test_first_record_creates_entry(self):
        record_llm_usage("user-1", tokens_used=100)
        usage = get_user_usage("user-1")
        assert usage["requests_this_minute"] >= 1

    def test_token_usage_recorded(self):
        record_llm_usage("user-2", tokens_used=500)
        usage = get_user_usage("user-2")
        assert usage["tokens_this_hour"] >= 500

    def test_multiple_records_accumulate(self):
        record_llm_usage("user-3", tokens_used=200)
        record_llm_usage("user-3", tokens_used=300)
        usage = get_user_usage("user-3")
        assert usage["tokens_this_hour"] >= 500

    def test_zero_tokens_records_request(self):
        record_llm_usage("user-4", tokens_used=0)
        usage = get_user_usage("user-4")
        assert usage["requests_this_minute"] >= 1

    def test_different_users_isolated(self):
        record_llm_usage("user-A", tokens_used=1000)
        record_llm_usage("user-B", tokens_used=200)
        usage_a = get_user_usage("user-A")
        usage_b = get_user_usage("user-B")
        assert usage_a["tokens_this_hour"] >= 1000
        assert usage_b["tokens_this_hour"] >= 200


# ---------------------------------------------------------------------------
# get_user_usage — in-memory path
# ---------------------------------------------------------------------------

class TestGetUserUsage:
    def test_returns_dict(self):
        usage = get_user_usage("new-user")
        assert isinstance(usage, dict)

    def test_has_all_expected_keys(self):
        usage = get_user_usage("new-user")
        assert "requests_this_minute" in usage
        assert "max_requests_per_minute" in usage
        assert "tokens_this_hour" in usage
        assert "max_tokens_per_hour" in usage
        assert "tokens_today" in usage
        assert "max_tokens_per_day" in usage

    def test_new_user_zero_usage(self):
        usage = get_user_usage("brand-new-user-xyz")
        assert usage["requests_this_minute"] == 0
        assert usage["tokens_this_hour"] == 0
        assert usage["tokens_today"] == 0

    def test_max_limits_match_constants(self):
        usage = get_user_usage("u")
        assert usage["max_requests_per_minute"] == MAX_REQUESTS_PER_MINUTE
        assert usage["max_tokens_per_hour"] == MAX_TOKENS_PER_HOUR
        assert usage["max_tokens_per_day"] == MAX_TOKENS_PER_DAY

    def test_tokens_today_includes_hour_tokens(self):
        record_llm_usage("user-X", tokens_used=100)
        usage = get_user_usage("user-X")
        assert usage["tokens_today"] >= usage["tokens_this_hour"]


# ---------------------------------------------------------------------------
# check_llm_rate_limit — in-memory path
# ---------------------------------------------------------------------------

class TestCheckLlmRateLimit:
    def test_fresh_user_does_not_raise(self):
        from fastapi import HTTPException
        try:
            check_llm_rate_limit("fresh-user")
        except HTTPException:
            pytest.fail("check_llm_rate_limit raised HTTPException for fresh user")

    def test_many_requests_raises_429(self):
        from fastapi import HTTPException
        user = "heavy-user"
        # Record MAX_REQUESTS_PER_MINUTE requests directly in state
        import app.domains.ai.llm_rate_limiter as mod
        import time
        now = time.time()
        mod._minute_counters[user] = [now] * MAX_REQUESTS_PER_MINUTE
        with pytest.raises(HTTPException) as exc_info:
            check_llm_rate_limit(user)
        assert exc_info.value.status_code == 429

    def test_hour_token_limit_raises_429(self):
        from fastapi import HTTPException
        import app.domains.ai.llm_rate_limiter as mod
        import time
        user = "token-heavy"
        now = time.time()
        # Simulate having used MAX_TOKENS_PER_HOUR within the last hour
        mod._usage_log[user] = [(now - 60, MAX_TOKENS_PER_HOUR)]
        with pytest.raises(HTTPException) as exc_info:
            check_llm_rate_limit(user)
        assert exc_info.value.status_code == 429

    def test_day_token_limit_raises_429(self):
        from fastapi import HTTPException
        import app.domains.ai.llm_rate_limiter as mod
        import time
        user = "day-heavy"
        now = time.time()
        # Simulate having used MAX_TOKENS_PER_DAY across the day
        # (hour check passes, day check fails)
        mod._usage_log[user] = [
            (now - 7200, MAX_TOKENS_PER_DAY)  # 2h ago → outside hour window, inside day
        ]
        with pytest.raises(HTTPException) as exc_info:
            check_llm_rate_limit(user)
        assert exc_info.value.status_code == 429
