"""Unit tests for locator fallback chain pure helpers.

Tests app/domains/agents/banking_team/locator_fallback_chain.py — pure Python.
Covers: _parse_selector_target, _extract_hints_from_selector,
        _build_pw_selector, _token_overlap, _css_to_playwright_selector.
"""

from __future__ import annotations

import pytest

from app.domains.agents.banking_team.locator_fallback_chain import (
    _build_pw_selector,
    _css_to_playwright_selector,
    _extract_hints_from_selector,
    _parse_selector_target,
    _token_overlap,
)


# ── _parse_selector_target ────────────────────────────────────────────────────


class TestParseSelectorTarget:
    def test_get_by_test_id(self) -> None:
        result = _parse_selector_target("page.getByTestId('login-btn')")
        assert result["type"] == "testid"
        assert result["value"] == "login-btn"

    def test_get_by_test_id_double_quotes(self) -> None:
        result = _parse_selector_target('page.getByTestId("submit-btn")')
        assert result["type"] == "testid"
        assert result["value"] == "submit-btn"

    def test_get_by_role_without_name(self) -> None:
        result = _parse_selector_target("page.getByRole('button')")
        assert result["type"] == "role"
        assert result["value"] == "button"

    def test_get_by_role_with_name(self) -> None:
        result = _parse_selector_target("page.getByRole('button', {name: 'OK'})")
        assert result["type"] == "role"
        assert result["value"] == "button"

    def test_get_by_label(self) -> None:
        result = _parse_selector_target("page.getByLabel('Username')")
        assert result["type"] == "label"
        assert result["value"] == "Username"

    def test_get_by_placeholder(self) -> None:
        result = _parse_selector_target("page.getByPlaceholder('Enter email')")
        assert result["type"] == "placeholder"
        assert result["value"] == "Enter email"

    def test_get_by_text(self) -> None:
        result = _parse_selector_target("page.getByText('Submit')")
        assert result["type"] == "text"
        assert result["value"] == "Submit"

    def test_locator_css(self) -> None:
        result = _parse_selector_target("page.locator('#my-id')")
        assert result["type"] == "css"
        assert result["value"] == "#my-id"

    def test_bare_xpath(self) -> None:
        result = _parse_selector_target("//div[@id='login']")
        assert result["type"] == "xpath"

    def test_bare_css_selector(self) -> None:
        result = _parse_selector_target(".my-class button")
        assert result["type"] == "css"
        assert result["value"] == ".my-class button"

    def test_empty_string_returns_nulls(self) -> None:
        result = _parse_selector_target("")
        assert result["type"] is None
        assert result["value"] is None


# ── _extract_hints_from_selector ──────────────────────────────────────────────


class TestExtractHintsFromSelector:
    def test_testid_hint_extracted(self) -> None:
        hints = _extract_hints_from_selector("page.getByTestId('login-form')")
        assert hints["testid_hint"] == "login-form"
        assert hints["text_hint"] == "login"  # first token of "login-form"

    def test_role_hint_extracted(self) -> None:
        hints = _extract_hints_from_selector("page.getByRole('button')")
        assert hints["role_hint"] == "button"

    def test_label_hint_extracted(self) -> None:
        hints = _extract_hints_from_selector("page.getByLabel('Email')")
        assert hints["text_hint"] == "Email"

    def test_css_id_extracted(self) -> None:
        hints = _extract_hints_from_selector("page.locator('#submit-btn')")
        assert hints["id_fragment"] == "submit-btn"

    def test_css_class_extracted(self) -> None:
        hints = _extract_hints_from_selector("page.locator('.submit-button')")
        assert hints["class_fragment"] == "submit-button"

    def test_css_attribute_extracted(self) -> None:
        hints = _extract_hints_from_selector("page.locator('[data-cy=\"login\"]')")
        assert hints["attr_name"] == "data-cy"
        assert hints["attr_value"] == "login"

    def test_xpath_tag_extracted(self) -> None:
        hints = _extract_hints_from_selector("//button[@id='ok']")
        assert hints["tag"] == "button"
        assert hints["attr_name"] == "id"
        assert hints["attr_value"] == "ok"


# ── _build_pw_selector ────────────────────────────────────────────────────────


class TestBuildPwSelector:
    def test_data_testid(self) -> None:
        result = _build_pw_selector("data-testid", "login-btn")
        assert result == "page.getByTestId('login-btn')"

    def test_role(self) -> None:
        result = _build_pw_selector("role", "button")
        assert result == "page.getByRole('button')"

    def test_aria_label(self) -> None:
        result = _build_pw_selector("aria-label", "Close dialog")
        assert result == "page.getByLabel('Close dialog')"

    def test_placeholder(self) -> None:
        result = _build_pw_selector("placeholder", "Enter email")
        assert result == "page.getByPlaceholder('Enter email')"

    def test_id(self) -> None:
        result = _build_pw_selector("id", "my-button")
        assert result == "page.locator('#my-button')"

    def test_name_with_tag(self) -> None:
        result = _build_pw_selector("name", "submit", tag="button")
        assert "button" in result
        assert "submit" in result

    def test_name_without_tag(self) -> None:
        result = _build_pw_selector("name", "submit")
        assert "submit" in result
        assert "[name" in result

    def test_fallback_attr(self) -> None:
        result = _build_pw_selector("data-custom", "value123")
        assert 'data-custom' in result
        assert 'value123' in result


# ── _token_overlap ────────────────────────────────────────────────────────────


class TestTokenOverlap:
    def test_identical_strings(self) -> None:
        assert _token_overlap("login-btn", "login-btn") == pytest.approx(1.0)

    def test_no_overlap(self) -> None:
        result = _token_overlap("login-form", "submit-button")
        assert result == 0.0

    def test_partial_overlap(self) -> None:
        result = _token_overlap("login-form", "login-page")
        # tokens: {login, form} vs {login, page} → intersection=1, union=3
        assert result == pytest.approx(1 / 3)

    def test_empty_strings(self) -> None:
        assert _token_overlap("", "") == 0.0

    def test_case_insensitive(self) -> None:
        assert _token_overlap("Login-BTN", "login-btn") == pytest.approx(1.0)

    def test_whitespace_separator(self) -> None:
        result = _token_overlap("login form", "login page")
        assert result > 0.0

    def test_single_common_token(self) -> None:
        result = _token_overlap("btn", "btn")
        assert result == pytest.approx(1.0)


# ── _css_to_playwright_selector ───────────────────────────────────────────────


class TestCssToPlaywrightSelector:
    def test_data_testid_converted(self) -> None:
        result = _css_to_playwright_selector('[data-testid="login-btn"]')
        assert result == "page.getByTestId('login-btn')"

    def test_aria_label_converted(self) -> None:
        result = _css_to_playwright_selector('[aria-label="Close"]')
        assert result == "page.getByLabel('Close')"

    def test_placeholder_converted(self) -> None:
        result = _css_to_playwright_selector('[placeholder="Enter email"]')
        assert result == "page.getByPlaceholder('Enter email')"

    def test_id_selector_wrapped_in_locator(self) -> None:
        result = _css_to_playwright_selector('#my-button')
        assert result == "page.locator('#my-button')"

    def test_text_selector_converted(self) -> None:
        result = _css_to_playwright_selector("text='Submit'")
        assert "getByText" in result
        assert "Submit" in result

    def test_role_selector_converted(self) -> None:
        result = _css_to_playwright_selector('[role="button"]')
        assert "getByRole" in result
        assert "button" in result

    def test_role_with_aria_label(self) -> None:
        result = _css_to_playwright_selector('[role="button"][aria-label="OK"]')
        assert "getByRole" in result
        assert "button" in result
        assert "OK" in result

    def test_generic_css_wrapped_in_locator(self) -> None:
        result = _css_to_playwright_selector('.my-class > button')
        assert result.startswith("page.locator(")
        assert "my-class" in result

    def test_empty_string_wrapped(self) -> None:
        result = _css_to_playwright_selector("")
        assert result.startswith("page.locator(")
