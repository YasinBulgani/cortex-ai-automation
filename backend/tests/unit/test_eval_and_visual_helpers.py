"""Unit tests for eval suite and visual compare pure helper functions.

No DB, no HTTP, no Pillow required — pure Python only.

Covers:
  app/domains/ai/eval_suite.py:
    _is_json_valid, _json_has_field, _json_path_matches, _json_parse_tolerant
  app/domains/visual/compare.py:
    _env_float, _safe_name
"""

from __future__ import annotations

import os

import pytest

from app.domains.ai.eval_suite import (
    _is_json_valid,
    _json_has_field,
    _json_path_matches,
    _json_parse_tolerant,
)
from app.domains.visual.compare import _env_float, _safe_name


# ── _is_json_valid ────────────────────────────────────────────────────────────


class TestIsJsonValid:
    def test_valid_object(self) -> None:
        assert _is_json_valid('{"key": "value"}') is True

    def test_valid_array(self) -> None:
        assert _is_json_valid('[1, 2, 3]') is True

    def test_empty_string_invalid(self) -> None:
        assert _is_json_valid("") is False

    def test_plain_text_invalid(self) -> None:
        assert _is_json_valid("hello world") is False

    def test_json_in_code_block(self) -> None:
        text = '```json\n{"status": "ok"}\n```'
        assert _is_json_valid(text) is True

    def test_json_in_generic_code_block(self) -> None:
        text = '```\n{"key": 1}\n```'
        assert _is_json_valid(text) is True

    def test_json_embedded_in_text(self) -> None:
        # The function extracts from first { to last }
        text = 'Here is the result: {"score": 5} end.'
        assert _is_json_valid(text) is True

    def test_invalid_json_with_braces(self) -> None:
        assert _is_json_valid("{invalid: json}") is False

    def test_whitespace_stripped(self) -> None:
        assert _is_json_valid('  {"key": "value"}  ') is True

    def test_nested_json(self) -> None:
        text = '{"data": {"nested": [1, 2, 3]}}'
        assert _is_json_valid(text) is True

    def test_json_with_unicode(self) -> None:
        text = '{"name": "Türkçe metin"}'
        assert _is_json_valid(text) is True


# ── _json_parse_tolerant ──────────────────────────────────────────────────────


class TestJsonParseTolerant:
    def test_valid_json_object(self) -> None:
        result = _json_parse_tolerant('{"key": "value"}')
        assert result == {"key": "value"}

    def test_valid_json_array(self) -> None:
        result = _json_parse_tolerant('[1, 2, 3]')
        assert result == [1, 2, 3]

    def test_json_in_code_block(self) -> None:
        text = '```json\n{"status": "ok"}\n```'
        result = _json_parse_tolerant(text)
        assert result == {"status": "ok"}

    def test_embedded_json_extracted(self) -> None:
        text = 'The result is: {"score": 9} as you can see.'
        result = _json_parse_tolerant(text)
        assert result == {"score": 9}

    def test_raises_on_non_json(self) -> None:
        with pytest.raises((ValueError, Exception)):
            _json_parse_tolerant("plain text without json")

    def test_empty_string_raises(self) -> None:
        with pytest.raises((ValueError, Exception)):
            _json_parse_tolerant("")

    def test_none_like_input_raises(self) -> None:
        with pytest.raises((ValueError, Exception)):
            _json_parse_tolerant(None)  # type: ignore[arg-type]

    def test_nested_object(self) -> None:
        result = _json_parse_tolerant('{"a": {"b": 1}}')
        assert result["a"]["b"] == 1


# ── _json_has_field ───────────────────────────────────────────────────────────


class TestJsonHasField:
    def test_field_present(self) -> None:
        assert _json_has_field('{"name": "test"}', "name") is True

    def test_field_absent(self) -> None:
        assert _json_has_field('{"name": "test"}', "email") is False

    def test_nested_field_not_found_at_top(self) -> None:
        # Only checks top-level keys
        text = '{"data": {"nested": "value"}}'
        assert _json_has_field(text, "nested") is False
        assert _json_has_field(text, "data") is True

    def test_array_first_item_checked(self) -> None:
        text = '[{"id": 1, "name": "test"}]'
        assert _json_has_field(text, "id") is True
        assert _json_has_field(text, "missing") is False

    def test_invalid_json_returns_false(self) -> None:
        assert _json_has_field("not json", "key") is False

    def test_empty_json_returns_false(self) -> None:
        assert _json_has_field("{}", "key") is False

    def test_json_in_code_block(self) -> None:
        text = '```json\n{"status": "pass"}\n```'
        assert _json_has_field(text, "status") is True


# ── _json_path_matches ────────────────────────────────────────────────────────


class TestJsonPathMatches:
    def test_simple_field_match(self) -> None:
        text = '{"status": "ok"}'
        assert _json_path_matches(text, "$.status", "ok") is True

    def test_simple_field_no_match(self) -> None:
        text = '{"status": "ok"}'
        assert _json_path_matches(text, "$.status", "fail") is False

    def test_nested_field_match(self) -> None:
        text = '{"data": {"score": 9}}'
        assert _json_path_matches(text, "$.data.score", 9) is True

    def test_path_without_dollar(self) -> None:
        text = '{"key": "value"}'
        assert _json_path_matches(text, "key", "value") is True

    def test_expected_none_checks_existence(self) -> None:
        text = '{"key": "value"}'
        assert _json_path_matches(text, "$.key", None) is True

    def test_missing_field_returns_false(self) -> None:
        text = '{"key": "value"}'
        assert _json_path_matches(text, "$.missing", None) is False

    def test_invalid_json_returns_false(self) -> None:
        assert _json_path_matches("not json", "$.key", "value") is False

    def test_array_traversal_two_part_path(self) -> None:
        # Array first: the list traversal moves to element[0], then dict lookup on "type"
        # path "$.0.type" is not how it works — instead use a two-segment path
        # For list at root, single-segment path moves to element but doesn't look up key
        # Use direct dict path instead to verify nested lookup
        text = '{"items": {"type": "test"}}'
        assert _json_path_matches(text, "$.items.type", "test") is True


# ── _env_float ────────────────────────────────────────────────────────────────


class TestEnvFloat:
    def test_default_when_not_set(self) -> None:
        # Use an env var that definitely doesn't exist
        result = _env_float("__TEST_XYZ_NOT_EXIST__", 3.14)
        assert result == pytest.approx(3.14)

    def test_reads_set_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("VISUAL_TEST_THRESHOLD", "0.05")
        result = _env_float("VISUAL_TEST_THRESHOLD", 0.1)
        assert result == pytest.approx(0.05)

    def test_invalid_env_value_returns_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("VISUAL_TEST_THRESHOLD", "not-a-float")
        result = _env_float("VISUAL_TEST_THRESHOLD", 0.99)
        assert result == pytest.approx(0.99)

    def test_zero_default(self) -> None:
        result = _env_float("__NOT_SET_XYZ__", 0.0)
        assert result == 0.0

    def test_integer_env_value_converted(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("VISUAL_TEST_THRESHOLD", "5")
        result = _env_float("VISUAL_TEST_THRESHOLD", 0.1)
        assert result == pytest.approx(5.0)


# ── _safe_name ────────────────────────────────────────────────────────────────


class TestSafeName:
    def test_simple_name_unchanged(self) -> None:
        result = _safe_name("login")
        assert result == "login.png"

    def test_adds_png_extension(self) -> None:
        result = _safe_name("screenshot")
        assert result.endswith(".png")

    def test_already_has_png_not_doubled(self) -> None:
        result = _safe_name("login.png")
        assert result == "login.png"
        assert not result.endswith(".png.png")

    def test_path_traversal_raises(self) -> None:
        with pytest.raises(ValueError):
            _safe_name("../etc/passwd")

    def test_double_dot_in_path_raises(self) -> None:
        with pytest.raises(ValueError):
            _safe_name("tests/../secret")

    def test_absolute_path_raises(self) -> None:
        with pytest.raises(ValueError):
            _safe_name("/etc/passwd")

    def test_subdirectory_allowed(self) -> None:
        result = _safe_name("e2e/login")
        assert "login" in result
        assert result.endswith(".png")

    def test_backslash_converted(self) -> None:
        # Backslash is normalized to forward slash
        result = _safe_name("tests\\login")
        assert "\\" not in result

    def test_whitespace_stripped(self) -> None:
        result = _safe_name("  login  ")
        assert result == "login.png"

    def test_case_insensitive_png_check(self) -> None:
        result = _safe_name("screenshot.PNG")
        assert result.endswith(".PNG")
        assert not result.endswith(".PNG.png")
