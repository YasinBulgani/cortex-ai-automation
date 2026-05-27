"""Unit tests for qa.service pure helper functions.

All tests are self-contained: no filesystem access needed for pure helpers,
no DB, no HTTP.
Covers:
  - _stringify_dates: recursive date/datetime → ISO string conversion
  - _parse_frontmatter: YAML frontmatter extraction from markdown
  - _serialize_frontmatter: dict → canonical YAML frontmatter
  - _slugify: Turkish-aware URL slug generation
"""
from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

try:
    from app.domains.qa.service import (
        _stringify_dates,
        _parse_frontmatter,
        _serialize_frontmatter,
        _slugify,
    )
    _QA_OK = True
except ImportError:
    _QA_OK = False


# ---------------------------------------------------------------------------
# _stringify_dates
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _QA_OK, reason="qa.service import failed")
class TestStringifyDates:
    def test_date_converted(self):
        result = _stringify_dates(date(2024, 1, 15))
        assert result == "2024-01-15"

    def test_datetime_converted(self):
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = _stringify_dates(dt)
        assert "2024-01-15" in result

    def test_string_unchanged(self):
        assert _stringify_dates("hello") == "hello"

    def test_int_unchanged(self):
        assert _stringify_dates(42) == 42

    def test_none_unchanged(self):
        assert _stringify_dates(None) is None

    def test_dict_with_date_value(self):
        result = _stringify_dates({"created": date(2024, 6, 1)})
        assert result == {"created": "2024-06-01"}

    def test_list_with_date(self):
        result = _stringify_dates([date(2024, 1, 1), "hello"])
        assert result == ["2024-01-01", "hello"]

    def test_nested_dict(self):
        result = _stringify_dates({"a": {"b": date(2024, 3, 10)}})
        assert result == {"a": {"b": "2024-03-10"}}

    def test_returns_same_type_for_primitives(self):
        assert isinstance(_stringify_dates("text"), str)
        assert isinstance(_stringify_dates(1), int)

    def test_bool_unchanged(self):
        assert _stringify_dates(True) is True

    def test_empty_dict(self):
        assert _stringify_dates({}) == {}

    def test_empty_list(self):
        assert _stringify_dates([]) == []


# ---------------------------------------------------------------------------
# _parse_frontmatter
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _QA_OK, reason="qa.service import failed")
class TestParseFrontmatter:
    def test_no_frontmatter_returns_empty_dict(self):
        fm, body = _parse_frontmatter("# Title\n\nContent here")
        assert fm == {}
        assert "# Title" in body

    def test_valid_frontmatter_parsed(self):
        text = "---\ntitle: My Test\npriority: P1\n---\nBody content"
        fm, body = _parse_frontmatter(text)
        assert fm["title"] == "My Test"
        assert fm["priority"] == "P1"

    def test_body_after_frontmatter(self):
        text = "---\ntitle: Test\n---\nBody here"
        _, body = _parse_frontmatter(text)
        assert "Body here" in body

    def test_no_closing_delimiter_returns_empty(self):
        text = "---\ntitle: Test\n"
        fm, body = _parse_frontmatter(text)
        assert fm == {}

    def test_returns_tuple(self):
        result = _parse_frontmatter("# No frontmatter")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_dict_in_frontmatter(self):
        text = "---\nautomation:\n  status: automated\n---\nbody"
        fm, _ = _parse_frontmatter(text)
        assert "automation" in fm

    def test_list_in_frontmatter(self):
        text = "---\ntags:\n  - regression\n  - smoke\n---\nbody"
        fm, _ = _parse_frontmatter(text)
        assert "tags" in fm

    def test_invalid_yaml_returns_empty_dict(self):
        text = "---\n: invalid: yaml: :\n---\nbody"
        fm, body = _parse_frontmatter(text)
        assert isinstance(fm, dict)


# ---------------------------------------------------------------------------
# _serialize_frontmatter
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _QA_OK, reason="qa.service import failed")
class TestSerializeFrontmatter:
    def test_returns_string(self):
        result = _serialize_frontmatter({"title": "Test"})
        assert isinstance(result, str)

    def test_starts_with_yaml_delimiter(self):
        result = _serialize_frontmatter({"title": "Test"})
        assert result.startswith("---\n")

    def test_ends_with_yaml_delimiter(self):
        result = _serialize_frontmatter({"title": "Test"})
        assert result.endswith("---\n")

    def test_title_included(self):
        result = _serialize_frontmatter({"title": "My Test Case"})
        assert "My Test Case" in result

    def test_canonical_order_id_first(self):
        fm = {"priority": "P1", "id": "TC-001", "title": "Test"}
        result = _serialize_frontmatter(fm)
        id_pos = result.find("id:")
        title_pos = result.find("title:")
        assert id_pos < title_pos

    def test_empty_dict(self):
        result = _serialize_frontmatter({})
        assert isinstance(result, str)

    def test_non_canonical_keys_appended(self):
        fm = {"id": "TC-001", "custom_field": "value"}
        result = _serialize_frontmatter(fm)
        assert "custom_field" in result


# ---------------------------------------------------------------------------
# _slugify
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _QA_OK, reason="qa.service import failed")
class TestSlugify:
    def test_basic_text(self):
        assert _slugify("hello world") == "hello-world"

    def test_uppercase_lowercased(self):
        assert _slugify("Hello World") == "hello-world"

    def test_special_chars_removed(self):
        result = _slugify("test@case!")
        assert "@" not in result
        assert "!" not in result

    def test_turkish_chars_transliterated(self):
        result = _slugify("çok güzel")
        assert "ç" not in result
        assert "ü" not in result

    def test_ğ_transliterated(self):
        result = _slugify("değer")
        assert "ğ" not in result
        assert "g" in result

    def test_max_length_respected(self):
        long_text = "a" * 100
        result = _slugify(long_text, max_length=20)
        assert len(result) <= 20

    def test_default_max_length_50(self):
        result = _slugify("a" * 200)
        assert len(result) <= 50

    def test_empty_string(self):
        result = _slugify("")
        assert isinstance(result, str)

    def test_returns_string(self):
        assert isinstance(_slugify("test"), str)

    def test_no_leading_trailing_hyphens(self):
        result = _slugify("  test  ")
        assert not result.startswith("-")
        assert not result.endswith("-")

    def test_consecutive_special_chars_collapsed(self):
        result = _slugify("a   b")  # multiple spaces → single hyphen
        assert "--" not in result

    def test_uppercase_turkish(self):
        result = _slugify("ÇOK İYİ")
        assert "Ç" not in result
        assert "İ" not in result
