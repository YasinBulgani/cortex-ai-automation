"""Unit tests for dsl.editor_service pure helper functions and exception classes.

All tests are self-contained: no DB, no HTTP, no YAML file I/O.
Covers:
  - _strip_source_yaml: source_yaml key removal from dict
  - _commit_message: git commit message generation from operation/action_id/actor
  - EditorError / NotFoundError / ConflictError: exception hierarchy
"""
from __future__ import annotations

import pytest

try:
    from app.domains.dsl.editor_service import (
        _strip_source_yaml,
        _commit_message,
        EditorError,
        NotFoundError,
        ConflictError,
    )
    _DSL_OK = True
except ImportError:
    _DSL_OK = False


# ---------------------------------------------------------------------------
# Fake user helper
# ---------------------------------------------------------------------------

class _FakeUser:
    def __init__(self, email: str = "bot@example.com"):
        self.email = email
        self.id = "user-001"


# ---------------------------------------------------------------------------
# _strip_source_yaml
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _DSL_OK, reason="dsl.editor_service import failed")
class TestStripSourceYaml:
    def test_removes_source_yaml_key(self):
        d = {"id": "a1", "title": "Test", "source_yaml": "raw: yaml content"}
        result = _strip_source_yaml(d)
        assert "source_yaml" not in result

    def test_preserves_other_keys(self):
        d = {"id": "a1", "title": "My Action", "source_yaml": "..."}
        result = _strip_source_yaml(d)
        assert result["id"] == "a1"
        assert result["title"] == "My Action"

    def test_no_source_yaml_unchanged(self):
        d = {"id": "a1", "title": "No YAML key"}
        result = _strip_source_yaml(d)
        assert result == d

    def test_empty_dict(self):
        result = _strip_source_yaml({})
        assert result == {}

    def test_only_source_yaml(self):
        result = _strip_source_yaml({"source_yaml": "content"})
        assert result == {}

    def test_returns_new_dict(self):
        d = {"id": "x", "source_yaml": "y"}
        result = _strip_source_yaml(d)
        d["new_key"] = "added"
        assert "new_key" not in result

    def test_returns_dict(self):
        assert isinstance(_strip_source_yaml({"a": 1}), dict)

    def test_multiple_keys_preserved(self):
        d = {"a": 1, "b": 2, "c": 3, "source_yaml": "raw"}
        result = _strip_source_yaml(d)
        assert len(result) == 3
        assert all(k in result for k in ("a", "b", "c"))


# ---------------------------------------------------------------------------
# _commit_message
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _DSL_OK, reason="dsl.editor_service import failed")
class TestCommitMessage:
    def test_create_uses_add_verb(self):
        msg = _commit_message("create", "act-001", None)
        assert "add" in msg

    def test_update_uses_update_verb(self):
        msg = _commit_message("update", "act-002", None)
        assert "update" in msg

    def test_delete_uses_remove_verb(self):
        msg = _commit_message("delete", "act-003", None)
        assert "remove" in msg

    def test_deprecate_uses_deprecate_verb(self):
        msg = _commit_message("deprecate", "act-004", None)
        assert "deprecate" in msg

    def test_unknown_operation_preserved(self):
        msg = _commit_message("archive", "act-005", None)
        assert "archive" in msg

    def test_action_id_in_message(self):
        msg = _commit_message("create", "my-action-123", None)
        assert "my-action-123" in msg

    def test_none_actor_uses_unknown(self):
        msg = _commit_message("create", "act", None)
        assert "unknown" in msg

    def test_actor_email_in_message(self):
        user = _FakeUser("author@example.com")
        msg = _commit_message("update", "act", user)
        assert "author@example.com" in msg

    def test_returns_string(self):
        assert isinstance(_commit_message("create", "act", None), str)

    def test_contains_dsl_prefix(self):
        msg = _commit_message("create", "act", None)
        assert msg.startswith("dsl:")

    def test_contains_change_proposed_by_line(self):
        msg = _commit_message("create", "act", _FakeUser("x@y.com"))
        assert "Change-Proposed-By" in msg

    def test_contains_auto_generated_notice(self):
        msg = _commit_message("create", "act", None)
        assert "Auto-generated" in msg

    def test_actor_without_email_uses_unknown(self):
        class NoEmail:
            pass
        msg = _commit_message("create", "act", NoEmail())
        assert "unknown" in msg


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _DSL_OK, reason="dsl.editor_service import failed")
class TestExceptionHierarchy:
    def test_editor_error_is_value_error(self):
        assert issubclass(EditorError, ValueError)

    def test_not_found_error_is_editor_error(self):
        assert issubclass(NotFoundError, EditorError)

    def test_conflict_error_is_editor_error(self):
        assert issubclass(ConflictError, EditorError)

    def test_editor_error_can_be_raised(self):
        with pytest.raises(EditorError):
            raise EditorError("test error")

    def test_editor_error_caught_as_value_error(self):
        with pytest.raises(ValueError):
            raise EditorError("also a value error")

    def test_not_found_error_can_be_raised(self):
        with pytest.raises(NotFoundError):
            raise NotFoundError("not found")

    def test_not_found_caught_as_editor_error(self):
        with pytest.raises(EditorError):
            raise NotFoundError("hierarchy works")

    def test_conflict_error_can_be_raised(self):
        with pytest.raises(ConflictError):
            raise ConflictError("conflict!")

    def test_conflict_caught_as_editor_error(self):
        with pytest.raises(EditorError):
            raise ConflictError("hierarchy works")

    def test_editor_error_message_preserved(self):
        try:
            raise EditorError("specific error message", details={"key": "val"})
        except EditorError as e:
            assert "specific error message" in str(e)

    def test_editor_error_with_details(self):
        e = EditorError("msg", details={"field": "value"})
        assert e.details == {"field": "value"}  # type: ignore[attr-defined]
