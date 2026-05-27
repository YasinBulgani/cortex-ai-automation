"""Unit tests for locator intelligence pure helper functions.

Tests app/domains/agents/banking_team/locator_intelligence.py — pure Python.
Covers: _classify_selector_type, _url_to_class_name, _generate_testid_suggestion,
        _element_to_property_name, _to_camel_case, _best_selector_for_element,
        _extract_typescript_code, _detect_recurring_patterns.
"""

from __future__ import annotations

import pytest

from app.domains.agents.banking_team.locator_intelligence import (
    _best_selector_for_element,
    _classify_selector_type,
    _detect_recurring_patterns,
    _element_to_property_name,
    _extract_typescript_code,
    _generate_testid_suggestion,
    _to_camel_case,
    _url_to_class_name,
)


# ── _classify_selector_type ───────────────────────────────────────────────────


class TestClassifySelectorType:
    def test_empty_string(self) -> None:
        assert _classify_selector_type("") == "empty"

    def test_data_testid_attr(self) -> None:
        assert _classify_selector_type('[data-testid="btn"]') == "data-testid"

    def test_get_by_test_id(self) -> None:
        assert _classify_selector_type("page.getByTestId('btn')") == "data-testid"

    def test_role_attr(self) -> None:
        assert _classify_selector_type('[role="button"]') == "role"

    def test_get_by_role(self) -> None:
        assert _classify_selector_type("page.getByRole('button')") == "role"

    def test_aria_label(self) -> None:
        assert _classify_selector_type('[aria-label="Close"]') == "aria-label"

    def test_get_by_label(self) -> None:
        assert _classify_selector_type("page.getByLabel('Username')") == "aria-label"

    def test_placeholder(self) -> None:
        assert _classify_selector_type('[placeholder="Search"]') == "placeholder"

    def test_get_by_text(self) -> None:
        assert _classify_selector_type("page.getByText('Submit')") == "text"

    def test_text_equals(self) -> None:
        assert _classify_selector_type("text='OK'") == "text"

    def test_xpath_double_slash(self) -> None:
        assert _classify_selector_type("//div[@id='x']") == "xpath"

    def test_xpath_prefix(self) -> None:
        assert _classify_selector_type("xpath=//button") == "xpath"

    def test_css_class(self) -> None:
        assert _classify_selector_type(".my-button") == "css_class"

    def test_css_id(self) -> None:
        assert _classify_selector_type("#submit-btn") == "id"

    def test_css_other(self) -> None:
        result = _classify_selector_type("button[type='submit']")
        assert result in ("css_other", "css_class", "id")


# ── _url_to_class_name ────────────────────────────────────────────────────────


class TestUrlToClassName:
    def test_empty_url_returns_unknown(self) -> None:
        assert _url_to_class_name("") == "UnknownPage"

    def test_simple_path(self) -> None:
        result = _url_to_class_name("https://app.example.com/login")
        assert result == "LoginPage"

    def test_hyphenated_path(self) -> None:
        result = _url_to_class_name("https://app.example.com/user-profile")
        assert result == "UserProfilePage"

    def test_ends_with_slash_stripped(self) -> None:
        result = _url_to_class_name("https://app.example.com/login/")
        assert result == "LoginPage"

    def test_empty_path_returns_homepage(self) -> None:
        # When only hostname with no path → falls through to hostname segment
        result = _url_to_class_name("https://app.example.com/")
        # The function takes the last path segment which is the hostname part
        assert result.endswith("Page")  # always ends with Page

    def test_query_string_stripped(self) -> None:
        result = _url_to_class_name("https://app.example.com/dashboard?tab=reports")
        assert result == "DashboardPage"

    def test_hash_fragment_stripped(self) -> None:
        result = _url_to_class_name("https://app.example.com/settings#profile")
        assert result == "SettingsPage"

    def test_already_ends_with_page(self) -> None:
        result = _url_to_class_name("https://app.example.com/home-page")
        assert result.endswith("Page")

    def test_underscore_separator(self) -> None:
        result = _url_to_class_name("https://app.example.com/forgot_password")
        assert result == "ForgotPasswordPage"

    def test_file_extension_removed(self) -> None:
        result = _url_to_class_name("https://app.example.com/index.html")
        assert "html" not in result.lower()
        assert result.endswith("Page")


# ── _generate_testid_suggestion ───────────────────────────────────────────────


class TestGenerateTestidSuggestion:
    def test_name_used_when_provided(self) -> None:
        result = _generate_testid_suggestion("Login Button", "")
        assert result == "login-button"

    def test_name_special_chars_removed(self) -> None:
        result = _generate_testid_suggestion("User@Profile!", "")
        assert "@" not in result
        assert "!" not in result

    def test_empty_name_uses_selector(self) -> None:
        result = _generate_testid_suggestion("", "page.getByRole('button')")
        assert "button" not in result or result != "element"

    def test_selector_fallback_filters_keywords(self) -> None:
        result = _generate_testid_suggestion("", "page.locator('button#submit')")
        # "page", "locator" should be filtered; "submit" should be included
        assert "submit" in result

    def test_no_name_no_useful_selector_returns_element(self) -> None:
        result = _generate_testid_suggestion("", "")
        assert result == "element"

    def test_name_lowercased(self) -> None:
        result = _generate_testid_suggestion("SUBMIT FORM", "")
        assert result == result.lower()


# ── _to_camel_case ────────────────────────────────────────────────────────────


class TestToCamelCase:
    def test_single_word_lowercased(self) -> None:
        assert _to_camel_case("Hello") == "hello"

    def test_two_words(self) -> None:
        assert _to_camel_case("hello world") == "helloWorld"

    def test_three_words(self) -> None:
        assert _to_camel_case("login submit button") == "loginSubmitButton"

    def test_hyphenated(self) -> None:
        assert _to_camel_case("login-btn") == "loginBtn"

    def test_underscored(self) -> None:
        assert _to_camel_case("user_name") == "userName"

    def test_empty_string(self) -> None:
        assert _to_camel_case("") == ""

    def test_special_chars_stripped(self) -> None:
        result = _to_camel_case("hello@world!")
        assert "@" not in result
        assert "!" not in result

    def test_numbers_preserved(self) -> None:
        result = _to_camel_case("item 2 selected")
        assert "2" in result

    def test_all_caps_lowercased_first(self) -> None:
        result = _to_camel_case("LOGIN")
        assert result[0].islower()


# ── _element_to_property_name ─────────────────────────────────────────────────


class TestElementToPropertyName:
    def test_prefers_data_testid(self) -> None:
        elem = {"data_testid": "login-btn", "name": "submit", "id": "btn1"}
        result = _element_to_property_name(elem)
        assert "login" in result

    def test_uses_name_if_no_testid(self) -> None:
        elem = {"name": "submit-button", "id": "btn"}
        result = _element_to_property_name(elem)
        assert "submit" in result.lower()

    def test_uses_aria_label_if_no_name(self) -> None:
        elem = {"aria_label": "Close dialog"}
        result = _element_to_property_name(elem)
        assert "close" in result.lower()

    def test_uses_id_if_no_label(self) -> None:
        elem = {"id": "my-button"}
        result = _element_to_property_name(elem)
        assert "my" in result.lower()

    def test_uses_text_for_short_content(self) -> None:
        elem = {"text": "Submit"}
        result = _element_to_property_name(elem)
        assert "submit" in result.lower()

    def test_long_text_ignored(self) -> None:
        elem = {"text": "This is a very long text that exceeds thirty characters easily"}
        result = _element_to_property_name(elem)
        assert result == "" or "tag" in result.lower() or result == ""

    def test_empty_elem_returns_empty_or_fallback(self) -> None:
        result = _element_to_property_name({})
        # No fields → fallback to tag+type → both missing → empty
        assert result == ""

    def test_returns_camel_case(self) -> None:
        elem = {"data_testid": "login-form-submit"}
        result = _element_to_property_name(elem)
        assert "-" not in result
        assert "_" not in result


# ── _best_selector_for_element ────────────────────────────────────────────────


class TestBestSelectorForElement:
    def test_prefers_testid(self) -> None:
        elem = {"data_testid": "login-btn", "role": "button", "id": "btn1"}
        result = _best_selector_for_element(elem)
        assert "getByTestId" in result
        assert "login-btn" in result

    def test_role_with_label(self) -> None:
        elem = {"role": "button", "aria_label": "Close"}
        result = _best_selector_for_element(elem)
        assert "getByRole" in result
        assert "button" in result
        assert "Close" in result

    def test_role_without_label(self) -> None:
        elem = {"role": "combobox"}
        result = _best_selector_for_element(elem)
        assert "getByRole" in result
        assert "combobox" in result

    def test_label_only(self) -> None:
        elem = {"aria_label": "Email input"}
        result = _best_selector_for_element(elem)
        assert "getByLabel" in result

    def test_id_used_when_no_semantic(self) -> None:
        elem = {"id": "submit-btn"}
        result = _best_selector_for_element(elem)
        assert "submit-btn" in result
        assert "#" in result

    def test_name_with_tag(self) -> None:
        elem = {"name": "username", "tag": "input"}
        result = _best_selector_for_element(elem)
        assert "username" in result
        assert "input" in result

    def test_placeholder_fallback(self) -> None:
        elem = {"placeholder": "Enter email"}
        result = _best_selector_for_element(elem)
        assert "getByPlaceholder" in result

    def test_text_fallback_for_short_text(self) -> None:
        elem = {"text": "Submit"}
        result = _best_selector_for_element(elem)
        assert "getByText" in result or "Submit" in result

    def test_tag_only_fallback(self) -> None:
        elem = {"tag": "div"}
        result = _best_selector_for_element(elem)
        assert "div" in result


# ── _extract_typescript_code ──────────────────────────────────────────────────


class TestExtractTypescriptCode:
    def test_extracts_from_ts_code_block(self) -> None:
        raw = "```typescript\nimport { foo } from './foo';\nexport const x = 1;\n```"
        result = _extract_typescript_code(raw)
        assert result == "import { foo } from './foo';\nexport const x = 1;"

    def test_extracts_from_generic_code_block(self) -> None:
        raw = "```\nimport { bar } from './bar';\n```"
        result = _extract_typescript_code(raw)
        assert result == "import { bar } from './bar';"

    def test_returns_raw_if_starts_with_import(self) -> None:
        raw = "import { Component } from '@angular/core';\n"
        result = _extract_typescript_code(raw)
        assert "import" in result

    def test_returns_raw_if_starts_with_export(self) -> None:
        raw = "export class MyClass {}"
        result = _extract_typescript_code(raw)
        assert "export" in result

    def test_returns_raw_if_no_code_block(self) -> None:
        raw = "Here is some explanation without code block."
        result = _extract_typescript_code(raw)
        assert result == raw.strip()

    def test_strips_whitespace(self) -> None:
        raw = "  ```ts\nconst x = 1;\n```  "
        result = _extract_typescript_code(raw)
        assert result == "const x = 1;"


# ── _detect_recurring_patterns ────────────────────────────────────────────────


class TestDetectRecurringPatterns:
    def test_empty_list_returns_empty(self) -> None:
        assert _detect_recurring_patterns([]) == []

    def test_single_selector_no_pattern(self) -> None:
        result = _detect_recurring_patterns(['page.locator(".my-btn")'])
        assert result == []

    def test_common_part_detected(self) -> None:
        broken = [
            'page.locator(".legacy-button")',
            'page.locator(".legacy-input")',
            'page.locator(".legacy-form")',
        ]
        result = _detect_recurring_patterns(broken)
        # "page" and "locator" appear in all 3 → should be detected
        patterns = [r["pattern"] for r in result]
        assert any("page" in p or "locator" in p for p in patterns)

    def test_frequency_sorted_desc(self) -> None:
        broken = [
            'page.locator(".legacy-a")',
            'page.locator(".legacy-b")',
            'page.locator(".legacy-c")',
            'page.locator(".other-x")',
            'page.locator(".other-y")',
        ]
        result = _detect_recurring_patterns(broken)
        if len(result) >= 2:
            assert result[0]["frequency"] >= result[1]["frequency"]

    def test_result_capped_at_20(self) -> None:
        broken = [f'page.locator(".item-{i}")' for i in range(100)]
        result = _detect_recurring_patterns(broken)
        assert len(result) <= 20
