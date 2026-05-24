"""Unit tests for CICD Quality Gate domain.

Tests app/domains/cicd/quality_gate.py — zero external dependencies,
pure Python logic.  Covers: CheckResult, all check classes, QualityGate,
build_gate_from_config factory.
"""

from __future__ import annotations

import pytest
from app.domains.cicd.quality_gate import (
    CheckResult,
    CoverageCheck,
    DurationCheck,
    GateResult,
    MaxFailuresCheck,
    NoNewFlakiesCheck,
    PassRateCheck,
    QualityGate,
    build_gate_from_config,
)


# ── CheckResult ───────────────────────────────────────────────────────────────


class TestCheckResult:
    def test_to_dict_keys(self) -> None:
        r = CheckResult(name="test", passed=True, value="90%", threshold="80%")
        d = r.to_dict()
        assert set(d.keys()) == {"name", "passed", "value", "threshold", "message"}

    def test_to_dict_values(self) -> None:
        r = CheckResult(name="pass_rate", passed=False, value="70%", threshold="80%", message="too low")
        d = r.to_dict()
        assert d["passed"] is False
        assert d["message"] == "too low"

    def test_default_message_empty(self) -> None:
        r = CheckResult(name="x", passed=True, value=1, threshold=2)
        assert r.message == ""


# ── PassRateCheck ─────────────────────────────────────────────────────────────


class TestPassRateCheck:
    def test_passes_when_above_threshold(self) -> None:
        check = PassRateCheck(min_pct=80.0)
        result = check.run({"total": 100, "passed": 90})
        assert result.passed is True
        assert result.message == ""

    def test_passes_when_exactly_at_threshold(self) -> None:
        check = PassRateCheck(min_pct=80.0)
        result = check.run({"total": 100, "passed": 80})
        assert result.passed is True

    def test_fails_when_below_threshold(self) -> None:
        check = PassRateCheck(min_pct=80.0)
        result = check.run({"total": 100, "passed": 70})
        assert result.passed is False
        assert "70.0%" in result.message

    def test_zero_total_passes_gracefully(self) -> None:
        check = PassRateCheck(min_pct=80.0)
        result = check.run({"total": 0, "passed": 0})
        # 0/0 → 0.0% — below threshold unless min_pct=0
        assert result.value == "0.0%"

    def test_custom_threshold(self) -> None:
        check = PassRateCheck(min_pct=95.0)
        assert check.run({"total": 100, "passed": 94}).passed is False
        assert check.run({"total": 100, "passed": 95}).passed is True

    def test_name(self) -> None:
        assert PassRateCheck.name == "Geçme Oranı"


# ── MaxFailuresCheck ──────────────────────────────────────────────────────────


class TestMaxFailuresCheck:
    def test_passes_when_at_limit(self) -> None:
        check = MaxFailuresCheck(max_count=5)
        assert check.run({"failed": 5}).passed is True

    def test_fails_when_over_limit(self) -> None:
        check = MaxFailuresCheck(max_count=5)
        result = check.run({"failed": 6})
        assert result.passed is False
        assert "6" in result.message

    def test_passes_when_zero_failures(self) -> None:
        check = MaxFailuresCheck(max_count=5)
        assert check.run({"failed": 0}).passed is True

    def test_default_max_is_5(self) -> None:
        check = MaxFailuresCheck()
        assert check.max_count == 5

    def test_name(self) -> None:
        assert "Başarısız" in MaxFailuresCheck.name


# ── DurationCheck ─────────────────────────────────────────────────────────────


class TestDurationCheck:
    def test_passes_when_within_limit(self) -> None:
        check = DurationCheck(max_seconds=600.0)
        assert check.run({"duration_s": 599.9}).passed is True

    def test_passes_when_exactly_at_limit(self) -> None:
        check = DurationCheck(max_seconds=600.0)
        assert check.run({"duration_s": 600.0}).passed is True

    def test_fails_when_over_limit(self) -> None:
        check = DurationCheck(max_seconds=600.0)
        result = check.run({"duration_s": 601.0})
        assert result.passed is False
        assert "601s" in result.message

    def test_zero_duration_passes(self) -> None:
        check = DurationCheck(max_seconds=600.0)
        assert check.run({"duration_s": 0.0}).passed is True

    def test_default_max_is_600(self) -> None:
        assert DurationCheck().max_seconds == 600.0


# ── NoNewFlakiesCheck ─────────────────────────────────────────────────────────


class TestNoNewFlakiesCheck:
    def test_passes_when_no_new_flakies(self) -> None:
        check = NoNewFlakiesCheck(max_new=0)
        assert check.run({"new_flaky_count": 0}).passed is True

    def test_fails_when_new_flakies_present(self) -> None:
        check = NoNewFlakiesCheck(max_new=0)
        result = check.run({"new_flaky_count": 1})
        assert result.passed is False
        assert "1" in result.message

    def test_allows_some_new_flakies(self) -> None:
        check = NoNewFlakiesCheck(max_new=2)
        assert check.run({"new_flaky_count": 2}).passed is True
        assert check.run({"new_flaky_count": 3}).passed is False

    def test_missing_key_defaults_to_zero(self) -> None:
        check = NoNewFlakiesCheck(max_new=0)
        assert check.run({}).passed is True  # 0 <= 0


# ── CoverageCheck ─────────────────────────────────────────────────────────────


class TestCoverageCheck:
    def test_passes_when_above_threshold(self) -> None:
        check = CoverageCheck(min_pct=70.0)
        assert check.run({"coverage_pct": 80.0}).passed is True

    def test_fails_when_below_threshold(self) -> None:
        check = CoverageCheck(min_pct=70.0)
        result = check.run({"coverage_pct": 60.0})
        assert result.passed is False

    def test_passes_when_coverage_absent(self) -> None:
        """When coverage_pct key missing, check is skipped (passes)."""
        check = CoverageCheck(min_pct=70.0)
        result = check.run({})
        assert result.passed is True
        assert "N/A" in result.value

    def test_coverage_none_is_skipped(self) -> None:
        check = CoverageCheck(min_pct=70.0)
        result = check.run({"coverage_pct": None})
        assert result.passed is True

    def test_string_coverage_is_cast(self) -> None:
        check = CoverageCheck(min_pct=70.0)
        assert check.run({"coverage_pct": "85.5"}).passed is True
        assert check.run({"coverage_pct": "65.0"}).passed is False


# ── GateResult ────────────────────────────────────────────────────────────────


class TestGateResult:
    def test_to_dict_structure(self) -> None:
        gate = GateResult(gate_name="CI Gate", result="passed")
        d = gate.to_dict()
        assert d["gate_name"] == "CI Gate"
        assert d["result"] == "passed"
        assert d["passed"] is True
        assert d["checks"] == []
        assert d["blocking_messages"] == []

    def test_failed_gate(self) -> None:
        gate = GateResult(
            gate_name="CI Gate",
            result="failed",
            blocking_messages=["too many failures"],
        )
        d = gate.to_dict()
        assert d["passed"] is False
        assert "too many failures" in d["blocking_messages"]


# ── QualityGate ───────────────────────────────────────────────────────────────


class TestQualityGate:
    def test_empty_gate_always_passes(self) -> None:
        gate = QualityGate("Empty Gate")
        result = gate.evaluate({"total": 100, "passed": 50})
        assert result.result == "passed"

    def test_all_checks_pass(self) -> None:
        gate = QualityGate("All Pass")
        gate.add_check(PassRateCheck(min_pct=80))
        gate.add_check(MaxFailuresCheck(max_count=5))
        result = gate.evaluate({"total": 100, "passed": 90, "failed": 2})
        assert result.result == "passed"
        assert len(result.checks) == 2

    def test_one_failing_check_fails_gate(self) -> None:
        gate = QualityGate("Strict Gate")
        gate.add_check(PassRateCheck(min_pct=95))  # will fail
        gate.add_check(MaxFailuresCheck(max_count=100))  # will pass
        result = gate.evaluate({"total": 100, "passed": 90, "failed": 10})
        assert result.result == "failed"
        assert len(result.blocking_messages) >= 1

    def test_all_failing_checks_reported(self) -> None:
        gate = QualityGate("Fail All")
        gate.add_check(PassRateCheck(min_pct=99))
        gate.add_check(MaxFailuresCheck(max_count=0))
        gate.add_check(DurationCheck(max_seconds=1))
        result = gate.evaluate({"total": 100, "passed": 80, "failed": 5, "duration_s": 200})
        assert result.result == "failed"
        assert len(result.checks) == 3
        assert all(not c.passed for c in result.checks)
        assert len(result.blocking_messages) == 3

    def test_add_check_returns_self(self) -> None:
        gate = QualityGate("Chain")
        result = gate.add_check(PassRateCheck())
        assert result is gate

    def test_chained_add_check(self) -> None:
        gate = (
            QualityGate("Fluent")
            .add_check(PassRateCheck(min_pct=80))
            .add_check(MaxFailuresCheck(max_count=5))
            .add_check(DurationCheck(max_seconds=300))
        )
        assert len(gate._checks) == 3

    def test_gate_name_in_result(self) -> None:
        gate = QualityGate("Production Deploy Gate")
        result = gate.evaluate({})
        assert result.gate_name == "Production Deploy Gate"

    def test_blocking_messages_only_from_failed_checks(self) -> None:
        gate = (
            QualityGate("Mixed")
            .add_check(PassRateCheck(min_pct=50))  # pass: 90%
            .add_check(MaxFailuresCheck(max_count=1))  # fail: 5 > 1
        )
        result = gate.evaluate({"total": 100, "passed": 90, "failed": 5})
        assert len(result.blocking_messages) == 1
        assert "5" in result.blocking_messages[0]


# ── build_gate_from_config ────────────────────────────────────────────────────


class TestBuildGateFromConfig:
    def test_empty_config_builds_empty_gate(self) -> None:
        gate = build_gate_from_config({})
        assert len(gate._checks) == 0
        assert gate.name == "Default Gate"

    def test_custom_name(self) -> None:
        gate = build_gate_from_config({"name": "Production Gate"})
        assert gate.name == "Production Gate"

    def test_pass_rate_check_added(self) -> None:
        gate = build_gate_from_config({"min_pass_rate": 85})
        assert len(gate._checks) == 1
        assert isinstance(gate._checks[0], PassRateCheck)
        assert gate._checks[0].min_pct == 85.0

    def test_max_failures_check_added(self) -> None:
        gate = build_gate_from_config({"max_failures": 3})
        assert isinstance(gate._checks[0], MaxFailuresCheck)
        assert gate._checks[0].max_count == 3

    def test_duration_check_added(self) -> None:
        gate = build_gate_from_config({"max_duration_s": 300})
        assert isinstance(gate._checks[0], DurationCheck)
        assert gate._checks[0].max_seconds == 300.0

    def test_flaky_check_added(self) -> None:
        gate = build_gate_from_config({"max_new_flakies": 0})
        assert isinstance(gate._checks[0], NoNewFlakiesCheck)

    def test_coverage_check_added(self) -> None:
        gate = build_gate_from_config({"min_coverage_pct": 75})
        assert isinstance(gate._checks[0], CoverageCheck)
        assert gate._checks[0].min_pct == 75.0

    def test_full_config_builds_all_checks(self) -> None:
        config = {
            "name": "Full Gate",
            "min_pass_rate": 85,
            "max_failures": 3,
            "max_duration_s": 300,
            "max_new_flakies": 0,
            "min_coverage_pct": 75,
        }
        gate = build_gate_from_config(config)
        assert len(gate._checks) == 5
        check_types = {type(c) for c in gate._checks}
        assert PassRateCheck in check_types
        assert MaxFailuresCheck in check_types
        assert DurationCheck in check_types
        assert NoNewFlakiesCheck in check_types
        assert CoverageCheck in check_types

    def test_evaluation_through_config_gate(self) -> None:
        config = {
            "name": "CI Gate",
            "min_pass_rate": 80,
            "max_failures": 5,
            "max_duration_s": 600,
        }
        gate = build_gate_from_config(config)
        passing_run = {"total": 100, "passed": 90, "failed": 3, "duration_s": 120}
        result = gate.evaluate(passing_run)
        assert result.result == "passed"

    def test_evaluation_through_config_gate_fails(self) -> None:
        config = {"min_pass_rate": 90, "max_failures": 2}
        gate = build_gate_from_config(config)
        failing_run = {"total": 100, "passed": 80, "failed": 5}
        result = gate.evaluate(failing_run)
        assert result.result == "failed"
        assert len(result.blocking_messages) == 2
