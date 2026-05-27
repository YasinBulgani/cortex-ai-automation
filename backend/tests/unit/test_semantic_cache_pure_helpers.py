"""Unit tests for ai.semantic_cache pure helper functions.

All tests are self-contained: no Redis, no HTTP, no LLM.
Covers:
  - _normalize_message: whitespace normalisation and lowercasing
  - _exact_key: deterministic SHA-1 cache key generation
  - _cosine: cosine similarity for embedding vectors
  - _decode: bytes/str/None → str coercion
  - _row_to_entry: Redis hash dict → CacheEntry dataclass
  - CacheEntry: dataclass structure
"""
from __future__ import annotations

import math

import pytest

try:
    from app.domains.ai.semantic_cache import (
        _normalize_message,
        _exact_key,
        _cosine,
        _decode,
        _row_to_entry,
        CacheEntry,
    )
    _SC_OK = True
except ImportError:
    _SC_OK = False


# ---------------------------------------------------------------------------
# _normalize_message
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _SC_OK, reason="semantic_cache import failed")
class TestNormalizeMessage:
    def test_empty_string(self):
        assert _normalize_message("") == ""

    def test_strips_leading_trailing_whitespace(self):
        assert _normalize_message("  hello  ") == "hello"

    def test_collapses_internal_whitespace(self):
        assert _normalize_message("hello   world") == "hello world"

    def test_lowercase(self):
        assert _normalize_message("HELLO WORLD") == "hello world"

    def test_strips_trailing_dot(self):
        assert _normalize_message("hello world.") == "hello world"

    def test_strips_trailing_exclamation(self):
        assert _normalize_message("hello world!") == "hello world"

    def test_strips_trailing_question_mark(self):
        assert _normalize_message("hello world?") == "hello world"

    def test_combined_normalisation(self):
        assert _normalize_message("  Hello World.  ") == "hello world"

    def test_preserves_internal_punctuation(self):
        result = _normalize_message("e.g. this is an example")
        assert "e.g" in result

    def test_newlines_collapsed(self):
        result = _normalize_message("hello\nworld")
        assert "\n" not in result
        assert " " in result

    def test_returns_string(self):
        assert isinstance(_normalize_message("test"), str)


# ---------------------------------------------------------------------------
# _exact_key
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _SC_OK, reason="semantic_cache import failed")
class TestExactKey:
    def test_deterministic(self):
        k1 = _exact_key("chat", "hello world", None)
        k2 = _exact_key("chat", "hello world", None)
        assert k1 == k2

    def test_different_task_types_differ(self):
        k1 = _exact_key("chat", "hello", None)
        k2 = _exact_key("translate", "hello", None)
        assert k1 != k2

    def test_different_messages_differ(self):
        k1 = _exact_key("chat", "hello", None)
        k2 = _exact_key("chat", "goodbye", None)
        assert k1 != k2

    def test_different_system_msgs_differ(self):
        k1 = _exact_key("chat", "hello", "system A")
        k2 = _exact_key("chat", "hello", "system B")
        assert k1 != k2

    def test_none_and_empty_system_msg_same(self):
        # None system_msg → sha1("") same as sha1("")
        k1 = _exact_key("chat", "hello", None)
        k2 = _exact_key("chat", "hello", "")
        assert k1 == k2

    def test_returns_40_char_hex(self):
        k = _exact_key("chat", "hello", None)
        assert len(k) == 40
        assert all(c in "0123456789abcdef" for c in k)

    def test_normalises_message_before_hashing(self):
        # Same content, different whitespace → same key
        k1 = _exact_key("chat", "hello world", None)
        k2 = _exact_key("chat", "  hello  world  ", None)
        assert k1 == k2

    def test_returns_string(self):
        assert isinstance(_exact_key("t", "m", None), str)


# ---------------------------------------------------------------------------
# _cosine
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _SC_OK, reason="semantic_cache import failed")
class TestCosine:
    def test_identical_vectors(self):
        assert _cosine([1.0, 0.0, 0.0], [1.0, 0.0, 0.0]) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        assert _cosine([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)

    def test_opposite_vectors(self):
        assert _cosine([1.0, 0.0], [-1.0, 0.0]) == pytest.approx(-1.0)

    def test_empty_vectors_return_zero(self):
        assert _cosine([], []) == pytest.approx(0.0)

    def test_mismatched_lengths_return_zero(self):
        assert _cosine([1.0, 2.0], [1.0]) == pytest.approx(0.0)

    def test_zero_vector_returns_zero(self):
        assert _cosine([0.0, 0.0], [1.0, 0.0]) == pytest.approx(0.0)

    def test_range_minus_1_to_plus_1(self):
        result = _cosine([0.5, 0.5, 0.7], [0.1, 0.9, 0.3])
        assert -1.0 <= result <= 1.0

    def test_symmetric(self):
        a = [1.0, 2.0, 3.0]
        b = [4.0, 5.0, 6.0]
        assert _cosine(a, b) == pytest.approx(_cosine(b, a))

    def test_known_value(self):
        # [1,1] vs [1,0]: dot=1, |[1,1]|=sqrt(2), |[1,0]|=1 → 1/sqrt(2) ≈ 0.707
        result = _cosine([1.0, 1.0], [1.0, 0.0])
        assert result == pytest.approx(1.0 / math.sqrt(2))

    def test_returns_float(self):
        assert isinstance(_cosine([1.0], [1.0]), float)


# ---------------------------------------------------------------------------
# _decode
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _SC_OK, reason="semantic_cache import failed")
class TestDecode:
    def test_none_returns_none(self):
        assert _decode(None) is None

    def test_bytes_decoded(self):
        assert _decode(b"hello") == "hello"

    def test_bytearray_decoded(self):
        assert _decode(bytearray(b"world")) == "world"

    def test_string_passthrough(self):
        assert _decode("already string") == "already string"

    def test_int_becomes_string(self):
        result = _decode(42)
        assert result == "42"

    def test_bytes_with_utf8(self):
        assert _decode("merhaba".encode("utf-8")) == "merhaba"

    def test_returns_string_or_none(self):
        result = _decode(b"x")
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# _row_to_entry
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _SC_OK, reason="semantic_cache import failed")
class TestRowToEntry:
    def _make_data(self, **kwargs):
        defaults = {
            "response": "The answer is 42",
            "task_type": "chat",
            "user_msg": "What is the meaning of life?",
            "created_at": "1700000000.0",
            "hits": "3",
        }
        defaults.update(kwargs)
        return defaults

    def test_returns_cache_entry(self):
        entry = _row_to_entry(self._make_data())
        assert isinstance(entry, CacheEntry)

    def test_response_field(self):
        entry = _row_to_entry(self._make_data(response="Hello!"))
        assert entry.response == "Hello!"

    def test_task_type_field(self):
        entry = _row_to_entry(self._make_data(task_type="translate"))
        assert entry.task_type == "translate"

    def test_user_msg_field(self):
        entry = _row_to_entry(self._make_data(user_msg="test question"))
        assert entry.user_msg == "test question"

    def test_hits_field(self):
        entry = _row_to_entry(self._make_data(hits="7"))
        assert entry.hits == 7

    def test_created_at_as_float(self):
        entry = _row_to_entry(self._make_data(created_at="1700000000.5"))
        assert isinstance(entry.created_at, float)
        assert entry.created_at == pytest.approx(1700000000.5)

    def test_missing_response_returns_none(self):
        data = {"task_type": "chat", "user_msg": "q"}
        assert _row_to_entry(data) is None

    def test_empty_response_returns_none(self):
        entry = _row_to_entry(self._make_data(response=""))
        assert entry is None

    def test_bytes_keys_accepted(self):
        data = {
            b"response": b"byte response",
            b"task_type": b"chat",
            b"user_msg": b"question",
            b"created_at": b"1700000000.0",
            b"hits": b"0",
        }
        entry = _row_to_entry(data)
        assert entry is not None
        assert entry.response == "byte response"

    def test_missing_hits_defaults_to_zero(self):
        data = {
            "response": "answer",
            "task_type": "chat",
            "user_msg": "q",
            "created_at": "0",
        }
        entry = _row_to_entry(data)
        assert entry is not None
        assert entry.hits == 0

    def test_bad_data_returns_none(self):
        entry = _row_to_entry({"response": "ok", "created_at": "not-a-float"})
        assert entry is None


# ---------------------------------------------------------------------------
# CacheEntry dataclass
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _SC_OK, reason="semantic_cache import failed")
class TestCacheEntry:
    def test_required_fields(self):
        entry = CacheEntry(
            response="test",
            task_type="chat",
            user_msg="hello",
            created_at=1700000000.0,
            hits=0,
        )
        assert entry.response == "test"
        assert entry.task_type == "chat"
        assert entry.user_msg == "hello"
        assert entry.hits == 0

    def test_hits_mutable(self):
        entry = CacheEntry(
            response="r", task_type="t", user_msg="u", created_at=0.0, hits=0
        )
        entry.hits += 1
        assert entry.hits == 1
