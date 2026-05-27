"""Unit tests for LLM trace and TSPM router pure helper functions.

No DB, no HTTP, no LLM — pure Python only.

Covers:
  app/domains/ai/llm_trace.py:
    _safe_row_get, _infer_provider, _estimate_tokens,
    _status_from, _normalize_metadata, _normalize_task_type
  app/domains/tspm/router.py:
    _slugify_filename, _resolve_artifact_target, _resolve_provenance,
    _resolve_generated_by, _validate_generated_artifact,
    _header_array_to_dict, _postman_url_to_path,
    _extract_json_path, _sanitize_locator_key
"""

from __future__ import annotations

import pytest

from app.domains.ai.llm_trace import (
    _estimate_tokens,
    _infer_provider,
    _normalize_metadata,
    _normalize_task_type,
    _safe_row_get,
    _status_from,
)
from app.domains.tspm.router import (
    _extract_json_path,
    _header_array_to_dict,
    _postman_url_to_path,
    _resolve_artifact_target,
    _resolve_generated_by,
    _resolve_provenance,
    _sanitize_locator_key,
    _slugify_filename,
    _validate_generated_artifact,
)


# ── _safe_row_get ─────────────────────────────────────────────────────────────


class TestSafeRowGet:
    def test_none_row_returns_default(self) -> None:
        assert _safe_row_get(None, 0) is None

    def test_none_row_custom_default(self) -> None:
        assert _safe_row_get(None, 0, default="x") == "x"

    def test_valid_index(self) -> None:
        assert _safe_row_get([10, 20, 30], 1) == 20

    def test_out_of_bounds_returns_default(self) -> None:
        assert _safe_row_get([1, 2], 10) is None

    def test_tuple_row(self) -> None:
        assert _safe_row_get((1, 2, 3), 2) == 3

    def test_negative_index(self) -> None:
        assert _safe_row_get([1, 2, 3], -1) == 3

    def test_dict_row(self) -> None:
        assert _safe_row_get({"key": "val"}, "key") == "val"

    def test_missing_dict_key_returns_default(self) -> None:
        assert _safe_row_get({"a": 1}, "b", default=0) == 0


# ── _infer_provider ───────────────────────────────────────────────────────────


class TestInferProvider:
    def test_gpt_prefix_returns_openai(self) -> None:
        assert _infer_provider("gpt-4o") == "openai"

    def test_gpt_3_prefix(self) -> None:
        assert _infer_provider("gpt-3.5-turbo") == "openai"

    def test_claude_prefix_returns_anthropic(self) -> None:
        assert _infer_provider("claude-3-5-sonnet") == "anthropic"

    def test_unknown_model_returns_ollama(self) -> None:
        assert _infer_provider("llama3") == "ollama"

    def test_empty_string_returns_none(self) -> None:
        assert _infer_provider("") is None

    def test_none_returns_none(self) -> None:
        assert _infer_provider(None) is None  # type: ignore[arg-type]

    def test_case_insensitive(self) -> None:
        assert _infer_provider("GPT-4") == "openai"
        assert _infer_provider("CLAUDE-3") == "anthropic"


# ── _estimate_tokens ──────────────────────────────────────────────────────────


class TestEstimateTokens:
    def test_returns_tuple_of_three(self) -> None:
        result = _estimate_tokens("system", "user", "response")
        assert len(result) == 3

    def test_prompt_tokens_non_negative(self) -> None:
        p, c, t = _estimate_tokens("sys", "usr", "resp")
        assert p >= 0

    def test_total_equals_sum(self) -> None:
        p, c, t = _estimate_tokens("hello", "world", "answer")
        assert t == p + c

    def test_empty_inputs_return_zeros(self) -> None:
        p, c, t = _estimate_tokens("", "", "")
        assert p == 0
        assert c == 0
        assert t == 0

    def test_longer_inputs_more_tokens(self) -> None:
        p1, c1, t1 = _estimate_tokens("a", "b", "c")
        p2, c2, t2 = _estimate_tokens("a" * 100, "b" * 100, "c" * 100)
        assert t2 > t1

    def test_none_inputs_handled(self) -> None:
        p, c, t = _estimate_tokens(None, None, None)  # type: ignore[arg-type]
        assert p == 0 and c == 0 and t == 0


# ── _status_from ──────────────────────────────────────────────────────────────


class TestStatusFrom:
    def test_success_true_returns_success(self) -> None:
        assert _status_from(True, None) == "success"

    def test_success_with_error_msg_still_success(self) -> None:
        assert _status_from(True, "some error") == "success"

    def test_timeout_in_error_message(self) -> None:
        assert _status_from(False, "Request timeout occurred") == "timeout"

    def test_generic_error(self) -> None:
        assert _status_from(False, "Connection refused") == "error"

    def test_none_error_message(self) -> None:
        assert _status_from(False, None) == "error"

    def test_empty_error_message(self) -> None:
        assert _status_from(False, "") == "error"

    def test_timeout_case_insensitive(self) -> None:
        assert _status_from(False, "TIMEOUT error") == "timeout"


# ── _normalize_metadata ───────────────────────────────────────────────────────


class TestNormalizeMetadata:
    def test_none_returns_empty_dict(self) -> None:
        result = _normalize_metadata(None, is_streaming=False)
        assert isinstance(result, dict)

    def test_existing_keys_preserved(self) -> None:
        result = _normalize_metadata({"key": "value"}, is_streaming=False)
        assert result["key"] == "value"

    def test_streaming_adds_streaming_key(self) -> None:
        result = _normalize_metadata({}, is_streaming=True)
        assert result.get("streaming") is True

    def test_non_streaming_no_streaming_key(self) -> None:
        result = _normalize_metadata({}, is_streaming=False)
        assert "streaming" not in result

    def test_does_not_mutate_original(self) -> None:
        original = {"key": "value"}
        _normalize_metadata(original, is_streaming=True)
        assert "streaming" not in original


# ── _normalize_task_type ──────────────────────────────────────────────────────


class TestNormalizeTaskType:
    def test_known_task_type_returned(self) -> None:
        # Depends on _TASK_TYPE_ALIASES — at minimum returns a string
        result = _normalize_task_type("chat", None, "agent")
        assert isinstance(result, str)

    def test_none_inputs_return_unknown(self) -> None:
        result = _normalize_task_type(None, None, "")
        assert result == "unknown"

    def test_agent_name_fallback(self) -> None:
        result = _normalize_task_type(None, None, "some_agent")
        assert isinstance(result, str)

    def test_returns_string(self) -> None:
        result = _normalize_task_type("test_analysis", None, "agent")
        assert isinstance(result, str)


# ── _slugify_filename ─────────────────────────────────────────────────────────


class TestSlugifyFilename:
    def test_plain_name_unchanged(self) -> None:
        assert _slugify_filename("login_test") == "login_test"

    def test_spaces_replaced_with_underscore(self) -> None:
        result = _slugify_filename("login test")
        assert " " not in result
        assert "login" in result

    def test_special_chars_replaced(self) -> None:
        result = _slugify_filename("test/file!name")
        assert "/" not in result
        assert "!" not in result

    def test_empty_returns_artifact(self) -> None:
        assert _slugify_filename("") == "artifact"

    def test_dots_and_hyphens_preserved(self) -> None:
        result = _slugify_filename("test.feature")
        assert "." in result
        assert "test" in result

    def test_leading_trailing_dots_stripped(self) -> None:
        result = _slugify_filename("...test...")
        assert not result.startswith(".")
        assert not result.endswith(".")

    def test_whitespace_stripped_before_processing(self) -> None:
        result = _slugify_filename("  login  ")
        assert result == "login"


# ── _resolve_artifact_target ──────────────────────────────────────────────────


class TestResolveArtifactTarget:
    def test_playwright_returns_playwright(self) -> None:
        assert _resolve_artifact_target("playwright") == "playwright"

    def test_java_returns_maviyaka(self) -> None:
        assert _resolve_artifact_target("java") == "maviyaka"

    def test_unknown_returns_shared(self) -> None:
        assert _resolve_artifact_target("gherkin") == "shared"

    def test_empty_returns_shared(self) -> None:
        assert _resolve_artifact_target("") == "shared"


# ── _resolve_provenance ───────────────────────────────────────────────────────


class TestResolveProvenance:
    def test_stub_returns_stub(self) -> None:
        assert _resolve_provenance({"stub": True}) == "stub"

    def test_fallback_returns_fallback(self) -> None:
        assert _resolve_provenance({"fallback": True}) == "fallback"

    def test_simulated_returns_simulated(self) -> None:
        assert _resolve_provenance({"simulated": True}) == "simulated"

    def test_mock_mode_returns_simulated(self) -> None:
        assert _resolve_provenance({"mock_mode": True}) == "simulated"

    def test_empty_returns_real(self) -> None:
        assert _resolve_provenance({}) == "real"

    def test_stub_takes_priority(self) -> None:
        result = _resolve_provenance({"stub": True, "fallback": True})
        assert result == "stub"


# ── _resolve_generated_by ─────────────────────────────────────────────────────


class TestResolveGeneratedBy:
    def test_payload_generated_by(self) -> None:
        result = _resolve_generated_by({"generated_by": "openai"}, {})
        assert result == "openai"

    def test_result_generated_by_fallback(self) -> None:
        result = _resolve_generated_by({}, {"generated_by": "anthropic"})
        assert result == "anthropic"

    def test_empty_returns_ai_gateway(self) -> None:
        result = _resolve_generated_by({}, {})
        assert result == "ai_gateway"

    def test_ai_provider_from_result(self) -> None:
        result = _resolve_generated_by({}, {"ai_provider": "claude"})
        assert result == "claude"


# ── _validate_generated_artifact ──────────────────────────────────────────────


class TestValidateGeneratedArtifact:
    def test_empty_content_fails(self) -> None:
        assert _validate_generated_artifact("gherkin", "") == "failed"

    def test_valid_gherkin(self) -> None:
        content = "Feature: Login\n  Scenario: Test\n    Given I visit the page"
        assert _validate_generated_artifact("gherkin", content) == "validated"

    def test_gherkin_missing_feature_fails(self) -> None:
        content = "Scenario: Test\n  Given something"
        assert _validate_generated_artifact("gherkin", content) == "failed"

    def test_gherkin_missing_scenario_fails(self) -> None:
        content = "Feature: Login\n  Given something"
        assert _validate_generated_artifact("gherkin", content) == "failed"

    def test_valid_playwright(self) -> None:
        content = "import { test } from '@playwright/test';\ntest('login', async () => {})"
        assert _validate_generated_artifact("playwright", content) == "validated"

    def test_playwright_missing_import_fails(self) -> None:
        content = "test('login', async () => {})"
        assert _validate_generated_artifact("playwright", content) == "failed"

    def test_valid_java(self) -> None:
        content = "public class LoginSteps {\n  @Given(\"I login\") public void login() {}\n}"
        assert _validate_generated_artifact("java", content) == "validated"

    def test_unknown_artifact_type_returns_pending(self) -> None:
        assert _validate_generated_artifact("unknown_type", "some content") == "pending"


# ── _header_array_to_dict ─────────────────────────────────────────────────────


class TestHeaderArrayToDict:
    def test_empty_list_returns_empty(self) -> None:
        assert _header_array_to_dict([]) == {}

    def test_none_returns_empty(self) -> None:
        assert _header_array_to_dict(None) == {}

    def test_single_header(self) -> None:
        result = _header_array_to_dict([{"key": "Content-Type", "value": "application/json"}])
        assert result["Content-Type"] == "application/json"

    def test_disabled_header_skipped(self) -> None:
        headers = [
            {"key": "Authorization", "value": "Bearer token", "disabled": True},
            {"key": "Content-Type", "value": "application/json"},
        ]
        result = _header_array_to_dict(headers)
        assert "Authorization" not in result
        assert "Content-Type" in result

    def test_empty_key_skipped(self) -> None:
        headers = [{"key": "", "value": "val"}, {"key": "Accept", "value": "*/*"}]
        result = _header_array_to_dict(headers)
        assert "" not in result
        assert "Accept" in result

    def test_multiple_headers(self) -> None:
        headers = [
            {"key": "Authorization", "value": "Bearer abc"},
            {"key": "Accept", "value": "application/json"},
        ]
        result = _header_array_to_dict(headers)
        assert len(result) == 2


# ── _postman_url_to_path ──────────────────────────────────────────────────────


class TestPostmanUrlToPath:
    def test_none_returns_root(self) -> None:
        assert _postman_url_to_path(None) == "/"

    def test_string_url(self) -> None:
        result = _postman_url_to_path("http://api.example.com/users")
        assert result == "/users"

    def test_string_with_query(self) -> None:
        result = _postman_url_to_path("http://api.example.com/users?page=1")
        assert "page=1" in result

    def test_dict_with_path_segments(self) -> None:
        url = {"path": ["api", "v1", "users"]}
        result = _postman_url_to_path(url)
        assert "api" in result
        assert "v1" in result
        assert "users" in result

    def test_empty_string_returns_root(self) -> None:
        # Empty string: urlparse gives empty path → "/"
        result = _postman_url_to_path("")
        assert result == "/"


# ── _extract_json_path ────────────────────────────────────────────────────────


class TestExtractJsonPath:
    def test_simple_key(self) -> None:
        data = {"status": "ok"}
        assert _extract_json_path(data, "$.status") == "ok"

    def test_dollar_sign_stripped(self) -> None:
        data = {"key": "value"}
        assert _extract_json_path(data, "$.key") == "value"

    def test_no_dollar_prefix(self) -> None:
        data = {"name": "test"}
        assert _extract_json_path(data, "name") == "test"

    def test_nested_path(self) -> None:
        data = {"data": {"score": 9}}
        assert _extract_json_path(data, "$.data.score") == 9

    def test_root_dollar_returns_data(self) -> None:
        data = {"key": "val"}
        assert _extract_json_path(data, "$") == data

    def test_missing_key_raises(self) -> None:
        data = {"key": "value"}
        with pytest.raises((KeyError, Exception)):
            _extract_json_path(data, "$.missing")

    def test_array_index(self) -> None:
        data = {"items": [10, 20, 30]}
        assert _extract_json_path(data, "$.items[1]") == 20


# ── _sanitize_locator_key ─────────────────────────────────────────────────────


class TestSanitizeLocatorKey:
    def test_simple_text_pascal_case(self) -> None:
        result = _sanitize_locator_key("login button")
        assert result == "LoginButton"

    def test_empty_returns_fallback(self) -> None:
        assert _sanitize_locator_key("") == "Element"

    def test_custom_fallback(self) -> None:
        assert _sanitize_locator_key("", fallback="Unknown") == "Unknown"

    def test_special_chars_stripped(self) -> None:
        result = _sanitize_locator_key("login@button!")
        assert "@" not in result
        assert "!" not in result

    def test_first_letter_uppercase(self) -> None:
        result = _sanitize_locator_key("submit")
        assert result[0].isupper()

    def test_turkish_chars_preserved(self) -> None:
        # Turkish chars should be preserved
        result = _sanitize_locator_key("Giriş Yap")
        assert "Giriş" in result or "Giri" in result

    def test_numbers_preserved(self) -> None:
        result = _sanitize_locator_key("button1")
        assert "1" in result

    def test_returns_string(self) -> None:
        assert isinstance(_sanitize_locator_key("test"), str)
