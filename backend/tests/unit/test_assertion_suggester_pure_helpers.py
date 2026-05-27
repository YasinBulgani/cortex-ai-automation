"""Unit tests for api_testing.assertion_suggester pure helper functions.

All tests are self-contained: no DB, no HTTP, no LLM.
Covers:
  - _make_suggestion: suggestion dict structure
  - _existing_assertion_types: assertion index builder
  - _suggest_status_code: missing status code suggestion
  - _suggest_content_type: content-type header suggestion
  - _suggest_response_time: performance threshold suggestion
  - _suggest_pii_checks: PII field leakage check suggestions
  - Constants: PRIORITY_*, CAT_*, PII_FIELDS, FINANCIAL_FIELDS
"""
from __future__ import annotations

import pytest

try:
    from app.domains.api_testing.assertion_suggester import (
        _make_suggestion,
        _existing_assertion_types,
        _suggest_status_code,
        _suggest_content_type,
        _suggest_response_time,
        _suggest_pii_checks,
        PRIORITY_CRITICAL,
        PRIORITY_HIGH,
        PRIORITY_MEDIUM,
        CAT_FUNCTIONAL,
        CAT_PERFORMANCE,
        CAT_COMPLIANCE,
        PII_FIELDS,
        FINANCIAL_FIELDS,
        EXPECTED_STATUS_MAP,
    )
    _AS_OK = True
except ImportError:
    _AS_OK = False


# ---------------------------------------------------------------------------
# _make_suggestion
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _AS_OK, reason="assertion_suggester import failed")
class TestMakeSuggestion:
    def test_returns_dict(self):
        r = _make_suggestion("status_code", "status_code", "eq", 200, "reason", "critical", "functional")
        assert isinstance(r, dict)

    def test_type_field(self):
        r = _make_suggestion("json_path", "$.name", "exists", None, "", "high", "security")
        assert r["type"] == "json_path"

    def test_field_preserved(self):
        r = _make_suggestion("header", "Content-Type", "contains", "json", "", "high", "functional")
        assert r["field"] == "Content-Type"

    def test_operator_preserved(self):
        r = _make_suggestion("status_code", "status_code", "one_of", [200, 201], "", "critical", "functional")
        assert r["operator"] == "one_of"

    def test_expected_value_preserved(self):
        r = _make_suggestion("status_code", "status_code", "eq", 404, "", "critical", "functional")
        assert r["expected"] == 404

    def test_reason_preserved(self):
        r = _make_suggestion("status_code", "status_code", "eq", 200, "Test reason", "high", "functional")
        assert r["reason"] == "Test reason"

    def test_priority_preserved(self):
        r = _make_suggestion("status_code", "status_code", "eq", 200, "", "medium", "functional")
        assert r["priority"] == "medium"

    def test_category_preserved(self):
        r = _make_suggestion("security", "$.password", "not_exists", None, "", "critical", "compliance")
        assert r["category"] == "compliance"

    def test_all_required_keys_present(self):
        r = _make_suggestion("status_code", "status_code", "eq", 200, "reason", "critical", "functional")
        for key in ("type", "field", "operator", "expected", "reason", "priority", "category"):
            assert key in r


# ---------------------------------------------------------------------------
# _existing_assertion_types
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _AS_OK, reason="assertion_suggester import failed")
class TestExistingAssertionTypes:
    def test_empty_list_returns_empty_dict(self):
        assert _existing_assertion_types([]) == {}

    def test_single_assertion_indexed(self):
        assertions = [{"type": "status_code", "expected": 200}]
        result = _existing_assertion_types(assertions)
        assert "status_code" in result
        assert len(result["status_code"]) == 1

    def test_multiple_same_type_grouped(self):
        assertions = [
            {"type": "json_path", "path": "$.id"},
            {"type": "json_path", "path": "$.name"},
        ]
        result = _existing_assertion_types(assertions)
        assert len(result["json_path"]) == 2

    def test_different_types_separate_keys(self):
        assertions = [
            {"type": "status_code"},
            {"type": "json_path"},
        ]
        result = _existing_assertion_types(assertions)
        assert "status_code" in result
        assert "json_path" in result

    def test_missing_type_key_indexed_as_empty_string(self):
        assertions = [{"expected": 200}]
        result = _existing_assertion_types(assertions)
        assert "" in result

    def test_returns_dict(self):
        assert isinstance(_existing_assertion_types([]), dict)

    def test_original_assertion_preserved(self):
        a = {"type": "status_code", "expected": 201}
        result = _existing_assertion_types([a])
        assert result["status_code"][0] == a


# ---------------------------------------------------------------------------
# _suggest_status_code
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _AS_OK, reason="assertion_suggester import failed")
class TestSuggestStatusCode:
    def test_missing_status_code_suggests(self):
        result = _suggest_status_code("positive", {})
        assert len(result) >= 1

    def test_existing_status_code_no_suggestion(self):
        existing = {"status_code": [{"type": "status_code", "expected": 200}]}
        result = _suggest_status_code("positive", existing)
        assert result == []

    def test_positive_test_suggests_200(self):
        result = _suggest_status_code("positive", {})
        # positive → [200, 201, 204] (multiple → one_of)
        assert result[0]["operator"] in ("eq", "one_of")

    def test_security_test_suggests_401_403(self):
        result = _suggest_status_code("security", {})
        assert len(result) >= 1
        assert result[0]["type"] == "status_code"

    def test_suggestion_is_critical_priority(self):
        result = _suggest_status_code("positive", {})
        assert result[0]["priority"] == PRIORITY_CRITICAL

    def test_suggestion_is_functional_category(self):
        result = _suggest_status_code("positive", {})
        assert result[0]["category"] == CAT_FUNCTIONAL

    def test_unknown_test_type_defaults(self):
        result = _suggest_status_code("unknown_type", {})
        assert len(result) >= 1


# ---------------------------------------------------------------------------
# _suggest_content_type
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _AS_OK, reason="assertion_suggester import failed")
class TestSuggestContentType:
    def test_missing_content_type_suggests(self):
        result = _suggest_content_type({})
        assert len(result) >= 1

    def test_existing_content_type_header_no_suggestion(self):
        existing = {
            "header": [{"type": "header", "path": "content-type", "expected": "application/json"}]
        }
        result = _suggest_content_type(existing)
        assert result == []

    def test_existing_content_type_assertion_no_suggestion(self):
        existing = {"content_type": [{"type": "content_type"}]}
        result = _suggest_content_type(existing)
        assert result == []

    def test_suggestion_type_is_header(self):
        result = _suggest_content_type({})
        assert result[0]["type"] == "header"

    def test_suggestion_contains_application_json(self):
        result = _suggest_content_type({})
        assert "application/json" in str(result[0]["expected"])

    def test_suggestion_is_high_priority(self):
        result = _suggest_content_type({})
        assert result[0]["priority"] == PRIORITY_HIGH

    def test_returns_list(self):
        assert isinstance(_suggest_content_type({}), list)


# ---------------------------------------------------------------------------
# _suggest_response_time
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _AS_OK, reason="assertion_suggester import failed")
class TestSuggestResponseTime:
    def test_missing_response_time_suggests(self):
        result = _suggest_response_time("high", {})
        assert len(result) >= 1

    def test_existing_response_time_no_suggestion(self):
        existing = {"response_time": [{"type": "response_time"}]}
        result = _suggest_response_time("high", existing)
        assert result == []

    def test_critical_risk_threshold_500ms(self):
        result = _suggest_response_time("critical", {})
        assert result[0]["expected"] == 500

    def test_high_risk_threshold_500ms(self):
        result = _suggest_response_time("high", {})
        assert result[0]["expected"] == 500

    def test_low_risk_threshold_2000ms(self):
        result = _suggest_response_time("low", {})
        assert result[0]["expected"] == 2000

    def test_medium_risk_threshold_2000ms(self):
        result = _suggest_response_time("medium", {})
        assert result[0]["expected"] == 2000

    def test_critical_risk_is_high_priority(self):
        result = _suggest_response_time("critical", {})
        assert result[0]["priority"] == PRIORITY_HIGH

    def test_low_risk_is_medium_priority(self):
        result = _suggest_response_time("low", {})
        assert result[0]["priority"] == PRIORITY_MEDIUM

    def test_type_is_performance(self):
        result = _suggest_response_time("high", {})
        assert result[0]["type"] == "performance"

    def test_category_is_performance(self):
        result = _suggest_response_time("high", {})
        assert result[0]["category"] == CAT_PERFORMANCE


# ---------------------------------------------------------------------------
# _suggest_pii_checks
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _AS_OK, reason="assertion_suggester import failed")
class TestSuggestPiiChecks:
    def test_no_pii_returns_empty(self):
        result = _suggest_pii_checks("negative", False, {})
        assert result == []

    def test_pii_positive_test_type_returns_empty(self):
        # Only suggests for negative/security/boundary test types
        result = _suggest_pii_checks("positive", True, {})
        assert result == []

    def test_pii_negative_test_suggests(self):
        result = _suggest_pii_checks("negative", True, {})
        assert len(result) >= 1

    def test_pii_security_test_suggests(self):
        result = _suggest_pii_checks("security", True, {})
        assert len(result) >= 1

    def test_suggestions_are_security_type(self):
        result = _suggest_pii_checks("negative", True, {})
        assert all(s["type"] == "security" for s in result)

    def test_suggestions_are_critical_priority(self):
        result = _suggest_pii_checks("negative", True, {})
        assert all(s["priority"] == PRIORITY_CRITICAL for s in result)

    def test_suggestions_are_compliance_category(self):
        result = _suggest_pii_checks("negative", True, {})
        assert all(s["category"] == CAT_COMPLIANCE for s in result)

    def test_returns_list(self):
        assert isinstance(_suggest_pii_checks("negative", True, {}), list)

    def test_max_8_pii_fields(self):
        result = _suggest_pii_checks("negative", True, {})
        assert len(result) <= 8


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _AS_OK, reason="assertion_suggester import failed")
class TestConstants:
    def test_priority_critical(self):
        assert PRIORITY_CRITICAL == "critical"

    def test_priority_high(self):
        assert PRIORITY_HIGH == "high"

    def test_priority_medium(self):
        assert PRIORITY_MEDIUM == "medium"

    def test_cat_functional(self):
        assert CAT_FUNCTIONAL == "functional"

    def test_cat_performance(self):
        assert CAT_PERFORMANCE == "performance"

    def test_cat_compliance(self):
        assert CAT_COMPLIANCE == "compliance"

    def test_pii_fields_is_list(self):
        assert isinstance(PII_FIELDS, list)

    def test_pii_fields_contains_email(self):
        assert "email" in PII_FIELDS

    def test_pii_fields_contains_iban(self):
        assert "iban" in PII_FIELDS

    def test_financial_fields_is_list(self):
        assert isinstance(FINANCIAL_FIELDS, list)

    def test_financial_fields_contains_amount(self):
        assert "amount" in FINANCIAL_FIELDS

    def test_expected_status_map_positive(self):
        assert 200 in EXPECTED_STATUS_MAP["positive"]

    def test_expected_status_map_security(self):
        assert 401 in EXPECTED_STATUS_MAP["security"]
