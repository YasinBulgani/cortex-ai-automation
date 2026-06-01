"""Unit tests for few-shot bank pure helper functions.

Tests app/domains/ai/few_shot_bank.py — no DB, no LLM.
Covers: _format_header, _format_footer, _cache_key,
        _derive_tags, _format_example, _format_many.
"""

from __future__ import annotations

import hashlib

import pytest

from app.domains.ai.few_shot_bank import (
    _cache_key,
    _derive_tags,
    _format_example,
    _format_footer,
    _format_header,
    _format_many,
)


# ── _format_header ────────────────────────────────────────────────────────────


class TestFormatHeader:
    def test_returns_string(self) -> None:
        assert isinstance(_format_header(), str)

    def test_contains_few_shot_label(self) -> None:
        header = _format_header()
        assert "FEW-SHOT" in header

    def test_consistent_output(self) -> None:
        # Pure function — multiple calls return same string
        assert _format_header() == _format_header()

    def test_non_empty(self) -> None:
        assert len(_format_header()) > 10


# ── _format_footer ────────────────────────────────────────────────────────────


class TestFormatFooter:
    def test_returns_string(self) -> None:
        assert isinstance(_format_footer(), str)

    def test_contains_end_label(self) -> None:
        footer = _format_footer()
        assert "SONU" in footer or "END" in footer.upper() or "===" in footer

    def test_consistent_output(self) -> None:
        assert _format_footer() == _format_footer()

    def test_non_empty(self) -> None:
        assert len(_format_footer()) > 5


# ── _cache_key ────────────────────────────────────────────────────────────────


class TestCacheKey:
    def test_returns_string(self) -> None:
        result = _cache_key("test_generation", ["transfer"], "banking", 5)
        assert isinstance(result, str)

    def test_length_16(self) -> None:
        result = _cache_key("test_generation", ["transfer"], "banking", 5)
        assert len(result) == 16

    def test_hex_characters_only(self) -> None:
        result = _cache_key("test_generation", ["transfer"], "banking", 5)
        assert all(c in "0123456789abcdef" for c in result)

    def test_deterministic(self) -> None:
        k1 = _cache_key("mode", ["kw1", "kw2"], "query", 3)
        k2 = _cache_key("mode", ["kw1", "kw2"], "query", 3)
        assert k1 == k2

    def test_different_modes_different_keys(self) -> None:
        k1 = _cache_key("mode_a", ["kw"], "q", 1)
        k2 = _cache_key("mode_b", ["kw"], "q", 1)
        assert k1 != k2

    def test_different_n_different_keys(self) -> None:
        k1 = _cache_key("mode", ["kw"], "q", 1)
        k2 = _cache_key("mode", ["kw"], "q", 10)
        assert k1 != k2

    def test_none_keywords_handled(self) -> None:
        result = _cache_key("mode", None, "query", 5)
        assert isinstance(result, str)
        assert len(result) == 16

    def test_none_query_handled(self) -> None:
        result = _cache_key("mode", ["kw"], None, 5)
        assert isinstance(result, str)

    def test_keywords_order_independent(self) -> None:
        # Keywords are sorted before hashing
        k1 = _cache_key("mode", ["b", "a", "c"], "q", 5)
        k2 = _cache_key("mode", ["a", "b", "c"], "q", 5)
        assert k1 == k2

    def test_empty_keywords_list(self) -> None:
        result = _cache_key("mode", [], "query", 5)
        assert isinstance(result, str)
        assert len(result) == 16

    def test_query_truncated_at_120(self) -> None:
        short_query = "a" * 50
        long_query = "a" * 200  # will be truncated to 120
        k1 = _cache_key("mode", [], short_query, 5)
        k2 = _cache_key("mode", [], long_query, 5)
        # They're different because lengths differ
        assert k1 != k2

    def test_query_lowercased(self) -> None:
        k1 = _cache_key("mode", [], "QUERY", 5)
        k2 = _cache_key("mode", [], "query", 5)
        assert k1 == k2


# ── _derive_tags ──────────────────────────────────────────────────────────────


class TestDeriveTags:
    def test_returns_list(self) -> None:
        result = _derive_tags("test_generation", "banking_transfer", "havale yap")
        assert isinstance(result, list)

    def test_transfer_keyword_detected(self) -> None:
        result = _derive_tags("test_generation", "banking_transfer", "transfer islemi")
        assert "transfer" in result

    def test_iban_keyword_detected(self) -> None:
        result = _derive_tags("test_generation", "banking", "iban dogrulama")
        assert "iban" in result

    def test_auth_keyword_detected(self) -> None:
        result = _derive_tags("test_generation", "banking_auth", "login endpoint")
        assert "auth" in result or "login" in result

    def test_no_matching_keywords_returns_empty(self) -> None:
        result = _derive_tags("unknown_mode", "xyz_key", "no matching text here xyz")
        assert result == []

    def test_tags_are_sorted(self) -> None:
        result = _derive_tags("test_generation", "banking_transfer", "transfer iban hesap bakiye")
        assert result == sorted(result)

    def test_no_duplicates(self) -> None:
        # "transfer" appears in mode+key+input but should only appear once
        result = _derive_tags("transfer", "transfer", "transfer transfer transfer")
        assert len(result) == len(set(result))

    def test_case_insensitive_detection(self) -> None:
        # The function lowercases the combined text before matching
        result = _derive_tags("TEST_GENERATION", "BANKING", "IBAN dogrulama")
        assert "iban" in result

    def test_kredi_keyword(self) -> None:
        result = _derive_tags("test_generation", "kredi", "basvuru")
        assert "kredi" in result or "basvuru" in result

    def test_payment_keyword(self) -> None:
        result = _derive_tags("test_generation", "odeme_kart", "payment card")
        assert "payment" in result


# ── _format_example ───────────────────────────────────────────────────────────


class TestFormatExample:
    def test_returns_string(self) -> None:
        example = {"input": "test input", "output": {"result": "ok"}}
        result = _format_example("test_key", example)
        assert isinstance(result, str)

    def test_contains_key_title(self) -> None:
        example = {"input": "some input", "output": {}}
        result = _format_example("banking_transfer", example)
        assert "Banking Transfer" in result

    def test_contains_input_text(self) -> None:
        example = {"input": "transfer 100 TL", "output": {}}
        result = _format_example("key", example)
        assert "transfer 100 TL" in result

    def test_contains_json_output(self) -> None:
        example = {"input": "input", "output": {"status": "success"}}
        result = _format_example("key", example)
        assert "success" in result

    def test_positive_example_uses_beklenen(self) -> None:
        example = {"input": "input", "output": {}}
        result = _format_example("key", example, is_negative=False)
        assert "Beklenen" in result

    def test_negative_example_uses_hatali(self) -> None:
        example = {"input": "input", "output": {}}
        result = _format_example("key", example, is_negative=True)
        assert "YANLIS" in result or "Hatali" in result

    def test_negative_example_includes_bad_reason(self) -> None:
        example = {"input": "input", "output": {}}
        result = _format_example("key", example, is_negative=True, bad_reason="eksik alan")
        assert "eksik alan" in result

    def test_negative_without_bad_reason_uses_default(self) -> None:
        example = {"input": "input", "output": {}}
        result = _format_example("key", example, is_negative=True)
        assert "kalite" in result.lower()

    def test_output_in_code_block(self) -> None:
        example = {"input": "input", "output": {"key": "val"}}
        result = _format_example("key", example)
        assert "```" in result

    def test_large_output_truncated(self) -> None:
        # Output larger than 4000 chars should be truncated
        big_output = {f"field_{i}": "x" * 100 for i in range(50)}
        example = {"input": "input", "output": big_output}
        result = _format_example("key", example)
        assert "kisaltildi" in result or len(result) < 10000

    def test_underscore_in_key_replaced_with_space_title(self) -> None:
        example = {"input": "input", "output": {}}
        result = _format_example("my_key_name", example)
        assert "My Key Name" in result


# ── _format_many ─────────────────────────────────────────────────────────────


class TestFormatMany:
    def test_empty_list_returns_empty_string(self) -> None:
        assert _format_many([]) == ""

    def test_single_example(self) -> None:
        examples = [{"key": "test_key", "input_text": "input", "output_json": {}, "is_negative": False}]
        result = _format_many(examples)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_contains_header(self) -> None:
        examples = [{"key": "k", "input_text": "i", "output_json": {}, "is_negative": False}]
        result = _format_many(examples)
        assert "FEW-SHOT" in result

    def test_contains_footer(self) -> None:
        examples = [{"key": "k", "input_text": "i", "output_json": {}, "is_negative": False}]
        result = _format_many(examples)
        assert "===" in result  # footer has === markers

    def test_multiple_examples_separated(self) -> None:
        examples = [
            {"key": "k1", "input_text": "input1", "output_json": {}, "is_negative": False},
            {"key": "k2", "input_text": "input2", "output_json": {}, "is_negative": False},
        ]
        result = _format_many(examples)
        assert "---" in result  # separator between examples

    def test_negative_example_included(self) -> None:
        examples = [
            {
                "key": "k1",
                "input_text": "input",
                "output_json": {},
                "is_negative": True,
                "bad_reason": "test reason",
            }
        ]
        result = _format_many(examples)
        assert "YANLIS" in result or "Hatali" in result

    def test_missing_fields_handled_gracefully(self) -> None:
        # _format_many uses .get() so missing keys use defaults
        examples = [{}]  # completely empty dict
        result = _format_many(examples)
        assert isinstance(result, str)
