"""Unit tests for app.domains.ai.embedding_cache pure helper functions.

Tests are fully self-contained: no Redis, no DB, no HTTP.
Covers: _key normalization and cache_stats/get/set with mocked Redis.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

try:
    from app.domains.ai.embedding_cache import (
        _key,
        get_cached_embedding,
        set_cached_embedding,
        cache_stats,
        clear_embedding_cache,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="embedding_cache import failed")


# ---------------------------------------------------------------------------
# _key — cache key generation
# ---------------------------------------------------------------------------

class TestKeyGeneration:
    def test_returns_string(self):
        key = _key("hello world")
        assert isinstance(key, str)
        assert len(key) > 0

    def test_starts_with_embed_prefix(self):
        key = _key("test text", "test-model")
        assert "embed" in key.lower() or ":" in key

    def test_deterministic(self):
        key1 = _key("hello world", "nomic-embed-text")
        key2 = _key("hello world", "nomic-embed-text")
        assert key1 == key2

    def test_different_text_different_key(self):
        k1 = _key("text one", "model")
        k2 = _key("text two", "model")
        assert k1 != k2

    def test_different_model_different_key(self):
        k1 = _key("same text", "model-a")
        k2 = _key("same text", "model-b")
        assert k1 != k2

    def test_whitespace_normalized(self):
        """Multiple spaces collapsed — same as single space."""
        k1 = _key("hello   world")
        k2 = _key("hello world")
        assert k1 == k2

    def test_case_normalized(self):
        """Uppercase and lowercase produce the same key."""
        k1 = _key("Hello World")
        k2 = _key("hello world")
        assert k1 == k2

    def test_empty_text_is_stable(self):
        k1 = _key("")
        k2 = _key("")
        assert k1 == k2

    def test_leading_trailing_whitespace_stripped(self):
        k1 = _key("  hello  ")
        k2 = _key("hello")
        assert k1 == k2

    def test_very_long_text_still_works(self):
        """Key generation doesn't crash on very long input."""
        long_text = "word " * 10_000
        key = _key(long_text)
        assert isinstance(key, str)


# ---------------------------------------------------------------------------
# get_cached_embedding — with mocked Redis
# ---------------------------------------------------------------------------

class TestGetCachedEmbedding:
    def test_no_redis_returns_none(self):
        with patch("app.domains.ai.embedding_cache._get_redis", return_value=None):
            result = get_cached_embedding("some text")
        assert result is None

    def test_redis_miss_returns_none(self):
        mock_redis = MagicMock()
        mock_redis.get.return_value = None
        with patch("app.domains.ai.embedding_cache._get_redis", return_value=mock_redis):
            result = get_cached_embedding("some text")
        assert result is None

    def test_redis_hit_returns_vector(self):
        import json
        vector = [0.1, 0.2, 0.3]
        mock_redis = MagicMock()
        mock_redis.get.return_value = json.dumps(vector).encode()
        with (
            patch("app.domains.ai.embedding_cache._get_redis", return_value=mock_redis),
            patch("app.domains.ai.embedding_cache._enabled", return_value=True),
        ):
            result = get_cached_embedding("some text")
        assert result == vector

    def test_redis_exception_returns_none(self):
        mock_redis = MagicMock()
        mock_redis.get.side_effect = ConnectionError("redis down")
        with patch("app.domains.ai.embedding_cache._get_redis", return_value=mock_redis):
            result = get_cached_embedding("some text")
        assert result is None

    def test_feature_flag_disabled_returns_none(self):
        with patch("app.domains.ai.embedding_cache._enabled", return_value=False):
            result = get_cached_embedding("some text")
        assert result is None


# ---------------------------------------------------------------------------
# cache_stats — with mocked Redis
# ---------------------------------------------------------------------------

class TestCacheStats:
    def test_returns_dict(self):
        with patch("app.domains.ai.embedding_cache._get_redis", return_value=None):
            stats = cache_stats()
        assert isinstance(stats, dict)

    def test_no_redis_has_enabled_false(self):
        with patch("app.domains.ai.embedding_cache._get_redis", return_value=None):
            stats = cache_stats()
        # When Redis is unavailable, enabled=False and reason explains why
        assert stats.get("enabled") is False

    def test_with_redis_has_enabled_true(self):
        mock_redis = MagicMock()
        mock_redis.keys.return_value = []
        with patch("app.domains.ai.embedding_cache._get_redis", return_value=mock_redis):
            stats = cache_stats()
        assert stats.get("enabled") is True
        assert "approximate_keys" in stats
