"""Unit tests for API Testing assertion suggester pure helpers.

Tests app/domains/api_testing/assertion_suggester.py — no DB, no LLM.
Covers: _make_suggestion, _existing_assertion_types, _suggest_status_code,
        _suggest_content_type, _suggest_response_time, _suggest_pii_checks,
        _suggest_financial_checks, _suggest_schema_validation,
        _suggest_auth_checks, _suggest_compliance_checks, _suggest_type_specific.
"""

from __future__ import annotations

import pytest

from app.domains.api_testing.assertion_suggester import (
    _existing_assertion_types,
    _make_suggestion,
    _suggest_auth_checks,
    _suggest_compliance_checks,
    _suggest_content_type,
    _suggest_financial_checks,
    _suggest_pii_checks,
    _suggest_response_time,
    _suggest_schema_validation,
    _suggest_status_code,
    _suggest_type_specific,
    CAT_COMPLIANCE,
    CAT_FUNCTIONAL,
    CAT_PERFORMANCE,
    CAT_SECURITY,
    PRIORITY_CRITICAL,
    PRIORITY_HIGH,
    PRIORITY_MEDIUM,
)


# ── _make_suggestion ──────────────────────────────────────────────────────────


class TestMakeSuggestion:
    def test_all_fields_present(self) -> None:
        result = _make_suggestion(
            "status_code", "status_code", "eq", 200,
            "Must check status", PRIORITY_CRITICAL, CAT_FUNCTIONAL,
        )
        assert result["type"] == "status_code"
        assert result["field"] == "status_code"
        assert result["operator"] == "eq"
        assert result["expected"] == 200
        assert result["reason"] == "Must check status"
        assert result["priority"] == PRIORITY_CRITICAL
        assert result["category"] == CAT_FUNCTIONAL

    def test_returns_dict(self) -> None:
        result = _make_suggestion("t", "f", "op", None, "r", "p", "c")
        assert isinstance(result, dict)

    def test_none_expected_preserved(self) -> None:
        result = _make_suggestion("security", "$.ssn", "not_exists", None, "r", "p", "c")
        assert result["expected"] is None

    def test_list_expected_preserved(self) -> None:
        result = _make_suggestion("status_code", "status_code", "one_of", [401, 403], "r", "p", "c")
        assert result["expected"] == [401, 403]


# ── _existing_assertion_types ─────────────────────────────────────────────────


class TestExistingAssertionTypes:
    def test_empty_list_returns_empty(self) -> None:
        assert _existing_assertion_types([]) == {}

    def test_groups_by_type(self) -> None:
        assertions = [
            {"type": "status_code", "expected": 200},
            {"type": "status_code", "expected": 201},
            {"type": "header", "key": "Content-Type"},
        ]
        index = _existing_assertion_types(assertions)
        assert len(index["status_code"]) == 2
        assert len(index["header"]) == 1

    def test_missing_type_defaults_to_empty_string_key(self) -> None:
        assertions = [{"no_type": "here"}]
        index = _existing_assertion_types(assertions)
        assert "" in index

    def test_each_value_is_list(self) -> None:
        assertions = [{"type": "json_path", "path": "$.id"}]
        index = _existing_assertion_types(assertions)
        assert isinstance(index["json_path"], list)


# ── _suggest_status_code ──────────────────────────────────────────────────────


class TestSuggestStatusCode:
    def test_positive_test_suggests_200_range(self) -> None:
        suggestions = _suggest_status_code("positive", {})
        assert len(suggestions) == 1
        s = suggestions[0]
        assert s["type"] == "status_code"
        # positive → [200, 201, 204] → one_of
        assert s["operator"] == "one_of"
        assert 200 in s["expected"]

    def test_security_test_suggests_401_403(self) -> None:
        suggestions = _suggest_status_code("security", {})
        assert len(suggestions) == 1
        assert 401 in suggestions[0]["expected"]
        assert 403 in suggestions[0]["expected"]

    def test_negative_test_suggests_4xx(self) -> None:
        suggestions = _suggest_status_code("negative", {})
        assert len(suggestions) == 1
        assert any(c >= 400 for c in suggestions[0]["expected"])

    def test_performance_test_suggests_200(self) -> None:
        suggestions = _suggest_status_code("performance", {})
        assert len(suggestions) == 1
        # performance → [200] → single code → "eq" operator, expected is int
        s = suggestions[0]
        assert s["operator"] == "eq"
        assert s["expected"] == 200

    def test_skips_when_already_present(self) -> None:
        existing = {"status_code": [{"type": "status_code", "expected": 200}]}
        assert _suggest_status_code("positive", existing) == []

    def test_unknown_test_type_falls_back_to_200(self) -> None:
        suggestions = _suggest_status_code("unknown_type", {})
        assert len(suggestions) == 1
        s = suggestions[0]
        # EXPECTED_STATUS_MAP.get("unknown_type", [200]) → single code → eq operator
        assert s["operator"] == "eq"
        assert s["expected"] == 200

    def test_priority_is_critical(self) -> None:
        suggestions = _suggest_status_code("positive", {})
        assert suggestions[0]["priority"] == PRIORITY_CRITICAL


# ── _suggest_content_type ─────────────────────────────────────────────────────


class TestSuggestContentType:
    def test_suggests_when_absent(self) -> None:
        suggestions = _suggest_content_type({})
        assert len(suggestions) == 1
        s = suggestions[0]
        assert s["field"] == "Content-Type"
        assert "application/json" in str(s["expected"])

    def test_skips_when_content_type_assertion_exists(self) -> None:
        existing = {"content_type": [{"type": "content_type"}]}
        assert _suggest_content_type(existing) == []

    def test_skips_when_header_assertion_has_content_type(self) -> None:
        existing = {
            "header": [{"type": "header", "key": "content-type", "expected": "application/json"}]
        }
        assert _suggest_content_type(existing) == []

    def test_header_without_content_type_still_suggests(self) -> None:
        existing = {"header": [{"type": "header", "key": "Authorization"}]}
        suggestions = _suggest_content_type(existing)
        assert len(suggestions) == 1

    def test_priority_is_high(self) -> None:
        suggestions = _suggest_content_type({})
        assert suggestions[0]["priority"] == PRIORITY_HIGH


# ── _suggest_response_time ────────────────────────────────────────────────────


class TestSuggestResponseTime:
    def test_critical_risk_uses_500ms(self) -> None:
        suggestions = _suggest_response_time("critical", {})
        assert suggestions[0]["expected"] == 500

    def test_high_risk_uses_500ms(self) -> None:
        suggestions = _suggest_response_time("high", {})
        assert suggestions[0]["expected"] == 500

    def test_medium_risk_uses_2000ms(self) -> None:
        suggestions = _suggest_response_time("medium", {})
        assert suggestions[0]["expected"] == 2000

    def test_low_risk_uses_2000ms(self) -> None:
        suggestions = _suggest_response_time("low", {})
        assert suggestions[0]["expected"] == 2000

    def test_skips_when_already_present(self) -> None:
        existing = {"response_time": [{"type": "response_time"}]}
        assert _suggest_response_time("critical", existing) == []

    def test_category_is_performance(self) -> None:
        suggestions = _suggest_response_time("high", {})
        assert suggestions[0]["category"] == CAT_PERFORMANCE

    def test_high_risk_priority_is_high(self) -> None:
        suggestions = _suggest_response_time("critical", {})
        assert suggestions[0]["priority"] == PRIORITY_HIGH

    def test_low_risk_priority_is_medium(self) -> None:
        suggestions = _suggest_response_time("low", {})
        assert suggestions[0]["priority"] == PRIORITY_MEDIUM


# ── _suggest_pii_checks ───────────────────────────────────────────────────────


class TestSuggestPiiChecks:
    def test_no_pii_returns_empty(self) -> None:
        assert _suggest_pii_checks("negative", False, {}) == []

    def test_positive_test_with_pii_skipped(self) -> None:
        # Only negative test types get PII checks
        suggestions = _suggest_pii_checks("positive", True, {})
        assert suggestions == []

    def test_negative_test_with_pii_suggests_checks(self) -> None:
        suggestions = _suggest_pii_checks("negative", True, {})
        assert len(suggestions) > 0
        for s in suggestions:
            assert s["category"] == CAT_COMPLIANCE
            assert s["priority"] == PRIORITY_CRITICAL

    def test_security_test_with_pii_suggests_checks(self) -> None:
        suggestions = _suggest_pii_checks("security", True, {})
        assert len(suggestions) > 0

    def test_already_checked_pii_field_skipped(self) -> None:
        existing = {"json_path": [{"path": "$.tc_kimlik"}]}
        suggestions = _suggest_pii_checks("negative", True, existing)
        # tc_kimlik already checked, should not be re-suggested
        fields = [s["field"] for s in suggestions]
        assert "$.tc_kimlik" not in fields

    def test_up_to_8_pii_fields(self) -> None:
        suggestions = _suggest_pii_checks("negative", True, {})
        assert len(suggestions) <= 8


# ── _suggest_financial_checks ─────────────────────────────────────────────────


class TestSuggestFinancialChecks:
    def test_no_financial_returns_empty(self) -> None:
        assert _suggest_financial_checks(False, None, {}) == []

    def test_financial_suggests_decimal_regex(self) -> None:
        suggestions = _suggest_financial_checks(True, None, {})
        regex_suggestions = [s for s in suggestions if s["type"] == "regex"]
        assert len(regex_suggestions) > 0
        # Pattern should require 2 decimal places
        assert any(r"\.{2}" in s.get("expected", "") or r"\.\d{2}" in s.get("expected", "")
                   for s in regex_suggestions)

    def test_financial_suggests_currency_format(self) -> None:
        suggestions = _suggest_financial_checks(True, None, {})
        currency_sugg = [s for s in suggestions if "currency" in s.get("field", "").lower()]
        assert len(currency_sugg) >= 1

    def test_already_checked_financial_field_skipped(self) -> None:
        existing = {"json_path": [{"path": "$.data.balance"}]}
        suggestions = _suggest_financial_checks(True, None, existing)
        fields = [s["field"] for s in suggestions]
        assert "$.data.balance" not in fields

    def test_category_is_compliance(self) -> None:
        suggestions = _suggest_financial_checks(True, None, {})
        for s in suggestions:
            assert s["category"] == CAT_COMPLIANCE


# ── _suggest_schema_validation ────────────────────────────────────────────────


class TestSuggestSchemaValidation:
    def test_no_schemas_returns_empty(self) -> None:
        assert _suggest_schema_validation(None, {}) == []

    def test_empty_schemas_returns_empty(self) -> None:
        assert _suggest_schema_validation({}, {}) == []

    def test_200_schema_suggests_validation(self) -> None:
        schemas = {"200": {"type": "object", "properties": {"id": {"type": "integer"}}}}
        suggestions = _suggest_schema_validation(schemas, {})
        assert len(suggestions) == 1
        s = suggestions[0]
        assert s["type"] == "schema"
        assert s["priority"] == PRIORITY_HIGH

    def test_201_schema_suggests_validation(self) -> None:
        schemas = {"201": {"type": "object"}}
        suggestions = _suggest_schema_validation(schemas, {})
        assert len(suggestions) == 1

    def test_only_404_schema_returns_empty(self) -> None:
        schemas = {"404": {"type": "object"}}
        assert _suggest_schema_validation(schemas, {}) == []

    def test_skips_when_schema_assertion_exists(self) -> None:
        schemas = {"200": {"type": "object"}}
        existing = {"schema": [{"type": "schema"}]}
        assert _suggest_schema_validation(schemas, existing) == []


# ── _suggest_auth_checks ──────────────────────────────────────────────────────


class TestSuggestAuthChecks:
    def test_no_auth_required_returns_empty(self) -> None:
        assert _suggest_auth_checks(False, "positive", {}) == []

    def test_security_test_suggests_401_403(self) -> None:
        suggestions = _suggest_auth_checks(True, "security", {})
        auth_status = [s for s in suggestions if s["type"] == "status_code"]
        assert len(auth_status) >= 1
        assert 401 in auth_status[0]["expected"] or 403 in auth_status[0]["expected"]

    def test_security_test_skips_if_already_has_401(self) -> None:
        existing = {"status_code": [{"expected": 401}]}
        suggestions = _suggest_auth_checks(True, "security", existing)
        status_suggs = [s for s in suggestions if s["type"] == "status_code"]
        assert len(status_suggs) == 0

    def test_positive_test_suggests_auth_header(self) -> None:
        suggestions = _suggest_auth_checks(True, "positive", {})
        header_sugg = [s for s in suggestions if s["type"] == "header"]
        assert len(header_sugg) >= 1
        assert "Authorization" in header_sugg[0]["field"]

    def test_positive_test_skips_if_auth_header_exists(self) -> None:
        existing = {"header": [{"key": "Authorization"}]}
        suggestions = _suggest_auth_checks(True, "positive", existing)
        header_sugg = [s for s in suggestions if s["type"] == "header"]
        assert len(header_sugg) == 0

    def test_priority_security_check_is_critical(self) -> None:
        suggestions = _suggest_auth_checks(True, "security", {})
        security_sugg = [s for s in suggestions if s["type"] == "status_code"]
        if security_sugg:
            assert security_sugg[0]["priority"] == PRIORITY_CRITICAL


# ── _suggest_compliance_checks ────────────────────────────────────────────────


class TestSuggestComplianceChecks:
    def test_no_tags_returns_empty(self) -> None:
        assert _suggest_compliance_checks([], "positive", False, {}) == []

    def test_kvkk_tag_suggests_tckn_check(self) -> None:
        suggestions = _suggest_compliance_checks(["KVKK"], "positive", False, {})
        assert len(suggestions) >= 1
        kvkk_sugg = [s for s in suggestions if "kvkk" in s.get("reason", "").lower() or
                     "tc_kimlik" in s.get("field", "").lower()]
        assert len(kvkk_sugg) >= 1

    def test_kvkk_already_checked_skipped(self) -> None:
        # If there's already a KVKK assertion in existing
        existing = {"security": [{"reason": "KVKK check"}]}
        suggestions = _suggest_compliance_checks(["KVKK"], "positive", False, existing)
        # kvkk_checked should be True → no new KVKK suggestion
        kvkk_sugg = [s for s in suggestions if "tc_kimlik" in s.get("field", "")]
        assert len(kvkk_sugg) == 0

    def test_bddk_tag_with_financial_suggests_audit_fields(self) -> None:
        suggestions = _suggest_compliance_checks(["BDDK"], "positive", True, {})
        bddk_sugg = [s for s in suggestions if "BDDK" in s.get("reason", "")]
        assert len(bddk_sugg) >= 1

    def test_bddk_without_financial_skips_audit(self) -> None:
        suggestions = _suggest_compliance_checks(["BDDK"], "positive", False, {})
        # BDDK audit only for financial endpoints
        bddk_audit = [s for s in suggestions if "BDDK: Finansal" in s.get("reason", "")]
        assert len(bddk_audit) == 0

    def test_pci_dss_suggests_card_masking(self) -> None:
        suggestions = _suggest_compliance_checks(["PCI-DSS"], "positive", False, {})
        pci_sugg = [s for s in suggestions if "PCI-DSS" in s.get("reason", "")]
        assert len(pci_sugg) >= 1
        # card_number should be checked
        fields = [s["field"] for s in pci_sugg]
        assert any("card_number" in f for f in fields)

    def test_all_three_tags(self) -> None:
        suggestions = _suggest_compliance_checks(["KVKK", "BDDK", "PCI-DSS"], "positive", True, {})
        assert len(suggestions) >= 3
        categories = {s["category"] for s in suggestions}
        assert CAT_COMPLIANCE in categories


# ── _suggest_type_specific ────────────────────────────────────────────────────


class TestSuggestTypeSpecific:
    def test_boundary_suggests_error_field(self) -> None:
        suggestions = _suggest_type_specific("boundary", {}, "GET")
        assert len(suggestions) == 1
        assert "error" in suggestions[0]["field"].lower()

    def test_boundary_skips_if_error_already_checked(self) -> None:
        existing = {"json_path": [{"path": "$.error"}]}
        assert _suggest_type_specific("boundary", existing, "GET") == []

    def test_contract_suggests_schema(self) -> None:
        suggestions = _suggest_type_specific("contract", {}, "GET")
        assert len(suggestions) == 1
        assert suggestions[0]["type"] == "schema"
        assert suggestions[0]["priority"] == PRIORITY_CRITICAL

    def test_contract_skips_if_schema_exists(self) -> None:
        existing = {"schema": [{"type": "schema"}]}
        assert _suggest_type_specific("contract", existing, "GET") == []

    def test_performance_suggests_response_time(self) -> None:
        suggestions = _suggest_type_specific("performance", {}, "GET")
        assert len(suggestions) == 1
        assert suggestions[0]["type"] == "performance"
        assert suggestions[0]["expected"] == 500

    def test_positive_post_suggests_id_field(self) -> None:
        suggestions = _suggest_type_specific("positive", {}, "POST")
        id_sugg = [s for s in suggestions if "id" in s.get("field", "").lower()]
        assert len(id_sugg) >= 1

    def test_positive_put_suggests_id_field(self) -> None:
        suggestions = _suggest_type_specific("positive", {}, "PUT")
        id_sugg = [s for s in suggestions if "id" in s.get("field", "").lower()]
        assert len(id_sugg) >= 1

    def test_positive_get_does_not_suggest_id(self) -> None:
        suggestions = _suggest_type_specific("positive", {}, "GET")
        assert suggestions == []

    def test_unknown_type_returns_empty(self) -> None:
        assert _suggest_type_specific("unknown_type", {}, "GET") == []

    def test_negative_type_returns_empty(self) -> None:
        assert _suggest_type_specific("negative", {}, "DELETE") == []
