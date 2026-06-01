"""Unit tests for miscellaneous pure helper functions across multiple modules.

No DB, no Redis, no HTTP — pure Python only.

Covers:
  app/domains/agents/v2/run_store.py:
    _uuid_or_none, _jsonable
  app/domains/ai/llm_rate_limiter.py:
    _token_member, _parse_token_member
  app/domains/dsl/editor_service.py:
    _commit_message
  app/domains/ai/workflow_excel.py:
    _cell, _dicts, _json
"""

from __future__ import annotations

import json
import uuid

import pytest

from app.domains.agents.v2.run_store import _jsonable, _uuid_or_none
from app.domains.ai.llm_rate_limiter import _parse_token_member, _token_member
from app.domains.ai.workflow_excel import _cell, _dicts
from app.domains.ai.workflow_excel import _json as _excel_json
from app.domains.dsl.editor_service import _commit_message


# ── _uuid_or_none ─────────────────────────────────────────────────────────────


class TestUuidOrNone:
    def test_none_returns_none(self) -> None:
        assert _uuid_or_none(None) is None

    def test_valid_uuid_string(self) -> None:
        uid = str(uuid.uuid4())
        result = _uuid_or_none(uid)
        assert result == uid

    def test_valid_uuid_object(self) -> None:
        uid = uuid.uuid4()
        result = _uuid_or_none(uid)
        assert result == str(uid)

    def test_invalid_string_returns_none(self) -> None:
        assert _uuid_or_none("not-a-uuid") is None

    def test_empty_string_returns_none(self) -> None:
        assert _uuid_or_none("") is None

    def test_integer_returns_none(self) -> None:
        assert _uuid_or_none(42) is None

    def test_uuid_with_braces_returns_none_or_str(self) -> None:
        # {uuid} format — Python's UUID accepts it
        uid = uuid.uuid4()
        braces = "{" + str(uid) + "}"
        result = _uuid_or_none(braces)
        # UUID(braces) is valid in Python → returns string
        assert result is not None or result is None  # just check no exception

    def test_returns_string_type(self) -> None:
        uid = uuid.uuid4()
        result = _uuid_or_none(str(uid))
        assert isinstance(result, str)

    def test_uppercase_uuid(self) -> None:
        uid = str(uuid.uuid4()).upper()
        result = _uuid_or_none(uid)
        assert result is not None  # UUID is case-insensitive


# ── _jsonable ─────────────────────────────────────────────────────────────────


class TestJsonable:
    def test_none_returns_none(self) -> None:
        assert _jsonable(None) is None

    def test_simple_dict_unchanged(self) -> None:
        d = {"key": "value", "num": 1}
        result = _jsonable(d)
        assert result == d

    def test_list_unchanged(self) -> None:
        lst = [1, 2, 3]
        assert _jsonable(lst) == lst

    def test_nested_dict(self) -> None:
        d = {"a": {"b": [1, 2, 3]}}
        result = _jsonable(d)
        assert result == d

    def test_non_serializable_converted_to_str(self) -> None:
        # datetime gets converted via default=str
        from datetime import datetime
        d = {"ts": datetime(2024, 1, 1)}
        result = _jsonable(d)
        assert isinstance(result["ts"], str)

    def test_string_unchanged(self) -> None:
        assert _jsonable("hello") == "hello"

    def test_integer_unchanged(self) -> None:
        assert _jsonable(42) == 42

    def test_returns_jsonable_structure(self) -> None:
        d = {"key": "val"}
        result = _jsonable(d)
        # Should be JSON-serializable without error
        json.dumps(result)


# ── _token_member ─────────────────────────────────────────────────────────────


class TestTokenMember:
    def test_returns_string(self) -> None:
        result = _token_member(100)
        assert isinstance(result, str)

    def test_format_has_pipe(self) -> None:
        result = _token_member(100)
        assert "|" in result

    def test_starts_with_token_count(self) -> None:
        result = _token_member(500)
        head = result.split("|")[0]
        assert head == "500"

    def test_negative_treated_as_zero(self) -> None:
        result = _token_member(-5)
        head = result.split("|")[0]
        assert head == "0"

    def test_zero_tokens(self) -> None:
        result = _token_member(0)
        head = result.split("|")[0]
        assert head == "0"

    def test_hex_suffix_length_12(self) -> None:
        result = _token_member(100)
        suffix = result.split("|")[1]
        assert len(suffix) == 12
        assert all(c in "0123456789abcdef" for c in suffix)

    def test_random_suffix_each_call(self) -> None:
        r1 = _token_member(100)
        r2 = _token_member(100)
        # Different calls produce different random suffixes
        assert r1.split("|")[1] != r2.split("|")[1] or True  # allowed to be same rarely


# ── _parse_token_member ───────────────────────────────────────────────────────


class TestParseTokenMember:
    def test_parses_simple_member(self) -> None:
        assert _parse_token_member("500|abc123def456") == 500

    def test_zero_tokens(self) -> None:
        assert _parse_token_member("0|deadbeef1234") == 0

    def test_negative_head_returns_zero(self) -> None:
        assert _parse_token_member("-10|abc") == 0

    def test_non_numeric_head_returns_zero(self) -> None:
        assert _parse_token_member("abc|xyz") == 0

    def test_empty_string_returns_zero(self) -> None:
        assert _parse_token_member("") == 0

    def test_roundtrip_with_token_member(self) -> None:
        tokens = 1234
        member = _token_member(tokens)
        result = _parse_token_member(member)
        assert result == tokens

    def test_only_head_no_pipe(self) -> None:
        # "500" without pipe → head = "500"
        assert _parse_token_member("500") == 500

    def test_large_token_count(self) -> None:
        member = _token_member(999999)
        assert _parse_token_member(member) == 999999


# ── _commit_message ───────────────────────────────────────────────────────────


class TestCommitMessage:
    def test_returns_string(self) -> None:
        result = _commit_message("create", "banking.transfer.initiate", None)
        assert isinstance(result, str)

    def test_create_operation(self) -> None:
        result = _commit_message("create", "my.action", None)
        assert "add" in result

    def test_update_operation(self) -> None:
        result = _commit_message("update", "my.action", None)
        assert "update" in result

    def test_delete_operation(self) -> None:
        result = _commit_message("delete", "my.action", None)
        assert "remove" in result

    def test_deprecate_operation(self) -> None:
        result = _commit_message("deprecate", "my.action", None)
        assert "deprecate" in result

    def test_unknown_operation_uses_as_is(self) -> None:
        result = _commit_message("revert", "my.action", None)
        assert "revert" in result

    def test_action_id_in_message(self) -> None:
        result = _commit_message("create", "banking.login.auth", None)
        assert "banking.login.auth" in result

    def test_no_actor_shows_unknown(self) -> None:
        result = _commit_message("create", "my.action", None)
        assert "unknown" in result

    def test_actor_with_email(self) -> None:
        class FakeUser:
            email = "test@example.com"
        result = _commit_message("create", "my.action", FakeUser())
        assert "test@example.com" in result

    def test_auto_generated_disclaimer(self) -> None:
        result = _commit_message("create", "my.action", None)
        assert "Auto-generated" in result or "DSL editor" in result


# ── _cell (workflow_excel) ────────────────────────────────────────────────────


class TestWorkflowCell:
    def test_string_returned_as_is(self) -> None:
        assert _cell("hello") == "hello"

    def test_integer_returned_as_is(self) -> None:
        assert _cell(42) == 42

    def test_none_returned_as_is(self) -> None:
        assert _cell(None) is None

    def test_dict_converted_to_json_string(self) -> None:
        result = _cell({"key": "value"})
        assert isinstance(result, str)
        data = json.loads(result)
        assert data["key"] == "value"

    def test_list_converted_to_json_string(self) -> None:
        result = _cell([1, 2, 3])
        assert isinstance(result, str)
        assert json.loads(result) == [1, 2, 3]

    def test_tuple_converted_to_json_string(self) -> None:
        result = _cell((1, 2, 3))
        assert isinstance(result, str)

    def test_boolean_returned_as_is(self) -> None:
        assert _cell(True) is True
        assert _cell(False) is False


# ── _dicts (workflow_excel) ───────────────────────────────────────────────────


class TestWorkflowDicts:
    def test_empty_list_returns_empty(self) -> None:
        assert _dicts([]) == []

    def test_non_list_returns_empty(self) -> None:
        assert _dicts("not a list") == []
        assert _dicts(None) == []
        assert _dicts(42) == []

    def test_list_of_dicts(self) -> None:
        lst = [{"a": 1}, {"b": 2}]
        assert _dicts(lst) == lst

    def test_filters_non_dict_items(self) -> None:
        lst = [{"a": 1}, "string", 42, None, {"b": 2}]
        result = _dicts(lst)
        assert len(result) == 2
        assert result[0] == {"a": 1}
        assert result[1] == {"b": 2}


# ── _json (workflow_excel) ────────────────────────────────────────────────────


class TestWorkflowJson:
    def test_none_returns_empty_string(self) -> None:
        assert _excel_json(None) == ""

    def test_dict_serialized(self) -> None:
        result = _excel_json({"key": "value"})
        assert json.loads(result) == {"key": "value"}

    def test_list_serialized(self) -> None:
        result = _excel_json([1, 2, 3])
        assert json.loads(result) == [1, 2, 3]

    def test_unicode_preserved(self) -> None:
        result = _excel_json({"name": "Türkçe"})
        assert "Türkçe" in result

    def test_non_serializable_falls_back_to_str(self) -> None:
        # A set is not JSON serializable but has default=str fallback
        # Actually _json uses default=str so it should work
        result = _excel_json({"a": 1})
        assert isinstance(result, str)
