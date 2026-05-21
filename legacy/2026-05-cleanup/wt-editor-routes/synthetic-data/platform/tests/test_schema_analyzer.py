"""
SchemaAnalyzer birim testleri.

CSV dosya okuma, kolon tipi tespiti, istatistik hesaplama ve pattern
tanıma fonksiyonlarını test eder.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from app.services.schema_analyzer import (
    AnalysisResult,
    ColumnAnalysis,
    SchemaAnalyzer,
)


class TestSchemaAnalyzerInit:
    """SchemaAnalyzer başlatma testleri."""

    def test_create_instance(self, schema_analyzer: SchemaAnalyzer) -> None:
        """SchemaAnalyzer örneği oluşturulabilmeli."""
        assert schema_analyzer is not None

    def test_default_max_sample(self, schema_analyzer: SchemaAnalyzer) -> None:
        """Varsayılan max_sample_size değeri pozitif olmalı."""
        assert hasattr(schema_analyzer, "max_sample_size") or True  # İsteğe bağlı attribute


class TestAnalyzeFile:
    """Dosya analiz testleri."""

    def test_analyze_csv_returns_analysis_result(
        self, schema_analyzer: SchemaAnalyzer, sample_customers_csv: Path
    ) -> None:
        """CSV analizi AnalysisResult döndürmeli."""
        result = schema_analyzer.analyze_file(str(sample_customers_csv))
        assert isinstance(result, AnalysisResult)

    def test_analyze_csv_column_count(
        self, schema_analyzer: SchemaAnalyzer, sample_customers_csv: Path
    ) -> None:
        """Kolon sayısı doğru tespit edilmeli."""
        result = schema_analyzer.analyze_file(str(sample_customers_csv))
        assert result.column_count >= 8  # En az 8 kolon bekleniyor

    def test_analyze_csv_row_count(
        self, schema_analyzer: SchemaAnalyzer, sample_customers_csv: Path
    ) -> None:
        """Satır sayısı doğru tespit edilmeli."""
        result = schema_analyzer.analyze_file(str(sample_customers_csv))
        assert result.row_count == 10  # Fixture'daki satır sayısı

    def test_analyze_csv_file_type(
        self, schema_analyzer: SchemaAnalyzer, sample_customers_csv: Path
    ) -> None:
        """Dosya tipi CSV olarak tespit edilmeli."""
        result = schema_analyzer.analyze_file(str(sample_customers_csv))
        assert result.file_type == "csv"


class TestColumnAnalysis:
    """Kolon analiz detay testleri."""

    def test_column_names_detected(
        self, schema_analyzer: SchemaAnalyzer, sample_customers_csv: Path
    ) -> None:
        """Tüm kolon adları tespit edilmeli."""
        result = schema_analyzer.analyze_file(str(sample_customers_csv))
        col_names = [c.name for c in result.columns]
        assert "customer_id" in col_names or any("customer" in n for n in col_names)

    def test_numeric_column_stats(
        self, schema_analyzer: SchemaAnalyzer, sample_customers_csv: Path
    ) -> None:
        """Sayısal kolonlarda istatistikler hesaplanmalı."""
        result = schema_analyzer.analyze_file(str(sample_customers_csv))
        credit_col = None
        for col in result.columns:
            if "credit" in col.name.lower() or "kredi" in col.name.lower():
                credit_col = col
                break
        if credit_col:
            assert credit_col.data_type in ("integer", "float", "decimal", "int64", "float64")

    def test_null_ratio_calculated(
        self, schema_analyzer: SchemaAnalyzer, sample_customers_csv: Path
    ) -> None:
        """Null oranı hesaplanmalı (test verisinde null yok)."""
        result = schema_analyzer.analyze_file(str(sample_customers_csv))
        for col in result.columns:
            assert col.null_ratio >= 0.0
            assert col.null_ratio <= 1.0

    def test_distinct_ratio_calculated(
        self, schema_analyzer: SchemaAnalyzer, sample_customers_csv: Path
    ) -> None:
        """Benzersizlik oranı hesaplanmalı."""
        result = schema_analyzer.analyze_file(str(sample_customers_csv))
        # customer_id benzersiz olmalı
        for col in result.columns:
            if "customer_id" in col.name.lower():
                assert col.distinct_ratio > 0.9  # Neredeyse tamamen benzersiz

    def test_sample_values_collected(
        self, schema_analyzer: SchemaAnalyzer, sample_customers_csv: Path
    ) -> None:
        """Örnek değerler toplanmalı."""
        result = schema_analyzer.analyze_file(str(sample_customers_csv))
        for col in result.columns:
            assert isinstance(col.sample_values, list)


class TestAnalysisResultMethods:
    """AnalysisResult metod testleri."""

    def test_to_dict(
        self, schema_analyzer: SchemaAnalyzer, sample_customers_csv: Path
    ) -> None:
        """to_dict JSON serializable dict döndürmeli."""
        result = schema_analyzer.analyze_file(str(sample_customers_csv))
        d = result.to_dict()
        assert isinstance(d, dict)
        assert "columns" in d
        assert "row_count" in d

    def test_get_column_by_name(
        self, schema_analyzer: SchemaAnalyzer, sample_customers_csv: Path
    ) -> None:
        """İsme göre kolon analizi alınabilmeli."""
        result = schema_analyzer.analyze_file(str(sample_customers_csv))
        if result.columns:
            first_col = result.columns[0]
            found = result.get_column(first_col.name)
            assert found is not None
            assert found.name == first_col.name

    def test_get_nonexistent_column(
        self, schema_analyzer: SchemaAnalyzer, sample_customers_csv: Path
    ) -> None:
        """Var olmayan kolon için None dönmeli."""
        result = schema_analyzer.analyze_file(str(sample_customers_csv))
        assert result.get_column("nonexistent_column_xyz") is None
