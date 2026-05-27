"""Unit tests for app.domains.migration.assistant — pure helpers.

Tests are fully self-contained: no DB, no HTTP, no file I/O.
Covers: _slugify, MigrationResult.success_rate/to_dict,
        MigratedStep / UnhandledStep dataclasses,
        migrate_source (unsupported framework raises ValueError).
"""
from __future__ import annotations

import pytest

try:
    from app.domains.migration.assistant import (
        _slugify,
        MigratedStep,
        UnhandledStep,
        MigrationResult,
        migrate_source,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="migration.assistant import failed")


# ---------------------------------------------------------------------------
# _slugify
# ---------------------------------------------------------------------------

class TestSlugify:
    def test_camelcase_split(self):
        result = _slugify("camelCaseWord")
        assert "camel" in result
        assert "case" in result

    def test_underscores_replaced_with_spaces(self):
        result = _slugify("snake_case_name")
        assert "_" not in result
        assert "snake" in result

    def test_lowercased(self):
        result = _slugify("UPPER_CASE")
        assert result == result.lower()

    def test_multiple_spaces_collapsed(self):
        result = _slugify("too   many  spaces")
        assert "  " not in result

    def test_returns_string(self):
        assert isinstance(_slugify("test"), str)

    def test_empty_string(self):
        result = _slugify("")
        assert isinstance(result, str)

    def test_strips_leading_trailing(self):
        result = _slugify("  padded  ")
        assert not result.startswith(" ")
        assert not result.endswith(" ")


# ---------------------------------------------------------------------------
# MigratedStep dataclass
# ---------------------------------------------------------------------------

class TestMigratedStep:
    def test_can_instantiate(self):
        step = MigratedStep(
            original='@When("user clicks button")',
            gherkin_keyword="When",
            gherkin_pattern="user clicks button",
            translated_code="await page.click('[data-testid=\"button\"]');",
        )
        assert step.gherkin_keyword == "When"

    def test_default_mapped_none(self):
        step = MigratedStep(
            original="x",
            gherkin_keyword="Given",
            gherkin_pattern="pat",
            translated_code="code",
        )
        assert step.mapped_to_dsl_action is None

    def test_default_notes_empty(self):
        step = MigratedStep(
            original="x",
            gherkin_keyword="Then",
            gherkin_pattern="pat",
            translated_code="code",
        )
        assert step.notes == ""

    def test_with_dsl_action(self):
        step = MigratedStep(
            original="x",
            gherkin_keyword="When",
            gherkin_pattern="pat",
            translated_code="code",
            mapped_to_dsl_action="click_element",
        )
        assert step.mapped_to_dsl_action == "click_element"


# ---------------------------------------------------------------------------
# UnhandledStep dataclass
# ---------------------------------------------------------------------------

class TestUnhandledStep:
    def test_can_instantiate(self):
        step = UnhandledStep(
            original="@When(\"complex pattern\")",
            reason="Pattern eşleşmesi yok",
        )
        assert "complex" in step.original

    def test_default_line_hint_none(self):
        step = UnhandledStep(original="x", reason="r")
        assert step.line_hint is None

    def test_with_line_hint(self):
        step = UnhandledStep(original="x", reason="r", line_hint=42)
        assert step.line_hint == 42


# ---------------------------------------------------------------------------
# MigrationResult.success_rate / to_dict
# ---------------------------------------------------------------------------

class TestMigrationResult:
    def test_default_success_rate_zero(self):
        result = MigrationResult(source_framework="selenium-java")
        assert result.success_rate == 0.0

    def test_success_rate_100_percent(self):
        result = MigrationResult(
            source_framework="selenium-java",
            steps_migrated=10,
            steps_total=10,
        )
        assert result.success_rate == pytest.approx(1.0)

    def test_success_rate_partial(self):
        result = MigrationResult(
            source_framework="selenium-java",
            steps_migrated=3,
            steps_total=4,
        )
        assert result.success_rate == pytest.approx(0.75)

    def test_to_dict_returns_dict(self):
        result = MigrationResult(source_framework="katalon")
        assert isinstance(result.to_dict(), dict)

    def test_to_dict_has_success_rate(self):
        result = MigrationResult(
            source_framework="selenium-py",
            steps_migrated=5,
            steps_total=10,
        )
        assert result.to_dict()["success_rate"] == pytest.approx(0.5)

    def test_to_dict_has_source_framework(self):
        result = MigrationResult(source_framework="katalon")
        assert result.to_dict()["source_framework"] == "katalon"

    def test_default_warnings_empty(self):
        result = MigrationResult(source_framework="selenium-java")
        assert result.warnings == []

    def test_default_output_code_empty(self):
        result = MigrationResult(source_framework="selenium-java")
        assert result.output_code == ""

    def test_total_zero_no_div_by_zero(self):
        result = MigrationResult(source_framework="selenium-java", steps_total=0)
        assert result.success_rate == 0.0


# ---------------------------------------------------------------------------
# migrate_source — unsupported framework
# ---------------------------------------------------------------------------

class TestMigrateSource:
    def test_unsupported_framework_raises_value_error(self):
        with pytest.raises(ValueError, match="Desteklenmeyen"):
            migrate_source("unsupported-framework", "source code")

    def test_empty_selenium_java_source(self):
        result = migrate_source("selenium-java", "")
        assert isinstance(result, MigrationResult)
        assert result.source_framework == "selenium-java"

    def test_empty_selenium_py_source(self):
        result = migrate_source("selenium-py", "")
        assert isinstance(result, MigrationResult)

    def test_empty_katalon_source(self):
        result = migrate_source("katalon", "")
        assert isinstance(result, MigrationResult)
