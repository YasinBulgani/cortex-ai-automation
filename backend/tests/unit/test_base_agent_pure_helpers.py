"""Unit tests for agents.banking_team.base_agent pure helpers and dataclasses.

All tests are self-contained: no Playwright, no HTTP, no LLM.
Covers:
  - BaseAgent._extract_json_object: nested-brace-aware JSON extraction
  - BaseAgent._extract_json_array: array extraction from text
  - AgentResult: dataclass fields and default values
"""
from __future__ import annotations

import pytest

try:
    from app.domains.agents.banking_team.base_agent import BaseAgent, AgentResult
    _BA_OK = True
except ImportError:
    _BA_OK = False


# ---------------------------------------------------------------------------
# BaseAgent._extract_json_object
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _BA_OK, reason="base_agent import failed")
class TestExtractJsonObject:
    def test_plain_dict(self):
        result = BaseAgent._extract_json_object('{"key": "value"}')
        assert result == {"key": "value"}

    def test_embedded_in_prose(self):
        text = 'Here is the result: {"status": "ok"} done.'
        result = BaseAgent._extract_json_object(text)
        assert result == {"status": "ok"}

    def test_nested_object(self):
        text = '{"outer": {"inner": 42}}'
        result = BaseAgent._extract_json_object(text)
        assert result == {"outer": {"inner": 42}}

    def test_deeply_nested(self):
        text = '{"a": {"b": {"c": "deep"}}}'
        result = BaseAgent._extract_json_object(text)
        assert result == {"a": {"b": {"c": "deep"}}}

    def test_no_braces_returns_none(self):
        assert BaseAgent._extract_json_object("no braces here") is None

    def test_empty_string_returns_none(self):
        assert BaseAgent._extract_json_object("") is None

    def test_invalid_json_returns_none(self):
        assert BaseAgent._extract_json_object("{not valid json}") is None

    def test_escaped_quotes_in_string(self):
        text = '{"message": "say \\"hello\\" now"}'
        result = BaseAgent._extract_json_object(text)
        assert result is not None
        assert result["message"] == 'say "hello" now'

    def test_string_with_braces_not_confused(self):
        # Braces inside a JSON string value should not fool the parser
        text = '{"path": "some/path/{id}/resource"}'
        result = BaseAgent._extract_json_object(text)
        assert result is not None
        assert result["path"] == "some/path/{id}/resource"

    def test_multiple_objects_returns_first(self):
        text = '{"first": 1} {"second": 2}'
        result = BaseAgent._extract_json_object(text)
        assert result == {"first": 1}

    def test_array_value_inside_object(self):
        text = '{"items": [1, 2, 3]}'
        result = BaseAgent._extract_json_object(text)
        assert result == {"items": [1, 2, 3]}

    def test_bool_values(self):
        result = BaseAgent._extract_json_object('{"active": true, "deleted": false}')
        assert result == {"active": True, "deleted": False}

    def test_null_value(self):
        result = BaseAgent._extract_json_object('{"key": null}')
        assert result == {"key": None}

    def test_numeric_values(self):
        result = BaseAgent._extract_json_object('{"count": 42, "ratio": 3.14}')
        assert result is not None
        assert result["count"] == 42
        assert result["ratio"] == pytest.approx(3.14)

    def test_returns_dict(self):
        assert isinstance(BaseAgent._extract_json_object('{"a": 1}'), dict)

    def test_prefix_text_ignored(self):
        text = "The answer is: {\"x\": 99} ."
        result = BaseAgent._extract_json_object(text)
        assert result == {"x": 99}

    def test_empty_object(self):
        result = BaseAgent._extract_json_object("{}")
        assert result == {}

    def test_unicode_value(self):
        result = BaseAgent._extract_json_object('{"city": "İstanbul"}')
        assert result is not None
        assert result["city"] == "İstanbul"

    def test_just_open_brace_returns_none(self):
        assert BaseAgent._extract_json_object("{") is None

    def test_unclosed_brace_returns_none(self):
        assert BaseAgent._extract_json_object('{"key": "val"') is None


# ---------------------------------------------------------------------------
# BaseAgent._extract_json_array
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _BA_OK, reason="base_agent import failed")
class TestExtractJsonArray:
    def test_plain_list(self):
        result = BaseAgent._extract_json_array("[1, 2, 3]")
        assert result == [1, 2, 3]

    def test_list_of_strings(self):
        result = BaseAgent._extract_json_array('["a", "b", "c"]')
        assert result == ["a", "b", "c"]

    def test_embedded_in_prose(self):
        text = 'The steps are: ["click", "type", "submit"] and done.'
        result = BaseAgent._extract_json_array(text)
        assert result == ["click", "type", "submit"]

    def test_list_of_dicts(self):
        text = '[{"id": 1}, {"id": 2}]'
        result = BaseAgent._extract_json_array(text)
        assert result == [{"id": 1}, {"id": 2}]

    def test_empty_list(self):
        result = BaseAgent._extract_json_array("[]")
        assert result == []

    def test_no_bracket_returns_none(self):
        assert BaseAgent._extract_json_array("no array here") is None

    def test_empty_string_returns_none(self):
        assert BaseAgent._extract_json_array("") is None

    def test_invalid_json_array_returns_none(self):
        assert BaseAgent._extract_json_array("[not valid") is None

    def test_nested_arrays(self):
        result = BaseAgent._extract_json_array("[[1, 2], [3, 4]]")
        assert result == [[1, 2], [3, 4]]

    def test_mixed_types(self):
        result = BaseAgent._extract_json_array('[1, "two", true, null]')
        assert result == [1, "two", True, None]

    def test_returns_list(self):
        assert isinstance(BaseAgent._extract_json_array("[1]"), list)

    def test_prefix_text_ignored(self):
        text = "Results: [10, 20, 30]"
        result = BaseAgent._extract_json_array(text)
        assert result == [10, 20, 30]

    def test_single_element(self):
        result = BaseAgent._extract_json_array('["only"]')
        assert result == ["only"]

    def test_unicode_elements(self):
        result = BaseAgent._extract_json_array('["Merhaba", "Dünya"]')
        assert result == ["Merhaba", "Dünya"]

    def test_multiple_arrays_with_gap_returns_none(self):
        # rfind("]") finds the last ], so the span [1, 2] extra text [3, 4]
        # fails to parse as JSON → None
        result = BaseAgent._extract_json_array('[1, 2] extra text [3, 4]')
        assert result is None


# ---------------------------------------------------------------------------
# AgentResult dataclass
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _BA_OK, reason="base_agent import failed")
class TestAgentResult:
    def test_required_fields(self):
        r = AgentResult(agent_name="TestAgent", success=True)
        assert r.agent_name == "TestAgent"
        assert r.success is True

    def test_success_false(self):
        r = AgentResult(agent_name="TestAgent", success=False)
        assert r.success is False

    def test_data_default_empty_dict(self):
        r = AgentResult(agent_name="TestAgent", success=True)
        assert r.data == {}

    def test_data_custom(self):
        r = AgentResult(agent_name="TestAgent", success=True, data={"key": "val"})
        assert r.data == {"key": "val"}

    def test_error_default_empty_string(self):
        r = AgentResult(agent_name="TestAgent", success=True)
        assert r.error == ""

    def test_error_custom(self):
        r = AgentResult(agent_name="TestAgent", success=False, error="Something went wrong")
        assert r.error == "Something went wrong"

    def test_duration_ms_default_zero(self):
        r = AgentResult(agent_name="TestAgent", success=True)
        assert r.duration_ms == 0

    def test_duration_ms_custom(self):
        r = AgentResult(agent_name="TestAgent", success=True, duration_ms=350)
        assert r.duration_ms == 350

    def test_tokens_used_default_zero(self):
        r = AgentResult(agent_name="TestAgent", success=True)
        assert r.tokens_used == 0

    def test_tokens_used_custom(self):
        r = AgentResult(agent_name="TestAgent", success=True, tokens_used=1024)
        assert r.tokens_used == 1024

    def test_data_instances_independent(self):
        # Mutable default should not be shared across instances
        r1 = AgentResult(agent_name="A", success=True)
        r2 = AgentResult(agent_name="B", success=True)
        r1.data["key"] = "value"
        assert "key" not in r2.data

    def test_is_dataclass_or_has_expected_attrs(self):
        r = AgentResult(agent_name="X", success=True)
        assert hasattr(r, "agent_name")
        assert hasattr(r, "success")
        assert hasattr(r, "data")
        assert hasattr(r, "error")
        assert hasattr(r, "duration_ms")
        assert hasattr(r, "tokens_used")

    def test_all_fields_set(self):
        r = AgentResult(
            agent_name="CompleteAgent",
            success=True,
            data={"result": [1, 2, 3]},
            error="",
            duration_ms=1500,
            tokens_used=2048,
        )
        assert r.agent_name == "CompleteAgent"
        assert r.success is True
        assert r.data == {"result": [1, 2, 3]}
        assert r.error == ""
        assert r.duration_ms == 1500
        assert r.tokens_used == 2048
