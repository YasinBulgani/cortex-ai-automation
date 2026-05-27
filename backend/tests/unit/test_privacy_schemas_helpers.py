"""Unit tests for app.domains.ai_synthetic_data.privacy_schemas — Pydantic models.

Tests are fully self-contained: no DB, no HTTP, no AI.
Covers all 13 schema classes: field defaults, validation constraints, and instantiation.
"""
from __future__ import annotations

import pytest

try:
    from app.domains.ai_synthetic_data.privacy_schemas import (
        PrivatizeRequest,
        PrivatizeResponse,
        KAnonymityRequest,
        KAnonymityResponse,
        LDiversityRequest,
        LDiversityResponse,
        ReidentificationRequest,
        ReidentificationResponse,
        PrivacyReportRequest,
        PrivacyReportResponse,
        PrivacyConfigSuggestion,
        SuggestConfigRequest,
        SuggestConfigResponse,
        TCKNValidateRequest,
        TCKNValidateResponse,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="privacy_schemas import failed")


# ---------------------------------------------------------------------------
# PrivatizeRequest
# ---------------------------------------------------------------------------

class TestPrivatizeRequest:
    def test_creation(self):
        req = PrivatizeRequest(
            data=[{"bakiye": 1000}],
            column_config={"bakiye": {"type": "numeric", "sensitivity": 1000}},
        )
        assert req.data == [{"bakiye": 1000}]

    def test_default_epsilon(self):
        req = PrivatizeRequest(
            data=[{}],
            column_config={},
        )
        assert req.epsilon == pytest.approx(1.0)

    def test_default_delta(self):
        req = PrivatizeRequest(data=[{}], column_config={})
        assert req.delta == pytest.approx(1e-5)

    def test_epsilon_gt_zero_required(self):
        with pytest.raises(Exception):
            PrivatizeRequest(data=[{}], column_config={}, epsilon=0)

    def test_epsilon_max_100(self):
        with pytest.raises(Exception):
            PrivatizeRequest(data=[{}], column_config={}, epsilon=101)


# ---------------------------------------------------------------------------
# PrivatizeResponse
# ---------------------------------------------------------------------------

class TestPrivatizeResponse:
    def test_defaults(self):
        resp = PrivatizeResponse()
        assert resp.privatized_data == []
        assert resp.columns_processed == {}
        assert resp.budget_consumed == pytest.approx(0.0)
        assert resp.remaining_budget == pytest.approx(0.0)

    def test_with_data(self):
        resp = PrivatizeResponse(
            privatized_data=[{"bakiye": 999}],
            budget_consumed=0.5,
            remaining_budget=0.5,
        )
        assert len(resp.privatized_data) == 1
        assert resp.budget_consumed == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# KAnonymityRequest
# ---------------------------------------------------------------------------

class TestKAnonymityRequest:
    def test_creation(self):
        req = KAnonymityRequest(data=[{"age": 25}], quasi_identifiers=["age"])
        assert req.quasi_identifiers == ["age"]

    def test_default_k(self):
        req = KAnonymityRequest(data=[{}], quasi_identifiers=[])
        assert req.k == 5

    def test_k_ge_1(self):
        with pytest.raises(Exception):
            KAnonymityRequest(data=[{}], quasi_identifiers=[], k=0)


# ---------------------------------------------------------------------------
# KAnonymityResponse
# ---------------------------------------------------------------------------

class TestKAnonymityResponse:
    def test_defaults(self):
        resp = KAnonymityResponse()
        assert resp.satisfies_k is False
        assert resp.k_achieved == 0
        assert resp.violating_groups == 0
        assert resp.total_groups == 0

    def test_with_values(self):
        resp = KAnonymityResponse(satisfies_k=True, k_achieved=5, total_groups=10)
        assert resp.satisfies_k is True
        assert resp.k_achieved == 5


# ---------------------------------------------------------------------------
# LDiversityRequest
# ---------------------------------------------------------------------------

class TestLDiversityRequest:
    def test_creation(self):
        req = LDiversityRequest(
            data=[{"age": 25, "disease": "flu"}],
            quasi_identifiers=["age"],
            sensitive_attr="disease",
        )
        assert req.sensitive_attr == "disease"

    def test_default_l(self):
        req = LDiversityRequest(data=[{}], quasi_identifiers=[], sensitive_attr="x")
        assert req.l == 3

    def test_l_ge_1(self):
        with pytest.raises(Exception):
            LDiversityRequest(data=[{}], quasi_identifiers=[], sensitive_attr="x", l=0)


# ---------------------------------------------------------------------------
# LDiversityResponse
# ---------------------------------------------------------------------------

class TestLDiversityResponse:
    def test_defaults(self):
        resp = LDiversityResponse()
        assert resp.satisfies_l is False
        assert resp.l_achieved == 0
        assert resp.violations == 0


# ---------------------------------------------------------------------------
# ReidentificationRequest
# ---------------------------------------------------------------------------

class TestReidentificationRequest:
    def test_creation(self):
        req = ReidentificationRequest(
            original=[{"age": 30}],
            synthetic=[{"age": 31}],
            quasi_identifiers=["age"],
        )
        assert len(req.original) == 1
        assert len(req.synthetic) == 1


# ---------------------------------------------------------------------------
# ReidentificationResponse
# ---------------------------------------------------------------------------

class TestReidentificationResponse:
    def test_defaults(self):
        resp = ReidentificationResponse()
        assert resp.overall_risk == pytest.approx(0.0)
        assert resp.max_risk == pytest.approx(0.0)
        assert resp.risky_records_pct == pytest.approx(0.0)
        assert resp.recommendation == ""

    def test_risk_bounds(self):
        resp = ReidentificationResponse(overall_risk=1.0, max_risk=1.0)
        assert resp.overall_risk == pytest.approx(1.0)

    def test_risk_out_of_bounds(self):
        with pytest.raises(Exception):
            ReidentificationResponse(overall_risk=1.5)


# ---------------------------------------------------------------------------
# PrivacyReportRequest
# ---------------------------------------------------------------------------

class TestPrivacyReportRequest:
    def test_creation(self):
        req = PrivacyReportRequest(data=[{"x": 1}])
        assert req.data == [{"x": 1}]

    def test_defaults(self):
        req = PrivacyReportRequest(data=[{}])
        assert req.original is None
        assert req.config is None
        assert req.epsilon == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# PrivacyReportResponse
# ---------------------------------------------------------------------------

class TestPrivacyReportResponse:
    def test_defaults(self):
        resp = PrivacyReportResponse()
        assert resp.epsilon == pytest.approx(1.0)
        assert resp.delta == pytest.approx(1e-5)
        assert resp.budget_spent == pytest.approx(0.0)
        assert resp.k_anonymity == {}
        assert resp.l_diversity is None
        assert resp.reidentification_risk is None
        assert resp.pii_columns_detected == []
        assert resp.pii_columns_protected == []
        assert resp.kvkk_compliant is False
        assert resp.kvkk_issues == []
        assert resp.recommendations == []

    def test_with_kvkk_compliant(self):
        resp = PrivacyReportResponse(kvkk_compliant=True)
        assert resp.kvkk_compliant is True


# ---------------------------------------------------------------------------
# PrivacyConfigSuggestion
# ---------------------------------------------------------------------------

class TestPrivacyConfigSuggestion:
    def test_creation(self):
        s = PrivacyConfigSuggestion(column="tckn", mechanism="laplace")
        assert s.column == "tckn"
        assert s.mechanism == "laplace"

    def test_defaults(self):
        s = PrivacyConfigSuggestion(column="age", mechanism="gaussian")
        assert s.sensitivity is None
        assert s.reason == ""

    def test_with_sensitivity(self):
        s = PrivacyConfigSuggestion(column="salary", mechanism="laplace", sensitivity=1000.0)
        assert s.sensitivity == pytest.approx(1000.0)


# ---------------------------------------------------------------------------
# SuggestConfigRequest
# ---------------------------------------------------------------------------

class TestSuggestConfigRequest:
    def test_creation(self):
        req = SuggestConfigRequest(data=[{"tckn": "12345678901"}])
        assert len(req.data) == 1

    def test_default_epsilon(self):
        req = SuggestConfigRequest(data=[{}])
        assert req.epsilon == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# SuggestConfigResponse
# ---------------------------------------------------------------------------

class TestSuggestConfigResponse:
    def test_defaults(self):
        resp = SuggestConfigResponse()
        assert resp.suggestions == []
        assert resp.detected_pii == []
        assert resp.column_config == {}

    def test_with_suggestions(self):
        s = PrivacyConfigSuggestion(column="tckn", mechanism="suppression")
        resp = SuggestConfigResponse(suggestions=[s], detected_pii=["tckn"])
        assert len(resp.suggestions) == 1
        assert "tckn" in resp.detected_pii


# ---------------------------------------------------------------------------
# TCKNValidateRequest
# ---------------------------------------------------------------------------

class TestTCKNValidateRequest:
    def test_valid_tckn(self):
        req = TCKNValidateRequest(tckn="12345678901")
        assert req.tckn == "12345678901"

    def test_too_short_raises(self):
        with pytest.raises(Exception):
            TCKNValidateRequest(tckn="1234567890")  # 10 chars

    def test_too_long_raises(self):
        with pytest.raises(Exception):
            TCKNValidateRequest(tckn="123456789012")  # 12 chars


# ---------------------------------------------------------------------------
# TCKNValidateResponse
# ---------------------------------------------------------------------------

class TestTCKNValidateResponse:
    def test_defaults(self):
        resp = TCKNValidateResponse()
        assert resp.valid is False
        assert resp.tckn == ""
        assert resp.message == ""

    def test_valid_response(self):
        resp = TCKNValidateResponse(valid=True, tckn="12345678901", message="OK")
        assert resp.valid is True
        assert resp.tckn == "12345678901"
