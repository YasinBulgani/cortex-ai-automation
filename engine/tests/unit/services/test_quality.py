"""Statistical Fidelity and Quality Report unit tests."""

import pytest

from ai_synthetic_data.quality.statistical_fidelity import StatisticalFidelity
from ai_synthetic_data.quality.quality_report import QualityReporter

class TestStatisticalFidelity:
    @pytest.fixture
    def sf(self):
        return StatisticalFidelity()

    def test_numeric_comparison(self, sf):
        orig = [{"age": 30}, {"age": 40}, {"age": 50}]
        syn = [{"age": 32}, {"age": 38}, {"age": 52}]
        scores = sf.compare_distributions(orig, syn, ["age"])
        assert len(scores) == 1
        assert scores[0].metric == "numeric_distribution"
        assert 0 <= scores[0].score <= 1

    def test_categorical_comparison(self, sf):
        orig = [{"seg": "A"}, {"seg": "A"}, {"seg": "B"}]
        syn = [{"seg": "A"}, {"seg": "B"}, {"seg": "B"}]
        scores = sf.compare_distributions(orig, syn, ["seg"])
        assert len(scores) == 1
        assert scores[0].metric == "categorical_distribution"

    def test_empty_lists(self, sf):
        assert sf.compare_distributions([], []) == []
        assert sf.compare_distributions([{"a": 1}], []) == []

    def test_mixed_types_no_crash(self, sf):
        orig = [{"val": 1}, {"val": "text"}, {"val": 3}]
        syn = [{"val": 2}, {"val": "other"}]
        scores = sf.compare_distributions(orig, syn, ["val"])
        assert len(scores) == 1

    def test_bool_treated_as_categorical(self, sf):
        orig = [{"flag": True}, {"flag": False}]
        syn = [{"flag": True}, {"flag": True}]
        scores = sf.compare_distributions(orig, syn, ["flag"])
        assert scores[0].metric == "categorical_distribution"

    def test_kl_with_missing_category(self, sf):
        orig = [{"cat": "A"}, {"cat": "B"}]
        syn = [{"cat": "A"}, {"cat": "C"}]
        scores = sf.compare_distributions(orig, syn, ["cat"])
        assert 0 <= scores[0].score <= 1

    def test_single_value(self, sf):
        orig = [{"x": 10}]
        syn = [{"x": 12}]
        scores = sf.compare_distributions(orig, syn, ["x"])
        assert len(scores) == 1

class TestQualityReporter:
    @pytest.fixture
    def reporter(self):
        return QualityReporter()

    def test_generate_report(self, reporter):
        orig = [{"age": 30, "seg": "A"}, {"age": 40, "seg": "B"}]
        syn = [{"age": 32, "seg": "A"}, {"age": 38, "seg": "B"}]
        report = reporter.generate_report(orig, syn)
        assert 0 <= report.overall_score <= 1
        assert len(report.fidelity_scores) > 0

    def test_fk_integrity_check(self):
        parents = [{"id": "1"}, {"id": "2"}]
        children = [{"parent_id": "1"}, {"parent_id": "2"}, {"parent_id": "3"}]
        result = QualityReporter.check_fk_integrity(parents, children, "id", "parent_id")
        assert result["orphan_count"] == 1
        assert result["integrity_pct"] < 100

    def test_fk_integrity_empty(self):
        result = QualityReporter.check_fk_integrity([], [], "id", "parent_id")
        assert result["orphan_count"] == 0
        assert result["integrity_pct"] == 100.0

    def test_save_report(self, reporter, tmp_path):
        report = reporter.generate_report([{"a": 1}], [{"a": 2}])
        output = tmp_path / "quality.json"
        reporter.save_report(report, str(output))
        assert output.exists()
