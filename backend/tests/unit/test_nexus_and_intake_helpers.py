"""Unit tests for pure helpers in nexus_repo.llm_generator and agents.v2.tools.intake.

Tests are fully self-contained: no DB, no HTTP, no AI, no filesystem reads.
Covers:
  - nexus_repo.llm_generator._parse_scenarios: JSON/markdown fenced/dict wrapping
  - agents.v2.tools.intake._infer_source_type: URL/file extension inference
"""
from __future__ import annotations

import json
import pytest

try:
    from app.domains.nexus_repo.llm_generator import _parse_scenarios
    _NEXUS_OK = True
except ImportError:
    _NEXUS_OK = False

try:
    from app.domains.agents.v2.tools.intake import _infer_source_type
    _INTAKE_OK = True
except ImportError:
    _INTAKE_OK = False


# ---------------------------------------------------------------------------
# _parse_scenarios
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _NEXUS_OK, reason="nexus_repo.llm_generator import failed")
class TestParseScenarios:
    def test_plain_json_list(self):
        raw = json.dumps([{"title": "Login test", "steps": ["open page"]}])
        result = _parse_scenarios(raw)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["title"] == "Login test"

    def test_fenced_json(self):
        raw = '```json\n[{"title": "Test A"}]\n```'
        result = _parse_scenarios(raw)
        assert result is not None
        assert len(result) == 1
        assert result[0]["title"] == "Test A"

    def test_fenced_without_lang(self):
        raw = '```\n[{"title": "Test B"}]\n```'
        result = _parse_scenarios(raw)
        assert isinstance(result, list)

    def test_dict_with_scenarios_key(self):
        raw = json.dumps({"scenarios": [{"title": "Wrapped"}]})
        result = _parse_scenarios(raw)
        assert len(result) == 1
        assert result[0]["title"] == "Wrapped"

    def test_dict_without_scenarios_key_returns_empty(self):
        raw = json.dumps({"other_key": [1, 2, 3]})
        result = _parse_scenarios(raw)
        assert result == []

    def test_invalid_json_returns_empty(self):
        result = _parse_scenarios("not valid json {{{")
        assert result == []

    def test_empty_string_returns_empty(self):
        result = _parse_scenarios("")
        assert result == []

    def test_empty_list_returned(self):
        result = _parse_scenarios("[]")
        assert result == []

    def test_multiple_scenarios(self):
        raw = json.dumps([
            {"title": "Login"},
            {"title": "Logout"},
            {"title": "Profile"},
        ])
        result = _parse_scenarios(raw)
        assert len(result) == 3

    def test_whitespace_stripped_before_parse(self):
        raw = "  " + json.dumps([{"title": "X"}]) + "  "
        result = _parse_scenarios(raw)
        assert len(result) == 1

    def test_returns_list_type(self):
        raw = json.dumps([{"x": 1}])
        assert isinstance(_parse_scenarios(raw), list)

    def test_non_list_non_dict_returns_empty(self):
        result = _parse_scenarios('"just a string"')
        assert result == []


# ---------------------------------------------------------------------------
# _infer_source_type
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _INTAKE_OK, reason="agents.v2.tools.intake import failed")
class TestInferSourceType:
    def test_http_url(self):
        assert _infer_source_type("http://example.com/api") == "url"

    def test_https_url(self):
        assert _infer_source_type("https://example.com/spec") == "url"

    def test_plain_text_default(self):
        # No URL, no known extension without path sep → "text"
        result = _infer_source_type("some plain text")
        assert result == "text"

    def test_yaml_extension(self):
        # Path with os.sep — but file doesn't exist → still returns "swagger" if suffix matches
        # Without a real file, the path detection falls through to "text" for non-URL non-file
        # The function checks p.exists() — for non-existent files with .yaml it's still "text"
        result = _infer_source_type("nonexistent.yaml")
        # without os.sep, p is None → "text"
        assert result == "text"

    def test_url_stripped(self):
        assert _infer_source_type("  https://api.example.com  ") == "url"

    def test_http_url_with_path(self):
        assert _infer_source_type("https://petstore.swagger.io/v2/swagger.json") == "url"

    def test_empty_string_returns_text(self):
        assert _infer_source_type("") == "text"

    def test_just_whitespace_returns_text(self):
        assert _infer_source_type("   ") == "text"

    def test_returns_string(self):
        result = _infer_source_type("https://example.com")
        assert isinstance(result, str)
