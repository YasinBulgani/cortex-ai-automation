"""Unit tests for rate limiter runtime safety.

A-MED-3: Rate limiter eager validation and fail-closed behavior.
"""

import pytest
from unittest.mock import patch, MagicMock

from app.core.runtime import build_rate_limiter, _redis_ping_ok


def test_redis_ping_ok_success():
    """Should return True when Redis is reachable."""
    with patch('redis.Redis.from_url') as mock_redis:
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        mock_redis.return_value = mock_client

        result = _redis_ping_ok()

        assert result is True
        mock_client.ping.assert_called_once()


def test_redis_ping_ok_failure():
    """Should return False when Redis is unreachable."""
    with patch('redis.Redis.from_url') as mock_redis:
        mock_redis.side_effect = Exception("Connection refused")

        result = _redis_ping_ok()

        assert result is False


def test_build_rate_limiter_redis_unavailable_non_prod():
    """Non-prod should disable rate limiting if Redis down."""
    with patch('app.config.settings.is_production_like', False), \
         patch('os.getenv', return_value=""), \
         patch('app.core.runtime._redis_ping_ok', return_value=False):

        limiter, enabled, exc_type, handler = build_rate_limiter()

        assert limiter is None
        assert enabled is False
        assert exc_type is None
        assert handler is None


def test_build_rate_limiter_redis_unavailable_prod():
    """Production should fail-closed if Redis unavailable."""
    with patch('app.config.settings.is_production_like', True), \
         patch('app.core.runtime._redis_ping_ok', return_value=False):

        with pytest.raises(RuntimeError) as exc_info:
            build_rate_limiter()

        assert "Redis unavailable" in str(exc_info.value)
        assert "rate limiting required" in str(exc_info.value).lower()


def test_build_rate_limiter_success():
    """Should initialize limiter when Redis available."""
    with patch('app.config.settings.is_production_like', False), \
         patch('app.config.settings.rate_limit_default', '10/minute'), \
         patch('app.config.settings.redis_url', 'redis://localhost'), \
         patch('app.core.runtime._redis_ping_ok', return_value=True), \
         patch('slowapi.Limiter') as mock_limiter_class, \
         patch('slowapi._rate_limit_exceeded_handler') as mock_handler:

        mock_limiter = MagicMock()
        mock_limiter_class.return_value = mock_limiter

        limiter, enabled, exc_type, handler = build_rate_limiter()

        assert limiter is not None
        assert enabled is True
        assert exc_type is not None
        assert handler is not None


def test_build_rate_limiter_slowapi_missing():
    """Should raise if slowapi missing in production."""
    with patch('app.config.settings.is_production_like', True), \
         patch('app.core.runtime._redis_ping_ok', return_value=True), \
         patch('builtins.__import__', side_effect=ImportError("No module named 'slowapi'")):

        with pytest.raises(RuntimeError) as exc_info:
            build_rate_limiter()

        assert "slowapi" in str(exc_info.value).lower()
        assert "required" in str(exc_info.value).lower()


def test_build_rate_limiter_slowapi_missing_non_prod():
    """Should warn if slowapi missing in non-production."""
    with patch('app.config.settings.is_production_like', False), \
         patch('app.core.runtime._redis_ping_ok', return_value=True), \
         patch('builtins.__import__', side_effect=ImportError("No module named 'slowapi'")):

        limiter, enabled, exc_type, handler = build_rate_limiter()

        assert limiter is None
        assert enabled is False
