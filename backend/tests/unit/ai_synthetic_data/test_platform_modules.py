"""
Unit tests — ai_synthetic_data.platform modülleri (Faz 3.B, ADR-0003).

Her modül için en az 2 test — plan kabul kriteri.

Modüller:
    - SchemaAnalyzer
    - ColumnClassifier
    - RuleEngine
    - LearningEngine
    - ScenarioManager
"""
from __future__ import annotations

import io
import json

import pytest

from app.domains.ai_synthetic_data.platform import (
    ColumnClassifier,
    LearningEngine,
    RuleEngine,
    SCENARIOS,
    SchemaAnalyzer,
    ScenarioManager,
)


# ══════════════════════════════════════════════════════════════════════
# SchemaAnalyzer
# ══════════════════════════════════════════════════════════════════════

_pandas_available = True
try:
    import pandas  # noqa: F401
except ImportError:
    _pandas_available = False

_needs_pandas = pytest.mark.skipif(
    not _pandas_available,
    reason="SchemaAnalyzer için pandas gerekli — opsiyonel bağımlılık",
)


@_needs_pandas
class TestSchemaAnalyzer:
    @pytest.fixture
    def analyzer(self) -> SchemaAnalyzer:
        return SchemaAnalyzer()

    def test_analyze_csv_returns_basic_structure(self, analyzer: SchemaAnalyzer):
        csv = b"id,name,balance\n1,Ali,1000.5\n2,Veli,2500\n3,Ayse,750\n"
        result = analyzer.analyze_csv(csv, "customers.csv")

        assert result["table_name"] == "customers"
        assert result["source_type"] == "csv"
        assert result["row_count"] == 3
        assert len(result["columns"]) == 3
        col_names = {c["name"] for c in result["columns"]}
        assert col_names == {"id", "name", "balance"}

    def test_analyze_csv_detects_numeric_stats(self, analyzer: SchemaAnalyzer):
        csv = b"amount\n100\n200\n300\n400\n500\n"
        result = analyzer.analyze_csv(csv, "t.csv")
        amount = next(c for c in result["columns"] if c["name"] == "amount")
        assert amount["stats"]["min"] == 100
        assert amount["stats"]["max"] == 500
        assert amount["stats"]["mean"] == 300

    def test_analyze_csv_detects_enum(self, analyzer: SchemaAnalyzer):
        csv = b"status\nactive\nactive\ninactive\nactive\ninactive\nactive\n"
        result = analyzer.analyze_csv(csv, "t.csv")
        status = next(c for c in result["columns"] if c["name"] == "status")
        assert status["classification"] == "enum"
        assert "top_values" in status["stats"]

    def test_analyze_json_array(self, analyzer: SchemaAnalyzer):
        data = json.dumps([{"a": 1, "b": "x"}, {"a": 2, "b": "y"}]).encode()
        result = analyzer.analyze_json(data, "d.json")
        assert result["row_count"] == 2
        assert result["source_type"] == "json"

    def test_detect_relationships_by_name_heuristic(self, analyzer: SchemaAnalyzer):
        schemas = [
            {
                "table_name": "customers",
                "columns": [{"name": "id"}, {"name": "name"}],
            },
            {
                "table_name": "orders",
                "columns": [{"name": "id"}, {"name": "customer_id"}],
            },
        ]
        rels = analyzer.detect_relationships(schemas)
        assert len(rels) == 1
        assert rels[0]["from_table"] == "orders"
        assert rels[0]["to_table"] == "customers"
        assert rels[0]["confidence"] == 0.9


# ══════════════════════════════════════════════════════════════════════
# ColumnClassifier
# ══════════════════════════════════════════════════════════════════════

class TestColumnClassifier:
    @pytest.fixture
    def classifier(self) -> ColumnClassifier:
        return ColumnClassifier()

    def test_classify_email_by_name(self, classifier: ColumnClassifier):
        col = {
            "name": "email",
            "dtype": "object",
            "sample_values": ["a@b.com"],
        }
        result = classifier.classify(col)
        assert result["classification"] == "email"
        assert result["pii"] is True
        assert result["pii_confidence"] > 0
        assert result["faker_config"]["provider"] == "email"

    def test_classify_tc_kimlik_by_name(self, classifier: ColumnClassifier):
        col = {
            "name": "tckn",  # direct name match
            "dtype": "object",
            "sample_values": ["12345678901", "23456789012"],
        }
        result = classifier.classify(col)
        assert result["classification"] == "tc_kimlik"
        assert result["pii"] is True

    def test_classify_unknown_column(self, classifier: ColumnClassifier):
        col = {
            "name": "foo_bar_baz",
            "dtype": "object",
            "sample_values": ["random"],
        }
        result = classifier.classify(col)
        # No pattern matches strongly → faker_config None, PII not promoted
        assert result.get("pii", False) is False
        assert result["faker_config"] is None

    def test_classify_schema_produces_pii_summary(self, classifier: ColumnClassifier):
        schema = {
            "table_name": "users",
            "columns": [
                {"name": "email", "dtype": "object", "sample_values": ["a@b.com"]},
                {"name": "age", "dtype": "int64", "sample_values": ["25", "30"]},
                {"name": "iban", "dtype": "object",
                 "sample_values": ["TR330006100519786457841326"]},
            ],
        }
        result = classifier.classify_schema(schema)
        assert result["pii_summary"]["total_columns"] == 3
        assert result["pii_summary"]["pii_columns"] >= 2
        assert "email" in result["pii_summary"]["pii_fields"]
        assert "iban" in result["pii_summary"]["pii_fields"]

    def test_classify_enum_untouched(self, classifier: ColumnClassifier):
        """Analyzer'ın enum olarak işaretlediğini classifier değiştirmez."""
        col = {
            "name": "status",
            "dtype": "object",
            "classification": "enum",
            "stats": {"top_values": {"a": 0.5, "b": 0.5}},
            "sample_values": ["a", "b"],
        }
        result = classifier.classify(col)
        assert result["classification"] == "enum"
        assert result["pii"] is False
        assert result["faker_config"] is None


# ══════════════════════════════════════════════════════════════════════
# RuleEngine
# ══════════════════════════════════════════════════════════════════════

class TestRuleEngine:
    @pytest.fixture
    def engine(self) -> RuleEngine:
        return RuleEngine()

    def test_faker_rule_for_classified_pii(self, engine: RuleEngine):
        schema = {
            "columns": [{
                "name": "email",
                "classification": "email",
                "faker_config": {"provider": "email"},
                "stats": {},
            }],
        }
        rules = engine.infer_rules(schema)
        assert len(rules) == 1
        assert rules[0]["rule_type"] == "faker"
        assert rules[0]["rule_config"]["provider"] == "email"

    def test_range_rule_for_numeric_with_stats(self, engine: RuleEngine):
        schema = {
            "columns": [{
                "name": "balance",
                "classification": "amount",  # but no faker_config → falls through
                "stats": {"min": 0, "max": 1000, "mean": 500, "std": 100},
                "null_ratio": 0,
            }],
        }
        rules = engine.infer_rules(schema)
        range_rule = next(r for r in rules if r["rule_type"] == "range")
        assert range_rule["rule_config"]["min"] == 0
        assert range_rule["rule_config"]["max"] == 1000
        assert range_rule["rule_config"]["distribution"] == "normal"

    def test_enum_rule_from_top_values(self, engine: RuleEngine):
        schema = {
            "columns": [{
                "name": "status",
                "classification": "enum",
                "stats": {"top_values": {"active": 0.7, "inactive": 0.3}},
                "null_ratio": 0,
            }],
        }
        rules = engine.infer_rules(schema)
        enum_rule = next(r for r in rules if r["rule_type"] == "enum")
        assert enum_rule["rule_config"]["values"] == ["active", "inactive"]
        assert enum_rule["rule_config"]["weights"] == [0.7, 0.3]

    def test_nullable_rule_appended_when_nulls_exist(self, engine: RuleEngine):
        schema = {
            "columns": [{
                "name": "optional_col",
                "classification": "unknown",
                "stats": {"min_length": 1, "max_length": 50},
                "null_ratio": 0.2,
            }],
        }
        rules = engine.infer_rules(schema)
        nullable = next(r for r in rules if r["rule_type"] == "nullable")
        assert nullable["rule_config"]["null_ratio"] == 0.2

    def test_temporal_order_rule_for_known_pairs(self, engine: RuleEngine):
        schema = {
            "columns": [
                {"name": "created_at", "classification": "datetime", "stats": {"min_date": "2024-01-01", "max_date": "2024-12-31"}},
                {"name": "updated_at", "classification": "datetime", "stats": {"min_date": "2024-01-01", "max_date": "2024-12-31"}},
            ],
        }
        rules = engine.infer_rules(schema)
        temporal = [r for r in rules if r["rule_type"] == "temporal_order"]
        assert len(temporal) == 1
        assert temporal[0]["column_name"] == "updated_at"
        assert temporal[0]["rule_config"]["after_column"] == "created_at"


# ══════════════════════════════════════════════════════════════════════
# LearningEngine
# ══════════════════════════════════════════════════════════════════════

class TestLearningEngine:
    @pytest.fixture
    def learner(self) -> LearningEngine:
        return LearningEngine()

    def test_no_data_returns_status(self, learner: LearningEngine):
        result = learner.analyze_schema({"columns": []}, [], [])
        assert result["status"] == "no_data"
        assert result["confidence"] == 0.0

    def test_numeric_drift_produces_suggestion(self, learner: LearningEngine):
        schema = {"columns": [{"name": "amount", "dtype": "int64"}]}
        rules = [{
            "column_name": "amount",
            "rule_type": "range",
            "rule_config": {"min": 0, "max": 100, "mean": 50, "std": 20},
        }]
        # Gerçek veri min=900, max=1100 → %800+ drift
        history_previews = [[{"amount": v} for v in range(900, 1101, 20)]]
        result = learner.analyze_schema(schema, rules, history_previews)
        assert result["status"] == "analyzed"
        assert len(result["suggestions"]) == 1
        assert result["suggestions"][0]["column"] == "amount"
        assert result["suggestions"][0]["drift_pct"] > 15

    def test_numeric_no_drift_produces_no_suggestion(self, learner: LearningEngine):
        schema = {"columns": [{"name": "amount", "dtype": "int64"}]}
        # Configured değerleri gerçekleşen ile neredeyse aynı → drift < %15
        rules = [{
            "column_name": "amount",
            "rule_type": "range",
            "rule_config": {"min": 48, "max": 53, "mean": 50, "std": 2},
        }]
        history_previews = [[{"amount": v} for v in [48, 50, 52, 49, 51, 50, 51, 49]]]
        result = learner.analyze_schema(schema, rules, history_previews)
        assert len(result["insights"]) == 1
        # Configured range gerçekleşen ile uyumlu → öneri yok
        assert len(result["suggestions"]) == 0

    def test_apply_suggestions_marks_learned(self, learner: LearningEngine):
        rules = [{"column_name": "x", "rule_type": "range", "rule_config": {"min": 0}}]
        suggestions = [{
            "column": "x",
            "rule_type": "range",
            "suggested_config": {"min": 100, "max": 200},
        }]
        result = learner.apply_suggestions(rules, suggestions)
        assert result[0]["rule_config"]["min"] == 100
        assert result[0]["learned"] is True

    def test_categorical_new_values_suggestion(self, learner: LearningEngine):
        schema = {"columns": [{"name": "type", "dtype": "object", "classification": "enum"}]}
        rules = [{
            "column_name": "type",
            "rule_type": "enum",
            "rule_config": {"values": ["A", "B"], "weights": [0.5, 0.5]},
        }]
        # Gerçek veride yeni değerler var
        history_previews = [[
            {"type": "A"}, {"type": "B"}, {"type": "C"}, {"type": "D"},
            {"type": "A"}, {"type": "C"},
        ]]
        result = learner.analyze_schema(schema, rules, history_previews)
        assert len(result["suggestions"]) == 1
        suggested_values = set(result["suggestions"][0]["suggested_config"]["values"])
        assert "C" in suggested_values
        assert "D" in suggested_values


# ══════════════════════════════════════════════════════════════════════
# ScenarioManager
# ══════════════════════════════════════════════════════════════════════

class TestScenarioManager:
    @pytest.fixture
    def manager(self) -> ScenarioManager:
        return ScenarioManager()

    def test_list_scenarios_has_core_entries(self, manager: ScenarioManager):
        scenarios = manager.list_scenarios()
        keys = {s["key"] for s in scenarios}
        assert "default" in keys
        assert "premium_customer" in keys
        assert "new_customer" in keys
        assert "high_risk" in keys
        assert "corporate" in keys
        assert "fraud_test" in keys

    def test_get_unknown_scenario_returns_none(self, manager: ScenarioManager):
        assert manager.get_scenario("does_not_exist") is None

    def test_get_overrides_returns_table_specific(self, manager: ScenarioManager):
        overrides = manager.get_overrides("premium_customer", "customers")
        assert overrides is not None
        assert "balance" in overrides
        assert overrides["balance"]["rule_type"] == "range"

    def test_apply_scenario_overrides_rules(self, manager: ScenarioManager):
        rules = [
            {"column_name": "balance", "rule_type": "range",
             "rule_config": {"min": 0, "max": 1000}},
            {"column_name": "name", "rule_type": "faker",
             "rule_config": {"provider": "name"}},
        ]
        new_rules = manager.apply_scenario("premium_customer", rules, "customers")

        balance_rule = next(r for r in new_rules if r["column_name"] == "balance")
        # Premium override: min=100000
        assert balance_rule["rule_config"]["min"] == 100000

        # Diğer kurallar korunur
        name_rule = next(r for r in new_rules if r["column_name"] == "name")
        assert name_rule["rule_type"] == "faker"

    def test_apply_scenario_no_overrides_returns_rules_unchanged(
        self, manager: ScenarioManager
    ):
        rules = [{"column_name": "balance", "rule_type": "range", "rule_config": {"min": 0}}]
        # 'default' senaryosunun overrides'ı boş
        result = manager.apply_scenario("default", rules, "customers")
        assert result == rules

    def test_all_scenarios_have_required_fields(self):
        for key, s in SCENARIOS.items():
            assert "name" in s, f"{key} missing name"
            assert "description" in s, f"{key} missing description"
            assert "overrides" in s, f"{key} missing overrides"
            assert isinstance(s["overrides"], dict)
