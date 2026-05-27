"""Unit tests for ai.knowledge_store pure helper functions.

All tests are self-contained: no DB, no Ollama, no HTTP.
Covers:
  - _embed_cache_key: SHA256-based cache key generation
  - _cosine_similarity: dot product of two float vectors
"""
from __future__ import annotations

import hashlib
import math

import pytest

try:
    from app.domains.ai.knowledge_store import (
        _embed_cache_key,
        _cosine_similarity,
    )
    _KS_OK = True
except ImportError:
    _KS_OK = False


# ---------------------------------------------------------------------------
# _embed_cache_key
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _KS_OK, reason="knowledge_store import failed")
class TestEmbedCacheKey:
    def test_returns_string(self):
        assert isinstance(_embed_cache_key("hello"), str)

    def test_length_is_32(self):
        # SHA256 hex is 64 chars; truncated to 32
        assert len(_embed_cache_key("hello")) == 32

    def test_deterministic(self):
        text = "same text for embedding"
        assert _embed_cache_key(text) == _embed_cache_key(text)

    def test_different_texts_different_keys(self):
        assert _embed_cache_key("text A") != _embed_cache_key("text B")

    def test_hex_chars_only(self):
        result = _embed_cache_key("test input")
        assert all(c in "0123456789abcdef" for c in result)

    def test_empty_string(self):
        result = _embed_cache_key("")
        assert isinstance(result, str)
        assert len(result) == 32

    def test_long_text_uses_first_4000_chars(self):
        # Both texts differ only after 4000 chars → same key
        base = "a" * 4000
        text1 = base + "X"
        text2 = base + "Y"
        assert _embed_cache_key(text1) == _embed_cache_key(text2)

    def test_matches_sha256_truncated(self):
        text = "canonical test"
        expected = hashlib.sha256(text[:4000].encode("utf-8", errors="replace")).hexdigest()[:32]
        assert _embed_cache_key(text) == expected

    def test_unicode_text(self):
        result = _embed_cache_key("Türkçe metin: çok güzel")
        assert len(result) == 32


# ---------------------------------------------------------------------------
# _cosine_similarity
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _KS_OK, reason="knowledge_store import failed")
class TestCosineSimilarity:
    def test_identical_unit_vectors(self):
        a = [1.0, 0.0, 0.0]
        assert _cosine_similarity(a, a) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert _cosine_similarity(a, b) == pytest.approx(0.0)

    def test_opposite_unit_vectors(self):
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert _cosine_similarity(a, b) == pytest.approx(-1.0)

    def test_identical_non_unit_vectors(self):
        a = [2.0, 3.0, 4.0]
        assert _cosine_similarity(a, a) == pytest.approx(sum(x * x for x in a))

    def test_parallel_scaled_vectors(self):
        # [1, 2] and [2, 4] — dot product = 1*2 + 2*4 = 10
        a = [1.0, 2.0]
        b = [2.0, 4.0]
        assert _cosine_similarity(a, b) == pytest.approx(10.0)

    def test_symmetric(self):
        a = [1.0, 2.0, 3.0]
        b = [4.0, 5.0, 6.0]
        assert _cosine_similarity(a, b) == pytest.approx(_cosine_similarity(b, a))

    def test_all_zeros(self):
        assert _cosine_similarity([0.0, 0.0], [0.0, 0.0]) == pytest.approx(0.0)

    def test_returns_float(self):
        result = _cosine_similarity([1.0, 0.0], [0.0, 1.0])
        assert isinstance(result, float)

    def test_single_element(self):
        assert _cosine_similarity([3.0], [4.0]) == pytest.approx(12.0)

    def test_negative_values(self):
        a = [-1.0, 0.0]
        b = [-1.0, 0.0]
        assert _cosine_similarity(a, b) == pytest.approx(1.0)

    def test_three_dimensional(self):
        a = [1.0, 0.0, 0.0]
        b = [0.0, 1.0, 0.0]
        assert _cosine_similarity(a, b) == pytest.approx(0.0)
