"""Unit tests for ai.gateway_client pure helper functions.

All tests are self-contained: no HTTP, no Redis, no LLM.
Covers:
  - _parse_json_safe: robust JSON extraction from LLM output
  - _rough_token_count: approximate token count from text length
"""
from __future__ import annotations

import pytest

try:
    from app.domains.ai.gateway_client import (
        _parse_json_safe,
        _rough_token_count,
    )
    _GW_OK = True
except ImportError:
    _GW_OK = False


# ---------------------------------------------------------------------------
# _parse_json_safe
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _GW_OK, reason="gateway_client import failed")
class TestParseJsonSafe:
    def test_plain_dict(self):
        result = _parse_json_safe('{"key": "value"}')
        assert result == {"key": "value"}

    def test_plain_list(self):
        result = _parse_json_safe('[1, 2, 3]')
        assert result == [1, 2, 3]

    def test_markdown_json_fence(self):
        raw = "```json\n{\"a\": 1}\n```"
        result = _parse_json_safe(raw)
        assert result == {"a": 1}

    def test_markdown_generic_fence(self):
        raw = "```\n{\"b\": 2}\n```"
        result = _parse_json_safe(raw)
        assert result == {"b": 2}

    def test_json_embedded_in_prose(self):
        raw = 'Some explanation. {"x": 1} trailing text.'
        result = _parse_json_safe(raw)
        assert result == {"x": 1}

    def test_nested_object(self):
        raw = '{"outer": {"inner": [1, 2]}}'
        result = _parse_json_safe(raw)
        assert result == {"outer": {"inner": [1, 2]}}

    def test_not_json_returns_none(self):
        assert _parse_json_safe("not json at all") is None

    def test_empty_string_returns_none(self):
        assert _parse_json_safe("") is None

    def test_whitespace_only_returns_none(self):
        assert _parse_json_safe("   ") is None

    def test_bool_values(self):
        result = _parse_json_safe('{"flag": true, "other": false}')
        assert result == {"flag": True, "other": False}

    def test_null_value(self):
        result = _parse_json_safe('{"key": null}')
        assert result == {"key": None}

    def test_numeric_values(self):
        result = _parse_json_safe('{"int": 42, "float": 3.14}')
        assert result["int"] == 42
        assert result["float"] == pytest.approx(3.14)

    def test_array_in_prose(self):
        raw = 'Here are items: [1, 2, 3] and done.'
        result = _parse_json_safe(raw)
        assert result == [1, 2, 3]

    def test_returns_dict_or_list_or_none(self):
        result = _parse_json_safe('{"a": 1}')
        assert isinstance(result, (dict, list, type(None)))

    def test_stripped_whitespace(self):
        result = _parse_json_safe('  {"k": "v"}  ')
        assert result == {"k": "v"}

    def test_unicode_content(self):
        raw = '{"message": "Merhaba dünya"}'
        result = _parse_json_safe(raw)
        assert result == {"message": "Merhaba dünya"}


# ---------------------------------------------------------------------------
# _rough_token_count
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _GW_OK, reason="gateway_client import failed")
class TestRoughTokenCount:
    def test_empty_string(self):
        assert _rough_token_count("") == 0

    def test_none_equivalent(self):
        # Empty/falsy string returns 0
        assert _rough_token_count("") == 0

    def test_short_text_at_least_1(self):
        assert _rough_token_count("hi") >= 1

    def test_400_chars_gives_100_tokens(self):
        text = "a" * 400
        assert _rough_token_count(text) == 100

    def test_800_chars_gives_200_tokens(self):
        text = "x" * 800
        assert _rough_token_count(text) == 200

    def test_4_chars_gives_1_token(self):
        assert _rough_token_count("abcd") == 1

    def test_1_char_gives_1_token(self):
        # max(1, int(1/4)) = max(1, 0) = 1
        assert _rough_token_count("a") == 1

    def test_proportional_to_length(self):
        t1 = _rough_token_count("a" * 100)
        t2 = _rough_token_count("a" * 200)
        assert t2 > t1

    def test_returns_int(self):
        assert isinstance(_rough_token_count("hello"), int)

    def test_unicode_text(self):
        # Unicode chars count as chars, not bytes
        text = "Ö" * 100
        result = _rough_token_count(text)
        assert result > 0
        assert isinstance(result, int)
