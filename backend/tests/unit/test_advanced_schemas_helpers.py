"""Unit tests for app.domains.ai_synthetic_data.advanced_schemas — Pydantic models.

Tests are fully self-contained: no DB, no HTTP, no AI.
Covers all 13 schema classes with defaults, validation constraints, and instantiation.
"""
from __future__ import annotations

import pytest

try:
    from app.domains.ai_synthetic_data.advanced_schemas import (
        KDEFitRequest,
        GenerateRequest,
        SyntheticRecord,
        GenerateResponse,
        BankingDatasetRequest,
        FullDatasetStats,
        BankingDatasetResponse,
        QualityCheckRequest,
        QualityMetrics,
        PrivacyRiskRequest,
        PrivacyRiskResponse,
        GeneratorInfo,
        GeneratorsListResponse,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="advanced_schemas import failed")


# ---------------------------------------------------------------------------
# KDEFitRequest
# ---------------------------------------------------------------------------

class TestKDEFitRequest:
    def test_creation(self):
        req = KDEFitRequest(data=[{"age": 25, "salary": 50000}])
        assert len(req.data) == 1

    def test_default_columns_none(self):
        req = KDEFitRequest(data=[{}])
        assert req.columns is None

    def test_with_columns(self):
        req = KDEFitRequest(data=[{"age": 25}], columns=["age"])
        assert req.columns == ["age"]


# ---------------------------------------------------------------------------
# GenerateRequest
# ---------------------------------------------------------------------------

class TestGenerateRequest:
    def test_defaults(self):
        req = GenerateRequest()
        assert req.count == 100
        assert req.seed is None
        assert req.generator_type == "kde"
        assert req.conditions is None
        assert req.sample_data is None

    def test_count_min(self):
        with pytest.raises(Exception):
            GenerateRequest(count=0)

    def test_count_max(self):
        with pytest.raises(Exception):
            GenerateRequest(count=100001)

    def test_custom_count(self):
        req = GenerateRequest(count=500)
        assert req.count == 500

    def test_with_seed(self):
        req = GenerateRequest(seed=42)
        assert req.seed == 42

    def test_ctgan_type(self):
        req = GenerateRequest(generator_type="ctgan")
        assert req.generator_type == "ctgan"


# ---------------------------------------------------------------------------
# SyntheticRecord
# ---------------------------------------------------------------------------

class TestSyntheticRecord:
    def test_default_empty_data(self):
        rec = SyntheticRecord()
        assert rec.data == {}

    def test_with_data(self):
        rec = SyntheticRecord(data={"age": 30, "name": "Test"})
        assert rec.data["age"] == 30


# ---------------------------------------------------------------------------
# GenerateResponse
# ---------------------------------------------------------------------------

class TestGenerateResponse:
    def test_defaults(self):
        resp = GenerateResponse()
        assert resp.records == []
        assert resp.quality_metrics is None
        assert resp.generator_type == "kde"
        assert resp.duration_ms == pytest.approx(0.0)
        assert resp.record_count == 0

    def test_with_records(self):
        resp = GenerateResponse(records=[{"age": 25}], record_count=1)
        assert len(resp.records) == 1
        assert resp.record_count == 1


# ---------------------------------------------------------------------------
# BankingDatasetRequest
# ---------------------------------------------------------------------------

class TestBankingDatasetRequest:
    def test_defaults(self):
        req = BankingDatasetRequest()
        assert req.customer_count == 100
        assert req.accounts_per_customer == 2
        assert req.transactions_per_account == 10
        assert req.days == 90
        assert req.generator_type == "kde"
        assert req.segment_distribution is None

    def test_customer_count_min(self):
        with pytest.raises(Exception):
            BankingDatasetRequest(customer_count=0)

    def test_customer_count_max(self):
        with pytest.raises(Exception):
            BankingDatasetRequest(customer_count=100001)

    def test_accounts_per_customer_max(self):
        with pytest.raises(Exception):
            BankingDatasetRequest(accounts_per_customer=21)

    def test_days_max(self):
        with pytest.raises(Exception):
            BankingDatasetRequest(days=3651)

    def test_with_segment_distribution(self):
        req = BankingDatasetRequest(segment_distribution={"bireysel": 0.6, "ticari": 0.4})
        assert req.segment_distribution["bireysel"] == pytest.approx(0.6)


# ---------------------------------------------------------------------------
# FullDatasetStats
# ---------------------------------------------------------------------------

class TestFullDatasetStats:
    def test_defaults(self):
        stats = FullDatasetStats()
        assert stats.customer_count == 0
        assert stats.account_count == 0
        assert stats.transaction_count == 0
        assert stats.total_volume_try == pytest.approx(0.0)
        assert stats.avg_balance == pytest.approx(0.0)
        assert stats.segments == {}
        assert stats.account_types == {}
        assert stats.transaction_types == {}

    def test_with_values(self):
        stats = FullDatasetStats(customer_count=100, account_count=200)
        assert stats.customer_count == 100
        assert stats.account_count == 200


# ---------------------------------------------------------------------------
# BankingDatasetResponse
# ---------------------------------------------------------------------------

class TestBankingDatasetResponse:
    def test_defaults(self):
        resp = BankingDatasetResponse()
        assert resp.customers == []
        assert resp.accounts == []
        assert resp.transactions == []
        assert resp.fk_integrity is True
        assert resp.duration_ms == pytest.approx(0.0)

    def test_stats_default_factory(self):
        resp = BankingDatasetResponse()
        assert isinstance(resp.stats, FullDatasetStats)


# ---------------------------------------------------------------------------
# QualityCheckRequest
# ---------------------------------------------------------------------------

class TestQualityCheckRequest:
    def test_creation(self):
        req = QualityCheckRequest(
            original=[{"age": 25}],
            synthetic=[{"age": 26}],
        )
        assert len(req.original) == 1
        assert len(req.synthetic) == 1


# ---------------------------------------------------------------------------
# QualityMetrics
# ---------------------------------------------------------------------------

class TestQualityMetrics:
    def test_defaults(self):
        m = QualityMetrics()
        assert m.column_stats == {}
        assert m.correlation_preservation == pytest.approx(0.0)
        assert m.distribution_similarity == {}
        assert m.overall_score == pytest.approx(0.0)

    def test_with_score(self):
        m = QualityMetrics(overall_score=0.85)
        assert m.overall_score == pytest.approx(0.85)


# ---------------------------------------------------------------------------
# PrivacyRiskRequest
# ---------------------------------------------------------------------------

class TestPrivacyRiskRequest:
    def test_creation(self):
        req = PrivacyRiskRequest(
            original=[{"tckn": "12345678901"}],
            synthetic=[{"tckn": "98765432100"}],
        )
        assert len(req.original) == 1


# ---------------------------------------------------------------------------
# PrivacyRiskResponse
# ---------------------------------------------------------------------------

class TestPrivacyRiskResponse:
    def test_defaults(self):
        resp = PrivacyRiskResponse()
        assert resp.risk_score == pytest.approx(0.0)
        assert resp.vulnerable_columns == []
        assert resp.recommendation == ""

    def test_risk_score_bounds_high(self):
        with pytest.raises(Exception):
            PrivacyRiskResponse(risk_score=1.5)

    def test_risk_score_bounds_low(self):
        with pytest.raises(Exception):
            PrivacyRiskResponse(risk_score=-0.1)

    def test_with_vulnerable_columns(self):
        resp = PrivacyRiskResponse(risk_score=0.7, vulnerable_columns=["tckn", "iban"])
        assert "tckn" in resp.vulnerable_columns
        assert resp.risk_score == pytest.approx(0.7)


# ---------------------------------------------------------------------------
# GeneratorInfo
# ---------------------------------------------------------------------------

class TestGeneratorInfo:
    def test_creation(self):
        info = GeneratorInfo(id="kde", name="KDE Generator", available=True, description="Kernel Density Estimation")
        assert info.id == "kde"
        assert info.available is True

    def test_unavailable(self):
        info = GeneratorInfo(id="ctgan", name="CTGAN", available=False, description="Conditional GAN")
        assert info.available is False


# ---------------------------------------------------------------------------
# GeneratorsListResponse
# ---------------------------------------------------------------------------

class TestGeneratorsListResponse:
    def test_default_empty(self):
        resp = GeneratorsListResponse()
        assert resp.generators == []

    def test_with_generators(self):
        g = GeneratorInfo(id="kde", name="KDE", available=True, description="desc")
        resp = GeneratorsListResponse(generators=[g])
        assert len(resp.generators) == 1
        assert resp.generators[0].id == "kde"
