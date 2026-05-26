"""Unit tests for health service, auth service and QA service pure helpers.

No DB, no HTTP, no LLM — pure Python only.

Covers:
  app/domains/health/service.py:
    _compute_overall
  app/domains/auth/service.py:
    _sha256_token, _utc_ts
  app/domains/qa/service.py:
    _stringify_dates, _parse_frontmatter, _serialize_frontmatter, _slugify
  app/domains/tspm/test_case_service.py (already covered separately)
"""

from __future__ import annotations

import hashlib
import time
from datetime import date, datetime, timezone

import pytest

from app.domains.health.schemas import ComponentStatus, HealthLevel
from app.domains.health.service import _compute_overall
from app.domains.auth.service import _sha256_token, _utc_ts
from app.domains.qa.service import (
    _parse_frontmatter,
    _serialize_frontmatter,
    _slugify,
    _stringify_dates,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _cs(level: HealthLevel, optional: bool = False, name: str = "svc") -> ComponentStatus:
    return ComponentStatus(name=name, label=name.title(), level=level, optional=optional)


# ── _compute_overall ──────────────────────────────────────────────────────────


class TestComputeOverall:
    def test_all_ok_returns_ok(self) -> None:
        components = [_cs(HealthLevel.ok), _cs(HealthLevel.ok)]
        assert _compute_overall(components) == HealthLevel.ok

    def test_one_required_down_returns_down(self) -> None:
        components = [_cs(HealthLevel.ok), _cs(HealthLevel.down)]
        assert _compute_overall(components) == HealthLevel.down

    def test_one_required_degraded_returns_degraded(self) -> None:
        components = [_cs(HealthLevel.ok), _cs(HealthLevel.degraded)]
        assert _compute_overall(components) == HealthLevel.degraded

    def test_down_beats_degraded(self) -> None:
        components = [_cs(HealthLevel.degraded), _cs(HealthLevel.down)]
        assert _compute_overall(components) == HealthLevel.down

    def test_optional_down_still_degraded(self) -> None:
        # Optional component is down but no required down → degraded not down
        components = [_cs(HealthLevel.ok), _cs(HealthLevel.down, optional=True)]
        result = _compute_overall(components)
        assert result == HealthLevel.degraded

    def test_optional_down_no_required_issues(self) -> None:
        # All required are ok, optional is down → degraded (visual cue)
        required = [_cs(HealthLevel.ok, optional=False, name="db")]
        optional = [_cs(HealthLevel.down, optional=True, name="ollama")]
        result = _compute_overall(required + optional)
        assert result == HealthLevel.degraded

    def test_empty_list_returns_ok(self) -> None:
        assert _compute_overall([]) == HealthLevel.ok

    def test_all_optional_down_returns_degraded(self) -> None:
        components = [_cs(HealthLevel.down, optional=True)]
        assert _compute_overall(components) == HealthLevel.degraded

    def test_returns_health_level_enum(self) -> None:
        result = _compute_overall([_cs(HealthLevel.ok)])
        assert isinstance(result, HealthLevel)


# ── _sha256_token ─────────────────────────────────────────────────────────────


class TestSha256Token:
    def test_returns_hex_string(self) -> None:
        result = _sha256_token("test_token")
        assert isinstance(result, str)
        assert len(result) == 64  # SHA-256 hex = 64 chars

    def test_deterministic(self) -> None:
        token = "my_secret_token_abc123"
        assert _sha256_token(token) == _sha256_token(token)

    def test_different_tokens_different_hash(self) -> None:
        assert _sha256_token("token_a") != _sha256_token("token_b")

    def test_matches_standard_sha256(self) -> None:
        token = "test_value"
        expected = hashlib.sha256(token.encode("utf-8")).hexdigest()
        assert _sha256_token(token) == expected

    def test_empty_string(self) -> None:
        result = _sha256_token("")
        assert len(result) == 64

    def test_unicode_token(self) -> None:
        result = _sha256_token("tökén_üñïcödé")
        assert len(result) == 64


# ── _utc_ts ───────────────────────────────────────────────────────────────────


class TestUtcTs:
    def test_returns_int(self) -> None:
        assert isinstance(_utc_ts(), int)

    def test_positive_value(self) -> None:
        assert _utc_ts() > 0

    def test_approximately_now(self) -> None:
        now = int(time.time())
        result = _utc_ts()
        assert abs(result - now) < 5  # within 5 seconds

    def test_monotonically_increasing(self) -> None:
        t1 = _utc_ts()
        t2 = _utc_ts()
        assert t2 >= t1


# ── _stringify_dates ──────────────────────────────────────────────────────────


class TestStringifyDates:
    def test_datetime_converted_to_iso(self) -> None:
        dt = datetime(2024, 1, 15, 12, 30, 0, tzinfo=timezone.utc)
        result = _stringify_dates(dt)
        assert isinstance(result, str)
        assert "2024-01-15" in result

    def test_date_converted_to_iso(self) -> None:
        d = date(2024, 6, 15)
        result = _stringify_dates(d)
        assert result == "2024-06-15"

    def test_string_unchanged(self) -> None:
        assert _stringify_dates("hello") == "hello"

    def test_int_unchanged(self) -> None:
        assert _stringify_dates(42) == 42

    def test_none_unchanged(self) -> None:
        assert _stringify_dates(None) is None

    def test_dict_with_dates_converted(self) -> None:
        d = date(2024, 3, 1)
        result = _stringify_dates({"created": d, "name": "test"})
        assert isinstance(result["created"], str)
        assert result["name"] == "test"

    def test_list_with_dates_converted(self) -> None:
        d = date(2024, 1, 1)
        result = _stringify_dates([d, "text", 42])
        assert isinstance(result[0], str)
        assert result[1] == "text"
        assert result[2] == 42

    def test_nested_dict(self) -> None:
        d = date(2024, 12, 31)
        result = _stringify_dates({"meta": {"date": d}})
        assert isinstance(result["meta"]["date"], str)


# ── _parse_frontmatter ────────────────────────────────────────────────────────


class TestParseFrontmatter:
    def test_valid_frontmatter(self) -> None:
        text = "---\ntitle: Test Case\npriority: high\n---\nBody text here"
        fm, body = _parse_frontmatter(text)
        assert fm["title"] == "Test Case"
        assert fm["priority"] == "high"
        assert body.strip() == "Body text here"

    def test_no_frontmatter_returns_empty_dict(self) -> None:
        text = "Just plain text without frontmatter"
        fm, body = _parse_frontmatter(text)
        assert fm == {}
        assert body == text

    def test_empty_frontmatter(self) -> None:
        text = "---\n---\nBody only"
        fm, body = _parse_frontmatter(text)
        assert isinstance(fm, dict)

    def test_incomplete_frontmatter_no_closing(self) -> None:
        text = "---\ntitle: Test\nNo closing delimiter"
        fm, body = _parse_frontmatter(text)
        assert fm == {}

    def test_returns_tuple_of_dict_and_str(self) -> None:
        text = "---\nkey: val\n---\nbody"
        result = _parse_frontmatter(text)
        assert isinstance(result, tuple)
        assert isinstance(result[0], dict)
        assert isinstance(result[1], str)

    def test_numeric_value(self) -> None:
        text = "---\nestimated_minutes: 30\n---\nbody"
        fm, _ = _parse_frontmatter(text)
        assert fm["estimated_minutes"] == 30

    def test_list_value(self) -> None:
        text = "---\ntags:\n  - smoke\n  - login\n---\nbody"
        fm, _ = _parse_frontmatter(text)
        assert "smoke" in fm.get("tags", [])


# ── _serialize_frontmatter ────────────────────────────────────────────────────


class TestSerializeFrontmatter:
    def test_returns_string(self) -> None:
        result = _serialize_frontmatter({"title": "My Test"})
        assert isinstance(result, str)

    def test_contains_key_value(self) -> None:
        result = _serialize_frontmatter({"title": "Login Test"})
        assert "title" in result
        assert "Login Test" in result

    def test_canonical_order_id_first(self) -> None:
        fm = {"priority": "high", "id": "tc-001", "title": "Test"}
        result = _serialize_frontmatter(fm)
        id_pos = result.find("id:")
        title_pos = result.find("title:")
        assert id_pos < title_pos

    def test_extra_keys_appended(self) -> None:
        fm = {"custom_key": "value", "id": "tc-001"}
        result = _serialize_frontmatter(fm)
        assert "custom_key" in result

    def test_empty_dict(self) -> None:
        result = _serialize_frontmatter({})
        assert isinstance(result, str)


# ── _slugify ──────────────────────────────────────────────────────────────────


class TestSlugify:
    def test_basic_lowercase(self) -> None:
        assert _slugify("Hello World") == "hello-world"

    def test_turkish_chars_transliterated(self) -> None:
        result = _slugify("Çalışan Öğrenci")
        assert result == "calisan-ogrenci"

    def test_special_chars_become_dashes(self) -> None:
        result = _slugify("test: value / 123")
        assert "-" in result
        assert ":" not in result

    def test_max_length_truncated(self) -> None:
        long = "a" * 100
        result = _slugify(long, max_length=20)
        assert len(result) <= 20

    def test_no_leading_trailing_dashes(self) -> None:
        result = _slugify("  hello  ")
        assert not result.startswith("-")
        assert not result.endswith("-")

    def test_empty_string(self) -> None:
        result = _slugify("")
        assert result == ""

    def test_returns_string(self) -> None:
        assert isinstance(_slugify("test"), str)

    def test_numbers_preserved(self) -> None:
        result = _slugify("test 123 case")
        assert "123" in result

    def test_multiple_separators_collapsed(self) -> None:
        result = _slugify("hello---world")
        assert "--" not in result
