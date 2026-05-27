"""Unit tests for agents v2 run_store and DSL editor service pure helpers.

No DB, no HTTP, no LLM — pure Python only.

Covers:
  app/domains/agents/v2/run_store.py:
    _uuid_or_none, _jsonable, _sha256_file
  app/domains/dsl/editor_service.py:
    _commit_message
"""

from __future__ import annotations

import hashlib
import tempfile
import types
from pathlib import Path

import pytest

from app.domains.agents.v2.run_store import (
    _jsonable,
    _sha256_file,
    _uuid_or_none,
)
from app.domains.dsl.editor_service import _commit_message


# ── _uuid_or_none ─────────────────────────────────────────────────────────────


class TestUuidOrNone:
    VALID_UUID = "550e8400-e29b-41d4-a716-446655440000"

    def test_none_returns_none(self) -> None:
        assert _uuid_or_none(None) is None

    def test_valid_uuid_string(self) -> None:
        result = _uuid_or_none(self.VALID_UUID)
        assert result == self.VALID_UUID

    def test_invalid_string_returns_none(self) -> None:
        assert _uuid_or_none("not-a-uuid") is None

    def test_empty_string_returns_none(self) -> None:
        assert _uuid_or_none("") is None

    def test_integer_returns_none(self) -> None:
        assert _uuid_or_none(12345) is None

    def test_returns_string_type(self) -> None:
        result = _uuid_or_none(self.VALID_UUID)
        assert isinstance(result, str)

    def test_uuid_without_dashes_parsed(self) -> None:
        no_dashes = self.VALID_UUID.replace("-", "")
        result = _uuid_or_none(no_dashes)
        assert result is not None
        assert "-" in result  # normalized with dashes

    def test_uppercase_uuid_normalized(self) -> None:
        upper = self.VALID_UUID.upper()
        result = _uuid_or_none(upper)
        assert result is not None


# ── _jsonable ─────────────────────────────────────────────────────────────────


class TestJsonable:
    def test_none_returns_none(self) -> None:
        assert _jsonable(None) is None

    def test_dict_passthrough(self) -> None:
        d = {"key": "value", "num": 42}
        result = _jsonable(d)
        assert result == d

    def test_list_passthrough(self) -> None:
        lst = [1, "two", 3.0]
        result = _jsonable(lst)
        assert result == lst

    def test_datetime_converted_to_string(self) -> None:
        from datetime import datetime, timezone
        dt = datetime(2024, 1, 15, tzinfo=timezone.utc)
        result = _jsonable({"ts": dt})
        assert isinstance(result["ts"], str)

    def test_set_converted_to_list_or_str(self) -> None:
        # set is not JSON-serializable by default
        # json.dumps with default=str converts it to string
        result = _jsonable({"items": {1, 2, 3}})
        # the set will be serialized as string via default=str
        assert result is not None

    def test_nested_dict_preserved(self) -> None:
        d = {"a": {"b": {"c": 42}}}
        result = _jsonable(d)
        assert result == d

    def test_returns_same_type_for_primitives(self) -> None:
        assert _jsonable(42) == 42
        assert _jsonable("hello") == "hello"
        assert _jsonable(3.14) == pytest.approx(3.14)
        assert _jsonable(True) is True

    def test_deeply_nested_list(self) -> None:
        lst = [[1, 2], [3, [4, 5]]]
        assert _jsonable(lst) == lst


# ── _sha256_file ──────────────────────────────────────────────────────────────


class TestSha256File:
    def test_returns_hex_string(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"hello world")
            path = Path(f.name)
        try:
            result = _sha256_file(path)
            assert isinstance(result, str)
            assert len(result) == 64
        finally:
            path.unlink()

    def test_matches_standard_sha256(self) -> None:
        content = b"test content for hashing"
        expected = hashlib.sha256(content).hexdigest()
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(content)
            path = Path(f.name)
        try:
            assert _sha256_file(path) == expected
        finally:
            path.unlink()

    def test_deterministic(self) -> None:
        content = b"repeated content"
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(content)
            path = Path(f.name)
        try:
            h1 = _sha256_file(path)
            h2 = _sha256_file(path)
            assert h1 == h2
        finally:
            path.unlink()

    def test_empty_file(self) -> None:
        with tempfile.NamedTemporaryFile(delete=False) as f:
            path = Path(f.name)
        try:
            result = _sha256_file(path)
            expected = hashlib.sha256(b"").hexdigest()
            assert result == expected
        finally:
            path.unlink()

    def test_different_content_different_hash(self) -> None:
        import tempfile as tf

        with tf.NamedTemporaryFile(delete=False) as f1:
            f1.write(b"content A")
            p1 = Path(f1.name)
        with tf.NamedTemporaryFile(delete=False) as f2:
            f2.write(b"content B")
            p2 = Path(f2.name)
        try:
            assert _sha256_file(p1) != _sha256_file(p2)
        finally:
            p1.unlink()
            p2.unlink()


# ── _commit_message ───────────────────────────────────────────────────────────


class TestCommitMessage:
    def _user(self, email: str = "dev@example.com") -> types.SimpleNamespace:
        return types.SimpleNamespace(email=email)

    def test_create_operation_uses_add_verb(self) -> None:
        msg = _commit_message("create", "my_action", self._user())
        assert "add" in msg

    def test_update_operation_uses_update_verb(self) -> None:
        msg = _commit_message("update", "my_action", self._user())
        assert "update" in msg

    def test_delete_operation_uses_remove_verb(self) -> None:
        msg = _commit_message("delete", "my_action", self._user())
        assert "remove" in msg

    def test_deprecate_operation(self) -> None:
        msg = _commit_message("deprecate", "my_action", self._user())
        assert "deprecate" in msg

    def test_action_id_included(self) -> None:
        msg = _commit_message("create", "login_api_test", self._user())
        assert "login_api_test" in msg

    def test_actor_email_included(self) -> None:
        msg = _commit_message("create", "action", self._user("alice@corp.com"))
        assert "alice@corp.com" in msg

    def test_none_actor_uses_unknown(self) -> None:
        msg = _commit_message("create", "action", None)
        assert "unknown" in msg

    def test_unknown_operation_uses_raw_verb(self) -> None:
        msg = _commit_message("restore", "action", self._user())
        assert "restore" in msg

    def test_returns_string(self) -> None:
        assert isinstance(_commit_message("create", "x", None), str)

    def test_contains_dsl_prefix(self) -> None:
        msg = _commit_message("create", "action", None)
        assert msg.startswith("dsl:")

    def test_contains_via_ui(self) -> None:
        msg = _commit_message("create", "action", None)
        assert "UI" in msg
