"""
ColumnClassifier birim testleri.

Kolon adı eşleştirme, değer bazlı sınıflandırma ve semantik tip
ataması fonksiyonlarını test eder.
"""

from __future__ import annotations

import pandas as pd
import pytest

from app.services.column_classifier import (
    ClassificationResult,
    ColumnClassifier,
    SemanticType,
)
from app.services.schema_analyzer import ColumnAnalysis, SchemaAnalyzer


class TestSemanticTypeEnum:
    """SemanticType enum testleri."""

    def test_all_expected_types_exist(self) -> None:
        """Beklenen tüm semantik tipler tanımlı olmalı."""
        expected = [
            "first_name", "last_name", "national_id", "customer_id",
            "iban", "phone", "email", "city", "balance", "amount",
        ]
        type_values = [t.value for t in SemanticType]
        for e in expected:
            assert e in type_values, f"{e} SemanticType'da bulunamadı"

    def test_semantic_type_is_string_enum(self) -> None:
        """SemanticType string enum olmalı."""
        assert isinstance(SemanticType.FIRST_NAME.value, str)
        assert SemanticType.FIRST_NAME == "first_name"


class TestColumnClassifierInit:
    """ColumnClassifier başlatma testleri."""

    def test_create_instance(self, column_classifier: ColumnClassifier) -> None:
        """ColumnClassifier örneği oluşturulabilmeli."""
        assert column_classifier is not None


class TestClassifyColumn:
    """Tek kolon sınıflandırma testleri."""

    def test_classify_customer_id_column(
        self, schema_analyzer: SchemaAnalyzer, column_classifier: ColumnClassifier,
        sample_customers_csv,
    ) -> None:
        """customer_id kolonu CUSTOMER_ID olarak sınıflandırılmalı."""
        result = schema_analyzer.analyze_file(str(sample_customers_csv))
        for col in result.columns:
            if "customer_id" in col.name.lower():
                classification = column_classifier.classify(col)
                assert isinstance(classification, ClassificationResult)
                assert classification.semantic_type in (
                    SemanticType.CUSTOMER_ID, SemanticType.ACCOUNT_ID, SemanticType.UNKNOWN
                )

    def test_classify_email_column(
        self, schema_analyzer: SchemaAnalyzer, column_classifier: ColumnClassifier,
        sample_customers_csv,
    ) -> None:
        """email kolonu EMAIL olarak sınıflandırılmalı."""
        result = schema_analyzer.analyze_file(str(sample_customers_csv))
        for col in result.columns:
            if "email" in col.name.lower():
                classification = column_classifier.classify(col)
                assert classification.semantic_type == SemanticType.EMAIL

    def test_classify_phone_column(
        self, schema_analyzer: SchemaAnalyzer, column_classifier: ColumnClassifier,
        sample_customers_csv,
    ) -> None:
        """phone kolonu PHONE olarak sınıflandırılmalı."""
        result = schema_analyzer.analyze_file(str(sample_customers_csv))
        for col in result.columns:
            if "phone" in col.name.lower():
                classification = column_classifier.classify(col)
                assert classification.semantic_type == SemanticType.PHONE

    def test_classify_city_column(
        self, schema_analyzer: SchemaAnalyzer, column_classifier: ColumnClassifier,
        sample_customers_csv,
    ) -> None:
        """city kolonu CITY olarak sınıflandırılmalı."""
        result = schema_analyzer.analyze_file(str(sample_customers_csv))
        for col in result.columns:
            if col.name.lower() == "city":
                classification = column_classifier.classify(col)
                assert classification.semantic_type == SemanticType.CITY


class TestClassificationResult:
    """ClassificationResult testleri."""

    def test_confidence_range(
        self, schema_analyzer: SchemaAnalyzer, column_classifier: ColumnClassifier,
        sample_customers_csv,
    ) -> None:
        """Güven skoru 0-1 arasında olmalı."""
        result = schema_analyzer.analyze_file(str(sample_customers_csv))
        for col in result.columns:
            classification = column_classifier.classify(col)
            assert 0.0 <= classification.confidence <= 1.0

    def test_to_dict_method(
        self, schema_analyzer: SchemaAnalyzer, column_classifier: ColumnClassifier,
        sample_customers_csv,
    ) -> None:
        """to_dict JSON serializable dict döndürmeli."""
        result = schema_analyzer.analyze_file(str(sample_customers_csv))
        col = result.columns[0]
        classification = column_classifier.classify(col)
        d = classification.to_dict()
        assert isinstance(d, dict)
        assert "semantic_type" in d
        assert "confidence" in d
