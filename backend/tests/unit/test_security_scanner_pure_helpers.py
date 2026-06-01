"""Unit tests for api_testing.security_scanner pure helper functions.

All tests are self-contained: no DB, no HTTP, no LLM.
Covers:
  - _is_banking_sensitive: banking path detection
  - _count_schema_properties: JSON schema property count
  - _has_path_id_param: ID path parameter detection
  - _get_param_names: parameter name extraction
  - _compute_security_score: finding-based 0-100 score
  - _check_bola: OWASP API1 rule check
  - _check_broken_auth: OWASP API2 rule check
  - _generate_test_suggestions_for_findings: suggestion generation
  - OWASP_CATEGORIES: constant completeness
  - _SEVERITY_WEIGHTS: constant completeness
"""
from __future__ import annotations

import pytest

try:
    from app.domains.api_testing.security_scanner import (
        _is_banking_sensitive,
        _count_schema_properties,
        _has_path_id_param,
        _get_param_names,
        _compute_security_score,
        _check_bola,
        _check_broken_auth,
        _generate_test_suggestions_for_findings,
        OWASP_CATEGORIES,
        _SEVERITY_WEIGHTS,
    )
    from app.domains.api_testing.models import ApiEndpoint
    _SS_OK = True
except ImportError:
    _SS_OK = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ep(path: str, method: str = "GET", auth_required: bool = True, **kwargs) -> "ApiEndpoint":
    return ApiEndpoint(path=path, method=method, auth_required=auth_required, **kwargs)


# ---------------------------------------------------------------------------
# _is_banking_sensitive
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _SS_OK, reason="security_scanner import failed")
class TestIsBankingSensitive:
    def test_transfer_path(self):
        assert _is_banking_sensitive("/api/transfer") is True

    def test_payment_path(self):
        assert _is_banking_sensitive("/api/payment/initiate") is True

    def test_balance_path(self):
        assert _is_banking_sensitive("/api/accounts/balance") is True

    def test_account_path(self):
        assert _is_banking_sensitive("/api/account/details") is True

    def test_credit_path(self):
        assert _is_banking_sensitive("/api/credit/apply") is True

    def test_public_path_not_sensitive(self):
        assert _is_banking_sensitive("/api/health") is False

    def test_users_path_not_sensitive(self):
        assert _is_banking_sensitive("/api/users") is False

    def test_empty_path(self):
        assert _is_banking_sensitive("") is False

    def test_returns_bool(self):
        assert isinstance(_is_banking_sensitive("/api/transfer"), bool)

    def test_case_insensitive(self):
        assert _is_banking_sensitive("/api/TRANSFER") is True
        assert _is_banking_sensitive("/api/Transfer") is True


# ---------------------------------------------------------------------------
# _count_schema_properties
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _SS_OK, reason="security_scanner import failed")
class TestCountSchemaProperties:
    def test_none_returns_zero(self):
        assert _count_schema_properties(None) == 0

    def test_empty_schema_returns_zero(self):
        assert _count_schema_properties({}) == 0

    def test_simple_properties(self):
        schema = {"properties": {"name": {}, "age": {}, "email": {}}}
        assert _count_schema_properties(schema) == 3

    def test_single_property(self):
        schema = {"properties": {"id": {}}}
        assert _count_schema_properties(schema) == 1

    def test_empty_properties_returns_zero(self):
        schema = {"properties": {}}
        assert _count_schema_properties(schema) == 0

    def test_nested_content_schema(self):
        schema = {
            "content": {
                "application/json": {
                    "schema": {
                        "properties": {"field1": {}, "field2": {}}
                    }
                }
            }
        }
        assert _count_schema_properties(schema) == 2

    def test_returns_int(self):
        assert isinstance(_count_schema_properties({"properties": {"x": {}}}), int)


# ---------------------------------------------------------------------------
# _has_path_id_param
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _SS_OK, reason="security_scanner import failed")
class TestHasPathIdParam:
    def test_user_id(self):
        assert _has_path_id_param("/api/users/{userId}") is True

    def test_account_id(self):
        assert _has_path_id_param("/api/accounts/{accountId}") is True

    def test_generic_id(self):
        assert _has_path_id_param("/api/items/{id}") is True

    def test_no_id_param(self):
        assert _has_path_id_param("/api/users") is False

    def test_non_id_path_param(self):
        assert _has_path_id_param("/api/users/{name}") is False

    def test_empty_path(self):
        assert _has_path_id_param("") is False

    def test_returns_bool(self):
        assert isinstance(_has_path_id_param("/api/{id}"), bool)

    def test_case_insensitive_id(self):
        assert _has_path_id_param("/api/resources/{resourceID}") is True


# ---------------------------------------------------------------------------
# _get_param_names
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _SS_OK, reason="security_scanner import failed")
class TestGetParamNames:
    def test_none_returns_empty(self):
        assert _get_param_names(None) == []

    def test_empty_list_returns_empty(self):
        assert _get_param_names([]) == []

    def test_single_param(self):
        assert _get_param_names([{"name": "userId", "in": "path"}]) == ["userId"]

    def test_multiple_params(self):
        params = [
            {"name": "userId", "in": "path"},
            {"name": "limit", "in": "query"},
            {"name": "offset", "in": "query"},
        ]
        result = _get_param_names(params)
        assert result == ["userId", "limit", "offset"]

    def test_non_dict_items_filtered(self):
        params = [{"name": "good"}, "not-a-dict", None]
        result = _get_param_names(params)  # type: ignore[arg-type]
        assert "good" in result

    def test_missing_name_key_gives_empty_string(self):
        params = [{"in": "path"}]  # no "name" key
        result = _get_param_names(params)
        assert result == [""]

    def test_returns_list(self):
        assert isinstance(_get_param_names([{"name": "x"}]), list)


# ---------------------------------------------------------------------------
# _compute_security_score
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _SS_OK, reason="security_scanner import failed")
class TestComputeSecurityScore:
    def test_no_findings_returns_100(self):
        assert _compute_security_score([]) == pytest.approx(100.0)

    def test_single_critical_full_confidence(self):
        findings = [{"severity": "critical", "confidence": 1.0}]
        score = _compute_security_score(findings)
        assert score == pytest.approx(75.0)  # 100 - 25*1.0

    def test_single_high_full_confidence(self):
        findings = [{"severity": "high", "confidence": 1.0}]
        assert _compute_security_score(findings) == pytest.approx(85.0)

    def test_single_medium_full_confidence(self):
        findings = [{"severity": "medium", "confidence": 1.0}]
        assert _compute_security_score(findings) == pytest.approx(92.0)

    def test_single_low_full_confidence(self):
        findings = [{"severity": "low", "confidence": 1.0}]
        assert _compute_security_score(findings) == pytest.approx(97.0)

    def test_info_severity_no_penalty(self):
        findings = [{"severity": "info", "confidence": 1.0}]
        assert _compute_security_score(findings) == pytest.approx(100.0)

    def test_confidence_scales_penalty(self):
        findings = [{"severity": "critical", "confidence": 0.5}]
        score = _compute_security_score(findings)
        assert score == pytest.approx(87.5)  # 100 - 25*0.5

    def test_score_never_below_zero(self):
        # Many critical findings
        findings = [{"severity": "critical", "confidence": 1.0} for _ in range(10)]
        assert _compute_security_score(findings) >= 0.0

    def test_score_range_0_to_100(self):
        findings = [{"severity": "high", "confidence": 0.8}]
        score = _compute_security_score(findings)
        assert 0.0 <= score <= 100.0

    def test_missing_severity_treated_as_info(self):
        findings = [{"confidence": 1.0}]  # no severity key
        score = _compute_security_score(findings)
        assert score == pytest.approx(100.0)

    def test_returns_float(self):
        assert isinstance(_compute_security_score([]), float)


# ---------------------------------------------------------------------------
# _check_bola (OWASP API1:2023)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _SS_OK, reason="security_scanner import failed")
class TestCheckBola:
    def test_unauth_id_endpoint_produces_finding(self):
        ep = _ep("/api/accounts/{accountId}", method="GET", auth_required=False)
        findings = _check_bola(ep)
        assert len(findings) >= 1

    def test_unauth_id_endpoint_category(self):
        ep = _ep("/api/users/{userId}", method="GET", auth_required=False)
        findings = _check_bola(ep)
        assert findings[0]["owasp_category"] == "API1:2023"

    def test_unauth_banking_id_is_critical(self):
        ep = _ep("/api/transfer/{transferId}", method="GET", auth_required=False)
        findings = _check_bola(ep)
        assert findings[0]["severity"] == "critical"

    def test_unauth_non_banking_id_is_high(self):
        ep = _ep("/api/items/{itemId}", method="GET", auth_required=False)
        findings = _check_bola(ep)
        assert findings[0]["severity"] == "high"

    def test_auth_id_no_mutation_no_finding(self):
        ep = _ep("/api/users/{userId}", method="GET", auth_required=True)
        findings = _check_bola(ep)
        assert len(findings) == 0

    def test_auth_id_put_produces_finding(self):
        ep = _ep("/api/accounts/{accountId}", method="PUT", auth_required=True)
        findings = _check_bola(ep)
        assert len(findings) >= 1

    def test_auth_id_delete_produces_finding(self):
        ep = _ep("/api/users/{userId}", method="DELETE", auth_required=True)
        findings = _check_bola(ep)
        assert len(findings) >= 1

    def test_no_id_param_no_finding(self):
        ep = _ep("/api/users", method="GET", auth_required=False)
        findings = _check_bola(ep)
        assert len(findings) == 0

    def test_finding_has_recommendation(self):
        ep = _ep("/api/users/{userId}", method="GET", auth_required=False)
        findings = _check_bola(ep)
        assert "recommendation" in findings[0]

    def test_returns_list(self):
        ep = _ep("/api/users/{userId}", method="GET", auth_required=False)
        assert isinstance(_check_bola(ep), list)


# ---------------------------------------------------------------------------
# _check_broken_auth (OWASP API2:2023)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _SS_OK, reason="security_scanner import failed")
class TestCheckBrokenAuth:
    def test_unauth_banking_path_produces_finding(self):
        ep = _ep("/api/transfer/initiate", method="POST", auth_required=False)
        findings = _check_broken_auth(ep)
        assert len(findings) >= 1

    def test_finding_category(self):
        ep = _ep("/api/transfer/initiate", method="POST", auth_required=False)
        findings = _check_broken_auth(ep)
        assert findings[0]["owasp_category"] == "API2:2023"

    def test_banking_unauth_is_critical(self):
        ep = _ep("/api/payment/process", method="POST", auth_required=False)
        findings = _check_broken_auth(ep)
        assert findings[0]["severity"] == "critical"

    def test_public_path_no_finding(self):
        ep = _ep("/api/health", method="GET", auth_required=False)
        findings = _check_broken_auth(ep)
        assert len(findings) == 0

    def test_authenticated_sensitive_no_finding(self):
        ep = _ep("/api/transfer/initiate", method="POST", auth_required=True)
        findings = _check_broken_auth(ep)
        assert len(findings) == 0

    def test_admin_path_unauth_produces_finding(self):
        ep = _ep("/api/admin/users", method="GET", auth_required=False)
        findings = _check_broken_auth(ep)
        assert len(findings) >= 1

    def test_pii_path_unauth_produces_finding(self):
        ep = _ep("/api/user/profile", method="GET", auth_required=False)
        findings = _check_broken_auth(ep)
        assert len(findings) >= 1

    def test_finding_has_confidence(self):
        ep = _ep("/api/transfer", method="POST", auth_required=False)
        findings = _check_broken_auth(ep)
        assert "confidence" in findings[0]

    def test_returns_list(self):
        ep = _ep("/api/transfer", method="POST", auth_required=False)
        assert isinstance(_check_broken_auth(ep), list)


# ---------------------------------------------------------------------------
# _generate_test_suggestions_for_findings
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _SS_OK, reason="security_scanner import failed")
class TestGenerateTestSuggestions:
    def test_empty_findings_returns_empty(self):
        ep = _ep("/api/users", method="GET")
        assert _generate_test_suggestions_for_findings(ep, []) == []

    def test_bola_finding_produces_suggestions(self):
        ep = _ep("/api/users/{userId}", method="GET")
        findings = [{"owasp_category": "API1:2023", "severity": "high", "confidence": 0.9}]
        suggestions = _generate_test_suggestions_for_findings(ep, findings)
        assert len(suggestions) >= 1

    def test_bola_suggestions_have_test_type_security(self):
        ep = _ep("/api/users/{userId}", method="GET")
        findings = [{"owasp_category": "API1:2023", "severity": "high", "confidence": 0.9}]
        suggestions = _generate_test_suggestions_for_findings(ep, findings)
        for s in suggestions:
            assert s["test_type"] == "security"

    def test_auth_finding_produces_suggestions(self):
        ep = _ep("/api/transfer", method="POST")
        findings = [{"owasp_category": "API2:2023", "severity": "critical", "confidence": 0.95}]
        suggestions = _generate_test_suggestions_for_findings(ep, findings)
        assert len(suggestions) >= 1

    def test_suggestion_has_expected_behavior(self):
        ep = _ep("/api/users/{userId}", method="GET")
        findings = [{"owasp_category": "API1:2023", "severity": "high", "confidence": 0.9}]
        suggestions = _generate_test_suggestions_for_findings(ep, findings)
        for s in suggestions:
            assert "expected_behavior" in s

    def test_same_category_not_duplicated(self):
        ep = _ep("/api/users/{userId}", method="GET")
        findings = [
            {"owasp_category": "API1:2023", "severity": "high", "confidence": 0.9},
            {"owasp_category": "API1:2023", "severity": "medium", "confidence": 0.7},
        ]
        # Duplicate categories should be deduped
        suggestions = _generate_test_suggestions_for_findings(ep, findings)
        categories = [s.get("owasp_category") for s in suggestions]
        # All suggestions should be for API1:2023 (deduplicated source)
        assert all(c == "API1:2023" for c in categories)

    def test_returns_list(self):
        ep = _ep("/api/users", method="GET")
        result = _generate_test_suggestions_for_findings(ep, [])
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _SS_OK, reason="security_scanner import failed")
class TestConstants:
    def test_owasp_categories_has_10_entries(self):
        assert len(OWASP_CATEGORIES) == 10

    def test_owasp_api1_present(self):
        assert "API1:2023" in OWASP_CATEGORIES

    def test_owasp_api10_present(self):
        assert "API10:2023" in OWASP_CATEGORIES

    def test_owasp_categories_all_strings(self):
        for k, v in OWASP_CATEGORIES.items():
            assert isinstance(k, str)
            assert isinstance(v, str)

    def test_severity_weights_has_standard_levels(self):
        for level in ("critical", "high", "medium", "low", "info"):
            assert level in _SEVERITY_WEIGHTS

    def test_severity_weights_ordered(self):
        assert _SEVERITY_WEIGHTS["critical"] > _SEVERITY_WEIGHTS["high"]
        assert _SEVERITY_WEIGHTS["high"] > _SEVERITY_WEIGHTS["medium"]
        assert _SEVERITY_WEIGHTS["medium"] > _SEVERITY_WEIGHTS["low"]
        assert _SEVERITY_WEIGHTS["low"] >= _SEVERITY_WEIGHTS["info"]

    def test_severity_weights_info_zero(self):
        assert _SEVERITY_WEIGHTS["info"] == pytest.approx(0.0)
