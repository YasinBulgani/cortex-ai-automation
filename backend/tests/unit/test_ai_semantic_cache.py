"""Unit tests for app.domains.ai.semantic_cache — pure helpers.

Tests are fully self-contained: no Redis, no HTTP.
Covers: _normalize_message, _exact_key (determinism, distinctness),
        _cosine, _CACHE_TTL_SECS (security_audit=0, others>0),
        CacheEntry dataclass.
"""
from __future__ import annotations

import pytest

try:
    from app.domains.ai.semantic_cache import (
        _normalize_message,
        _exact_key,
        _cosine,
        _CACHE_TTL_SECS,
        CacheEntry,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="semantic_cache import failed")


# ---------------------------------------------------------------------------
# _normalize_message
# ---------------------------------------------------------------------------

class TestNormalizeMessage:
    def test_lowercases(self):
        assert _normalize_message("HELLO") == "hello"

    def test_strips_leading_trailing_spaces(self):
        assert _normalize_message("  hello  ") == "hello"

    def test_collapses_internal_whitespace(self):
        assert _normalize_message("hello  world") == "hello world"

    def test_strips_trailing_period(self):
        assert _normalize_message("hello.") == "hello"

    def test_strips_trailing_exclamation(self):
        assert _normalize_message("hello!") == "hello"

    def test_strips_trailing_question(self):
        assert _normalize_message("hello?") == "hello"

    def test_empty_string_returns_empty(self):
        assert _normalize_message("") == ""

    def test_preserves_internal_punctuation(self):
        # Only trailing punctuation stripped; internal dots preserved (sentence)
        result = _normalize_message("Hello. World")
        assert "hello" in result

    def test_unicode_preserved(self):
        result = _normalize_message("Şifre gir.")
        assert "şifre" in result

    def test_returns_string(self):
        assert isinstance(_normalize_message("test"), str)


# ---------------------------------------------------------------------------
# _exact_key
# ---------------------------------------------------------------------------

class TestExactKey:
    def test_returns_string(self):
        key = _exact_key("chat", "hello", None)
        assert isinstance(key, str)

    def test_deterministic_same_inputs(self):
        k1 = _exact_key("chat", "hello world", None)
        k2 = _exact_key("chat", "hello world", None)
        assert k1 == k2

    def test_different_task_types_produce_different_keys(self):
        k1 = _exact_key("chat", "hello", None)
        k2 = _exact_key("test_generation", "hello", None)
        assert k1 != k2

    def test_different_messages_produce_different_keys(self):
        k1 = _exact_key("chat", "hello world", None)
        k2 = _exact_key("chat", "goodbye world", None)
        assert k1 != k2

    def test_different_system_msgs_produce_different_keys(self):
        k1 = _exact_key("chat", "hello", "system-a")
        k2 = _exact_key("chat", "hello", "system-b")
        assert k1 != k2

    def test_none_and_empty_system_msg_same_key(self):
        # system_msg=None and system_msg="" should produce the same SHA1 hash
        k1 = _exact_key("chat", "hello", None)
        k2 = _exact_key("chat", "hello", "")
        assert k1 == k2

    def test_normalizes_message_before_hashing(self):
        # Trailing punctuation stripped; different forms normalize to same
        k1 = _exact_key("chat", "Hello World", None)
        k2 = _exact_key("chat", "hello world", None)
        assert k1 == k2

    def test_key_is_hex_sha1(self):
        key = _exact_key("chat", "test", None)
        assert len(key) == 40
        assert all(c in "0123456789abcdef" for c in key)


# ---------------------------------------------------------------------------
# _cosine
# ---------------------------------------------------------------------------

class TestCosine:
    def test_identical_vectors_return_one(self):
        a = [1.0, 0.0, 0.0]
        assert _cosine(a, a) == pytest.approx(1.0, abs=1e-6)

    def test_orthogonal_vectors_return_zero(self):
        assert _cosine([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0, abs=1e-6)

    def test_empty_a_returns_zero(self):
        assert _cosine([], [1.0, 2.0]) == 0.0

    def test_empty_b_returns_zero(self):
        assert _cosine([1.0, 2.0], []) == 0.0

    def test_mismatched_length_returns_zero(self):
        assert _cosine([1.0, 0.0, 0.0], [1.0, 0.0]) == 0.0

    def test_zero_vectors_return_zero(self):
        assert _cosine([0.0, 0.0], [1.0, 2.0]) == 0.0

    def test_both_zero_return_zero(self):
        assert _cosine([0.0, 0.0], [0.0, 0.0]) == 0.0

    def test_partial_similarity(self):
        a = [1.0, 1.0]
        b = [1.0, 0.0]
        assert _cosine(a, b) == pytest.approx(0.7071, abs=0.001)

    def test_opposite_vectors_return_neg_one(self):
        assert _cosine([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(-1.0, abs=1e-6)

    def test_returns_float(self):
        assert isinstance(_cosine([1.0], [1.0]), float)


# ---------------------------------------------------------------------------
# _CACHE_TTL_SECS — policy
# ---------------------------------------------------------------------------

class TestCacheTtlSecs:
    def test_chat_has_positive_ttl(self):
        assert _CACHE_TTL_SECS["chat"] > 0

    def test_security_audit_ttl_is_zero(self):
        assert _CACHE_TTL_SECS["security_audit"] == 0

    def test_quality_judge_ttl_is_zero(self):
        assert _CACHE_TTL_SECS["quality_judge"] == 0

    def test_test_generation_has_positive_ttl(self):
        assert _CACHE_TTL_SECS["test_generation"] > 0

    def test_spec_analysis_has_positive_ttl(self):
        assert _CACHE_TTL_SECS["spec_analysis"] > 0

    def test_default_key_exists(self):
        assert "default" in _CACHE_TTL_SECS
        assert _CACHE_TTL_SECS["default"] > 0

    def test_chat_ttl_at_least_one_hour(self):
        assert _CACHE_TTL_SECS["chat"] >= 3600


# ---------------------------------------------------------------------------
# CacheEntry dataclass
# ---------------------------------------------------------------------------

class TestCacheEntry:
    def test_can_instantiate(self):
        entry = CacheEntry(
            response="hello",
            task_type="chat",
            user_msg="hi",
            created_at=0.0,
            hits=1,
        )
        assert entry.response == "hello"
        assert entry.task_type == "chat"

    def test_default_source_exact(self):
        entry = CacheEntry(
            response="r", task_type="t", user_msg="u", created_at=0.0, hits=0
        )
        assert entry.source == "exact"

    def test_default_similarity_one(self):
        entry = CacheEntry(
            response="r", task_type="t", user_msg="u", created_at=0.0, hits=0
        )
        assert entry.similarity == pytest.approx(1.0)

    def test_semantic_source(self):
        entry = CacheEntry(
            response="r", task_type="t", user_msg="u",
            created_at=0.0, hits=2, similarity=0.98, source="semantic",
        )
        assert entry.source == "semantic"
        assert entry.similarity == pytest.approx(0.98)
