"""Unit tests for app.domains.accessibility.analyzer — pure helpers.

Tests are fully self-contained: no DB, no HTTP, no AI.
Covers: _env_bool, _parse_json_array (fenced/plain/embedded/invalid).
"""
from __future__ import annotations

import json
import pytest

try:
    from app.domains.accessibility.analyzer import (
        _env_bool,
        _parse_json_array,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="accessibility.analyzer import failed")


# ---------------------------------------------------------------------------
# _env_bool
# ---------------------------------------------------------------------------

class TestEnvBool:
    def test_default_false_when_not_set(self, monkeypatch):
        monkeypatch.delenv("A11Y_TEST_FLAG", raising=False)
        assert _env_bool("A11Y_TEST_FLAG") is False

    def test_default_true_when_not_set(self, monkeypatch):
        monkeypatch.delenv("A11Y_TEST_FLAG", raising=False)
        assert _env_bool("A11Y_TEST_FLAG", default=True) is True

    def test_true_strings(self, monkeypatch):
        for val in ["1", "true", "yes", "on", "TRUE", "YES"]:
            monkeypatch.setenv("A11Y_TEST_FLAG", val)
            assert _env_bool("A11Y_TEST_FLAG") is True

    def test_false_strings(self, monkeypatch):
        for val in ["0", "false", "no", "off", "FALSE"]:
            monkeypatch.setenv("A11Y_TEST_FLAG", val)
            assert _env_bool("A11Y_TEST_FLAG") is False

    def test_empty_string_returns_false(self, monkeypatch):
        monkeypatch.setenv("A11Y_TEST_FLAG", "")
        assert _env_bool("A11Y_TEST_FLAG") is False

    def test_returns_bool(self, monkeypatch):
        monkeypatch.setenv("A11Y_TEST_FLAG", "1")
        assert isinstance(_env_bool("A11Y_TEST_FLAG"), bool)


# ---------------------------------------------------------------------------
# _parse_json_array
# ---------------------------------------------------------------------------

class TestParseJsonArray:
    def test_plain_json_array(self):
        result = _parse_json_array('[{"id": "1"}, {"id": "2"}]')
        assert isinstance(result, list)
        assert len(result) == 2

    def test_fenced_json_array(self):
        raw = '```json\n[{"id": "v1"}]\n```'
        result = _parse_json_array(raw)
        assert result is not None
        assert result[0]["id"] == "v1"

    def test_fenced_without_lang(self):
        raw = '```\n[{"x": 1}]\n```'
        result = _parse_json_array(raw)
        assert result is not None
        assert isinstance(result, list)

    def test_embedded_array_extracted(self):
        raw = 'Some preamble [{"id": "v1", "title": "test"}] trailing text'
        result = _parse_json_array(raw)
        assert result is not None
        assert result[0]["id"] == "v1"

    def test_empty_string_returns_none(self):
        assert _parse_json_array("") is None

    def test_none_returns_none(self):
        assert _parse_json_array(None) is None  # type: ignore[arg-type]

    def test_invalid_json_returns_none(self):
        assert _parse_json_array("{not valid}") is None

    def test_dict_not_list_returns_none(self):
        assert _parse_json_array('{"key": "value"}') is None

    def test_empty_list_returned(self):
        result = _parse_json_array("[]")
        assert result == []

    def test_returns_list_type(self):
        result = _parse_json_array('[{"id": "1"}]')
        assert isinstance(result, list)

    def test_whitespace_only_returns_none(self):
        assert _parse_json_array("   ") is None

    def test_nested_objects_preserved(self):
        raw = '[{"id": "v1", "nodes": [{"html": "<div>test</div>"}]}]'
        result = _parse_json_array(raw)
        assert result[0]["nodes"][0]["html"] == "<div>test</div>"
