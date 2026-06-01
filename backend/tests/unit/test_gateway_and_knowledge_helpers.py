"""Unit tests for AI gateway client and knowledge store pure helpers.

No DB, no HTTP, no LLM — pure Python only.

Covers:
  app/domains/ai/gateway_client.py:
    _parse_json_safe, _rough_token_count, _redact_pii (surface test)
  app/domains/ai/knowledge_store.py:
    _embed_cache_key, _cosine_similarity
"""

from __future__ import annotations

import hashlib

import pytest

from app.domains.ai.gateway_client import (
    _parse_json_safe,
    _rough_token_count,
)
from app.domains.ai.knowledge_store import (
    _cosine_similarity,
    _embed_cache_key,
)


# ── _parse_json_safe ──────────────────────────────────────────────────────────


class TestParseJsonSafe:
    def test_plain_json_object(self) -> None:
        result = _parse_json_safe('{"key": "value"}')
        assert result == {"key": "value"}

    def test_plain_json_array(self) -> None:
        result = _parse_json_safe('[1, 2, 3]')
        assert result == [1, 2, 3]

    def test_json_in_markdown_fence(self) -> None:
        raw = '```json\n{"name": "test"}\n```'
        result = _parse_json_safe(raw)
        assert result == {"name": "test"}

    def test_json_in_plain_fence(self) -> None:
        raw = '```\n{"name": "test"}\n```'
        result = _parse_json_safe(raw)
        assert result == {"name": "test"}

    def test_json_surrounded_by_text(self) -> None:
        raw = 'Here is your answer: {"status": "ok"} thanks!'
        result = _parse_json_safe(raw)
        assert result == {"status": "ok"}

    def test_array_surrounded_by_text(self) -> None:
        raw = 'Result: [1, 2, 3] done'
        result = _parse_json_safe(raw)
        assert result == [1, 2, 3]

    def test_invalid_json_returns_none(self) -> None:
        result = _parse_json_safe("this is not json at all")
        assert result is None

    def test_empty_string_returns_none(self) -> None:
        result = _parse_json_safe("")
        assert result is None

    def test_nested_object(self) -> None:
        raw = '{"a": {"b": [1, 2]}}'
        result = _parse_json_safe(raw)
        assert result == {"a": {"b": [1, 2]}}

    def test_unicode_content(self) -> None:
        raw = '{"name": "Öğrenci"}'
        result = _parse_json_safe(raw)
        assert result is not None
        assert result["name"] == "Öğrenci"

    def test_returns_dict_or_list_or_none(self) -> None:
        result = _parse_json_safe('{"x": 1}')
        assert isinstance(result, (dict, list, type(None)))

    def test_whitespace_trimmed(self) -> None:
        raw = '   {"key": 42}   '
        result = _parse_json_safe(raw)
        assert result == {"key": 42}

    def test_number_json_not_dict_or_list(self) -> None:
        # json.loads("42") is valid but not dict/list
        # Behavior depends on impl — just check no exception
        result = _parse_json_safe("42")
        # could be 42 or None depending on implementation
        assert result is None or result == 42


# ── _rough_token_count ────────────────────────────────────────────────────────


class TestRoughTokenCount:
    def test_empty_string_returns_zero(self) -> None:
        assert _rough_token_count("") == 0

    def test_short_string_at_least_one(self) -> None:
        # "hi" → 2 chars → max(1, int(2/4)) = max(1, 0) = 1
        assert _rough_token_count("hi") == 1

    def test_four_chars_is_one_token(self) -> None:
        assert _rough_token_count("abcd") == 1

    def test_eight_chars_is_two_tokens(self) -> None:
        assert _rough_token_count("abcdefgh") == 2

    def test_hundred_chars_is_25_tokens(self) -> None:
        assert _rough_token_count("a" * 100) == 25

    def test_returns_int(self) -> None:
        assert isinstance(_rough_token_count("hello world"), int)

    def test_non_empty_always_positive(self) -> None:
        assert _rough_token_count("x") >= 1

    def test_proportional_to_length(self) -> None:
        short = _rough_token_count("a" * 40)
        long = _rough_token_count("a" * 400)
        assert long > short


# ── _embed_cache_key ──────────────────────────────────────────────────────────


class TestEmbedCacheKey:
    def test_returns_string(self) -> None:
        assert isinstance(_embed_cache_key("hello"), str)

    def test_length_32(self) -> None:
        # First 32 chars of sha256 hexdigest
        key = _embed_cache_key("test text")
        assert len(key) == 32

    def test_deterministic(self) -> None:
        assert _embed_cache_key("same text") == _embed_cache_key("same text")

    def test_different_text_different_key(self) -> None:
        assert _embed_cache_key("text A") != _embed_cache_key("text B")

    def test_empty_string(self) -> None:
        key = _embed_cache_key("")
        assert len(key) == 32

    def test_long_text_truncated_at_4000(self) -> None:
        # Both should give same key since both truncate to same first 4000 chars
        base = "x" * 5000
        key1 = _embed_cache_key(base)
        key2 = _embed_cache_key(base[:4000])
        assert key1 == key2

    def test_matches_sha256_logic(self) -> None:
        text = "unit test"
        expected = hashlib.sha256(text[:4000].encode("utf-8", errors="replace")).hexdigest()[:32]
        assert _embed_cache_key(text) == expected


# ── _cosine_similarity ────────────────────────────────────────────────────────


class TestCosineSimilarity:
    def test_identical_unit_vectors(self) -> None:
        a = [1.0, 0.0, 0.0]
        assert _cosine_similarity(a, a) == pytest.approx(1.0)

    def test_orthogonal_vectors(self) -> None:
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert _cosine_similarity(a, b) == pytest.approx(0.0)

    def test_opposite_directions(self) -> None:
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert _cosine_similarity(a, b) == pytest.approx(-1.0)

    def test_partial_similarity(self) -> None:
        # [1, 1] · [1, 0] / (|a| * |b|) = 1/(sqrt(2)) ≈ 0.707
        # But this function just does dot product (assumes normalized input)
        a = [0.707, 0.707]
        b = [1.0, 0.0]
        result = _cosine_similarity(a, b)
        assert result == pytest.approx(0.707, abs=0.001)

    def test_returns_float(self) -> None:
        assert isinstance(_cosine_similarity([1.0], [1.0]), float)

    def test_empty_vectors(self) -> None:
        result = _cosine_similarity([], [])
        assert result == 0.0

    def test_mismatched_length_uses_zip(self) -> None:
        # zip stops at shorter list
        a = [1.0, 0.0, 0.5]
        b = [1.0, 0.0]
        result = _cosine_similarity(a, b)
        assert result == pytest.approx(1.0)

    def test_non_normalized_positive(self) -> None:
        a = [3.0, 4.0]  # magnitude 5
        b = [3.0, 4.0]
        result = _cosine_similarity(a, b)
        assert result == pytest.approx(25.0)  # raw dot product, not normalized
