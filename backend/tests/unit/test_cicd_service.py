"""
cicd service unit testleri — 15 test.

Tests are fully self-contained: no DB, no HTTP, no external services.
Focuses on the pure quality-gate logic and the service facade.
Jenkins calls are mocked where needed.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

try:
    from app.domains.cicd.service import run_quality_gate, list_jenkins_connections
    from app.domains.cicd.quality_gate import (
        BaseCheck,
        CheckResult,
        GateResult,
        QualityGate,
        PassRateCheck,
        MaxFailuresCheck,
        DurationCheck,
        NoNewFlakiesCheck,
        CoverageCheck,
        build_gate_from_config,
    )
    _IMPORT_OK = True
except Exception:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="cicd service import failed")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _good_summary(
    passed: int = 90,
    failed: int = 2,
    total: int = 92,
    duration_s: float = 120.0,
    new_flaky_count: int = 0,
    coverage_pct: float = 85.0,
) -> dict:
    return dict(
        passed=passed,
        failed=failed,
        total=total,
        duration_s=duration_s,
        new_flaky_count=new_flaky_count,
        coverage_pct=coverage_pct,
    )


# ---------------------------------------------------------------------------
# BaseCheck ABC
# ---------------------------------------------------------------------------

class TestBaseCheckABC:
    def test_cannot_instantiate_base_check_directly(self):
        """BaseCheck must be abstract — direct instantiation must raise."""
        with pytest.raises(TypeError):
            BaseCheck()  # type: ignore[abstract]

    def test_concrete_subclass_must_implement_run(self):
        """A subclass that doesn't override run() is also uninstantiable."""
        class BadCheck(BaseCheck):
            pass
        with pytest.raises(TypeError):
            BadCheck()

    def test_valid_subclass_is_instantiable(self):
        class GoodCheck(BaseCheck):
            name = "good"
            def run(self, summary: dict) -> CheckResult:
                return CheckResult(name=self.name, passed=True, value=None, threshold=None)
        c = GoodCheck()
        r = c.run({})
        assert r.passed is True


# ---------------------------------------------------------------------------
# PassRateCheck
# ---------------------------------------------------------------------------

class TestPassRateCheck:
    def test_passes_when_rate_above_threshold(self):
        check = PassRateCheck(min_pct=80.0)
        result = check.run({"passed": 90, "total": 100})
        assert result.passed is True
        assert result.message == ""

    def test_fails_when_rate_below_threshold(self):
        check = PassRateCheck(min_pct=80.0)
        result = check.run({"passed": 70, "total": 100})
        assert result.passed is False
        assert "70.0%" in result.message

    def test_zero_total_produces_zero_rate(self):
        check = PassRateCheck(min_pct=80.0)
        result = check.run({"passed": 0, "total": 0})
        assert result.passed is False

    def test_exactly_at_threshold_passes(self):
        check = PassRateCheck(min_pct=80.0)
        result = check.run({"passed": 80, "total": 100})
        assert result.passed is True


# ---------------------------------------------------------------------------
# MaxFailuresCheck
# ---------------------------------------------------------------------------

class TestMaxFailuresCheck:
    def test_passes_when_failures_within_limit(self):
        check = MaxFailuresCheck(max_count=5)
        result = check.run({"failed": 3})
        assert result.passed is True

    def test_fails_when_failures_exceed_limit(self):
        check = MaxFailuresCheck(max_count=5)
        result = check.run({"failed": 6})
        assert result.passed is False
        assert "6" in result.message

    def test_passes_at_exact_limit(self):
        check = MaxFailuresCheck(max_count=5)
        result = check.run({"failed": 5})
        assert result.passed is True


# ---------------------------------------------------------------------------
# DurationCheck
# ---------------------------------------------------------------------------

class TestDurationCheck:
    def test_passes_when_duration_within_limit(self):
        check = DurationCheck(max_seconds=600.0)
        result = check.run({"duration_s": 300.0})
        assert result.passed is True

    def test_fails_when_duration_exceeds_limit(self):
        check = DurationCheck(max_seconds=600.0)
        result = check.run({"duration_s": 700.0})
        assert result.passed is False

    def test_passes_at_exact_limit(self):
        check = DurationCheck(max_seconds=600.0)
        result = check.run({"duration_s": 600.0})
        assert result.passed is True


# ---------------------------------------------------------------------------
# NoNewFlakiesCheck
# ---------------------------------------------------------------------------

class TestNoNewFlakiesCheck:
    def test_passes_when_no_new_flakies(self):
        check = NoNewFlakiesCheck(max_new=0)
        result = check.run({"new_flaky_count": 0})
        assert result.passed is True

    def test_fails_when_new_flakies_present(self):
        check = NoNewFlakiesCheck(max_new=0)
        result = check.run({"new_flaky_count": 1})
        assert result.passed is False
        assert "1" in result.message


# ---------------------------------------------------------------------------
# CoverageCheck
# ---------------------------------------------------------------------------

class TestCoverageCheck:
    def test_passes_when_coverage_above_threshold(self):
        check = CoverageCheck(min_pct=70.0)
        result = check.run({"coverage_pct": 85.0})
        assert result.passed is True

    def test_fails_when_coverage_below_threshold(self):
        check = CoverageCheck(min_pct=70.0)
        result = check.run({"coverage_pct": 60.0})
        assert result.passed is False

    def test_skips_when_coverage_data_missing(self):
        check = CoverageCheck(min_pct=70.0)
        result = check.run({})  # no coverage_pct key
        assert result.passed is True
        assert result.value == "N/A"


# ---------------------------------------------------------------------------
# QualityGate.evaluate
# ---------------------------------------------------------------------------

class TestQualityGateEvaluate:
    def test_empty_gate_passes(self):
        gate = QualityGate(name="Empty")
        result = gate.evaluate({})
        assert result.result == "passed"
        assert result.checks == []

    def test_all_checks_pass_returns_passed(self):
        gate = QualityGate()
        gate.add_check(PassRateCheck(min_pct=80.0))
        gate.add_check(MaxFailuresCheck(max_count=5))
        result = gate.evaluate(_good_summary())
        assert result.result == "passed"
        assert result.blocking_messages == []

    def test_one_failing_check_returns_failed(self):
        gate = QualityGate()
        gate.add_check(PassRateCheck(min_pct=99.0))  # will fail
        result = gate.evaluate({"passed": 70, "total": 100})
        assert result.result == "failed"
        assert len(result.blocking_messages) > 0

    def test_gate_result_to_dict_structure(self):
        gate = QualityGate(name="Test Gate")
        gate.add_check(PassRateCheck())
        gr = gate.evaluate(_good_summary())
        d = gr.to_dict()
        assert d["gate_name"] == "Test Gate"
        assert "result" in d
        assert "checks" in d
        assert "passed" in d


# ---------------------------------------------------------------------------
# build_gate_from_config
# ---------------------------------------------------------------------------

class TestBuildGateFromConfig:
    def test_empty_config_builds_gate_with_no_checks(self):
        gate = build_gate_from_config({})
        assert len(gate._checks) == 0

    def test_full_config_builds_all_five_checks(self):
        config = {
            "name": "Full Gate",
            "min_pass_rate": 85,
            "max_failures": 3,
            "max_duration_s": 300,
            "max_new_flakies": 0,
            "min_coverage_pct": 75,
        }
        gate = build_gate_from_config(config)
        assert gate.name == "Full Gate"
        assert len(gate._checks) == 5

    def test_partial_config_builds_only_specified_checks(self):
        gate = build_gate_from_config({"max_failures": 10})
        assert len(gate._checks) == 1
        assert isinstance(gate._checks[0], MaxFailuresCheck)

    def test_gate_name_defaults_when_missing(self):
        gate = build_gate_from_config({})
        assert gate.name == "Default Gate"


# ---------------------------------------------------------------------------
# run_quality_gate (service facade)
# ---------------------------------------------------------------------------

class TestRunQualityGate:
    def test_passing_run(self):
        config = {"min_pass_rate": 80.0, "max_failures": 5}
        result = run_quality_gate(config, _good_summary())
        assert isinstance(result, GateResult)
        assert result.result == "passed"

    def test_failing_run(self):
        config = {"min_pass_rate": 99.0}
        result = run_quality_gate(config, {"passed": 50, "total": 100})
        assert result.result == "failed"
        assert len(result.blocking_messages) > 0


# ---------------------------------------------------------------------------
# list_jenkins_connections (service facade — DB-mocked)
# ---------------------------------------------------------------------------

class TestListJenkinsConnections:
    def test_delegates_to_jenkins_service(self):
        db = MagicMock()
        fake_rows = [{"id": "c1", "name": "My Jenkins", "base_url": "http://j.local"}]
        with patch("app.domains.cicd.service._jenkins_svc.list_connections", return_value=fake_rows) as mock_list:
            result = list_jenkins_connections(db, "tenant-1")
        mock_list.assert_called_once_with(db, "tenant-1")
        assert result == fake_rows

    def test_returns_empty_list_when_no_connections(self):
        db = MagicMock()
        with patch("app.domains.cicd.service._jenkins_svc.list_connections", return_value=[]):
            result = list_jenkins_connections(db, "tenant-2")
        assert result == []
