"""Migration assistant testleri — Selenium Java/Python + Katalon."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.domains.migration.assistant import (
    MigrationResult,
    migrate_directory,
    migrate_katalon,
    migrate_selenium_java,
    migrate_selenium_py,
    migrate_source,
)


# ── Selenium Java ────────────────────────────────────────────────────────


_JAVA_SAMPLE = """
import io.cucumber.java.en.Given;
import io.cucumber.java.en.When;
import io.cucumber.java.en.Then;

public class LoginSteps {
    @Given("I navigate to {string}")
    public void i_navigate_to(String url) {
        driver.get(url);
    }

    @When("I click the button {string}")
    public void i_click_the_button(String name) {
        driver.findElement(By.xpath(...)).click();
    }

    @When("I enter {string} into the field {string}")
    public void i_enter_into(String value, String field) {
        driver.findElement(...).sendKeys(value);
    }

    @Then("I verify that {string} is visible")
    public void i_verify_visible(String text) {
        // assert ...
    }

    @Then("the weird custom step {string}")
    public void weird(String s) {
        // ...
    }
}
"""


class TestSeleniumJava:
    def test_detects_all_steps(self) -> None:
        r = migrate_selenium_java(_JAVA_SAMPLE)
        assert r.steps_total == 5

    def test_navigate_mapped(self) -> None:
        r = migrate_selenium_java(_JAVA_SAMPLE)
        nav = next(s for s in r.migrated if "navigate" in s.gherkin_pattern.lower())
        assert nav.mapped_to_dsl_action == "en_open_url"
        assert "page.goto" in nav.translated_code

    def test_click_mapped(self) -> None:
        r = migrate_selenium_java(_JAVA_SAMPLE)
        click = next(s for s in r.migrated if "click the button" in s.gherkin_pattern)
        assert "getByRole" in click.translated_code

    def test_unhandled_step_reported(self) -> None:
        r = migrate_selenium_java(_JAVA_SAMPLE)
        assert r.steps_unhandled >= 1
        weird_unhandled = [u for u in r.unhandled if "weird" in u.original]
        assert weird_unhandled

    def test_empty_source(self) -> None:
        r = migrate_selenium_java("")
        assert r.steps_total == 0
        assert r.warnings

    def test_output_is_valid_ts_structure(self) -> None:
        r = migrate_selenium_java(_JAVA_SAMPLE)
        assert "import { test, expect, Page }" in r.output_code
        assert "test('" in r.output_code
        # Her step için bir test() bloğu
        assert r.output_code.count("test('") == r.steps_total

    def test_success_rate(self) -> None:
        r = migrate_selenium_java(_JAVA_SAMPLE)
        # 5 total, 4 mapped (1 weird unhandled)
        assert r.success_rate == 0.8


# ── Selenium Python ──────────────────────────────────────────────────────


_PY_SAMPLE = '''
from pytest_bdd import given, when, then

@given("I am on the login page")
def navigate_login(page):
    page.goto("/login")

@when("I click submit")
def click_submit(page):
    page.locator(".submit").click()

@when("I fill the username")
def fill_username(page):
    pass

@then("I see welcome message")
def verify_visible(page):
    pass

@then("something strange and wonderful happens")
def weird(page):
    pass
'''


class TestSeleniumPy:
    def test_detects_steps(self) -> None:
        r = migrate_selenium_py(_PY_SAMPLE)
        assert r.steps_total == 5

    def test_click_mapped(self) -> None:
        r = migrate_selenium_py(_PY_SAMPLE)
        clicks = [s for s in r.migrated if "click" in s.gherkin_pattern.lower()]
        assert clicks
        assert "click()" in clicks[0].translated_code

    def test_fill_mapped(self) -> None:
        r = migrate_selenium_py(_PY_SAMPLE)
        fills = [s for s in r.migrated if "fill" in s.gherkin_pattern.lower() or "fill" in s.translated_code]
        assert fills

    def test_output_contains_pytest_bdd(self) -> None:
        r = migrate_selenium_py(_PY_SAMPLE)
        assert "from pytest_bdd" in r.output_code
        assert "from playwright" in r.output_code


# ── Katalon ──────────────────────────────────────────────────────────────


_KATALON_SAMPLE = """
import com.kms.katalon.core.webui.keyword.WebUiBuiltInKeywords as WebUI

WebUI.navigateToUrl('https://example.com/login')
WebUI.setText(findTestObject('Page_Login/input_Username'), 'admin')
WebUI.setText(findTestObject('Page_Login/input_Password'), 'secret')
WebUI.click(findTestObject('Page_Login/button_Login'))
WebUI.verifyElementVisible(findTestObject('Page_Dashboard/header'))
WebUI.delay(2)
WebUI.someUnknownMethod(findTestObject('X'))
"""


class TestKatalon:
    def test_detects_actions(self) -> None:
        r = migrate_katalon(_KATALON_SAMPLE)
        # navigate + 2×setText + click + verifyElementVisible + delay = 6 mapped
        # someUnknownMethod pattern'e uymadığı için hiç yakalanmaz (regex'te değil)
        assert r.steps_total == 6

    def test_all_supported_mapped(self) -> None:
        r = migrate_katalon(_KATALON_SAMPLE)
        assert r.steps_migrated == 6
        assert r.steps_unhandled == 0

    def test_output_has_playwright_skeleton(self) -> None:
        r = migrate_katalon(_KATALON_SAMPLE)
        assert "@playwright/test" in r.output_code
        assert "page.goto" in r.output_code or "// Kaynak: WebUI.navigateToUrl" in r.output_code

    def test_empty_source_warns(self) -> None:
        r = migrate_katalon("// sadece yorum")
        assert r.steps_total == 0
        assert r.warnings


# ── Facade + directory ──────────────────────────────────────────────────


def test_migrate_source_dispatch() -> None:
    r = migrate_source("selenium-java", _JAVA_SAMPLE)
    assert r.source_framework == "selenium-java"
    assert r.steps_total > 0


def test_migrate_source_invalid_framework() -> None:
    with pytest.raises(ValueError):
        migrate_source("cobol-migration", "x")  # type: ignore[arg-type]


def test_migrate_directory_multiple_files(tmp_path: Path) -> None:
    (tmp_path / "A.java").write_text(_JAVA_SAMPLE, encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "B.java").write_text(_JAVA_SAMPLE, encoding="utf-8")
    (tmp_path / "README.md").write_text("ignored", encoding="utf-8")
    results = migrate_directory("selenium-java", tmp_path)
    assert len(results) == 2
    assert all(r.steps_total > 0 for r in results)


def test_to_dict_json_safe() -> None:
    import json

    r = migrate_selenium_java(_JAVA_SAMPLE)
    s = json.dumps(r.to_dict(), ensure_ascii=False)
    assert len(s) > 200
