"""Unit tests for app.domains.ai.rate_limit_monitor — pure helpers + state.

Tests are fully self-contained: no DB, no HTTP.
Covers: _parse_int, _parse_duration, RateLimitState (pct helpers,
        should_throttle, is_stale, to_dict), record_rate_limit_headers
        (OpenAI + Anthropic headers), should_throttle module function.
"""
from __future__ import annotations

import time
import pytest

try:
    from app.domains.ai.rate_limit_monitor import (
        _parse_int,
        _parse_duration,
        RateLimitState,
        record_rate_limit_headers,
        should_throttle,
        get_rate_limit_state,
        _state,
        _THROTTLE_PCT,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="rate_limit_monitor import failed")


@pytest.fixture(autouse=True)
def _clear_state():
    _state.clear()
    yield
    _state.clear()


# ---------------------------------------------------------------------------
# _parse_int
# ---------------------------------------------------------------------------

class TestParseInt:
    def test_integer_string(self):
        assert _parse_int("100") == 100

    def test_float_string_truncates(self):
        assert _parse_int("99.9") == 99

    def test_zero(self):
        assert _parse_int("0") == 0

    def test_none_returns_none(self):
        assert _parse_int(None) is None

    def test_invalid_returns_none(self):
        assert _parse_int("abc") is None

    def test_empty_string_returns_none(self):
        assert _parse_int("") is None

    def test_integer_input(self):
        assert _parse_int(42) == 42

    def test_whitespace_stripped(self):
        assert _parse_int("  50  ") == 50


# ---------------------------------------------------------------------------
# _parse_duration
# ---------------------------------------------------------------------------

class TestParseDuration:
    def test_pure_float_string(self):
        assert _parse_duration("30") == pytest.approx(30.0)

    def test_pure_integer(self):
        assert _parse_duration("60") == pytest.approx(60.0)

    def test_seconds_suffix(self):
        assert _parse_duration("45s") == pytest.approx(45.0)

    def test_milliseconds_suffix(self):
        assert _parse_duration("500ms") == pytest.approx(0.5)

    def test_minutes_suffix(self):
        assert _parse_duration("2m") == pytest.approx(120.0)

    def test_hours_suffix(self):
        assert _parse_duration("1h") == pytest.approx(3600.0)

    def test_compound_hours_minutes_seconds(self):
        assert _parse_duration("1h30m45s") == pytest.approx(3600 + 1800 + 45)

    def test_compound_minutes_seconds(self):
        assert _parse_duration("1m30s") == pytest.approx(90.0)

    def test_milliseconds_and_seconds(self):
        assert _parse_duration("500ms30s") == pytest.approx(30.5)

    def test_none_returns_none(self):
        assert _parse_duration(None) is None

    def test_empty_string_returns_none(self):
        assert _parse_duration("") is None

    def test_invalid_string_returns_none(self):
        assert _parse_duration("notaduration") is None

    def test_iso_timestamp_future_returns_positive(self):
        from datetime import datetime, timezone, timedelta
        future = datetime.now(timezone.utc) + timedelta(seconds=60)
        iso = future.strftime("%Y-%m-%dT%H:%M:%SZ")
        result = _parse_duration(iso)
        assert result is not None
        assert result > 0

    def test_iso_timestamp_past_returns_zero(self):
        result = _parse_duration("2020-01-01T00:00:00Z")
        assert result is not None
        assert result == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# RateLimitState helpers
# ---------------------------------------------------------------------------

class TestRateLimitStatePct:
    def _state(self, **kwargs):
        return RateLimitState(model="gpt-4o", **kwargs)

    def test_pct_remaining_requests_calculates(self):
        s = self._state(remaining_requests=80, limit_requests=100)
        assert s.pct_remaining_requests() == pytest.approx(80.0)

    def test_pct_remaining_requests_none_when_no_limit(self):
        s = self._state(remaining_requests=80, limit_requests=None)
        assert s.pct_remaining_requests() is None

    def test_pct_remaining_requests_none_when_no_remaining(self):
        s = self._state(remaining_requests=None, limit_requests=100)
        assert s.pct_remaining_requests() is None

    def test_pct_remaining_tokens_calculates(self):
        s = self._state(remaining_tokens=5000, limit_tokens=100000)
        assert s.pct_remaining_tokens() == pytest.approx(5.0)

    def test_pct_remaining_tokens_none_when_missing(self):
        s = self._state(remaining_tokens=None, limit_tokens=None)
        assert s.pct_remaining_tokens() is None


class TestRateLimitStateShouldThrottle:
    def _fresh_state(self, **kwargs):
        s = RateLimitState(model="model-x", **kwargs)
        s.updated_at = time.time()  # fresh
        return s

    def test_ok_when_well_above_threshold(self):
        s = self._fresh_state(remaining_requests=50, limit_requests=100)
        throttle, reason = s.should_throttle()
        assert throttle is False
        assert reason == "ok"

    def test_throttle_when_requests_below_threshold(self):
        s = self._fresh_state(remaining_requests=5, limit_requests=100)  # 5%
        throttle, _ = s.should_throttle()
        assert throttle is True

    def test_throttle_when_tokens_below_threshold(self):
        s = self._fresh_state(remaining_tokens=500, limit_tokens=100000)  # 0.5%
        throttle, _ = s.should_throttle()
        assert throttle is True

    def test_throttle_when_retry_after_set(self):
        s = self._fresh_state(retry_after_secs=30.0)
        throttle, reason = s.should_throttle()
        assert throttle is True
        assert "retry_after" in reason

    def test_stale_state_does_not_throttle(self):
        s = RateLimitState(model="model-x", remaining_requests=1, limit_requests=100)
        s.updated_at = time.time() - 200.0  # > _STATE_STALE_SECS
        throttle, reason = s.should_throttle()
        assert throttle is False
        assert reason == "stale"

    def test_at_exactly_threshold_does_not_throttle(self):
        # remaining = exactly threshold → not < threshold → no throttle
        s = self._fresh_state(remaining_requests=10, limit_requests=100)  # exactly 10%
        throttle, _ = s.should_throttle()
        assert throttle is False


class TestRateLimitStateToDict:
    def test_returns_dict(self):
        s = RateLimitState(model="gpt-4o")
        d = s.to_dict()
        assert isinstance(d, dict)

    def test_has_model(self):
        s = RateLimitState(model="claude-sonnet-4")
        d = s.to_dict()
        assert d["model"] == "claude-sonnet-4"

    def test_has_age_secs(self):
        s = RateLimitState(model="m")
        d = s.to_dict()
        assert "age_secs" in d
        assert d["age_secs"] >= 0


# ---------------------------------------------------------------------------
# record_rate_limit_headers
# ---------------------------------------------------------------------------

class TestRecordRateLimitHeaders:
    def test_returns_none_for_empty_headers(self):
        result = record_rate_limit_headers("gpt-4o", {})
        assert result is None

    def test_returns_none_for_empty_model(self):
        result = record_rate_limit_headers("", {"x-ratelimit-remaining-requests": "100"})
        assert result is None

    def test_openai_remaining_requests_parsed(self):
        state = record_rate_limit_headers("gpt-4o", {
            "x-ratelimit-remaining-requests": "500",
            "x-ratelimit-limit-requests": "1000",
        })
        assert state is not None
        assert state.remaining_requests == 500
        assert state.limit_requests == 1000
        assert state.provider == "openai"

    def test_openai_tokens_parsed(self):
        state = record_rate_limit_headers("gpt-4o", {
            "x-ratelimit-remaining-tokens": "80000",
            "x-ratelimit-limit-tokens": "100000",
        })
        assert state is not None
        assert state.remaining_tokens == 80000

    def test_anthropic_headers_parsed(self):
        state = record_rate_limit_headers("claude-sonnet", {
            "anthropic-ratelimit-requests-remaining": "200",
            "anthropic-ratelimit-requests-limit": "1000",
        })
        assert state is not None
        assert state.remaining_requests == 200
        assert state.provider == "anthropic"

    def test_retry_after_parsed(self):
        state = record_rate_limit_headers("gpt-4o", {
            "x-ratelimit-remaining-requests": "5",
            "retry-after": "30",
        })
        assert state is not None
        assert state.retry_after_secs == pytest.approx(30.0)

    def test_state_saved_in_module_dict(self):
        record_rate_limit_headers("test-model", {
            "x-ratelimit-remaining-requests": "100",
        })
        assert "test-model" in _state

    def test_case_insensitive_headers(self):
        state = record_rate_limit_headers("gpt-4o", {
            "X-RateLimit-Remaining-Requests": "300",
            "X-RateLimit-Limit-Requests": "1000",
        })
        assert state is not None
        assert state.remaining_requests == 300


# ---------------------------------------------------------------------------
# should_throttle module function
# ---------------------------------------------------------------------------

class TestShouldThrottleModule:
    def test_no_data_returns_false(self):
        throttle, reason = should_throttle("unknown-model")
        assert throttle is False
        assert reason == "no_data"

    def test_throttles_after_headers_below_threshold(self):
        record_rate_limit_headers("low-model", {
            "x-ratelimit-remaining-requests": "1",
            "x-ratelimit-limit-requests": "100",
        })
        throttle, _ = should_throttle("low-model")
        assert throttle is True

    def test_no_throttle_for_healthy_state(self):
        record_rate_limit_headers("healthy-model", {
            "x-ratelimit-remaining-requests": "800",
            "x-ratelimit-limit-requests": "1000",
        })
        throttle, reason = should_throttle("healthy-model")
        assert throttle is False
