"""Unit tests for migration service facade.

Tests: 12 total
- get_supported_frameworks (1)
- migrate (5)
- migrate_file (2)
- migrate_dir (2)
- migration_summary (2)
"""
from __future__ import annotations

import pytest

from app.domains.migration.service import (
    get_supported_frameworks,
    migrate,
    migrate_dir,
    migrate_file,
    migration_summary,
)

SAMPLE_JAVA = '''
@Given("kullanıcı ana sayfadadır")
public void kullanici_ana_sayfadadir() { }

@When("kullanıcı login butonuna tıklar")
public void kullanici_login_butonuna_tiklar() { }
'''

SAMPLE_PY = '''\
@given("the user is on the home page")
def user_on_home_page(page):
    pass

@when("the user clicks the login button")
def user_clicks_login(page):
    pass
'''

SAMPLE_KATALON = 'WebUI.navigateToUrl("https://example.com")\nWebUI.click(findTestObject("btn_login"))'


# ── get_supported_frameworks ────────────────────────────────────────────────


def test_get_supported_frameworks_returns_list():
    frameworks = get_supported_frameworks()
    assert isinstance(frameworks, list)
    assert "selenium-java" in frameworks
    assert "selenium-py" in frameworks
    assert "katalon" in frameworks


# ── migrate ─────────────────────────────────────────────────────────────────


def test_migrate_selenium_java_returns_dict():
    result = migrate(SAMPLE_JAVA, "selenium-java")
    assert isinstance(result, dict)
    assert result["source_framework"] == "selenium-java"
    assert result["steps_total"] >= 1
    assert "success_rate" in result


def test_migrate_selenium_py_returns_dict():
    result = migrate(SAMPLE_PY, "selenium-py")
    assert isinstance(result, dict)
    assert result["source_framework"] == "selenium-py"


def test_migrate_katalon_returns_dict():
    result = migrate(SAMPLE_KATALON, "katalon")
    assert isinstance(result, dict)
    assert result["source_framework"] == "katalon"
    assert result["steps_total"] >= 1


def test_migrate_raises_value_error_for_empty_source():
    with pytest.raises(ValueError, match="must not be empty"):
        migrate("", "selenium-java")


def test_migrate_raises_value_error_for_unsupported_framework():
    with pytest.raises(ValueError, match="Unsupported framework"):
        migrate(SAMPLE_JAVA, "jest-unit")


# ── migrate_file ─────────────────────────────────────────────────────────────


def test_migrate_file_reads_and_migrates(tmp_path):
    f = tmp_path / "Steps.java"
    f.write_text(SAMPLE_JAVA, encoding="utf-8")
    result = migrate_file(str(f), "selenium-java")
    assert result["steps_total"] >= 1
    assert result["source_file"] == str(f)


def test_migrate_file_raises_key_error_when_missing():
    with pytest.raises(KeyError, match="not found"):
        migrate_file("/nonexistent/path/Steps.java", "selenium-java")


# ── migrate_dir ──────────────────────────────────────────────────────────────


def test_migrate_dir_raises_key_error_when_missing():
    with pytest.raises(KeyError, match="not found"):
        migrate_dir("/nonexistent/dir", "selenium-java")


def test_migrate_dir_raises_value_error_for_unsupported_framework(tmp_path):
    with pytest.raises(ValueError, match="Unsupported framework"):
        migrate_dir(str(tmp_path), "ruby-capybara")


# ── migration_summary ────────────────────────────────────────────────────────


def test_migration_summary_extracts_key_fields():
    result = migrate(SAMPLE_JAVA, "selenium-java")
    summary = migration_summary(result)
    assert set(summary.keys()) == {
        "source_framework",
        "source_file",
        "steps_total",
        "steps_migrated",
        "steps_unhandled",
        "success_rate",
        "warnings",
    }


def test_migration_summary_success_rate_between_0_and_1():
    result = migrate(SAMPLE_JAVA, "selenium-java")
    summary = migration_summary(result)
    assert 0.0 <= summary["success_rate"] <= 1.0
