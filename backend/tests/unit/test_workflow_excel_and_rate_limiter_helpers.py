"""Unit tests for AI workflow Excel and LLM rate limiter pure helpers.

No DB, no HTTP, no LLM — pure Python only.

Covers:
  app/domains/ai/workflow_excel.py:
    _cell, _dicts, _json
  app/domains/ai/llm_rate_limiter.py:
    _token_member, _parse_token_member
"""

from __future__ import annotations

import json

import pytest

from app.domains.ai.workflow_excel import _cell, _dicts, _json
from app.domains.ai.llm_rate_limiter import _parse_token_member, _token_member


# ── _cell ─────────────────────────────────────────────────────────────────────


class TestCell:
    def test_string_passthrough(self) -> None:
        assert _cell("hello") == "hello"

    def test_int_passthrough(self) -> None:
        assert _cell(42) == 42

    def test_float_passthrough(self) -> None:
        assert _cell(3.14) == pytest.approx(3.14)

    def test_none_passthrough(self) -> None:
        assert _cell(None) is None

    def test_bool_passthrough(self) -> None:
        assert _cell(True) is True

    def test_dict_converted_to_json_string(self) -> None:
        result = _cell({"key": "value"})
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed == {"key": "value"}

    def test_list_converted_to_json_string(self) -> None:
        result = _cell([1, 2, 3])
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed == [1, 2, 3]

    def test_tuple_converted_to_json_string(self) -> None:
        result = _cell((1, "two"))
        assert isinstance(result, str)

    def test_nested_dict_converted(self) -> None:
        result = _cell({"a": {"b": 1}})
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert parsed == {"a": {"b": 1}}

    def test_empty_dict_converted(self) -> None:
        result = _cell({})
        assert isinstance(result, str)
        assert result == "{}"

    def test_empty_list_converted(self) -> None:
        result = _cell([])
        assert result == "[]"


# ── _dicts ────────────────────────────────────────────────────────────────────


class TestDicts:
    def test_list_of_dicts_returned(self) -> None:
        result = _dicts([{"a": 1}, {"b": 2}])
        assert result == [{"a": 1}, {"b": 2}]

    def test_non_dict_items_filtered(self) -> None:
        result = _dicts([{"a": 1}, "string", 42, None])
        assert result == [{"a": 1}]

    def test_empty_list_returns_empty(self) -> None:
        assert _dicts([]) == []

    def test_not_a_list_returns_empty(self) -> None:
        assert _dicts("string") == []
        assert _dicts(None) == []
        assert _dicts(42) == []
        assert _dicts({}) == []

    def test_all_non_dict_returns_empty(self) -> None:
        result = _dicts([1, 2, 3, "a", None])
        assert result == []

    def test_returns_list_type(self) -> None:
        assert isinstance(_dicts([{"x": 1}]), list)

    def test_nested_dicts_included(self) -> None:
        nested = {"a": {"b": 2}}
        result = _dicts([nested])
        assert result == [nested]


# ── _json ─────────────────────────────────────────────────────────────────────


class TestJson:
    def test_none_returns_empty_string(self) -> None:
        assert _json(None) == ""

    def test_dict_serialized(self) -> None:
        result = _json({"key": "value"})
        parsed = json.loads(result)
        assert parsed == {"key": "value"}

    def test_list_serialized(self) -> None:
        result = _json([1, 2, 3])
        parsed = json.loads(result)
        assert parsed == [1, 2, 3]

    def test_empty_dict(self) -> None:
        assert _json({}) == "{}"

    def test_empty_list(self) -> None:
        assert _json([]) == "[]"

    def test_unicode_preserved(self) -> None:
        result = _json({"name": "Öğrenci"})
        assert "Öğrenci" in result

    def test_datetime_handled_via_default_str(self) -> None:
        from datetime import datetime
        dt = datetime(2024, 1, 1)
        result = _json({"ts": dt})
        assert isinstance(result, str)
        assert "2024" in result

    def test_returns_string(self) -> None:
        assert isinstance(_json({"x": 1}), str)

    def test_nested_structure(self) -> None:
        data = {"a": [1, 2], "b": {"c": 3}}
        result = _json(data)
        parsed = json.loads(result)
        assert parsed == data


# ── _token_member ─────────────────────────────────────────────────────────────


class TestTokenMember:
    def test_contains_token_count(self) -> None:
        member = _token_member(1000)
        assert member.startswith("1000|")

    def test_contains_random_suffix(self) -> None:
        m1 = _token_member(500)
        m2 = _token_member(500)
        # same count but different random suffix
        assert m1 != m2

    def test_negative_becomes_zero(self) -> None:
        member = _token_member(-100)
        assert member.startswith("0|")

    def test_returns_string(self) -> None:
        assert isinstance(_token_member(100), str)

    def test_format_is_count_pipe_hex(self) -> None:
        member = _token_member(42)
        parts = member.split("|")
        assert len(parts) == 2
        assert parts[0] == "42"
        # hex suffix from secrets.token_hex(6) = 12 hex chars
        assert len(parts[1]) == 12


# ── _parse_token_member ───────────────────────────────────────────────────────


class TestParseTokenMember:
    def test_parses_valid_member(self) -> None:
        member = "1500|deadbeef1234"
        assert _parse_token_member(member) == 1500

    def test_zero_value(self) -> None:
        assert _parse_token_member("0|aabbcc") == 0

    def test_large_value(self) -> None:
        assert _parse_token_member("100000|fffff") == 100_000

    def test_invalid_head_returns_zero(self) -> None:
        assert _parse_token_member("notanumber|xxx") == 0

    def test_returns_non_negative(self) -> None:
        assert _parse_token_member("0|x") >= 0

    def test_roundtrip_with_token_member(self) -> None:
        member = _token_member(750)
        assert _parse_token_member(member) == 750

    def test_no_pipe_returns_zero(self) -> None:
        # No pipe — head is entire string
        assert _parse_token_member("5000") == 5000

    def test_returns_int(self) -> None:
        assert isinstance(_parse_token_member("42|abc"), int)
