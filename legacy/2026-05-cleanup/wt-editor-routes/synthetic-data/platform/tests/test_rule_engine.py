"""
RuleInferenceEngine birim testleri.

Otomatik kural çıkarma, doğrulama ve dışa aktarma fonksiyonlarını
test eder.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from app.services.rule_engine import (
    InferredRuleResult,
    RuleInferenceEngine,
    RuleInferenceReport,
    ValidationResult,
)
from app.services.schema_analyzer import SchemaAnalyzer


class TestRuleInferenceEngineInit:
    """RuleInferenceEngine başlatma testleri."""

    def test_create_instance(self, rule_engine: RuleInferenceEngine) -> None:
        """RuleInferenceEngine örneği oluşturulabilmeli."""
        assert rule_engine is not None


class TestInferRules:
    """Kural çıkarma testleri."""

    def test_infer_rules_returns_report(
        self, schema_analyzer: SchemaAnalyzer, rule_engine: RuleInferenceEngine,
        sample_customers_csv: Path,
    ) -> None:
        """infer_rules RuleInferenceReport döndürmeli."""
        analysis = schema_analyzer.analyze_file(str(sample_customers_csv))
        report = rule_engine.infer_rules(analysis)
        assert isinstance(report, RuleInferenceReport)

    def test_infer_rules_generates_rules(
        self, schema_analyzer: SchemaAnalyzer, rule_engine: RuleInferenceEngine,
        sample_customers_csv: Path,
    ) -> None:
        """En az birkaç kural çıkarılmalı."""
        analysis = schema_analyzer.analyze_file(str(sample_customers_csv))
        report = rule_engine.infer_rules(analysis)
        assert report.total_rules > 0
        assert len(report.rules) > 0

    def test_inferred_rule_has_valid_type(
        self, schema_analyzer: SchemaAnalyzer, rule_engine: RuleInferenceEngine,
        sample_customers_csv: Path,
    ) -> None:
        """Çıkarılan kurallar geçerli tipte olmalı."""
        valid_types = {
            "RANGE", "ENUM", "REGEX", "DISTRIBUTION", "DEPENDENCY",
            "NOT_NULL", "UNIQUE", "LENGTH", "CONDITIONAL",
        }
        analysis = schema_analyzer.analyze_file(str(sample_customers_csv))
        report = rule_engine.infer_rules(analysis)
        for rule in report.rules:
            assert rule.rule_type in valid_types, f"Geçersiz kural tipi: {rule.rule_type}"


class TestInferredRuleResult:
    """InferredRuleResult dataclass testleri."""

    def test_auto_generated_id(self) -> None:
        """Kural ID'si otomatik üretilmeli."""
        rule = InferredRuleResult(
            rule_id="",
            column_name="test_col",
            rule_type="RANGE",
            definition={"min": 0, "max": 100},
        )
        assert rule.rule_id != ""  # UUID otomatik atanmalı

    def test_to_dict(self) -> None:
        """to_dict JSON serializable dict döndürmeli."""
        rule = InferredRuleResult(
            rule_id="test-123",
            column_name="balance",
            rule_type="RANGE",
            definition={"min": 0, "max": 1000000},
            confidence=0.95,
            description="Bakiye aralığı",
        )
        d = rule.to_dict()
        assert isinstance(d, dict)
        assert d["column_name"] == "balance"
        assert d["rule_type"] == "RANGE"
        assert d["confidence"] == 0.95

    def test_to_orm_dict(self) -> None:
        """ORM uyumlu dict döndürmeli."""
        rule = InferredRuleResult(
            rule_id="test-456",
            column_name="segment",
            rule_type="ENUM",
            definition={"values": ["Bireysel", "KOBİ", "Ticari"]},
            confidence=0.90,
        )
        orm_dict = rule.to_orm_dict()
        assert "column_name" in orm_dict
        assert "rule_type" in orm_dict
        assert "rule_definition" in orm_dict
        assert "confidence_score" in orm_dict
