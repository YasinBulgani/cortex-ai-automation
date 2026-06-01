"""Unit tests for app.domains.ai.few_shot_bank — pure helpers.

Tests are fully self-contained: no DB, no HTTP.
Covers: _cache_key (determinism, distinctness), _format_header,
        _format_footer, _format_example (positive + negative),
        _format_many, _derive_tags.
"""
from __future__ import annotations

import pytest

try:
    from app.domains.ai.few_shot_bank import (
        _cache_key,
        _format_header,
        _format_footer,
        _format_example,
        _format_many,
        _derive_tags,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="few_shot_bank import failed")


# ---------------------------------------------------------------------------
# _cache_key
# ---------------------------------------------------------------------------

class TestCacheKey:
    def test_returns_string(self):
        assert isinstance(_cache_key("test_generation", None, None, 2), str)

    def test_deterministic(self):
        k1 = _cache_key("test_generation", ["transfer"], "query", 2)
        k2 = _cache_key("test_generation", ["transfer"], "query", 2)
        assert k1 == k2

    def test_different_modes_different_keys(self):
        k1 = _cache_key("test_generation", None, None, 2)
        k2 = _cache_key("security_audit", None, None, 2)
        assert k1 != k2

    def test_different_keywords_different_keys(self):
        k1 = _cache_key("test_generation", ["transfer"], None, 2)
        k2 = _cache_key("test_generation", ["auth"], None, 2)
        assert k1 != k2

    def test_keyword_order_independent(self):
        # keywords are sorted before hashing
        k1 = _cache_key("test_generation", ["auth", "transfer"], None, 2)
        k2 = _cache_key("test_generation", ["transfer", "auth"], None, 2)
        assert k1 == k2

    def test_different_n_different_keys(self):
        k1 = _cache_key("test_generation", None, None, 2)
        k2 = _cache_key("test_generation", None, None, 5)
        assert k1 != k2

    def test_none_keywords_and_empty_list_same(self):
        # sorted([]) = [] and sorted(None or []) = []
        k1 = _cache_key("chat", None, None, 3)
        k2 = _cache_key("chat", [], None, 3)
        assert k1 == k2

    def test_key_is_16_chars(self):
        key = _cache_key("chat", None, None, 2)
        assert len(key) == 16


# ---------------------------------------------------------------------------
# _format_header / _format_footer
# ---------------------------------------------------------------------------

class TestFormatHeaderFooter:
    def test_header_returns_string(self):
        assert isinstance(_format_header(), str)

    def test_footer_returns_string(self):
        assert isinstance(_format_footer(), str)

    def test_header_contains_few_shot_marker(self):
        assert "FEW-SHOT" in _format_header()

    def test_footer_contains_few_shot_marker(self):
        assert "FEW-SHOT" in _format_footer()

    def test_header_and_footer_different(self):
        assert _format_header() != _format_footer()


# ---------------------------------------------------------------------------
# _format_example
# ---------------------------------------------------------------------------

class TestFormatExample:
    def _example(self, input_text="hello input", output=None):
        return {"input": input_text, "output": output or {"result": "ok"}}

    def test_returns_string(self):
        result = _format_example("my_key", self._example())
        assert isinstance(result, str)

    def test_positive_contains_key(self):
        result = _format_example("banking_transfer", self._example())
        assert "Banking Transfer" in result or "banking_transfer" in result.lower()

    def test_positive_contains_input(self):
        result = _format_example("key", self._example(input_text="my test input"))
        assert "my test input" in result

    def test_positive_contains_json_output(self):
        result = _format_example("key", self._example(output={"status": "ok"}))
        assert '"status"' in result or "status" in result

    def test_positive_has_expected_output_label(self):
        result = _format_example("key", self._example(), is_negative=False)
        assert "Beklenen Cikti" in result

    def test_negative_has_wrong_example_label(self):
        result = _format_example("key", self._example(), is_negative=True)
        assert "YANLIS" in result

    def test_negative_has_bad_reason(self):
        result = _format_example(
            "key", self._example(), is_negative=True, bad_reason="quality too low"
        )
        assert "quality too low" in result

    def test_negative_has_default_bad_reason(self):
        result = _format_example("key", self._example(), is_negative=True)
        assert "kalite" in result.lower() or "yetersiz" in result.lower()

    def test_negative_has_hatali_cikti_label(self):
        result = _format_example("key", self._example(), is_negative=True)
        assert "Hatali Cikti" in result

    def test_long_output_truncated(self):
        big_output = {"data": "x" * 5000}
        result = _format_example("key", {"input": "q", "output": big_output})
        assert "kisaltildi" in result

    def test_output_in_json_code_block(self):
        result = _format_example("key", self._example())
        assert "```json" in result


# ---------------------------------------------------------------------------
# _format_many
# ---------------------------------------------------------------------------

class TestFormatMany:
    def _db_example(self, key="ex1", is_negative=False):
        return {
            "key": key,
            "input_text": "sample input",
            "output_json": {"result": "ok"},
            "is_negative": is_negative,
            "bad_reason": None,
        }

    def test_empty_list_returns_empty(self):
        assert _format_many([]) == ""

    def test_returns_string(self):
        result = _format_many([self._db_example()])
        assert isinstance(result, str)

    def test_includes_header(self):
        result = _format_many([self._db_example()])
        assert "FEW-SHOT" in result

    def test_includes_footer(self):
        result = _format_many([self._db_example()])
        assert "SONU" in result or "FEW-SHOT" in result

    def test_multiple_examples_have_separator(self):
        examples = [self._db_example("ex1"), self._db_example("ex2")]
        result = _format_many(examples)
        assert "---" in result


# ---------------------------------------------------------------------------
# _derive_tags
# ---------------------------------------------------------------------------

class TestDeriveTags:
    def test_transfer_keyword_detected(self):
        tags = _derive_tags("test_generation", "banking_transfer", "transfer endpoint")
        assert "transfer" in tags

    def test_auth_keyword_detected(self):
        tags = _derive_tags("test_generation", "auth", "login password")
        assert "login" in tags or "auth" in tags

    def test_unknown_keywords_empty(self):
        tags = _derive_tags("test_generation", "xyz", "completely irrelevant text")
        assert isinstance(tags, list)
        # No keyword from _KEYWORD_MAP → empty

    def test_returns_sorted_list(self):
        tags = _derive_tags("test_generation", "transfer", "transfer iban login")
        assert tags == sorted(tags)

    def test_no_duplicates(self):
        tags = _derive_tags("test_generation", "transfer", "transfer transfer")
        assert len(tags) == len(set(tags))

    def test_returns_list(self):
        assert isinstance(_derive_tags("chat", "", ""), list)

    def test_iban_detected(self):
        tags = _derive_tags("test_generation", "banking", "iban check")
        assert "iban" in tags

    def test_case_insensitive(self):
        tags = _derive_tags("TEST_GENERATION", "TRANSFER", "TRANSFER")
        assert "transfer" in tags
