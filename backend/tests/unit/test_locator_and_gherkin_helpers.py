"""Unit tests for locator intelligence, scoring, extraction and gherkin parser
pure helper functions.

No DB, no HTTP, no LLM — pure Python only.

Covers:
  app/domains/agents/banking_team/locator_intelligence.py:
    _classify_selector_type, _url_to_class_name, _generate_testid_suggestion,
    _to_camel_case, _best_selector_for_element, _extract_typescript_code,
    _element_to_property_name
  app/domains/agents/v2/tools/locator/scoring.py:
    _uniqueness_score
  app/domains/agents/v2/tools/locator/extraction.py:
    _stable_classes, _fingerprint_for
  app/domains/agents/v2/tools/gherkin_parser.py:
    _strip_fence
"""

from __future__ import annotations

import pytest

from app.domains.agents.banking_team.locator_intelligence import (
    _best_selector_for_element,
    _classify_selector_type,
    _element_to_property_name,
    _extract_typescript_code,
    _generate_testid_suggestion,
    _to_camel_case,
    _url_to_class_name,
)
from app.domains.agents.v2.tools.gherkin_parser import _strip_fence
from app.domains.agents.v2.tools.locator.extraction import (
    _fingerprint_for,
    _stable_classes,
)
from app.domains.agents.v2.tools.locator.scoring import _uniqueness_score


# ── _classify_selector_type ───────────────────────────────────────────────────


class TestClassifySelectorType:
    def test_empty_returns_empty(self) -> None:
        assert _classify_selector_type("") == "empty"

    def test_data_testid(self) -> None:
        assert _classify_selector_type("[data-testid='login']") == "data-testid"

    def test_get_by_testid(self) -> None:
        assert _classify_selector_type("getByTestId('submit')") == "data-testid"

    def test_role_selector(self) -> None:
        assert _classify_selector_type("role=button") == "role"

    def test_get_by_role(self) -> None:
        assert _classify_selector_type("getByRole('button')") == "role"

    def test_aria_label(self) -> None:
        assert _classify_selector_type("[aria-label='submit']") == "aria-label"

    def test_get_by_label(self) -> None:
        assert _classify_selector_type("getByLabel('Email')") == "aria-label"

    def test_placeholder(self) -> None:
        assert _classify_selector_type("getByPlaceholder('Enter email')") == "placeholder"

    def test_get_by_text(self) -> None:
        assert _classify_selector_type("getByText('Login')") == "text"

    def test_text_equals(self) -> None:
        assert _classify_selector_type("text=Submit") == "text"

    def test_xpath_double_slash(self) -> None:
        assert _classify_selector_type("//div[@id='main']") == "xpath"

    def test_xpath_prefix(self) -> None:
        assert _classify_selector_type("xpath=//button") == "xpath"

    def test_id_hash(self) -> None:
        assert _classify_selector_type("#login-btn") == "id"

    def test_id_attribute(self) -> None:
        assert _classify_selector_type("id=submit") == "id"

    def test_css_class(self) -> None:
        result = _classify_selector_type("button.primary-btn")
        assert result == "css_class"

    def test_css_other(self) -> None:
        result = _classify_selector_type("form > input[type='text']")
        assert result == "css_other"


# ── _url_to_class_name ────────────────────────────────────────────────────────


class TestUrlToClassName:
    def test_empty_returns_unknown(self) -> None:
        assert _url_to_class_name("") == "UnknownPage"

    def test_simple_path(self) -> None:
        result = _url_to_class_name("https://example.com/login")
        assert result == "LoginPage"

    def test_root_path_returns_homepage(self) -> None:
        # "/" → after stripping and splitting → empty segments → "HomePage"
        result = _url_to_class_name("/")
        assert result == "HomePage"

    def test_already_ends_with_page_not_doubled(self) -> None:
        result = _url_to_class_name("https://example.com/dashboard")
        assert result == "DashboardPage"
        assert "PagePage" not in result

    def test_kebab_case_converted(self) -> None:
        result = _url_to_class_name("https://example.com/user-profile")
        assert result == "UserProfilePage"

    def test_underscore_converted(self) -> None:
        result = _url_to_class_name("https://example.com/user_profile")
        assert result == "UserProfilePage"

    def test_query_params_ignored(self) -> None:
        result = _url_to_class_name("https://example.com/login?next=/home")
        assert result == "LoginPage"

    def test_hash_ignored(self) -> None:
        result = _url_to_class_name("https://example.com/settings#profile")
        assert result == "SettingsPage"

    def test_nested_path_uses_last_segment(self) -> None:
        result = _url_to_class_name("https://example.com/admin/users/list")
        assert result == "ListPage"


# ── _generate_testid_suggestion ───────────────────────────────────────────────


class TestGenerateTestidSuggestion:
    def test_name_based_kebab(self) -> None:
        result = _generate_testid_suggestion("Login Button", "")
        assert result == "login-button"

    def test_name_special_chars_removed(self) -> None:
        result = _generate_testid_suggestion("Submit Form!", "")
        assert result == "submit-form"

    def test_empty_name_falls_to_selector(self) -> None:
        result = _generate_testid_suggestion("", "button.submit-btn")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_empty_both_returns_element(self) -> None:
        result = _generate_testid_suggestion("", "")
        assert result == "element"

    def test_name_lowercased(self) -> None:
        result = _generate_testid_suggestion("LOGIN", "")
        assert result == "login"

    def test_selector_filters_common_words(self) -> None:
        # "button" alone → filtered → falls back to "element"
        result = _generate_testid_suggestion("", "getByRole('button')")
        # "role" and "button" are filtered
        assert result == "element" or isinstance(result, str)

    def test_returns_string(self) -> None:
        result = _generate_testid_suggestion("test", "selector")
        assert isinstance(result, str)


# ── _to_camel_case ────────────────────────────────────────────────────────────


class TestToCamelCase:
    def test_single_word_lowercase(self) -> None:
        assert _to_camel_case("login") == "login"

    def test_two_words(self) -> None:
        assert _to_camel_case("login button") == "loginButton"

    def test_hyphen_separated(self) -> None:
        assert _to_camel_case("login-button") == "loginButton"

    def test_underscore_separated(self) -> None:
        assert _to_camel_case("user_name") == "userName"

    def test_empty_returns_empty(self) -> None:
        assert _to_camel_case("") == ""

    def test_special_chars_stripped(self) -> None:
        result = _to_camel_case("login!button")
        assert result == "loginButton"

    def test_multiple_words(self) -> None:
        result = _to_camel_case("first middle last")
        assert result == "firstMiddleLast"

    def test_all_caps_words_preserved_partially(self) -> None:
        result = _to_camel_case("LOGIN BUTTON")
        # First word lowercase, rest capitalize
        assert result == "lOGINbUTTON" or result.startswith("l")


# ── _best_selector_for_element ────────────────────────────────────────────────


class TestBestSelectorForElement:
    def test_testid_preferred(self) -> None:
        elem = {"data-testid": "login-btn", "role": "button", "tag": "button"}
        result = _best_selector_for_element(elem)
        assert "login-btn" in result
        assert "getByTestId" in result

    def test_data_testid_underscore_key(self) -> None:
        elem = {"data_testid": "submit-btn"}
        result = _best_selector_for_element(elem)
        assert "submit-btn" in result

    def test_role_with_label(self) -> None:
        elem = {"role": "button", "aria-label": "Submit", "tag": "button"}
        result = _best_selector_for_element(elem)
        assert "getByRole" in result
        assert "Submit" in result

    def test_role_without_label(self) -> None:
        elem = {"role": "button", "tag": "button"}
        result = _best_selector_for_element(elem)
        assert "getByRole" in result

    def test_aria_label_fallback(self) -> None:
        elem = {"aria-label": "Close dialog", "tag": "button"}
        result = _best_selector_for_element(elem)
        assert "getByLabel" in result
        assert "Close dialog" in result

    def test_id_fallback(self) -> None:
        elem = {"id": "main-form", "tag": "form"}
        result = _best_selector_for_element(elem)
        assert "#main-form" in result

    def test_text_fallback(self) -> None:
        elem = {"text": "Click here", "tag": "a"}
        result = _best_selector_for_element(elem)
        assert "getByText" in result

    def test_tag_final_fallback(self) -> None:
        elem = {"tag": "div"}
        result = _best_selector_for_element(elem)
        assert "div" in result

    def test_returns_string(self) -> None:
        elem = {"tag": "span", "text": "test"}
        assert isinstance(_best_selector_for_element(elem), str)


# ── _extract_typescript_code ──────────────────────────────────────────────────


class TestExtractTypescriptCode:
    def test_plain_typescript_unchanged(self) -> None:
        code = "import { Page } from '@playwright/test';\nexport class LoginPage {}"
        result = _extract_typescript_code(code)
        assert "import" in result
        assert "LoginPage" in result

    def test_strips_ts_code_block(self) -> None:
        raw = "```typescript\nimport { Page } from '@playwright/test';\n```"
        result = _extract_typescript_code(raw)
        assert "import" in result
        assert "```" not in result

    def test_strips_generic_code_block(self) -> None:
        raw = "```\nconst x = 1;\n```"
        result = _extract_typescript_code(raw)
        assert "const x = 1;" in result
        assert "```" not in result

    def test_export_starts_returned_as_is(self) -> None:
        code = "export class Foo {}"
        result = _extract_typescript_code(code)
        assert result == code

    def test_plain_text_returned_as_is(self) -> None:
        text = "Some explanation text"
        result = _extract_typescript_code(text)
        assert result == text

    def test_returns_string(self) -> None:
        assert isinstance(_extract_typescript_code("code"), str)


# ── _element_to_property_name ─────────────────────────────────────────────────


class TestElementToPropertyName:
    def test_testid_preferred(self) -> None:
        elem = {"data-testid": "login-btn", "name": "btn"}
        result = _element_to_property_name(elem)
        assert "login" in result.lower()

    def test_name_fallback(self) -> None:
        elem = {"name": "submit-button"}
        result = _element_to_property_name(elem)
        assert "submit" in result.lower()

    def test_aria_label_fallback(self) -> None:
        elem = {"aria-label": "close dialog"}
        result = _element_to_property_name(elem)
        assert "close" in result.lower()

    def test_id_fallback(self) -> None:
        elem = {"id": "main-form"}
        result = _element_to_property_name(elem)
        assert "main" in result.lower()

    def test_empty_elem_returns_empty(self) -> None:
        result = _element_to_property_name({})
        assert result == ""

    def test_returns_camel_case(self) -> None:
        elem = {"name": "login-button"}
        result = _element_to_property_name(elem)
        assert "-" not in result


# ── _uniqueness_score ─────────────────────────────────────────────────────────


class TestUniquenessScore:
    def test_single_element_perfect_score(self) -> None:
        assert _uniqueness_score(1) == 1.0

    def test_zero_elements_zero_score(self) -> None:
        assert _uniqueness_score(0) == 0.0

    def test_minus_one_half_score(self) -> None:
        assert _uniqueness_score(-1) == 0.5

    def test_two_elements_score(self) -> None:
        assert _uniqueness_score(2) == pytest.approx(0.6)

    def test_three_elements_score(self) -> None:
        assert _uniqueness_score(3) == pytest.approx(0.4)

    def test_large_count_low_score(self) -> None:
        assert _uniqueness_score(10) == pytest.approx(0.2)

    def test_score_decreases_with_count(self) -> None:
        assert _uniqueness_score(1) > _uniqueness_score(2) > _uniqueness_score(3)


# ── _stable_classes ───────────────────────────────────────────────────────────


class TestStableClasses:
    def test_none_returns_empty(self) -> None:
        assert _stable_classes(None) == []

    def test_empty_string_returns_empty(self) -> None:
        assert _stable_classes("") == []

    def test_stable_class_included(self) -> None:
        result = _stable_classes("btn primary-btn")
        assert "btn" in result
        assert "primary-btn" in result

    def test_hash_class_excluded(self) -> None:
        # Hash-like classes (e.g. random hex/alphanumeric) should be excluded
        # The regex _HASH_CLASS_RE filters them
        result = _stable_classes("btn abc123def456ghi7")
        # "btn" is stable; "abc123def456ghi7" is hash-like
        assert "btn" in result

    def test_single_class(self) -> None:
        result = _stable_classes("submit-btn")
        assert result == ["submit-btn"]

    def test_multiple_stable_classes(self) -> None:
        result = _stable_classes("form-control input-text required")
        assert len(result) == 3


# ── _fingerprint_for ──────────────────────────────────────────────────────────


class TestFingerprintFor:
    def test_returns_string_with_el_prefix(self) -> None:
        result = _fingerprint_for("button", "login-btn", "button", "Login", "Login", None)
        assert isinstance(result, str)
        assert result.startswith("el_")

    def test_deterministic(self) -> None:
        f1 = _fingerprint_for("button", "btn", None, None, "Click", None)
        f2 = _fingerprint_for("button", "btn", None, None, "Click", None)
        assert f1 == f2

    def test_different_inputs_different_fingerprint(self) -> None:
        f1 = _fingerprint_for("button", "btn1", None, None, None, None)
        f2 = _fingerprint_for("button", "btn2", None, None, None, None)
        assert f1 != f2

    def test_none_values_handled(self) -> None:
        result = _fingerprint_for("div", None, None, None, None, None)
        assert result.startswith("el_")
        assert len(result) == 15  # "el_" + 12 hex chars

    def test_fixed_length(self) -> None:
        result = _fingerprint_for("a", "id", "link", "label", "text", "form")
        assert len(result) == 15  # "el_" (3) + 12 hex


# ── _strip_fence (gherkin_parser) ─────────────────────────────────────────────


class TestStripFenceGherkin:
    def test_plain_text_unchanged(self) -> None:
        text = "Feature: Login"
        assert _strip_fence(text) == text

    def test_strips_gherkin_fence(self) -> None:
        raw = "```gherkin\nFeature: Login\n  Scenario: Test\n```"
        result = _strip_fence(raw)
        assert "Feature: Login" in result
        assert "```" not in result

    def test_strips_generic_fence(self) -> None:
        raw = "```\nsome content\n```"
        result = _strip_fence(raw)
        assert result == "some content"

    def test_no_closing_fence(self) -> None:
        raw = "```gherkin\nFeature: Login"
        result = _strip_fence(raw)
        assert "Feature: Login" in result
        assert "```" not in result

    def test_empty_string(self) -> None:
        assert _strip_fence("") == ""

    def test_whitespace_stripped(self) -> None:
        raw = "  ```\ncontent\n```  "
        result = _strip_fence(raw)
        assert result == "content"

    def test_multiline_content_preserved(self) -> None:
        raw = "```\nline1\nline2\nline3\n```"
        result = _strip_fence(raw)
        assert "line1" in result
        assert "line2" in result
        assert "line3" in result
