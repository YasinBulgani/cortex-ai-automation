"""Unit tests for OWASP API security scanner pure helper functions.

Tests app/domains/api_testing/security_scanner.py — no DB, no LLM.
Covers: _is_banking_sensitive, _count_schema_properties,
        _has_path_id_param, _get_param_names, _compute_security_score.
"""

from __future__ import annotations

import pytest

from app.domains.api_testing.security_scanner import (
    _compute_security_score,
    _count_schema_properties,
    _get_param_names,
    _has_path_id_param,
    _is_banking_sensitive,
)


# ── _is_banking_sensitive ─────────────────────────────────────────────────────


class TestIsBankingSensitive:
    def test_transfer_path(self) -> None:
        assert _is_banking_sensitive("/api/transfer") is True

    def test_payment_path(self) -> None:
        assert _is_banking_sensitive("/api/payment/process") is True

    def test_havale_path(self) -> None:
        assert _is_banking_sensitive("/api/havale") is True

    def test_eft_path(self) -> None:
        assert _is_banking_sensitive("/api/eft/send") is True

    def test_bakiye_path(self) -> None:
        assert _is_banking_sensitive("/api/bakiye") is True

    def test_balance_path(self) -> None:
        assert _is_banking_sensitive("/api/account/balance") is True

    def test_hesap_path(self) -> None:
        assert _is_banking_sensitive("/api/hesap/detay") is True

    def test_account_path(self) -> None:
        assert _is_banking_sensitive("/api/account/list") is True

    def test_kredi_path(self) -> None:
        assert _is_banking_sensitive("/api/kredi/basvuru") is True

    def test_credit_path(self) -> None:
        assert _is_banking_sensitive("/api/credit/score") is True

    def test_fatura_path(self) -> None:
        assert _is_banking_sensitive("/api/fatura/odeme") is True

    def test_atm_path(self) -> None:
        assert _is_banking_sensitive("/api/atm/locations") is True

    def test_case_insensitive(self) -> None:
        assert _is_banking_sensitive("/API/TRANSFER") is True

    def test_non_banking_path(self) -> None:
        assert _is_banking_sensitive("/api/users/profile") is False

    def test_health_path(self) -> None:
        assert _is_banking_sensitive("/health") is False

    def test_empty_path(self) -> None:
        assert _is_banking_sensitive("") is False

    def test_unrelated_path(self) -> None:
        assert _is_banking_sensitive("/api/reports/summary") is False

    def test_partial_match_in_segment(self) -> None:
        # "pos" pattern should match /api/pos-terminal
        assert _is_banking_sensitive("/api/pos-terminal") is True


# ── _count_schema_properties ──────────────────────────────────────────────────


class TestCountSchemaProperties:
    def test_none_schema_returns_zero(self) -> None:
        assert _count_schema_properties(None) == 0

    def test_empty_dict_returns_zero(self) -> None:
        assert _count_schema_properties({}) == 0

    def test_schema_with_properties(self) -> None:
        schema = {"properties": {"name": {}, "email": {}, "age": {}}}
        assert _count_schema_properties(schema) == 3

    def test_schema_no_properties_key(self) -> None:
        schema = {"type": "object", "title": "User"}
        assert _count_schema_properties(schema) == 0

    def test_empty_properties(self) -> None:
        schema = {"properties": {}}
        assert _count_schema_properties(schema) == 0

    def test_nested_content_fallback(self) -> None:
        schema = {
            "content": {
                "application/json": {
                    "schema": {
                        "properties": {"id": {}, "name": {}}
                    }
                }
            }
        }
        assert _count_schema_properties(schema) == 2

    def test_direct_properties_takes_priority(self) -> None:
        # Direct properties key wins over nested fallback
        schema = {
            "properties": {"a": {}, "b": {}},
            "content": {
                "application/json": {
                    "schema": {"properties": {"x": {}, "y": {}, "z": {}}}
                }
            }
        }
        assert _count_schema_properties(schema) == 2

    def test_large_schema(self) -> None:
        props = {f"field_{i}": {} for i in range(20)}
        schema = {"properties": props}
        assert _count_schema_properties(schema) == 20


# ── _has_path_id_param ────────────────────────────────────────────────────────


class TestHasPathIdParam:
    def test_path_with_id_param(self) -> None:
        assert _has_path_id_param("/api/users/{user_id}") is True

    def test_path_with_plain_id(self) -> None:
        assert _has_path_id_param("/api/items/{id}") is True

    def test_path_with_account_id(self) -> None:
        assert _has_path_id_param("/api/accounts/{account_id}") is True

    def test_path_with_transfer_id(self) -> None:
        assert _has_path_id_param("/api/transfers/{transferId}") is True

    def test_path_without_id_param(self) -> None:
        assert _has_path_id_param("/api/users") is False

    def test_path_with_non_id_param(self) -> None:
        assert _has_path_id_param("/api/users/{username}") is False

    def test_empty_path(self) -> None:
        assert _has_path_id_param("") is False

    def test_case_insensitive_id(self) -> None:
        assert _has_path_id_param("/api/items/{ID}") is True

    def test_path_with_multiple_params_one_id(self) -> None:
        assert _has_path_id_param("/api/users/{user_id}/posts/{post_id}") is True

    def test_path_with_no_params(self) -> None:
        assert _has_path_id_param("/api/health/status") is False


# ── _get_param_names ──────────────────────────────────────────────────────────


class TestGetParamNames:
    def test_none_returns_empty_list(self) -> None:
        assert _get_param_names(None) == []

    def test_empty_list_returns_empty_list(self) -> None:
        assert _get_param_names([]) == []

    def test_single_param(self) -> None:
        params = [{"name": "user_id", "in": "path"}]
        assert _get_param_names(params) == ["user_id"]

    def test_multiple_params(self) -> None:
        params = [
            {"name": "user_id", "in": "path"},
            {"name": "limit", "in": "query"},
            {"name": "offset", "in": "query"},
        ]
        result = _get_param_names(params)
        assert "user_id" in result
        assert "limit" in result
        assert "offset" in result
        assert len(result) == 3

    def test_param_without_name_key(self) -> None:
        params = [{"in": "query", "type": "string"}]
        result = _get_param_names(params)
        assert result == [""]

    def test_non_dict_params_skipped(self) -> None:
        params = [{"name": "id"}, "invalid", None, 42]
        result = _get_param_names(params)
        assert result == ["id"]

    def test_mixed_params(self) -> None:
        params = [
            {"name": "account_id", "in": "path"},
            {"name": "include_deleted", "in": "query"},
        ]
        result = _get_param_names(params)
        assert len(result) == 2


# ── _compute_security_score ───────────────────────────────────────────────────


class TestComputeSecurityScore:
    def test_no_findings_returns_100(self) -> None:
        assert _compute_security_score([]) == 100.0

    def test_single_critical_finding(self) -> None:
        findings = [{"severity": "critical", "confidence": 1.0}]
        score = _compute_security_score(findings)
        # penalty = 25.0 * 1.0 = 25, score = 75
        assert score == pytest.approx(75.0)

    def test_single_high_finding(self) -> None:
        findings = [{"severity": "high", "confidence": 1.0}]
        score = _compute_security_score(findings)
        # penalty = 15.0
        assert score == pytest.approx(85.0)

    def test_single_medium_finding(self) -> None:
        findings = [{"severity": "medium", "confidence": 1.0}]
        score = _compute_security_score(findings)
        assert score == pytest.approx(92.0)

    def test_single_low_finding(self) -> None:
        findings = [{"severity": "low", "confidence": 1.0}]
        score = _compute_security_score(findings)
        assert score == pytest.approx(97.0)

    def test_info_finding_no_penalty(self) -> None:
        findings = [{"severity": "info", "confidence": 1.0}]
        assert _compute_security_score(findings) == 100.0

    def test_confidence_scales_penalty(self) -> None:
        findings_half = [{"severity": "critical", "confidence": 0.5}]
        score = _compute_security_score(findings_half)
        # penalty = 25 * 0.5 = 12.5, score = 87.5
        assert score == pytest.approx(87.5)

    def test_score_floored_at_zero(self) -> None:
        # Many critical findings → should not go below 0
        findings = [{"severity": "critical", "confidence": 1.0}] * 10
        score = _compute_security_score(findings)
        assert score == 0.0

    def test_multiple_findings_accumulated(self) -> None:
        findings = [
            {"severity": "critical", "confidence": 1.0},
            {"severity": "high", "confidence": 1.0},
        ]
        score = _compute_security_score(findings)
        # penalty = 25 + 15 = 40, score = 60
        assert score == pytest.approx(60.0)

    def test_unknown_severity_treated_as_zero(self) -> None:
        findings = [{"severity": "unknown_xyz", "confidence": 1.0}]
        assert _compute_security_score(findings) == 100.0

    def test_missing_severity_uses_info(self) -> None:
        findings = [{"confidence": 1.0}]
        assert _compute_security_score(findings) == 100.0

    def test_score_rounded_to_one_decimal(self) -> None:
        findings = [{"severity": "critical", "confidence": 0.3}]
        score = _compute_security_score(findings)
        # penalty = 25 * 0.3 = 7.5, score = 92.5
        assert score == pytest.approx(92.5)
        # Check it's a float with at most 1 decimal
        assert score == round(score, 1)

    def test_default_confidence_when_missing(self) -> None:
        findings = [{"severity": "high"}]
        score = _compute_security_score(findings)
        # default confidence = 0.5, penalty = 15 * 0.5 = 7.5, score = 92.5
        assert score == pytest.approx(92.5)
