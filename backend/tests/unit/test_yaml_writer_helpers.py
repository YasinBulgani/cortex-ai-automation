"""Unit tests for dsl.yaml_writer pure helpers.

Tests are fully self-contained: no filesystem writes needed for pure functions.
Covers:
  - _CATEGORY_TO_FILE: mapping verification
  - DEFAULT_FILE: uncategorized fallback
  - target_file_for_category: category prefix mapping, unknown fallback
  - _reorder_fields: field ordering, extra fields at end, source_yaml excluded
"""
from __future__ import annotations

import pytest

try:
    from app.domains.dsl.yaml_writer import (
        _reorder_fields,
        target_file_for_category,
        _CATEGORY_TO_FILE,
        DEFAULT_FILE,
        _ACTION_FIELD_ORDER,
    )
    from ruamel.yaml.comments import CommentedMap
    _OK = True
except ImportError:
    _OK = False

pytestmark = pytest.mark.skipif(not _OK, reason="yaml_writer import failed")


# ---------------------------------------------------------------------------
# _CATEGORY_TO_FILE constants
# ---------------------------------------------------------------------------

class TestCategoryToFile:
    def test_ui_maps_to_ui_actions(self):
        assert _CATEGORY_TO_FILE["ui"] == "ui-actions.yaml"

    def test_api_maps_to_api_actions(self):
        assert _CATEGORY_TO_FILE["api"] == "api-actions.yaml"

    def test_assert_maps_to_assertions(self):
        assert _CATEGORY_TO_FILE["assert"] == "assertions.yaml"

    def test_bgts_maps_to_bgts_domain(self):
        assert _CATEGORY_TO_FILE["bgts"] == "bgts-domain.yaml"

    def test_mobile_maps_to_mobile_actions(self):
        assert _CATEGORY_TO_FILE["mobile"] == "mobile-actions.yaml"

    def test_default_file_is_uncategorized(self):
        assert DEFAULT_FILE == "uncategorized.yaml"


# ---------------------------------------------------------------------------
# target_file_for_category
# ---------------------------------------------------------------------------

class TestTargetFileForCategory:
    def test_ui_category(self):
        result = target_file_for_category("ui")
        assert result.name == "ui-actions.yaml"

    def test_ui_dot_click_extracts_prefix(self):
        result = target_file_for_category("ui.click.button")
        assert result.name == "ui-actions.yaml"

    def test_api_category(self):
        result = target_file_for_category("api.get.users")
        assert result.name == "api-actions.yaml"

    def test_assert_category(self):
        result = target_file_for_category("assert.equals.text")
        assert result.name == "assertions.yaml"

    def test_mobile_category(self):
        result = target_file_for_category("mobile.tap.element")
        assert result.name == "mobile-actions.yaml"

    def test_bgts_category(self):
        result = target_file_for_category("bgts.approval.flow")
        assert result.name == "bgts-domain.yaml"

    def test_unknown_prefix_falls_back_to_uncategorized(self):
        result = target_file_for_category("xyz.something")
        assert result.name == DEFAULT_FILE

    def test_empty_string_falls_back(self):
        result = target_file_for_category("")
        assert result.name == DEFAULT_FILE

    def test_returns_path(self):
        from pathlib import Path
        result = target_file_for_category("ui")
        assert isinstance(result, Path)


# ---------------------------------------------------------------------------
# _reorder_fields
# ---------------------------------------------------------------------------

class TestReorderFields:
    def _full_action(self, **kwargs):
        base = {
            "id": "ui.login.submit",
            "category": "ui",
            "description": "Click submit",
            "aliases": ["submit_btn"],
            "parameters": [],
            "implementations": [],
            "tags": ["auth"],
            "since": "1.0",
        }
        base.update(kwargs)
        return base

    def test_returns_commented_map(self):
        result = _reorder_fields(self._full_action())
        assert isinstance(result, CommentedMap)

    def test_id_is_first_key(self):
        result = _reorder_fields(self._full_action())
        assert list(result.keys())[0] == "id"

    def test_category_is_second(self):
        result = _reorder_fields(self._full_action())
        keys = list(result.keys())
        assert keys[1] == "category"

    def test_description_is_third(self):
        result = _reorder_fields(self._full_action())
        keys = list(result.keys())
        assert keys[2] == "description"

    def test_all_known_fields_preserved(self):
        action = self._full_action()
        result = _reorder_fields(action)
        for key in ("id", "category", "description", "aliases", "parameters"):
            assert key in result

    def test_extra_field_appended_at_end(self):
        action = self._full_action(custom_field="custom_value")
        result = _reorder_fields(action)
        last_key = list(result.keys())[-1]
        assert last_key == "custom_field"

    def test_source_yaml_excluded(self):
        action = self._full_action(source_yaml="ui-actions.yaml")
        result = _reorder_fields(action)
        assert "source_yaml" not in result

    def test_values_preserved(self):
        action = self._full_action()
        result = _reorder_fields(action)
        assert result["id"] == "ui.login.submit"
        assert result["category"] == "ui"
        assert result["tags"] == ["auth"]

    def test_partial_action_only_present_fields(self):
        # Only id and description — no category
        action = {"id": "test.action", "description": "A test"}
        result = _reorder_fields(action)
        keys = list(result.keys())
        assert "id" in keys
        assert "description" in keys
        assert "category" not in keys

    def test_action_field_order_constant_is_list(self):
        assert isinstance(_ACTION_FIELD_ORDER, list)
        assert "id" in _ACTION_FIELD_ORDER
        assert _ACTION_FIELD_ORDER[0] == "id"
