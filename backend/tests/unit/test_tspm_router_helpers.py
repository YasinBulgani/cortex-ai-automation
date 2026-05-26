"""Unit tests for TSPM router pure helper functions.

No DB, no HTTP, no LLM — pure Python only.

Covers:
  app/domains/tspm/router.py:
    _slugify_filename, _header_array_to_dict, _postman_url_to_path,
    _postman_body_to_json, _is_disallowed_api_host, _extract_json_path,
    _sanitize_locator_key, _normalize_xpath, _validate_xpath_syntax,
    _score_xpath, _detect_action_from_step, _build_maviyaka_line,
    _json_compact
"""

from __future__ import annotations

import pytest

from app.domains.tspm.router import (
    _build_maviyaka_line,
    _detect_action_from_step,
    _extract_json_path,
    _header_array_to_dict,
    _is_disallowed_api_host,
    _json_compact,
    _normalize_xpath,
    _postman_body_to_json,
    _postman_url_to_path,
    _sanitize_locator_key,
    _score_xpath,
    _slugify_filename,
    _validate_xpath_syntax,
)


# ── _slugify_filename ─────────────────────────────────────────────────────────


class TestSlugifyFilename:
    def test_basic_ascii(self) -> None:
        assert _slugify_filename("hello world") == "hello_world"

    def test_special_chars_replaced(self) -> None:
        result = _slugify_filename("file/name:here")
        assert "/" not in result
        assert ":" not in result

    def test_dots_and_hyphens_preserved(self) -> None:
        assert _slugify_filename("my-file.txt") == "my-file.txt"

    def test_strips_leading_trailing_dots(self) -> None:
        result = _slugify_filename(".hidden.")
        assert not result.startswith(".")
        assert not result.endswith(".")

    def test_empty_string_returns_artifact(self) -> None:
        assert _slugify_filename("") == "artifact"

    def test_only_special_chars_returns_artifact(self) -> None:
        assert _slugify_filename("!!!") == "artifact"

    def test_alphanumeric_unchanged(self) -> None:
        assert _slugify_filename("MyFile123") == "MyFile123"

    def test_whitespace_only_returns_artifact(self) -> None:
        assert _slugify_filename("   ") == "artifact"

    def test_mixed_unicode_replaced(self) -> None:
        result = _slugify_filename("file@#$%name")
        assert "@" not in result
        assert "#" not in result


# ── _header_array_to_dict ─────────────────────────────────────────────────────


class TestHeaderArrayToDict:
    def test_basic_conversion(self) -> None:
        headers = [{"key": "Content-Type", "value": "application/json"}]
        result = _header_array_to_dict(headers)
        assert result == {"Content-Type": "application/json"}

    def test_none_input_returns_empty(self) -> None:
        assert _header_array_to_dict(None) == {}

    def test_empty_list_returns_empty(self) -> None:
        assert _header_array_to_dict([]) == {}

    def test_disabled_headers_skipped(self) -> None:
        headers = [
            {"key": "Accept", "value": "text/html", "disabled": True},
            {"key": "X-Custom", "value": "123"},
        ]
        result = _header_array_to_dict(headers)
        assert "Accept" not in result
        assert result["X-Custom"] == "123"

    def test_empty_key_skipped(self) -> None:
        headers = [{"key": "", "value": "something"}]
        assert _header_array_to_dict(headers) == {}

    def test_multiple_headers(self) -> None:
        headers = [
            {"key": "Authorization", "value": "Bearer token"},
            {"key": "Accept", "value": "application/json"},
        ]
        result = _header_array_to_dict(headers)
        assert len(result) == 2
        assert result["Authorization"] == "Bearer token"

    def test_value_coerced_to_string(self) -> None:
        headers = [{"key": "X-Count", "value": 42}]
        result = _header_array_to_dict(headers)
        assert result["X-Count"] == "42"

    def test_key_whitespace_stripped(self) -> None:
        headers = [{"key": "  X-Trim  ", "value": "val"}]
        result = _header_array_to_dict(headers)
        assert "X-Trim" in result


# ── _postman_url_to_path ──────────────────────────────────────────────────────


class TestPostmanUrlToPath:
    def test_string_url_extracts_path(self) -> None:
        result = _postman_url_to_path("https://api.example.com/v1/users")
        assert result == "/v1/users"

    def test_string_url_with_query(self) -> None:
        result = _postman_url_to_path("https://api.example.com/search?q=test")
        assert "q=test" in result

    def test_none_returns_slash(self) -> None:
        assert _postman_url_to_path(None) == "/"

    def test_dict_with_path_segments(self) -> None:
        url_obj = {"path": ["api", "v1", "users"]}
        result = _postman_url_to_path(url_obj)
        assert result == "/api/v1/users"

    def test_dict_with_query_params(self) -> None:
        url_obj = {
            "path": ["search"],
            "query": [{"key": "q", "value": "hello"}],
        }
        result = _postman_url_to_path(url_obj)
        assert "q=hello" in result

    def test_dict_disabled_query_skipped(self) -> None:
        url_obj = {
            "path": ["items"],
            "query": [{"key": "page", "value": "1", "disabled": True}],
        }
        result = _postman_url_to_path(url_obj)
        assert "page" not in result

    def test_dict_empty_path_falls_back_to_raw(self) -> None:
        url_obj = {"path": [], "raw": "https://example.com/fallback"}
        result = _postman_url_to_path(url_obj)
        assert result == "/fallback"

    def test_dict_no_path_no_raw_returns_slash(self) -> None:
        result = _postman_url_to_path({})
        assert result == "/"

    def test_invalid_type_returns_slash(self) -> None:
        assert _postman_url_to_path(12345) == "/"  # type: ignore[arg-type]


# ── _postman_body_to_json ─────────────────────────────────────────────────────


class TestPostmanBodyToJson:
    def test_none_input_returns_none(self) -> None:
        assert _postman_body_to_json(None) is None

    def test_empty_dict_returns_none(self) -> None:
        assert _postman_body_to_json({}) is None

    def test_raw_json_mode_returns_dict(self) -> None:
        # Bug fixed: `import json` added to router.py module scope
        body = {"mode": "raw", "raw": '{"key": "value"}'}
        result = _postman_body_to_json(body)
        assert result == {"key": "value"}

    def test_raw_non_dict_wrapped_in_value_key(self) -> None:
        body = {"mode": "raw", "raw": "[1, 2, 3]"}
        result = _postman_body_to_json(body)
        assert result == {"value": [1, 2, 3]}

    def test_raw_invalid_json_returns_raw_key(self) -> None:
        body = {"mode": "raw", "raw": "not-json"}
        result = _postman_body_to_json(body)
        assert result == {"raw": "not-json"}

    def test_raw_empty_string_returns_none(self) -> None:
        body = {"mode": "raw", "raw": "   "}
        assert _postman_body_to_json(body) is None

    def test_urlencoded_mode(self) -> None:
        body = {
            "mode": "urlencoded",
            "urlencoded": [
                {"key": "username", "value": "admin"},
                {"key": "password", "value": "secret"},
            ],
        }
        result = _postman_body_to_json(body)
        assert result == {"username": "admin", "password": "secret"}

    def test_urlencoded_disabled_items_skipped(self) -> None:
        body = {
            "mode": "urlencoded",
            "urlencoded": [
                {"key": "active", "value": "yes"},
                {"key": "skipped", "value": "no", "disabled": True},
            ],
        }
        result = _postman_body_to_json(body)
        assert "skipped" not in result
        assert result["active"] == "yes"

    def test_urlencoded_empty_key_skipped(self) -> None:
        body = {
            "mode": "urlencoded",
            "urlencoded": [{"key": "", "value": "orphan"}],
        }
        assert _postman_body_to_json(body) is None

    def test_formdata_mode_returns_none(self) -> None:
        body = {"mode": "formdata", "formdata": []}
        assert _postman_body_to_json(body) is None


# ── _is_disallowed_api_host ───────────────────────────────────────────────────


class TestIsDisallowedApiHost:
    def test_localhost_allowed(self) -> None:
        assert _is_disallowed_api_host("http://localhost:8080") is False

    def test_127_allowed(self) -> None:
        assert _is_disallowed_api_host("http://127.0.0.1:3000") is False

    def test_public_https_allowed(self) -> None:
        assert _is_disallowed_api_host("https://api.example.com") is False

    def test_private_ip_disallowed(self) -> None:
        assert _is_disallowed_api_host("http://192.168.1.100") is True

    def test_private_10_range_disallowed(self) -> None:
        assert _is_disallowed_api_host("http://10.0.0.5/api") is True

    def test_link_local_disallowed(self) -> None:
        assert _is_disallowed_api_host("http://169.254.0.1") is True

    def test_no_host_returns_false(self) -> None:
        assert _is_disallowed_api_host("not-a-url") is False

    def test_172_16_private_disallowed(self) -> None:
        assert _is_disallowed_api_host("http://172.16.0.1") is True


# ── _extract_json_path ────────────────────────────────────────────────────────


class TestExtractJsonPath:
    def test_simple_key(self) -> None:
        data = {"name": "Alice"}
        assert _extract_json_path(data, "name") == "Alice"

    def test_dollar_prefix(self) -> None:
        data = {"user": {"id": 42}}
        assert _extract_json_path(data, "$.user.id") == 42

    def test_dollar_dot_prefix(self) -> None:
        data = {"status": "ok"}
        assert _extract_json_path(data, "$.status") == "ok"

    def test_nested_path(self) -> None:
        data = {"a": {"b": {"c": "deep"}}}
        assert _extract_json_path(data, "a.b.c") == "deep"

    def test_array_index(self) -> None:
        data = {"items": ["x", "y", "z"]}
        assert _extract_json_path(data, "items[1]") == "y"

    def test_missing_key_raises(self) -> None:
        with pytest.raises(KeyError):
            _extract_json_path({"a": 1}, "b")

    def test_empty_path_returns_data(self) -> None:
        data = {"key": "val"}
        assert _extract_json_path(data, "$") is data

    def test_index_out_of_range_raises(self) -> None:
        data = {"items": [1, 2]}
        with pytest.raises(IndexError):
            _extract_json_path(data, "items[5]")

    def test_non_dict_intermediate_raises(self) -> None:
        data = {"a": "string"}
        with pytest.raises(KeyError):
            _extract_json_path(data, "a.b")


# ── _sanitize_locator_key ─────────────────────────────────────────────────────


class TestSanitizeLocatorKey:
    def test_simple_word(self) -> None:
        assert _sanitize_locator_key("login") == "Login"

    def test_multiple_words_pascal_case(self) -> None:
        assert _sanitize_locator_key("submit button") == "SubmitButton"

    def test_empty_string_returns_fallback(self) -> None:
        assert _sanitize_locator_key("") == "Element"

    def test_custom_fallback(self) -> None:
        assert _sanitize_locator_key("", fallback="MyFallback") == "MyFallback"

    def test_special_chars_stripped(self) -> None:
        result = _sanitize_locator_key("my-button!")
        assert "-" not in result
        assert "!" not in result

    def test_turkish_chars_preserved(self) -> None:
        result = _sanitize_locator_key("giriş yap")
        assert result  # should not be empty/fallback
        assert isinstance(result, str)

    def test_numbers_preserved(self) -> None:
        result = _sanitize_locator_key("form2 submit")
        assert "2" in result or "Form2" in result

    def test_already_pascal(self) -> None:
        result = _sanitize_locator_key("LoginButton")
        assert result == "LoginButton"


# ── _normalize_xpath ──────────────────────────────────────────────────────────


class TestNormalizeXpath:
    def test_strips_html_body_prefix(self) -> None:
        xpath = "/html/body/div/button"
        result = _normalize_xpath(xpath)
        assert not result.startswith("/html")

    def test_strips_html_prefix_without_body(self) -> None:
        xpath = "/html/div/span"
        result = _normalize_xpath(xpath)
        assert not result.startswith("/html")

    def test_relative_xpath_unchanged(self) -> None:
        xpath = "//div[@id='main']"
        result = _normalize_xpath(xpath)
        assert "//div" in result

    def test_text_eq_becomes_normalize_space(self) -> None:
        xpath = "//button[text()='Submit']"
        result = _normalize_xpath(xpath)
        assert "normalize-space()" in result
        assert "text()" not in result

    def test_collapses_whitespace(self) -> None:
        xpath = "//div[  @id  =  'main'  ]"
        result = _normalize_xpath(xpath)
        assert "  " not in result

    def test_empty_returns_empty(self) -> None:
        assert _normalize_xpath("") == ""

    def test_non_string_returns_empty(self) -> None:
        assert _normalize_xpath(None) == ""  # type: ignore[arg-type]

    def test_turkish_literal_wrapped_in_translate(self) -> None:
        xpath = "//button[normalize-space()='Giriş Yap']"
        result = _normalize_xpath(xpath)
        assert "translate(" in result

    def test_no_turkish_chars_not_wrapped(self) -> None:
        xpath = "//button[normalize-space()='Submit']"
        result = _normalize_xpath(xpath)
        assert "translate(" not in result


# ── _validate_xpath_syntax ────────────────────────────────────────────────────


class TestValidateXpathSyntax:
    def test_valid_absolute(self) -> None:
        ok, msg = _validate_xpath_syntax("//div[@id='main']")
        assert ok is True
        assert msg == ""

    def test_valid_relative_dot(self) -> None:
        ok, _ = _validate_xpath_syntax("./span")
        assert ok is True

    def test_empty_string_invalid(self) -> None:
        ok, msg = _validate_xpath_syntax("")
        assert ok is False
        assert msg == "empty"

    def test_non_string_invalid(self) -> None:
        ok, msg = _validate_xpath_syntax(None)  # type: ignore[arg-type]
        assert ok is False

    def test_paren_imbalance(self) -> None:
        ok, msg = _validate_xpath_syntax("//div[contains(@class,'x'")
        assert ok is False
        assert "paren" in msg

    def test_bracket_imbalance(self) -> None:
        ok, msg = _validate_xpath_syntax("//div[@id='a'")
        assert ok is False
        assert "bracket" in msg

    def test_quote_imbalance(self) -> None:
        ok, msg = _validate_xpath_syntax("//div[@id='a]")
        # single quote is odd
        assert ok is False

    def test_css_selector_not_xpath(self) -> None:
        ok, msg = _validate_xpath_syntax("css=.myClass")
        assert ok is False
        assert "not-xpath" in msg

    def test_id_pseudo_not_xpath(self) -> None:
        ok, msg = _validate_xpath_syntax("id=myId")
        assert ok is False

    def test_empty_step_invalid(self) -> None:
        ok, msg = _validate_xpath_syntax("//[something]")
        assert ok is False


# ── _score_xpath ──────────────────────────────────────────────────────────────


class TestScoreXpath:
    def test_empty_returns_invalid(self) -> None:
        result = _score_xpath("")
        assert result["grade"] == "invalid"
        assert result["score"] == 0

    def test_data_testid_boosts_score(self) -> None:
        xpath = "//*[@data-testid='submit-btn']"
        result = _score_xpath(xpath)
        assert result["score"] > 70
        assert "data-testid" in result["strengths"]

    def test_absolute_html_path_penalized(self) -> None:
        xpath = "/html/body/div/button"
        result = _score_xpath(xpath)
        assert result["score"] < 70

    def test_numeric_index_penalized(self) -> None:
        xpath = "//div[3]/button"
        result = _score_xpath(xpath)
        assert any("numeric" in issue or "[n]" in issue for issue in result["issues"])

    def test_aria_label_boosts_score(self) -> None:
        xpath = "//*[@aria-label='Close']"
        result = _score_xpath(xpath)
        assert "aria-label" in result["strengths"]

    def test_normalize_space_boosts_score(self) -> None:
        xpath = "//button[normalize-space()='Submit']"
        result = _score_xpath(xpath)
        assert "normalize-space" in result["strengths"]

    def test_result_has_required_keys(self) -> None:
        result = _score_xpath("//div")
        assert "score" in result
        assert "grade" in result
        assert "issues" in result
        assert "strengths" in result

    def test_good_grade_high_score(self) -> None:
        xpath = "//*[@data-testid='login-btn']"
        result = _score_xpath(xpath)
        assert result["grade"] == "good"

    def test_bad_grade_low_score(self) -> None:
        # Absolute /html path with many levels should score low
        xpath = "/html/body/div/div/div/div/div/div/button[2]"
        result = _score_xpath(xpath)
        assert result["grade"] in ("bad", "warn")

    def test_pseudo_selector_returns_warn(self) -> None:
        result = _score_xpath("css=.myClass")
        assert result["grade"] == "warn"
        assert result["score"] == 30

    def test_score_clamped_0_to_100(self) -> None:
        result = _score_xpath("//div")
        assert 0 <= result["score"] <= 100

    def test_tr_char_without_translate_penalized(self) -> None:
        # Turkish character without translate() should be penalized
        xpath = "//button[normalize-space()='Giriş']"
        result = _score_xpath(xpath)
        assert any("TR" in issue or "translate" in issue for issue in result["issues"])


# ── _detect_action_from_step ──────────────────────────────────────────────────


class TestDetectActionFromStep:
    def test_click_keyword(self) -> None:
        assert _detect_action_from_step("When", "I click on the button") == "click"

    def test_fill_maps_to_input(self) -> None:
        assert _detect_action_from_step("When", "fill in the form field") == "input"

    def test_type_maps_to_input(self) -> None:
        assert _detect_action_from_step("When", "type the username") == "input"

    def test_navigate_maps_to_open(self) -> None:
        assert _detect_action_from_step("Given", "navigate to the homepage") == "open"

    def test_open_maps_to_open(self) -> None:
        assert _detect_action_from_step("Given", "open the url") == "open"

    def test_see_maps_to_see(self) -> None:
        assert _detect_action_from_step("Then", "I see the success message") == "see"

    def test_verify_maps_to_see(self) -> None:
        assert _detect_action_from_step("Then", "verify the title exists") == "see"

    def test_wait_maps_to_wait(self) -> None:
        assert _detect_action_from_step("When", "wait for the loader") == "wait"

    def test_then_fallback_is_see(self) -> None:
        assert _detect_action_from_step("Then", "something vague happens") == "see"

    def test_unknown_fallback_is_click(self) -> None:
        assert _detect_action_from_step("When", "do something unknown") == "click"

    def test_turkish_tikla_maps_to_click(self) -> None:
        assert _detect_action_from_step("When", "butona tıkla") == "click"

    def test_turkish_gir_maps_to_input(self) -> None:
        assert _detect_action_from_step("When", "kullanıcı adını gir") == "input"

    def test_turkish_dogrula_maps_to_see(self) -> None:
        assert _detect_action_from_step("Then", "sonucu dogrula") == "see"


# ── _build_maviyaka_line ──────────────────────────────────────────────────────


class TestBuildMaviyakaLine:
    def test_open_action(self) -> None:
        line = _build_maviyaka_line("open", None, None, "https://example.com")
        assert "Given I open the application url" in line
        assert "https://example.com" in line

    def test_click_action(self) -> None:
        line = _build_maviyaka_line("click", "LoginButton", None, "")
        assert "When I click on" in line
        assert "LoginButton" in line

    def test_input_action_with_value(self) -> None:
        line = _build_maviyaka_line("input", "EmailField", "user@example.com", "")
        assert "When I enter" in line
        assert "user@example.com" in line
        assert "EmailField" in line

    def test_input_action_no_value_uses_placeholder(self) -> None:
        line = _build_maviyaka_line("input", "PasswordField", None, "")
        assert "+-value" in line

    def test_clear_action(self) -> None:
        line = _build_maviyaka_line("clear", "SearchBox", None, "")
        assert "When I clear the input" in line
        assert "SearchBox" in line

    def test_wait_action(self) -> None:
        line = _build_maviyaka_line("wait", "LoadingSpinner", None, "")
        assert "I wait for element" in line
        assert "clickable" in line

    def test_see_action(self) -> None:
        line = _build_maviyaka_line("see", "SuccessMessage", None, "")
        assert "Then I see the element" in line
        assert "SuccessMessage" in line

    def test_verify_action(self) -> None:
        line = _build_maviyaka_line("verify", "Title", "Welcome", "")
        assert "Then I verify element" in line
        assert "Welcome" in line

    def test_no_locator_key_uses_element(self) -> None:
        line = _build_maviyaka_line("click", None, None, "")
        assert '"Element"' in line

    def test_xpath_comment_included(self) -> None:
        line = _build_maviyaka_line(
            "click", "Btn", None, "", xpath="//button[@id='x']"
        )
        assert "# xpath=" in line
        assert "//button[@id='x']" in line

    def test_xpath_quality_grade_in_comment(self) -> None:
        line = _build_maviyaka_line(
            "click", "Btn", None, "",
            xpath="//button",
            xpath_quality={"grade": "warn", "score": 55},
        )
        assert "warn" in line
        assert "55" in line

    def test_no_locator_key_with_locator_action_adds_todo(self) -> None:
        line = _build_maviyaka_line("click", None, None, "")
        assert "TODO" in line

    def test_open_action_no_todo_comment(self) -> None:
        # open action does not need a locator
        line = _build_maviyaka_line("open", None, None, "https://example.com")
        assert "TODO" not in line


# ── _json_compact ─────────────────────────────────────────────────────────────


class TestJsonCompact:
    def test_basic_dict(self) -> None:
        result = _json_compact({"a": 1, "b": 2})
        assert result == '{"a":1,"b":2}'

    def test_list(self) -> None:
        result = _json_compact([1, 2, 3])
        assert result == "[1,2,3]"

    def test_no_extra_spaces(self) -> None:
        result = _json_compact({"key": "value"})
        assert " " not in result

    def test_unicode_preserved(self) -> None:
        result = _json_compact({"name": "Giriş"})
        assert "Giriş" in result
        assert "\\u" not in result

    def test_nested_object(self) -> None:
        result = _json_compact({"a": {"b": "c"}})
        assert result == '{"a":{"b":"c"}}'

    def test_non_serializable_returns_str(self) -> None:
        class Weird:
            pass

        result = _json_compact(Weird())
        assert isinstance(result, str)

    def test_none_value(self) -> None:
        result = _json_compact(None)
        assert result == "null"

    def test_boolean_values(self) -> None:
        result = _json_compact({"flag": True})
        assert "true" in result
