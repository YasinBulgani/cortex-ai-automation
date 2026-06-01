"""Unit tests for app.domains.ai.tools and workflow_excel pure helpers.

Tests are fully self-contained: no DB, no HTTP.
Covers: tools — list_tools, tool_names, ToolSpec, _TOOLS, openai_tools_payload;
        workflow_excel — _cell, _dicts, _json.
"""
from __future__ import annotations

import pytest

try:
    from app.domains.ai.tools import (
        list_tools,
        tool_names,
        ToolSpec,
        _TOOLS,
        openai_tools_payload,
    )
    from app.domains.ai.workflow_excel import (
        _cell,
        _dicts,
        _json,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="tools/workflow_excel import failed")


# ---------------------------------------------------------------------------
# _TOOLS constant / list_tools / tool_names
# ---------------------------------------------------------------------------

class TestTools:
    def test_list_tools_returns_list(self):
        assert isinstance(list_tools(), list)

    def test_tool_names_returns_list(self):
        assert isinstance(tool_names(), list)

    def test_known_tool_names(self):
        names = tool_names()
        assert "get_project_stats" in names
        assert "get_recent_failures" in names
        assert "list_scenarios" in names

    def test_list_tools_and_tool_names_same_count(self):
        assert len(list_tools()) == len(tool_names())

    def test_each_tool_spec_has_name(self):
        for spec in list_tools():
            assert isinstance(spec.name, str) and spec.name

    def test_each_tool_spec_has_description(self):
        for spec in list_tools():
            assert isinstance(spec.description, str) and spec.description

    def test_each_tool_spec_has_schema_cls(self):
        for spec in list_tools():
            assert spec.schema_cls is not None

    def test_each_tool_spec_has_handler(self):
        for spec in list_tools():
            assert callable(spec.handler)

    def test_tools_dict_nonempty(self):
        assert len(_TOOLS) >= 4


# ---------------------------------------------------------------------------
# openai_tools_payload
# ---------------------------------------------------------------------------

class TestOpenAIToolsPayload:
    def test_returns_list(self):
        result = openai_tools_payload()
        assert isinstance(result, list)

    def test_each_has_type_function(self):
        for tool in openai_tools_payload():
            assert tool.get("type") == "function"

    def test_each_has_function_dict(self):
        for tool in openai_tools_payload():
            assert isinstance(tool.get("function"), dict)

    def test_function_has_name(self):
        for tool in openai_tools_payload():
            func = tool["function"]
            assert "name" in func and func["name"]

    def test_function_has_description(self):
        for tool in openai_tools_payload():
            func = tool["function"]
            assert "description" in func

    def test_function_has_parameters(self):
        for tool in openai_tools_payload():
            func = tool["function"]
            assert "parameters" in func


# ---------------------------------------------------------------------------
# ToolSpec dataclass
# ---------------------------------------------------------------------------

class TestToolSpec:
    def test_can_instantiate(self):
        from pydantic import BaseModel
        class M(BaseModel):
            x: int

        spec = ToolSpec(name="test", description="desc", schema_cls=M, handler=lambda a: {})
        assert spec.name == "test"

    def test_fields_accessible(self):
        spec = list_tools()[0]
        assert spec.name
        assert spec.description
        assert spec.schema_cls
        assert callable(spec.handler)


# ---------------------------------------------------------------------------
# _cell (workflow_excel)
# ---------------------------------------------------------------------------

class TestCell:
    def test_dict_converted_to_json_string(self):
        result = _cell({"key": "value"})
        assert isinstance(result, str)
        assert "key" in result

    def test_list_converted_to_json_string(self):
        result = _cell([1, 2, 3])
        assert isinstance(result, str)
        assert "1" in result

    def test_tuple_converted_to_json_string(self):
        result = _cell((1, "a"))
        assert isinstance(result, str)

    def test_string_passthrough(self):
        assert _cell("hello") == "hello"

    def test_int_passthrough(self):
        assert _cell(42) == 42

    def test_none_passthrough(self):
        assert _cell(None) is None

    def test_float_passthrough(self):
        assert _cell(3.14) == 3.14


# ---------------------------------------------------------------------------
# _dicts (workflow_excel)
# ---------------------------------------------------------------------------

class TestDicts:
    def test_list_of_dicts_returned(self):
        result = _dicts([{"a": 1}, {"b": 2}])
        assert result == [{"a": 1}, {"b": 2}]

    def test_non_list_returns_empty(self):
        assert _dicts("not a list") == []
        assert _dicts(42) == []
        assert _dicts(None) == []

    def test_mixed_list_filters_non_dicts(self):
        result = _dicts([{"a": 1}, "string", 42, {"b": 2}])
        assert result == [{"a": 1}, {"b": 2}]

    def test_empty_list_returns_empty(self):
        assert _dicts([]) == []

    def test_returns_list(self):
        assert isinstance(_dicts([{"x": 1}]), list)


# ---------------------------------------------------------------------------
# _json (workflow_excel)
# ---------------------------------------------------------------------------

class TestJson:
    def test_none_returns_empty_string(self):
        assert _json(None) == ""

    def test_dict_serialized(self):
        import json
        result = _json({"key": "value"})
        assert json.loads(result) == {"key": "value"}

    def test_list_serialized(self):
        import json
        result = _json([1, 2, 3])
        assert json.loads(result) == [1, 2, 3]

    def test_unicode_preserved(self):
        result = _json({"name": "Türkçe"})
        assert "Türkçe" in result

    def test_returns_string(self):
        assert isinstance(_json({"x": 1}), str)

    def test_unserializable_falls_back_to_str(self):
        class NotSerializable:
            def __str__(self):
                return "repr_value"
        result = _json({"obj": NotSerializable()})
        assert isinstance(result, str)

    def test_integer_serialized(self):
        result = _json(42)
        assert result == "42"
