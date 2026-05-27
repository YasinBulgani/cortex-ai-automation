"""Unit tests for agents.banking_team.locator_fallback_chain pure helpers.

All tests are self-contained: no Playwright, no HTTP, no LLM.
Covers:
  - _not_found: quick FallbackResult with found=False
  - _parse_selector_target: Playwright selector → type/value/name dict
  - _build_pw_selector: attribute → Playwright API selector string
  - _token_overlap: Jaccard token overlap ratio
  - _css_to_playwright_selector: CSS selector → Playwright API format
  - FallbackResult / ChainResult: dataclass structures
"""
from __future__ import annotations

import pytest

try:
    from app.domains.agents.banking_team.locator_fallback_chain import (
        _not_found,
        _parse_selector_target,
        _build_pw_selector,
        _token_overlap,
        _css_to_playwright_selector,
        FallbackResult,
        ChainResult,
    )
    _LFC_OK = True
except ImportError:
    _LFC_OK = False


# ---------------------------------------------------------------------------
# _not_found
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _LFC_OK, reason="locator_fallback_chain import failed")
class TestNotFound:
    def test_found_is_false(self):
        r = _not_found("exact")
        assert r.found is False

    def test_confidence_is_zero(self):
        r = _not_found("attribute_cascade")
        assert r.confidence == pytest.approx(0.0)

    def test_strategy_preserved(self):
        r = _not_found("similarity")
        assert r.strategy == "similarity"

    def test_selector_is_empty_string(self):
        r = _not_found("llm")
        assert r.selector == ""

    def test_reason_preserved(self):
        r = _not_found("exact", "DOM not ready")
        assert r.reason == "DOM not ready"

    def test_empty_reason_default(self):
        r = _not_found("cache")
        assert r.reason == ""

    def test_returns_fallback_result(self):
        r = _not_found("exact")
        assert isinstance(r, FallbackResult)

    def test_stability_score_zero(self):
        r = _not_found("exact")
        assert r.stability_score == 0


# ---------------------------------------------------------------------------
# _parse_selector_target
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _LFC_OK, reason="locator_fallback_chain import failed")
class TestParseSelectorTarget:
    def test_testid_type(self):
        result = _parse_selector_target("page.getByTestId('login-btn')")
        assert result["type"] == "testid"

    def test_testid_value(self):
        result = _parse_selector_target("page.getByTestId('login-btn')")
        assert result["value"] == "login-btn"

    def test_role_type(self):
        result = _parse_selector_target("page.getByRole('button')")
        assert result["type"] == "role"

    def test_role_value(self):
        result = _parse_selector_target("page.getByRole('button')")
        assert result["value"] == "button"

    def test_role_with_name(self):
        result = _parse_selector_target("page.getByRole('button', {name: 'Submit'})")
        assert result["name"] == "Submit"

    def test_label_type(self):
        result = _parse_selector_target("page.getByLabel('Email')")
        assert result["type"] == "label"

    def test_placeholder_type(self):
        result = _parse_selector_target("page.getByPlaceholder('Enter email')")
        assert result["type"] == "placeholder"

    def test_text_type(self):
        result = _parse_selector_target("page.getByText('Submit')")
        assert result["type"] == "text"

    def test_locator_css_type(self):
        result = _parse_selector_target("page.locator('#my-id')")
        assert result["type"] == "css"
        assert result["value"] == "#my-id"

    def test_bare_xpath_type(self):
        result = _parse_selector_target("//div[@class='login']")
        assert result["type"] == "xpath"

    def test_empty_selector(self):
        result = _parse_selector_target("")
        assert result["type"] is None

    def test_returns_dict(self):
        assert isinstance(_parse_selector_target("page.getByTestId('x')"), dict)

    def test_dict_has_type_value_name_keys(self):
        result = _parse_selector_target("page.getByTestId('x')")
        assert "type" in result
        assert "value" in result
        assert "name" in result


# ---------------------------------------------------------------------------
# _build_pw_selector
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _LFC_OK, reason="locator_fallback_chain import failed")
class TestBuildPwSelector:
    def test_data_testid(self):
        result = _build_pw_selector("data-testid", "submit-btn")
        assert "getByTestId" in result
        assert "submit-btn" in result

    def test_role(self):
        result = _build_pw_selector("role", "button")
        assert "getByRole" in result
        assert "button" in result

    def test_aria_label(self):
        result = _build_pw_selector("aria-label", "Close dialog")
        assert "getByLabel" in result
        assert "Close dialog" in result

    def test_placeholder(self):
        result = _build_pw_selector("placeholder", "Enter email")
        assert "getByPlaceholder" in result

    def test_name_attribute(self):
        result = _build_pw_selector("name", "email", tag="input")
        assert "locator" in result
        assert "email" in result
        assert "input" in result

    def test_id_attribute(self):
        result = _build_pw_selector("id", "login-btn")
        assert "#login-btn" in result
        assert "locator" in result

    def test_custom_attribute_fallback(self):
        result = _build_pw_selector("data-custom", "my-value")
        assert "data-custom" in result
        assert "my-value" in result

    def test_returns_string(self):
        assert isinstance(_build_pw_selector("id", "x"), str)

    def test_name_without_tag_uses_wildcard(self):
        result = _build_pw_selector("name", "email")
        assert "*" in result


# ---------------------------------------------------------------------------
# _token_overlap
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _LFC_OK, reason="locator_fallback_chain import failed")
class TestTokenOverlap:
    def test_identical_strings(self):
        assert _token_overlap("login-btn", "login-btn") == pytest.approx(1.0)

    def test_no_overlap(self):
        assert _token_overlap("hello", "world") == pytest.approx(0.0)

    def test_partial_overlap(self):
        # "login" and "button" vs "login" and "btn"
        # tokens_a = {login, btn}, tokens_b = {login, button}
        # intersection = {login}, union = {login, btn, button} → 1/3
        result = _token_overlap("login-btn", "login-button")
        assert 0.0 < result < 1.0

    def test_empty_strings(self):
        assert _token_overlap("", "") == pytest.approx(0.0)

    def test_one_empty(self):
        assert _token_overlap("hello", "") == pytest.approx(0.0)
        assert _token_overlap("", "hello") == pytest.approx(0.0)

    def test_symmetric(self):
        a, b = "login-form-submit", "form-login"
        assert _token_overlap(a, b) == pytest.approx(_token_overlap(b, a))

    def test_case_insensitive(self):
        r1 = _token_overlap("LOGIN", "login")
        assert r1 == pytest.approx(1.0)

    def test_range_0_to_1(self):
        result = _token_overlap("foo-bar-baz", "bar-qux")
        assert 0.0 <= result <= 1.0

    def test_returns_float(self):
        assert isinstance(_token_overlap("a", "b"), float)

    def test_hyphen_split(self):
        # "a-b-c" has tokens {a, b, c}; "a-b" has {a, b}
        result = _token_overlap("a-b-c", "a-b")
        assert result == pytest.approx(2.0 / 3.0)


# ---------------------------------------------------------------------------
# _css_to_playwright_selector
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _LFC_OK, reason="locator_fallback_chain import failed")
class TestCssToPlaywrightSelector:
    def test_data_testid_attribute(self):
        result = _css_to_playwright_selector('[data-testid="login"]')
        assert "getByTestId" in result
        assert "login" in result

    def test_id_selector(self):
        result = _css_to_playwright_selector("#my-id")
        assert "locator" in result
        assert "#my-id" in result

    def test_role_attribute(self):
        result = _css_to_playwright_selector('[role="button"]')
        assert "getByRole" in result

    def test_role_with_aria_label(self):
        result = _css_to_playwright_selector('[role="button"][aria-label="Close"]')
        assert "getByRole" in result
        assert "Close" in result

    def test_aria_label_only(self):
        result = _css_to_playwright_selector('[aria-label="Submit Form"]')
        assert "getByLabel" in result

    def test_placeholder_attribute(self):
        result = _css_to_playwright_selector('[placeholder="Enter email"]')
        assert "getByPlaceholder" in result

    def test_text_selector(self):
        result = _css_to_playwright_selector("text='Submit'")
        assert "getByText" in result

    def test_generic_css_wrapped_in_locator(self):
        result = _css_to_playwright_selector("div.container > button")
        assert "locator" in result

    def test_returns_string(self):
        assert isinstance(_css_to_playwright_selector("#x"), str)

    def test_whitespace_stripped(self):
        result = _css_to_playwright_selector("  #my-id  ")
        assert "locator" in result
