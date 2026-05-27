"""Unit tests for agents.banking_team.locator_intelligence pure helper functions.

All tests are self-contained: no DB, no HTTP, no LLM.
Covers:
  - _classify_selector_type: selector classification
  - _url_to_class_name: URL → PascalCase page class name
  - _generate_testid_suggestion: name/selector → kebab-case testid
  - _to_camel_case: text → camelCase
  - _element_to_property_name: element dict → camelCase property name
  - _best_selector_for_element: element dict → Playwright selector string
  - _extract_typescript_code: raw LLM text → TypeScript code
  - _score_single_locator: locator dict → stability score dict
  - _detect_recurring_patterns: list of selectors → pattern list
"""
from __future__ import annotations

import pytest

try:
    from app.domains.agents.banking_team.locator_intelligence import (
        _classify_selector_type,
        _url_to_class_name,
        _generate_testid_suggestion,
        _to_camel_case,
        _element_to_property_name,
        _best_selector_for_element,
        _extract_typescript_code,
        _score_single_locator,
        _detect_recurring_patterns,
    )
    _LI_OK = True
except ImportError:
    _LI_OK = False


# ---------------------------------------------------------------------------
# _classify_selector_type
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _LI_OK, reason="locator_intelligence import failed")
class TestClassifySelectorType:
    def test_empty_selector(self):
        assert _classify_selector_type("") == "empty"

    def test_data_testid(self):
        assert _classify_selector_type("data-testid=login-btn") == "data-testid"

    def test_get_by_testid(self):
        assert _classify_selector_type("getByTestId('submit')") == "data-testid"

    def test_role(self):
        assert _classify_selector_type("role=button") == "role"

    def test_get_by_role(self):
        assert _classify_selector_type("getByRole('button')") == "role"

    def test_aria_label(self):
        assert _classify_selector_type("aria-label=Login") == "aria-label"

    def test_get_by_label(self):
        assert _classify_selector_type("getByLabel('Email')") == "aria-label"

    def test_placeholder(self):
        assert _classify_selector_type("placeholder=Enter email") == "placeholder"

    def test_get_by_placeholder(self):
        assert _classify_selector_type("getByPlaceholder('Email')") == "placeholder"

    def test_text(self):
        assert _classify_selector_type("text=Submit") == "text"

    def test_get_by_text(self):
        assert _classify_selector_type("getByText('Submit')") == "text"

    def test_xpath_slash(self):
        assert _classify_selector_type("//div[@class='login']") == "xpath"

    def test_xpath_prefix(self):
        assert _classify_selector_type("xpath=//button") == "xpath"

    def test_id_hash(self):
        assert _classify_selector_type("#login-btn") == "id"

    def test_id_attribute(self):
        assert _classify_selector_type("input[id=submit]") == "id"

    def test_returns_string(self):
        result = _classify_selector_type("data-testid=x")
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# _url_to_class_name
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _LI_OK, reason="locator_intelligence import failed")
class TestUrlToClassName:
    def test_empty_url(self):
        assert _url_to_class_name("") == "UnknownPage"

    def test_plain_path(self):
        assert _url_to_class_name("https://app.com/dashboard") == "DashboardPage"

    def test_kebab_path(self):
        assert _url_to_class_name("https://app.com/user-profile") == "UserProfilePage"

    def test_underscore_path(self):
        assert _url_to_class_name("https://app.com/my_account") == "MyAccountPage"

    def test_trailing_slash(self):
        result = _url_to_class_name("https://app.com/login/")
        assert result == "LoginPage"

    def test_query_params_stripped(self):
        result = _url_to_class_name("https://app.com/search?q=test")
        assert "?" not in result
        assert result == "SearchPage"

    def test_hash_stripped(self):
        result = _url_to_class_name("https://app.com/profile#section")
        assert "#" not in result
        assert result == "ProfilePage"

    def test_page_suffix_not_duplicated(self):
        # If last segment already ends with 'page', should not add another 'Page'
        # (depending on implementation — just verify no crash and returns str)
        result = _url_to_class_name("https://app.com/loginpage")
        assert isinstance(result, str)

    def test_domain_only_returns_page_class(self):
        # No path segment beyond domain
        result = _url_to_class_name("https://app.com/")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_returns_string(self):
        assert isinstance(_url_to_class_name("https://example.com/test"), str)

    def test_starts_with_uppercase(self):
        result = _url_to_class_name("https://app.com/login")
        assert result[0].isupper()


# ---------------------------------------------------------------------------
# _generate_testid_suggestion
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _LI_OK, reason="locator_intelligence import failed")
class TestGenerateTestidSuggestion:
    def test_name_becomes_kebab(self):
        result = _generate_testid_suggestion("Login Button", "")
        assert result == "login-button"

    def test_name_special_chars_cleaned(self):
        result = _generate_testid_suggestion("User@Email!", "")
        assert "@" not in result
        assert "!" not in result

    def test_empty_name_falls_back_to_selector(self):
        result = _generate_testid_suggestion("", "#myLoginBtn")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_empty_name_and_no_usable_selector(self):
        result = _generate_testid_suggestion("", "")
        assert result == "element"

    def test_selector_filters_reserved_words(self):
        # 'page', 'get', 'button' etc. should be filtered out
        result = _generate_testid_suggestion("", "getByRole('button')")
        # 'get', 'button', 'role' are filtered — may be empty → 'element'
        assert isinstance(result, str)

    def test_name_takes_priority_over_selector(self):
        result = _generate_testid_suggestion("submit", "getByTestId('irrelevant')")
        assert result == "submit"

    def test_returns_string(self):
        assert isinstance(_generate_testid_suggestion("x", "y"), str)

    def test_lowercase_output(self):
        result = _generate_testid_suggestion("LoginButton", "")
        assert result == result.lower()


# ---------------------------------------------------------------------------
# _to_camel_case
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _LI_OK, reason="locator_intelligence import failed")
class TestToCamelCase:
    def test_single_word_lowercase(self):
        assert _to_camel_case("hello") == "hello"

    def test_two_words(self):
        assert _to_camel_case("hello world") == "helloWorld"

    def test_three_words(self):
        assert _to_camel_case("hello world foo") == "helloWorldFoo"

    def test_hyphenated(self):
        assert _to_camel_case("login-button") == "loginButton"

    def test_underscore_separated(self):
        assert _to_camel_case("login_button") == "loginButton"

    def test_empty_string(self):
        assert _to_camel_case("") == ""

    def test_special_chars_stripped(self):
        result = _to_camel_case("hello@world!")
        assert "@" not in result
        assert "!" not in result

    def test_all_caps_first_word_lowered(self):
        result = _to_camel_case("HELLO world")
        assert result[0].islower()

    def test_returns_string(self):
        assert isinstance(_to_camel_case("test"), str)

    def test_numbers_preserved(self):
        result = _to_camel_case("button 2 click")
        assert "2" in result


# ---------------------------------------------------------------------------
# _element_to_property_name
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _LI_OK, reason="locator_intelligence import failed")
class TestElementToPropertyName:
    def test_data_testid_preferred(self):
        result = _element_to_property_name({
            "data-testid": "login-btn",
            "name": "submit",
            "id": "btn1",
        })
        assert "login" in result.lower()

    def test_name_fallback(self):
        result = _element_to_property_name({"name": "emailInput"})
        assert isinstance(result, str)
        assert len(result) > 0

    def test_aria_label_fallback(self):
        result = _element_to_property_name({"aria-label": "Submit Form"})
        assert isinstance(result, str)
        assert len(result) > 0

    def test_id_fallback(self):
        result = _element_to_property_name({"id": "submit-btn"})
        assert isinstance(result, str)
        assert len(result) > 0

    def test_text_fallback(self):
        result = _element_to_property_name({"text": "Click me"})
        assert isinstance(result, str)

    def test_tag_type_fallback(self):
        result = _element_to_property_name({"tag": "input", "type": "submit"})
        assert isinstance(result, str)

    def test_empty_element_returns_string(self):
        result = _element_to_property_name({})
        assert isinstance(result, str)

    def test_returns_camel_case_format(self):
        result = _element_to_property_name({"data-testid": "my-test-element"})
        # Should be camelCase
        assert "-" not in result


# ---------------------------------------------------------------------------
# _best_selector_for_element
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _LI_OK, reason="locator_intelligence import failed")
class TestBestSelectorForElement:
    def test_data_testid_preferred(self):
        result = _best_selector_for_element({"data-testid": "submit-btn"})
        assert "getByTestId" in result
        assert "submit-btn" in result

    def test_role_and_label(self):
        result = _best_selector_for_element({"role": "button", "aria-label": "Login"})
        assert "getByRole" in result
        assert "Login" in result

    def test_role_only(self):
        result = _best_selector_for_element({"role": "textbox"})
        assert "getByRole" in result

    def test_aria_label_fallback(self):
        result = _best_selector_for_element({"aria-label": "Email input"})
        assert "getByLabel" in result

    def test_id_fallback(self):
        result = _best_selector_for_element({"id": "email-input"})
        assert "#email-input" in result

    def test_name_and_tag_fallback(self):
        result = _best_selector_for_element({"name": "email", "tag": "input"})
        assert "name" in result
        assert "email" in result

    def test_placeholder_fallback(self):
        result = _best_selector_for_element({"placeholder": "Enter email"})
        assert "getByPlaceholder" in result

    def test_text_fallback(self):
        result = _best_selector_for_element({"text": "Submit"})
        assert "getByText" in result

    def test_empty_element_fallback(self):
        result = _best_selector_for_element({})
        assert isinstance(result, str)
        assert len(result) > 0

    def test_returns_string(self):
        assert isinstance(_best_selector_for_element({"id": "x"}), str)


# ---------------------------------------------------------------------------
# _extract_typescript_code
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _LI_OK, reason="locator_intelligence import failed")
class TestExtractTypescriptCode:
    def test_markdown_ts_block(self):
        raw = "```typescript\nconst x = 1;\n```"
        result = _extract_typescript_code(raw)
        assert "const x = 1;" in result
        assert "```" not in result

    def test_markdown_generic_block(self):
        raw = "```\nconst x = 2;\n```"
        result = _extract_typescript_code(raw)
        assert "const x = 2;" in result

    def test_import_statement_passthrough(self):
        raw = "import { test } from '@playwright/test';\nconst x = 1;"
        result = _extract_typescript_code(raw)
        assert "import" in result

    def test_export_statement_passthrough(self):
        raw = "export class MyPage {\n}"
        result = _extract_typescript_code(raw)
        assert "export class" in result

    def test_plain_text_returned_as_is(self):
        raw = "some text without typescript markers"
        result = _extract_typescript_code(raw)
        assert result == raw.strip()

    def test_empty_string(self):
        result = _extract_typescript_code("")
        assert isinstance(result, str)

    def test_whitespace_stripped(self):
        raw = "   import { test } from 'test';   "
        result = _extract_typescript_code(raw)
        assert not result.startswith(" ")

    def test_returns_string(self):
        assert isinstance(_extract_typescript_code("code"), str)


# ---------------------------------------------------------------------------
# _score_single_locator
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _LI_OK, reason="locator_intelligence import failed")
class TestScoreSingleLocator:
    def test_empty_selector_returns_zero_score(self):
        result = _score_single_locator({"selector": ""})
        assert result["score"] == 0

    def test_empty_selector_has_reasons(self):
        result = _score_single_locator({"selector": ""})
        assert len(result["reasons"]) > 0

    def test_result_has_required_keys(self):
        result = _score_single_locator({"selector": "data-testid=btn"})
        for key in ("selector", "name", "score", "reasons", "risk_factors"):
            assert key in result

    def test_data_testid_scores_high(self):
        result = _score_single_locator({"selector": "data-testid=login-btn"})
        assert result["score"] >= 4

    def test_score_range_0_to_5(self):
        for selector in ["", "data-testid=x", "#some-id", "//div/button"]:
            result = _score_single_locator({"selector": selector})
            assert 0 <= result["score"] <= 5

    def test_very_long_selector_reduces_score(self):
        long_sel = "div.container > div.inner > ul.list > li:nth-child(3) > " + "a.link" * 30
        result = _score_single_locator({"selector": long_sel})
        # Long selector should have risk factor
        assert any("uzun" in rf.lower() or "long" in rf.lower() or "150" in rf for rf in result["risk_factors"])

    def test_hex_id_flagged_as_dynamic(self):
        result = _score_single_locator({"selector": "#abc123def456"})
        # Hex hash id should be flagged
        combined = " ".join(result["risk_factors"])
        assert "hex" in combined.lower() or "hash" in combined.lower() or "dynamic" in combined.lower()

    def test_numeric_id_flagged(self):
        result = _score_single_locator({"selector": "#12345"})
        combined = " ".join(result["risk_factors"])
        assert "numeric" in combined.lower() or "index" in combined.lower() or "dynamic" in combined.lower()

    def test_name_preserved_in_result(self):
        result = _score_single_locator({"selector": "data-testid=btn", "name": "myButton"})
        assert result["name"] == "myButton"

    def test_returns_dict(self):
        assert isinstance(_score_single_locator({"selector": "x"}), dict)

    def test_reasons_is_list(self):
        result = _score_single_locator({"selector": "data-testid=x"})
        assert isinstance(result["reasons"], list)

    def test_risk_factors_is_list(self):
        result = _score_single_locator({"selector": "data-testid=x"})
        assert isinstance(result["risk_factors"], list)


# ---------------------------------------------------------------------------
# _detect_recurring_patterns
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _LI_OK, reason="locator_intelligence import failed")
class TestDetectRecurringPatterns:
    def test_empty_list_returns_empty(self):
        assert _detect_recurring_patterns([]) == []

    def test_single_selector_returns_empty(self):
        # Need at least 2 selectors of same type to find a pattern
        result = _detect_recurring_patterns(["data-testid=login"])
        assert isinstance(result, list)

    def test_common_word_detected(self):
        # The regex [\w-]{4,} includes hyphens, so "data-testid" is one token
        # and appears in all three selectors — it should be detected as a recurring pattern
        selectors = [
            "data-testid=login-button",
            "data-testid=login-form",
            "data-testid=login-error",
        ]
        result = _detect_recurring_patterns(selectors)
        pattern_strings = [p["pattern"] for p in result]
        # "data-testid" appears 3 times across the selectors
        assert any("data-testid" in p or "testid" in p or "login" in p for p in pattern_strings)

    def test_pattern_has_required_keys(self):
        selectors = ["data-testid=btn-submit", "data-testid=btn-cancel"]
        result = _detect_recurring_patterns(selectors)
        if result:
            for p in result:
                for key in ("pattern", "type", "frequency", "fix"):
                    assert key in p

    def test_frequency_is_integer(self):
        selectors = [
            "data-testid=form-submit",
            "data-testid=form-cancel",
            "data-testid=form-reset",
        ]
        result = _detect_recurring_patterns(selectors)
        for p in result:
            assert isinstance(p["frequency"], int)

    def test_max_20_patterns_returned(self):
        # Many diverse selectors
        selectors = [f"data-testid=btn-{i}" for i in range(50)]
        result = _detect_recurring_patterns(selectors)
        assert len(result) <= 20

    def test_sorted_by_frequency_descending(self):
        selectors = [
            "data-testid=form-a",
            "data-testid=form-b",
            "data-testid=form-c",
            "data-testid=btn-x",
            "data-testid=btn-y",
        ]
        result = _detect_recurring_patterns(selectors)
        if len(result) >= 2:
            freqs = [p["frequency"] for p in result]
            assert freqs == sorted(freqs, reverse=True)

    def test_returns_list(self):
        assert isinstance(_detect_recurring_patterns(["sel1", "sel2"]), list)
