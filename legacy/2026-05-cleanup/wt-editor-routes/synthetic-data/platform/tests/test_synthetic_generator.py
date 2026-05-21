"""
SyntheticDataGenerator birim testleri.

Türk bankacılık sentetik veri üretimi, TCKN/IBAN doğrulama, kural bazlı
üretim ve export fonksiyonlarını test eder.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from app.services.synthetic_generator import (
    GenerationProgress,
    GenerationResult,
    SyntheticDataGenerator,
)


class TestSyntheticGeneratorInit:
    """SyntheticDataGenerator başlatma testleri."""

    def test_create_instance(self, synthetic_generator: SyntheticDataGenerator) -> None:
        """SyntheticDataGenerator örneği oluşturulabilmeli."""
        assert synthetic_generator is not None


class TestTurkishDataGeneration:
    """Türk bankacılık domain verisi üretim testleri."""

    def test_generate_tckn_valid_format(self, synthetic_generator: SyntheticDataGenerator) -> None:
        """Üretilen TCKN 11 haneli ve sayısal olmalı."""
        tckn = synthetic_generator._generate_tckn()
        assert len(tckn) == 11
        assert tckn.isdigit()
        assert tckn[0] != "0"  # İlk hane 0 olamaz

    def test_generate_tckn_checksum(self, synthetic_generator: SyntheticDataGenerator) -> None:
        """Üretilen TCKN kontrol haneleri doğru olmalı."""
        tckn = synthetic_generator._generate_tckn()
        digits = [int(d) for d in tckn]
        # 10. hane kontrolü
        d10 = ((digits[0] + digits[2] + digits[4] + digits[6] + digits[8]) * 7
               - (digits[1] + digits[3] + digits[5] + digits[7])) % 10
        assert digits[9] == d10
        # 11. hane kontrolü
        d11 = sum(digits[:10]) % 10
        assert digits[10] == d11

    def test_generate_iban_valid_format(self, synthetic_generator: SyntheticDataGenerator) -> None:
        """Üretilen IBAN TR formatında ve doğru uzunlukta olmalı."""
        iban = synthetic_generator._generate_iban()
        assert iban.startswith("TR")
        assert len(iban) == 26
        assert iban[2:].isdigit()  # TR sonrası tamamı rakam

    def test_generate_phone_valid_format(self, synthetic_generator: SyntheticDataGenerator) -> None:
        """Üretilen telefon numarası Türk formatında olmalı."""
        phone = synthetic_generator._generate_phone()
        assert phone.startswith("+90") or phone.startswith("05")
        # Sadece rakam ve + içermeli
        cleaned = phone.replace("+", "").replace(" ", "").replace("-", "")
        assert cleaned.isdigit()

    def test_generate_email_valid_format(self, synthetic_generator: SyntheticDataGenerator) -> None:
        """Üretilen email geçerli formatda olmalı."""
        email = synthetic_generator._generate_email()
        assert "@" in email
        assert "." in email.split("@")[1]


class TestGenerationResult:
    """GenerationResult testleri."""

    def test_generation_result_creation(self) -> None:
        """GenerationResult doğru oluşturulmalı."""
        result = GenerationResult(
            table_name="customers",
            row_count=100,
            dataframe=pd.DataFrame({"id": range(100)}),
        )
        assert result.table_name == "customers"
        assert result.row_count == 100
        assert len(result.dataframe) == 100

    def test_generation_progress_creation(self) -> None:
        """GenerationProgress doğru oluşturulmalı."""
        progress = GenerationProgress(
            table_name="accounts",
            total_rows=500,
            completed_rows=250,
            current_chunk=5,
            total_chunks=10,
        )
        assert progress.table_name == "accounts"
        assert progress.total_rows == 500
        assert progress.completed_rows == 250


class TestExportFormats:
    """Dışa aktarma format testleri."""

    def test_export_csv(self, synthetic_generator: SyntheticDataGenerator, tmp_path: Path) -> None:
        """CSV export fonksiyonu çalışmalı."""
        df = pd.DataFrame({
            "customer_id": ["MUS001", "MUS002", "MUS003"],
            "first_name": ["Ahmet", "Ayşe", "Mehmet"],
            "balance": [1500.50, 25000.00, 8900.75],
        })
        result = GenerationResult(
            table_name="test_customers",
            row_count=3,
            dataframe=df,
        )
        output_path = tmp_path / "test_export.csv"
        synthetic_generator.export_csv(result, str(output_path))
        assert output_path.exists()
        # İçerik doğrulama
        exported_df = pd.read_csv(output_path)
        assert len(exported_df) == 3
        assert "customer_id" in exported_df.columns

    def test_export_json(self, synthetic_generator: SyntheticDataGenerator, tmp_path: Path) -> None:
        """JSON export fonksiyonu çalışmalı."""
        df = pd.DataFrame({
            "account_id": ["HSP001", "HSP002"],
            "balance": [5000.0, 12000.0],
        })
        result = GenerationResult(
            table_name="test_accounts",
            row_count=2,
            dataframe=df,
        )
        output_path = tmp_path / "test_export.json"
        synthetic_generator.export_json(result, str(output_path))
        assert output_path.exists()
