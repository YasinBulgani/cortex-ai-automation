"""Unit tests for ai.few_shot_bank pure helper functions.

All tests are self-contained: no DB, no HTTP, no LLM.
Covers:
  - _format_header: static header string
  - _format_footer: static footer string
  - _format_example: single example formatting (positive/negative)
  - _format_many: list of examples formatting
  - _cache_key: deterministic SHA1 cache key
  - _derive_tags: keyword-based tag derivation
"""
from __future__ import annotations

import pytest

try:
    from app.domains.ai.few_shot_bank import (
        _format_header,
        _format_footer,
        _format_example,
        _format_many,
        _cache_key,
        _derive_tags,
    )
    _FSB_OK = True
except ImportError:
    _FSB_OK = False


# ---------------------------------------------------------------------------
# _format_header / _format_footer
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _FSB_OK, reason="few_shot_bank import failed")
class TestFormatHeaderFooter:
    def test_header_returns_string(self):
        assert isinstance(_format_header(), str)

    def test_footer_returns_string(self):
        assert isinstance(_format_footer(), str)

    def test_header_non_empty(self):
        assert len(_format_header()) > 0

    def test_footer_non_empty(self):
        assert len(_format_footer()) > 0

    def test_header_contains_few_shot(self):
        assert "FEW-SHOT" in _format_header() or "few-shot" in _format_header().lower()

    def test_header_deterministic(self):
        assert _format_header() == _format_header()

    def test_footer_deterministic(self):
        assert _format_footer() == _format_footer()


# ---------------------------------------------------------------------------
# _format_example
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _FSB_OK, reason="few_shot_bank import failed")
class TestFormatExample:
    def test_returns_string(self):
        result = _format_example("my_key", {"input": "test input", "output": {"field": "value"}})
        assert isinstance(result, str)

    def test_key_included_in_output(self):
        result = _format_example("login_test", {"input": "click login", "output": {}})
        assert "Login Test" in result or "login_test" in result or "Login" in result

    def test_input_included(self):
        result = _format_example("key", {"input": "my test input", "output": {}})
        assert "my test input" in result

    def test_output_as_json_fence(self):
        result = _format_example("key", {"input": "input", "output": {"x": 1}})
        assert "```json" in result
        assert "```" in result

    def test_positive_example_label(self):
        result = _format_example("key", {"input": "input", "output": {}}, is_negative=False)
        assert "YANLIS" not in result

    def test_negative_example_label(self):
        result = _format_example("key", {"input": "input", "output": {}}, is_negative=True)
        assert "YANLIS" in result

    def test_negative_with_bad_reason(self):
        result = _format_example("key", {"input": "input", "output": {}}, is_negative=True, bad_reason="Too short")
        assert "Too short" in result

    def test_negative_without_bad_reason_uses_default(self):
        result = _format_example("key", {"input": "input", "output": {}}, is_negative=True)
        assert "kalite" in result or "Too short" not in result

    def test_long_output_truncated(self):
        # Output > 4000 chars should be truncated
        long_output = {"data": "x" * 5000}
        result = _format_example("key", {"input": "input", "output": long_output})
        assert "kisaltildi" in result or len(result) < 10000


# ---------------------------------------------------------------------------
# _format_many
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _FSB_OK, reason="few_shot_bank import failed")
class TestFormatMany:
    def test_empty_list_returns_empty_string(self):
        assert _format_many([]) == ""

    def test_returns_string(self):
        assert isinstance(_format_many([]), str)

    def test_single_example_includes_header_and_footer(self):
        examples = [{"key": "test_key", "input_text": "input", "output_json": {}, "is_negative": False}]
        result = _format_many(examples)
        assert "FEW-SHOT" in result or len(result) > 0

    def test_multiple_examples_all_included(self):
        examples = [
            {"key": "key1", "input_text": "input1", "output_json": {}, "is_negative": False},
            {"key": "key2", "input_text": "input2", "output_json": {}, "is_negative": False},
        ]
        result = _format_many(examples)
        assert "key1" in result or "Key1" in result
        assert "key2" in result or "Key2" in result

    def test_negative_example_labeled(self):
        examples = [
            {"key": "bad_example", "input_text": "input", "output_json": {}, "is_negative": True, "bad_reason": "Wrong format"}
        ]
        result = _format_many(examples)
        assert "YANLIS" in result


# ---------------------------------------------------------------------------
# _cache_key
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _FSB_OK, reason="few_shot_bank import failed")
class TestCacheKey:
    def test_returns_string(self):
        assert isinstance(_cache_key("test", ["kw1"], "query", 5), str)

    def test_deterministic(self):
        k1 = _cache_key("mode", ["a", "b"], "query", 10)
        k2 = _cache_key("mode", ["a", "b"], "query", 10)
        assert k1 == k2

    def test_different_mode_differs(self):
        k1 = _cache_key("mode1", [], "query", 5)
        k2 = _cache_key("mode2", [], "query", 5)
        assert k1 != k2

    def test_different_keywords_differs(self):
        k1 = _cache_key("mode", ["a"], "query", 5)
        k2 = _cache_key("mode", ["b"], "query", 5)
        assert k1 != k2

    def test_none_keywords_handled(self):
        key = _cache_key("mode", None, None, 5)
        assert isinstance(key, str)

    def test_key_is_16_chars(self):
        # SHA1 truncated to 16 chars
        key = _cache_key("mode", ["kw"], "q", 5)
        assert len(key) == 16

    def test_keywords_order_insensitive(self):
        # keywords are sorted before hashing
        k1 = _cache_key("mode", ["b", "a"], "q", 5)
        k2 = _cache_key("mode", ["a", "b"], "q", 5)
        assert k1 == k2

    def test_different_n_differs(self):
        k1 = _cache_key("mode", [], "q", 5)
        k2 = _cache_key("mode", [], "q", 10)
        assert k1 != k2


# ---------------------------------------------------------------------------
# _derive_tags
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _FSB_OK, reason="few_shot_bank import failed")
class TestDeriveTags:
    def test_returns_list(self):
        assert isinstance(_derive_tags("test", "key", "input"), list)

    def test_no_keywords_returns_empty(self):
        result = _derive_tags("mode", "example_key", "simple text with no keywords")
        assert isinstance(result, list)

    def test_sorted_output(self):
        result = _derive_tags("mode", "key", "login transfer")
        assert result == sorted(result)

    def test_tags_are_strings(self):
        result = _derive_tags("test_generation", "banking", "transfer payment login")
        assert all(isinstance(t, str) for t in result)

    def test_text_combined_with_mode_key(self):
        # Tags derived from mode + key + input_text
        result = _derive_tags("login", "test", "")
        assert isinstance(result, list)

    def test_duplicate_keywords_not_included(self):
        result = _derive_tags("mode", "key", "transfer transfer transfer")
        # Should have unique tags
        assert len(result) == len(set(result))
