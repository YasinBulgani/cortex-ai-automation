"""
PIIDetector birim testleri.

KVKK uyumlu PII tespiti, kategori ataması ve aksiyon önerisi
fonksiyonlarını test eder.
"""

from __future__ import annotations

import pytest

from app.services.column_classifier import (
    ClassificationResult,
    ColumnClassifier,
    SemanticType,
)
from app.services.pii_detector import (
    DetectionMethod,
    KVKKCategory,
    PIIAction,
    PIICategory,
    PIIDetector,
    PIIReport,
    PIIResult,
)
from app.services.schema_analyzer import SchemaAnalyzer


class TestPIICategoryEnum:
    """PIICategory enum testleri."""

    def test_all_levels_exist(self) -> None:
        """Tüm PII seviyeleri tanımlı olmalı."""
        levels = [c.value for c in PIICategory]
        assert "critical" in levels
        assert "high" in levels
        assert "medium" in levels
        assert "low" in levels
        assert "none" in levels


class TestPIIActionEnum:
    """PIIAction enum testleri."""

    def test_all_actions_exist(self) -> None:
        """Tüm PII aksiyonları tanımlı olmalı."""
        actions = [a.value for a in PIIAction]
        assert "synthesize" in actions
        assert "mask" in actions
        assert "hash" in actions
        assert "keep" in actions
        assert "redact" in actions


class TestKVKKCategory:
    """KVKK kategori testleri."""

    def test_kvkk_categories_exist(self) -> None:
        """KVKK kategorileri tanımlı olmalı."""
        cats = [c.value for c in KVKKCategory]
        assert "kimlik" in cats
        assert "iletisim" in cats
        assert "finansal" in cats


class TestPIIDetection:
    """PII tespit testleri."""

    def test_detect_tckn_as_critical(
        self, schema_analyzer: SchemaAnalyzer, column_classifier: ColumnClassifier,
        pii_detector: PIIDetector, sample_customers_csv,
    ) -> None:
        """TCKN kolonu CRITICAL PII olarak tespit edilmeli."""
        result = schema_analyzer.analyze_file(str(sample_customers_csv))
        for col in result.columns:
            if "tckn" in col.name.lower():
                classification = column_classifier.classify(col)
                pii = pii_detector.detect(col, classification)
                assert isinstance(pii, PIIResult)
                assert pii.is_pii is True
                assert pii.pii_category in (PIICategory.CRITICAL, PIICategory.HIGH)

    def test_detect_email_as_high(
        self, schema_analyzer: SchemaAnalyzer, column_classifier: ColumnClassifier,
        pii_detector: PIIDetector, sample_customers_csv,
    ) -> None:
        """Email kolonu HIGH PII olarak tespit edilmeli."""
        result = schema_analyzer.analyze_file(str(sample_customers_csv))
        for col in result.columns:
            if "email" in col.name.lower():
                classification = column_classifier.classify(col)
                pii = pii_detector.detect(col, classification)
                assert pii.is_pii is True
                assert pii.pii_category in (PIICategory.HIGH, PIICategory.MEDIUM)

    def test_detect_city_as_low(
        self, schema_analyzer: SchemaAnalyzer, column_classifier: ColumnClassifier,
        pii_detector: PIIDetector, sample_customers_csv,
    ) -> None:
        """Şehir kolonu LOW PII olarak tespit edilmeli."""
        result = schema_analyzer.analyze_file(str(sample_customers_csv))
        for col in result.columns:
            if col.name.lower() == "city":
                classification = column_classifier.classify(col)
                pii = pii_detector.detect(col, classification)
                assert pii.pii_category in (PIICategory.LOW, PIICategory.NONE)


class TestPIIResultMethods:
    """PIIResult metod testleri."""

    def test_to_dict(
        self, schema_analyzer: SchemaAnalyzer, column_classifier: ColumnClassifier,
        pii_detector: PIIDetector, sample_customers_csv,
    ) -> None:
        """to_dict JSON serializable dict döndürmeli."""
        result = schema_analyzer.analyze_file(str(sample_customers_csv))
        col = result.columns[0]
        classification = column_classifier.classify(col)
        pii = pii_detector.detect(col, classification)
        d = pii.to_dict()
        assert isinstance(d, dict)
        assert "is_pii" in d
        assert "pii_category" in d
        assert "recommended_action" in d
        assert "kvkk_category" in d
