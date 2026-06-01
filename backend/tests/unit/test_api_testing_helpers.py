"""Unit tests for API Testing domain pure helpers.

Covers two modules — no DB, no HTTP, no LLM:

  app/domains/api_testing/assertion_suggester.py
    _existing_assertion_types, _suggest_status_code, _suggest_content_type,
    _suggest_response_time, _suggest_pii_checks, _suggest_financial_checks

  app/domains/api_testing/security_scanner.py
    _is_banking_sensitive, _count_schema_properties,
    _has_path_id_param, _get_param_names
"""

from __future__ import annotations

import pytest

from app.domains.api_testing.assertion_suggester import (
    CAT_COMPLIANCE,
    CAT_FUNCTIONAL,
    CAT_PERFORMANCE,
    CAT_SECURITY,
    PRIORITY_CRITICAL,
    PRIORITY_HIGH,
    PRIORITY_MEDIUM,
    _existing_assertion_types,
    _suggest_content_type,
    _suggest_financial_checks,
    _suggest_pii_checks,
    _suggest_response_time,
    _suggest_status_code,
)
from app.domains.api_testing.security_scanner import (
    _count_schema_properties,
    _get_param_names,
    _has_path_id_param,
    _is_banking_sensitive,
)


# ============================================================================
# assertion_suggester — _existing_assertion_types
# ============================================================================


class TestExistingAssertionTypes:
    def test_empty_list_returns_empty_dict(self) -> None:
        assert _existing_assertion_types([]) == {}

    def test_single_assertion_creates_one_key(self) -> None:
        result = _existing_assertion_types([{"type": "status_code", "expected": 200}])
        assert "status_code" in result
        assert len(result["status_code"]) == 1

    def test_groups_same_types_together(self) -> None:
        assertions = [
            {"type": "status_code", "expected": 200},
            {"type": "status_code", "expected": 201},
            {"type": "header", "key": "Content-Type"},
        ]
        index = _existing_assertion_types(assertions)
        assert len(index["status_code"]) == 2
        assert len(index["header"]) == 1

    def test_missing_type_key_uses_empty_string(self) -> None:
        assertions = [{"expected": 200}]
        index = _existing_assertion_types(assertions)
        assert "" in index
        assert len(index[""]) == 1

    def test_each_value_is_list(self) -> None:
        assertions = [{"type": "json_path", "path": "$.id"}]
        index = _existing_assertion_types(assertions)
        assert isinstance(index["json_path"], list)

    def test_original_dicts_preserved_in_lists(self) -> None:
        a = {"type": "schema", "expected": {"type": "object"}}
        index = _existing_assertion_types([a])
        assert index["schema"][0] is a

    def test_multiple_distinct_types(self) -> None:
        assertions = [
            {"type": "status_code"},
            {"type": "header"},
            {"type": "json_path"},
            {"type": "schema"},
            {"type": "performance"},
        ]
        index = _existing_assertion_types(assertions)
        assert len(index) == 5

    def test_three_of_same_type(self) -> None:
        assertions = [{"type": "regex"}, {"type": "regex"}, {"type": "regex"}]
        index = _existing_assertion_types(assertions)
        assert len(index["regex"]) == 3


# ============================================================================
# assertion_suggester — _suggest_status_code
# ============================================================================


class TestSuggestStatusCode:
    def test_returns_empty_when_status_code_already_in_existing(self) -> None:
        existing = {"status_code": [{"type": "status_code", "expected": 200}]}
        assert _suggest_status_code("positive", existing) == []

    def test_positive_type_suggests_one_of_with_200(self) -> None:
        suggestions = _suggest_status_code("positive", {})
        assert len(suggestions) == 1
        s = suggestions[0]
        assert s["operator"] == "one_of"
        assert 200 in s["expected"]

    def test_positive_type_includes_201_and_204(self) -> None:
        s = _suggest_status_code("positive", {})[0]
        assert 201 in s["expected"]
        assert 204 in s["expected"]

    def test_security_type_suggests_401_and_403(self) -> None:
        s = _suggest_status_code("security", {})[0]
        assert 401 in s["expected"]
        assert 403 in s["expected"]

    def test_negative_type_suggests_4xx_codes(self) -> None:
        s = _suggest_status_code("negative", {})[0]
        assert all(c >= 400 for c in s["expected"])

    def test_performance_type_uses_eq_operator_200(self) -> None:
        s = _suggest_status_code("performance", {})[0]
        assert s["operator"] == "eq"
        assert s["expected"] == 200

    def test_regression_type_uses_eq_operator_200(self) -> None:
        s = _suggest_status_code("regression", {})[0]
        assert s["operator"] == "eq"
        assert s["expected"] == 200

    def test_boundary_type_suggests_400_and_422(self) -> None:
        s = _suggest_status_code("boundary", {})[0]
        assert 400 in s["expected"]
        assert 422 in s["expected"]

    def test_unknown_type_falls_back_to_200_eq(self) -> None:
        s = _suggest_status_code("nonexistent_type", {})[0]
        assert s["operator"] == "eq"
        assert s["expected"] == 200

    def test_priority_is_always_critical(self) -> None:
        for test_type in ("positive", "negative", "security", "boundary"):
            s = _suggest_status_code(test_type, {})[0]
            assert s["priority"] == PRIORITY_CRITICAL

    def test_type_field_is_status_code(self) -> None:
        s = _suggest_status_code("positive", {})[0]
        assert s["type"] == "status_code"

    def test_category_is_functional(self) -> None:
        s = _suggest_status_code("positive", {})[0]
        assert s["category"] == CAT_FUNCTIONAL

    def test_compliance_type_suggests_200_201(self) -> None:
        s = _suggest_status_code("compliance", {})[0]
        assert 200 in s["expected"]
        assert 201 in s["expected"]


# ============================================================================
# assertion_suggester — _suggest_content_type
# ============================================================================


class TestSuggestContentType:
    def test_suggests_when_no_assertions(self) -> None:
        suggestions = _suggest_content_type({})
        assert len(suggestions) == 1

    def test_suggested_field_is_content_type(self) -> None:
        s = _suggest_content_type({})[0]
        assert s["field"] == "Content-Type"

    def test_expected_contains_application_json(self) -> None:
        s = _suggest_content_type({})[0]
        assert "application/json" in str(s["expected"])

    def test_operator_is_contains(self) -> None:
        s = _suggest_content_type({})[0]
        assert s["operator"] == "contains"

    def test_skips_when_content_type_assertion_exists(self) -> None:
        existing = {"content_type": [{"type": "content_type"}]}
        assert _suggest_content_type(existing) == []

    def test_skips_when_header_has_content_type_key(self) -> None:
        existing = {"header": [{"key": "content-type", "expected": "application/json"}]}
        assert _suggest_content_type(existing) == []

    def test_skips_when_header_has_content_type_path(self) -> None:
        existing = {"header": [{"path": "Content-Type"}]}
        assert _suggest_content_type(existing) == []

    def test_does_not_skip_when_header_is_authorization(self) -> None:
        existing = {"header": [{"key": "Authorization"}]}
        assert len(_suggest_content_type(existing)) == 1

    def test_priority_is_high(self) -> None:
        s = _suggest_content_type({})[0]
        assert s["priority"] == PRIORITY_HIGH

    def test_category_is_functional(self) -> None:
        s = _suggest_content_type({})[0]
        assert s["category"] == CAT_FUNCTIONAL

    def test_type_is_header(self) -> None:
        s = _suggest_content_type({})[0]
        assert s["type"] == "header"


# ============================================================================
# assertion_suggester — _suggest_response_time
# ============================================================================


class TestSuggestResponseTime:
    def test_critical_risk_threshold_is_500(self) -> None:
        s = _suggest_response_time("critical", {})[0]
        assert s["expected"] == 500

    def test_high_risk_threshold_is_500(self) -> None:
        s = _suggest_response_time("high", {})[0]
        assert s["expected"] == 500

    def test_medium_risk_threshold_is_2000(self) -> None:
        s = _suggest_response_time("medium", {})[0]
        assert s["expected"] == 2000

    def test_low_risk_threshold_is_2000(self) -> None:
        s = _suggest_response_time("low", {})[0]
        assert s["expected"] == 2000

    def test_unknown_risk_threshold_is_2000(self) -> None:
        s = _suggest_response_time("unknown", {})[0]
        assert s["expected"] == 2000

    def test_skips_when_response_time_already_present(self) -> None:
        existing = {"response_time": [{"type": "response_time"}]}
        assert _suggest_response_time("critical", existing) == []

    def test_type_is_performance(self) -> None:
        s = _suggest_response_time("high", {})[0]
        assert s["type"] == "performance"

    def test_field_is_response_time(self) -> None:
        s = _suggest_response_time("high", {})[0]
        assert s["field"] == "response_time"

    def test_operator_is_lt(self) -> None:
        s = _suggest_response_time("critical", {})[0]
        assert s["operator"] == "lt"

    def test_category_is_performance(self) -> None:
        s = _suggest_response_time("medium", {})[0]
        assert s["category"] == CAT_PERFORMANCE

    def test_critical_high_priority_is_high(self) -> None:
        for level in ("critical", "high"):
            s = _suggest_response_time(level, {})[0]
            assert s["priority"] == PRIORITY_HIGH

    def test_medium_low_priority_is_medium(self) -> None:
        for level in ("medium", "low"):
            s = _suggest_response_time(level, {})[0]
            assert s["priority"] == PRIORITY_MEDIUM

    def test_reason_contains_risk_level(self) -> None:
        s = _suggest_response_time("critical", {})[0]
        assert "critical" in s["reason"]

    def test_reason_contains_threshold(self) -> None:
        s = _suggest_response_time("high", {})[0]
        assert "500" in s["reason"]


# ============================================================================
# assertion_suggester — _suggest_pii_checks
# ============================================================================


class TestSuggestPiiChecks:
    def test_no_pii_returns_empty(self) -> None:
        assert _suggest_pii_checks("negative", False, {}) == []

    def test_positive_type_with_pii_returns_empty(self) -> None:
        assert _suggest_pii_checks("positive", True, {}) == []

    def test_compliance_type_with_pii_returns_empty(self) -> None:
        # "compliance" is not in NEGATIVE_TEST_TYPES
        assert _suggest_pii_checks("compliance", True, {}) == []

    def test_negative_type_with_pii_returns_suggestions(self) -> None:
        suggestions = _suggest_pii_checks("negative", True, {})
        assert len(suggestions) > 0

    def test_security_type_with_pii_returns_suggestions(self) -> None:
        suggestions = _suggest_pii_checks("security", True, {})
        assert len(suggestions) > 0

    def test_boundary_type_with_pii_returns_suggestions(self) -> None:
        suggestions = _suggest_pii_checks("boundary", True, {})
        assert len(suggestions) > 0

    def test_suggestion_type_is_security(self) -> None:
        suggestions = _suggest_pii_checks("negative", True, {})
        for s in suggestions:
            assert s["type"] == "security"

    def test_suggestion_priority_is_critical(self) -> None:
        suggestions = _suggest_pii_checks("negative", True, {})
        for s in suggestions:
            assert s["priority"] == PRIORITY_CRITICAL

    def test_suggestion_category_is_compliance(self) -> None:
        suggestions = _suggest_pii_checks("negative", True, {})
        for s in suggestions:
            assert s["category"] == CAT_COMPLIANCE

    def test_operator_is_not_exists(self) -> None:
        suggestions = _suggest_pii_checks("negative", True, {})
        for s in suggestions:
            assert s["operator"] == "not_exists"

    def test_max_8_suggestions_returned(self) -> None:
        suggestions = _suggest_pii_checks("negative", True, {})
        assert len(suggestions) <= 8

    def test_already_checked_field_not_re_suggested(self) -> None:
        existing = {"json_path": [{"path": "$.tc_kimlik"}]}
        suggestions = _suggest_pii_checks("negative", True, existing)
        fields = [s["field"] for s in suggestions]
        assert "$.tc_kimlik" not in fields

    def test_not_exists_assertion_blocks_re_suggestion(self) -> None:
        existing = {"not_exists": [{"path": "$.tckn"}]}
        suggestions = _suggest_pii_checks("negative", True, existing)
        fields = [s["field"] for s in suggestions]
        assert "$.tckn" not in fields

    def test_reason_contains_kvkk(self) -> None:
        suggestions = _suggest_pii_checks("negative", True, {})
        assert any("KVKK" in s["reason"] for s in suggestions)


# ============================================================================
# assertion_suggester — _suggest_financial_checks
# ============================================================================


class TestSuggestFinancialChecks:
    def test_no_financial_returns_empty(self) -> None:
        assert _suggest_financial_checks(False, None, {}) == []

    def test_financial_true_returns_suggestions(self) -> None:
        suggestions = _suggest_financial_checks(True, None, {})
        assert len(suggestions) > 0

    def test_regex_suggestions_for_decimal_precision(self) -> None:
        suggestions = _suggest_financial_checks(True, None, {})
        regex_suggs = [s for s in suggestions if s["type"] == "regex"]
        assert len(regex_suggs) > 0

    def test_decimal_pattern_requires_two_places(self) -> None:
        suggestions = _suggest_financial_checks(True, None, {})
        regex_suggs = [s for s in suggestions if s["type"] == "regex"]
        assert all(r"\d{2}" in s["expected"] for s in regex_suggs)

    def test_currency_format_suggested(self) -> None:
        suggestions = _suggest_financial_checks(True, None, {})
        currency = [s for s in suggestions if "currency" in s.get("field", "")]
        assert len(currency) >= 1

    def test_currency_suggestion_is_json_path_type(self) -> None:
        suggestions = _suggest_financial_checks(True, None, {})
        currency = [s for s in suggestions if "currency" in s.get("field", "")]
        assert currency[0]["type"] == "json_path"

    def test_all_suggestions_category_is_compliance(self) -> None:
        suggestions = _suggest_financial_checks(True, None, {})
        for s in suggestions:
            assert s["category"] == CAT_COMPLIANCE

    def test_balance_field_not_re_suggested_when_in_existing_json_path(self) -> None:
        existing = {"json_path": [{"path": "$.data.balance"}]}
        suggestions = _suggest_financial_checks(True, None, existing)
        fields = [s["field"] for s in suggestions]
        assert "$.data.balance" not in fields

    def test_balance_field_not_re_suggested_when_in_existing_regex(self) -> None:
        existing = {"regex": [{"field": "balance"}]}
        suggestions = _suggest_financial_checks(True, None, existing)
        fields = [s.get("field", "") for s in suggestions]
        # The field "$.data.balance" should be suppressed
        assert "$.data.balance" not in fields

    def test_currency_not_re_suggested_when_already_in_json_path(self) -> None:
        existing = {"json_path": [{"path": "$.data.currency"}]}
        suggestions = _suggest_financial_checks(True, None, existing)
        currency = [s for s in suggestions if "currency" in s.get("field", "")]
        assert len(currency) == 0

    def test_financial_checks_cap_at_six_regex(self) -> None:
        suggestions = _suggest_financial_checks(True, None, {})
        regex_suggs = [s for s in suggestions if s["type"] == "regex"]
        assert len(regex_suggs) <= 6

    def test_reason_contains_bddk(self) -> None:
        suggestions = _suggest_financial_checks(True, None, {})
        regex_suggs = [s for s in suggestions if s["type"] == "regex"]
        assert all("BDDK" in s["reason"] for s in regex_suggs)


# ============================================================================
# security_scanner — _is_banking_sensitive
# ============================================================================


class TestIsBankingSensitive:
    def test_transfer_returns_true(self) -> None:
        assert _is_banking_sensitive("/api/transfer") is True

    def test_payment_returns_true(self) -> None:
        assert _is_banking_sensitive("/api/payment/process") is True

    def test_havale_returns_true(self) -> None:
        assert _is_banking_sensitive("/api/havale") is True

    def test_eft_returns_true(self) -> None:
        assert _is_banking_sensitive("/api/eft/send") is True

    def test_odeme_returns_true(self) -> None:
        assert _is_banking_sensitive("/api/odeme") is True

    def test_bakiye_returns_true(self) -> None:
        assert _is_banking_sensitive("/api/bakiye") is True

    def test_balance_returns_true(self) -> None:
        assert _is_banking_sensitive("/api/account/balance") is True

    def test_hesap_returns_true(self) -> None:
        assert _is_banking_sensitive("/api/hesap/detay") is True

    def test_account_returns_true(self) -> None:
        assert _is_banking_sensitive("/api/account/list") is True

    def test_kredi_returns_true(self) -> None:
        assert _is_banking_sensitive("/api/kredi/basvuru") is True

    def test_credit_returns_true(self) -> None:
        assert _is_banking_sensitive("/api/credit/score") is True

    def test_deposit_returns_true(self) -> None:
        assert _is_banking_sensitive("/api/deposit") is True

    def test_withdraw_returns_true(self) -> None:
        assert _is_banking_sensitive("/api/withdraw") is True

    def test_fatura_returns_true(self) -> None:
        assert _is_banking_sensitive("/api/fatura/odeme") is True

    def test_invoice_returns_true(self) -> None:
        assert _is_banking_sensitive("/api/invoice/create") is True

    def test_pos_returns_true(self) -> None:
        assert _is_banking_sensitive("/api/pos-terminal") is True

    def test_atm_returns_true(self) -> None:
        assert _is_banking_sensitive("/api/atm/locations") is True

    def test_case_insensitive_match(self) -> None:
        assert _is_banking_sensitive("/API/TRANSFER") is True
        assert _is_banking_sensitive("/Api/Balance") is True

    def test_users_profile_returns_false(self) -> None:
        assert _is_banking_sensitive("/api/users/profile") is False

    def test_health_returns_false(self) -> None:
        assert _is_banking_sensitive("/health") is False

    def test_empty_string_returns_false(self) -> None:
        assert _is_banking_sensitive("") is False

    def test_reports_summary_returns_false(self) -> None:
        assert _is_banking_sensitive("/api/reports/summary") is False

    def test_returns_bool_type(self) -> None:
        assert isinstance(_is_banking_sensitive("/api/transfer"), bool)
        assert isinstance(_is_banking_sensitive("/api/users"), bool)


# ============================================================================
# security_scanner — _count_schema_properties
# ============================================================================


class TestCountSchemaProperties:
    def test_none_returns_zero(self) -> None:
        assert _count_schema_properties(None) == 0

    def test_empty_dict_returns_zero(self) -> None:
        assert _count_schema_properties({}) == 0

    def test_direct_properties_counted(self) -> None:
        schema = {"properties": {"name": {}, "email": {}, "age": {}}}
        assert _count_schema_properties(schema) == 3

    def test_schema_without_properties_key_returns_zero(self) -> None:
        schema = {"type": "object", "title": "User"}
        assert _count_schema_properties(schema) == 0

    def test_empty_properties_returns_zero(self) -> None:
        schema = {"properties": {}}
        assert _count_schema_properties(schema) == 0

    def test_single_property(self) -> None:
        schema = {"properties": {"id": {"type": "integer"}}}
        assert _count_schema_properties(schema) == 1

    def test_nested_content_fallback(self) -> None:
        schema = {
            "content": {
                "application/json": {
                    "schema": {"properties": {"id": {}, "name": {}}}
                }
            }
        }
        assert _count_schema_properties(schema) == 2

    def test_direct_properties_wins_over_nested(self) -> None:
        schema = {
            "properties": {"a": {}, "b": {}},
            "content": {
                "application/json": {
                    "schema": {"properties": {"x": {}, "y": {}, "z": {}}}
                }
            },
        }
        assert _count_schema_properties(schema) == 2

    def test_large_property_count(self) -> None:
        props = {f"field_{i}": {} for i in range(15)}
        schema = {"properties": props}
        assert _count_schema_properties(schema) == 15

    def test_returns_int(self) -> None:
        result = _count_schema_properties({"properties": {"x": {}}})
        assert isinstance(result, int)


# ============================================================================
# security_scanner — _has_path_id_param
# ============================================================================


class TestHasPathIdParam:
    def test_user_id_param_returns_true(self) -> None:
        assert _has_path_id_param("/api/users/{user_id}") is True

    def test_plain_id_param_returns_true(self) -> None:
        assert _has_path_id_param("/api/items/{id}") is True

    def test_account_id_param_returns_true(self) -> None:
        assert _has_path_id_param("/api/accounts/{account_id}") is True

    def test_transfer_id_camel_case_returns_true(self) -> None:
        assert _has_path_id_param("/api/transfers/{transferId}") is True

    def test_uppercase_id_returns_true(self) -> None:
        assert _has_path_id_param("/api/items/{ID}") is True

    def test_multiple_id_params_returns_true(self) -> None:
        assert _has_path_id_param("/api/users/{user_id}/posts/{post_id}") is True

    def test_no_params_returns_false(self) -> None:
        assert _has_path_id_param("/api/users") is False

    def test_non_id_param_returns_false(self) -> None:
        assert _has_path_id_param("/api/users/{username}") is False

    def test_empty_path_returns_false(self) -> None:
        assert _has_path_id_param("") is False

    def test_plain_path_no_braces_returns_false(self) -> None:
        assert _has_path_id_param("/api/health/status") is False

    def test_returns_bool_type(self) -> None:
        assert isinstance(_has_path_id_param("/api/users/{id}"), bool)
        assert isinstance(_has_path_id_param("/api/users"), bool)


# ============================================================================
# security_scanner — _get_param_names
# ============================================================================


class TestGetParamNames:
    def test_none_returns_empty_list(self) -> None:
        assert _get_param_names(None) == []

    def test_empty_list_returns_empty_list(self) -> None:
        assert _get_param_names([]) == []

    def test_single_param_extracted(self) -> None:
        params = [{"name": "user_id", "in": "path"}]
        assert _get_param_names(params) == ["user_id"]

    def test_multiple_params_all_extracted(self) -> None:
        params = [
            {"name": "user_id", "in": "path"},
            {"name": "limit", "in": "query"},
            {"name": "offset", "in": "query"},
        ]
        result = _get_param_names(params)
        assert sorted(result) == sorted(["user_id", "limit", "offset"])

    def test_param_without_name_key_returns_empty_string(self) -> None:
        params = [{"in": "query", "type": "string"}]
        result = _get_param_names(params)
        assert result == [""]

    def test_non_dict_entries_skipped(self) -> None:
        params = [{"name": "id"}, "invalid_string", None, 42, ["list"]]
        result = _get_param_names(params)
        assert result == ["id"]

    def test_mixed_valid_and_invalid(self) -> None:
        params = [
            {"name": "account_id", "in": "path"},
            "not_a_dict",
            {"name": "include_deleted", "in": "query"},
        ]
        result = _get_param_names(params)
        assert "account_id" in result
        assert "include_deleted" in result
        assert len(result) == 2

    def test_returns_list_type(self) -> None:
        result = _get_param_names([{"name": "x"}])
        assert isinstance(result, list)

    def test_order_preserved(self) -> None:
        params = [{"name": "a"}, {"name": "b"}, {"name": "c"}]
        result = _get_param_names(params)
        assert result == ["a", "b", "c"]
