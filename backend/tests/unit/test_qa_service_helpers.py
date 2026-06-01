"""Unit tests for QA service pure helper functions.

Tests app/domains/qa/service.py — pure, filesystem-free helpers.
Covers: _stringify_dates, _parse_frontmatter, _serialize_frontmatter, _slugify.
"""

from __future__ import annotations

import textwrap
from datetime import date, datetime, time

import pytest

from app.domains.qa.service import (
    _parse_frontmatter,
    _serialize_frontmatter,
    _slugify,
    _stringify_dates,
)


# ── _stringify_dates ──────────────────────────────────────────────────────────


class TestStringifyDates:
    def test_passthrough_string(self) -> None:
        assert _stringify_dates("hello") == "hello"

    def test_passthrough_int(self) -> None:
        assert _stringify_dates(42) == 42

    def test_passthrough_none(self) -> None:
        assert _stringify_dates(None) is None

    def test_date_converted(self) -> None:
        d = date(2024, 1, 15)
        result = _stringify_dates(d)
        assert result == "2024-01-15"

    def test_datetime_converted(self) -> None:
        dt = datetime(2024, 6, 20, 10, 30, 0)
        result = _stringify_dates(dt)
        assert result == "2024-06-20T10:30:00"

    def test_time_converted(self) -> None:
        t = time(14, 45, 0)
        result = _stringify_dates(t)
        assert result == "14:45:00"

    def test_dict_recursion(self) -> None:
        d = {"created": date(2024, 3, 1), "title": "test", "count": 5}
        result = _stringify_dates(d)
        assert result["created"] == "2024-03-01"
        assert result["title"] == "test"
        assert result["count"] == 5

    def test_list_recursion(self) -> None:
        lst = [date(2024, 1, 1), "string", 99]
        result = _stringify_dates(lst)
        assert result[0] == "2024-01-01"
        assert result[1] == "string"
        assert result[2] == 99

    def test_nested_dict_with_list(self) -> None:
        data = {
            "dates": [date(2024, 1, 1), date(2024, 2, 2)],
            "meta": {"updated": date(2024, 3, 3)},
        }
        result = _stringify_dates(data)
        assert result["dates"] == ["2024-01-01", "2024-02-02"]
        assert result["meta"]["updated"] == "2024-03-03"

    def test_empty_dict(self) -> None:
        assert _stringify_dates({}) == {}

    def test_empty_list(self) -> None:
        assert _stringify_dates([]) == []


# ── _parse_frontmatter ────────────────────────────────────────────────────────


class TestParseFrontmatter:
    def test_basic_frontmatter(self) -> None:
        text = "---\nid: TC-001\ntitle: Login Test\n---\n## Body\ntest steps"
        fm, body = _parse_frontmatter(text)
        assert fm["id"] == "TC-001"
        assert fm["title"] == "Login Test"
        assert "## Body" in body
        assert "test steps" in body

    def test_no_frontmatter_returns_empty_dict(self) -> None:
        text = "# Just a markdown file\nNo frontmatter here."
        fm, body = _parse_frontmatter(text)
        assert fm == {}
        assert body == text

    def test_frontmatter_without_closing_marker(self) -> None:
        text = "---\nid: TC-001\ntitle: Incomplete"
        fm, body = _parse_frontmatter(text)
        assert fm == {}
        assert body == text

    def test_empty_frontmatter(self) -> None:
        text = "---\n---\n## Body"
        fm, body = _parse_frontmatter(text)
        assert isinstance(fm, dict)
        assert "## Body" in body

    def test_numeric_values(self) -> None:
        text = "---\nid: TC-010\nestimated_minutes: 30\n---\nbody"
        fm, body = _parse_frontmatter(text)
        assert fm["estimated_minutes"] == 30

    def test_boolean_values(self) -> None:
        text = "---\nid: TC-020\nautomation:\n  enabled: true\n---\nbody"
        fm, body = _parse_frontmatter(text)
        assert fm["automation"]["enabled"] is True

    def test_list_values(self) -> None:
        text = "---\nid: TC-030\ntags:\n  - smoke\n  - login\n---\nbody"
        fm, body = _parse_frontmatter(text)
        assert fm["tags"] == ["smoke", "login"]

    def test_body_after_frontmatter_preserved(self) -> None:
        text = "---\nid: TC-040\n---\nLine 1\nLine 2\n## Steps\n- Step A"
        fm, body = _parse_frontmatter(text)
        assert "Line 1" in body
        assert "Line 2" in body
        assert "## Steps" in body
        assert "- Step A" in body

    def test_invalid_yaml_returns_empty_dict(self) -> None:
        text = "---\n: this: is: broken:\n  yaml: [unclosed\n---\nbody"
        fm, body = _parse_frontmatter(text)
        assert fm == {}

    def test_date_converted_to_string(self) -> None:
        """YAML dates like 2024-01-15 should be converted to string."""
        text = "---\nid: TC-050\ncreated: 2024-01-15\n---\nbody"
        fm, body = _parse_frontmatter(text)
        # After conversion, created should be a string, not date object
        assert isinstance(fm["created"], str)


# ── _serialize_frontmatter ────────────────────────────────────────────────────


class TestSerializeFrontmatter:
    def test_produces_yaml_block(self) -> None:
        fm = {"id": "TC-001", "title": "Login Test"}
        result = _serialize_frontmatter(fm)
        assert result.startswith("---\n")
        assert result.endswith("---\n")

    def test_canonical_order_id_first(self) -> None:
        fm = {"title": "T", "id": "TC-001", "suite": "auth"}
        result = _serialize_frontmatter(fm)
        lines = result.split("\n")
        id_line = next(i for i, l in enumerate(lines) if l.startswith("id:"))
        title_line = next(i for i, l in enumerate(lines) if l.startswith("title:"))
        suite_line = next(i for i, l in enumerate(lines) if l.startswith("suite:"))
        assert id_line < title_line < suite_line

    def test_roundtrip_basic(self) -> None:
        import yaml
        fm = {"id": "TC-002", "title": "Checkout", "priority": "P1", "status": "active"}
        serialized = _serialize_frontmatter(fm)
        # Strip the "---\n" delimiters and parse back
        inner = serialized[4:-4]  # Remove leading "---\n" and trailing "---\n"
        parsed = yaml.safe_load(inner) or {}
        assert parsed["id"] == "TC-002"
        assert parsed["title"] == "Checkout"
        assert parsed["priority"] == "P1"

    def test_extra_keys_appended_after_canonical(self) -> None:
        fm = {"id": "TC-003", "custom_key": "value"}
        result = _serialize_frontmatter(fm)
        id_pos = result.index("id:")
        custom_pos = result.index("custom_key:")
        assert id_pos < custom_pos

    def test_unicode_preserved(self) -> None:
        fm = {"id": "TC-004", "title": "Giriş Testi — ödeme"}
        result = _serialize_frontmatter(fm)
        assert "Giriş Testi" in result
        assert "ödeme" in result

    def test_list_value(self) -> None:
        fm = {"id": "TC-005", "tags": ["smoke", "login", "auth"]}
        result = _serialize_frontmatter(fm)
        assert "smoke" in result
        assert "login" in result

    def test_empty_frontmatter(self) -> None:
        result = _serialize_frontmatter({})
        assert result.startswith("---\n")
        assert result.endswith("---\n")

    def test_nested_dict(self) -> None:
        fm = {"id": "TC-006", "automation": {"status": "automated", "framework": "playwright"}}
        result = _serialize_frontmatter(fm)
        assert "automation:" in result
        assert "status:" in result


# ── _slugify ──────────────────────────────────────────────────────────────────


class TestSlugify:
    def test_basic_english(self) -> None:
        assert _slugify("Login Test") == "login-test"

    def test_spaces_to_hyphens(self) -> None:
        assert _slugify("Hello World") == "hello-world"

    def test_special_chars_removed(self) -> None:
        result = _slugify("Test: user@login!")
        assert "@" not in result
        assert ":" not in result
        assert "!" not in result

    def test_turkish_chars_transliterated(self) -> None:
        result = _slugify("Çıkış Giriş")
        assert "ç" not in result.lower()
        assert "ı" not in result.lower()
        # ç → c, ı → i
        assert "c" in result
        assert "i" in result

    def test_turkish_extended(self) -> None:
        result = _slugify("Ödeme şifresi üye")
        # ö→o, ş→s, ü→u
        assert "ö" not in result
        assert "ş" not in result
        assert "ü" not in result
        assert "o" in result or "s" in result or "u" in result

    def test_max_length_default(self) -> None:
        long_text = "a" * 100
        result = _slugify(long_text)
        assert len(result) <= 50

    def test_max_length_custom(self) -> None:
        result = _slugify("hello world foo bar baz", max_length=10)
        assert len(result) <= 10

    def test_no_trailing_hyphen(self) -> None:
        result = _slugify("hello world---")
        assert not result.endswith("-")

    def test_no_leading_hyphen(self) -> None:
        result = _slugify("---hello")
        assert not result.startswith("-")

    def test_multiple_spaces_become_one_hyphen(self) -> None:
        result = _slugify("hello   world")
        assert "--" not in result
        assert "hello-world" == result

    def test_empty_string(self) -> None:
        result = _slugify("")
        assert result == ""

    def test_only_special_chars(self) -> None:
        result = _slugify("!!!###")
        assert result == ""

    def test_numbers_preserved(self) -> None:
        result = _slugify("Test Case 001")
        assert "001" in result

    def test_uppercase_lowercased(self) -> None:
        result = _slugify("UPPER CASE")
        assert result == result.lower()
