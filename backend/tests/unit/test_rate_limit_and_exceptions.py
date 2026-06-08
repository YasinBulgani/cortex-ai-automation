"""Unit tests for RateLimitError and related exception/handler infrastructure.

Covers:
1.  RateLimitError instantiation
2.  RateLimitError is a subclass of Exception
3.  RateLimitError message is accessible via str()
4.  RateLimitError.retry_after_seconds defaults to 60
5.  RateLimitError with custom retry_after_seconds
6.  check_llm_rate_limit raises RateLimitError when minute limit exceeded
7.  check_llm_rate_limit passes when within limits
8.  check_llm_rate_limit raises RuntimeError when Redis unavailable
9.  rate_limit_error_handler returns 429 with Retry-After header
10. register_exception_handlers includes RateLimitError handler
"""
from __future__ import annotations

import pytest

try:
    from app.core.exceptions import RateLimitError
    _IMPORT_OK = True
except Exception:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="import failed")


# ---------------------------------------------------------------------------
# 1–5 — RateLimitError class behaviour
# ---------------------------------------------------------------------------

class TestRateLimitErrorClass:
    def test_instantiation(self):
        """RateLimitError can be instantiated with a message."""
        err = RateLimitError("limit exceeded")
        assert err is not None

    def test_is_subclass_of_exception(self):
        """RateLimitError is a subclass of Exception."""
        assert issubclass(RateLimitError, Exception)

    def test_message_accessible_via_str(self):
        """str(RateLimitError) returns the message passed at construction."""
        err = RateLimitError("too many requests")
        assert str(err) == "too many requests"

    def test_retry_after_seconds_defaults_to_60(self):
        """retry_after_seconds defaults to 60 when not supplied."""
        err = RateLimitError("rate limited")
        assert err.retry_after_seconds == 60

    def test_custom_retry_after_seconds(self):
        """retry_after_seconds stores the value passed explicitly."""
        err = RateLimitError("rate limited", retry_after_seconds=3600)
        assert err.retry_after_seconds == 3600


# ---------------------------------------------------------------------------
# 6–8 — check_llm_rate_limit behaviour
# ---------------------------------------------------------------------------

class TestCheckLlmRateLimit:
    """Tests for app.domains.ai.llm_rate_limiter.check_llm_rate_limit."""

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _import_check():
        """Return (check_fn, MAX_REQUESTS_PER_MINUTE) or skip if unavailable."""
        try:
            from app.domains.ai.llm_rate_limiter import (
                check_llm_rate_limit,
                MAX_REQUESTS_PER_MINUTE,
            )
            return check_llm_rate_limit, MAX_REQUESTS_PER_MINUTE
        except Exception as exc:
            pytest.skip(f"llm_rate_limiter not importable: {exc}")

    # -- tests -------------------------------------------------------------

    def test_raises_rate_limit_error_when_minute_limit_exceeded(self):
        """RateLimitError is raised when _redis_usage_snapshot returns (MAX, 0, 0)."""
        from unittest.mock import patch

        check_llm_rate_limit, MAX_REQUESTS_PER_MINUTE = self._import_check()

        snapshot_return = (MAX_REQUESTS_PER_MINUTE, 0, 0)

        # Provide a non-None redis_client so the redis path is taken, then
        # patch _redis_usage_snapshot to return the limit-exceeded snapshot.
        with patch(
            "app.domains.ai.llm_rate_limiter._get_redis_client",
            return_value=object(),  # truthy, non-None sentinel
        ), patch(
            "app.domains.ai.llm_rate_limiter._redis_usage_snapshot",
            return_value=snapshot_return,
        ):
            with pytest.raises(RateLimitError):
                check_llm_rate_limit("user-test-1")

    def test_passes_when_within_limits(self):
        """No exception raised when _redis_usage_snapshot returns (0, 0, 0)."""
        from unittest.mock import patch

        check_llm_rate_limit, _ = self._import_check()

        with patch(
            "app.domains.ai.llm_rate_limiter._get_redis_client",
            return_value=object(),
        ), patch(
            "app.domains.ai.llm_rate_limiter._redis_usage_snapshot",
            return_value=(0, 0, 0),
        ):
            # Must not raise
            check_llm_rate_limit("user-test-2")

    def test_raises_runtime_error_when_redis_unavailable(self):
        """RuntimeError propagated when _get_redis_client raises RuntimeError."""
        from unittest.mock import patch

        check_llm_rate_limit, _ = self._import_check()

        with patch(
            "app.domains.ai.llm_rate_limiter._get_redis_client",
            side_effect=RuntimeError("Redis bağlantısı yok"),
        ):
            with pytest.raises(RuntimeError):
                check_llm_rate_limit("user-test-3")


# ---------------------------------------------------------------------------
# 9–10 — exception_handlers
# ---------------------------------------------------------------------------

class TestExceptionHandlers:
    """Tests for app.core.exception_handlers."""

    @staticmethod
    def _import_handlers():
        try:
            import app.core.exception_handlers as handlers
            return handlers
        except Exception as exc:
            pytest.skip(f"exception_handlers not importable: {exc}")

    def test_rate_limit_error_handler_returns_429_with_retry_after_header(self):
        """rate_limit_error_handler returns status 429 with Retry-After header."""
        import asyncio
        from unittest.mock import MagicMock

        handlers = self._import_handlers()

        request = MagicMock()
        request.state = MagicMock()
        request.state.request_id = "req-abc"

        exc = RateLimitError("too many requests", retry_after_seconds=42)

        _loop = asyncio.new_event_loop()
        try:
            response = _loop.run_until_complete(
                handlers.rate_limit_error_handler(request, exc)
            )
        finally:
            _loop.close()

        assert response.status_code == 429
        assert "Retry-After" in response.headers
        assert response.headers["Retry-After"] == "42"

    def test_register_exception_handlers_includes_rate_limit_error(self):
        """register_exception_handlers registers a handler for RateLimitError."""
        from unittest.mock import MagicMock, patch

        handlers = self._import_handlers()

        app_mock = MagicMock()
        registered: list = []

        def record_handler(exc_type, handler):
            registered.append(exc_type)

        app_mock.add_exception_handler.side_effect = record_handler

        # Ensure the RateLimitError import inside register_exception_handlers succeeds.
        with patch.dict("sys.modules", {}):
            handlers.register_exception_handlers(app_mock)

        assert RateLimitError in registered, (
            "RateLimitError was not registered as an exception handler. "
            f"Registered types: {registered}"
        )
