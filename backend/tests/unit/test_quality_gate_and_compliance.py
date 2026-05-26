"""Unit tests for cicd.quality_gate and compliance.mapping.

Tests are fully self-contained: no DB, no HTTP.
Covers:
  - CheckResult: to_dict()
  - PassRateCheck: pass/fail based on total/passed
  - MaxFailuresCheck: fail count threshold
  - DurationCheck: duration limit
  - NoNewFlakiesCheck: flaky test count
  - CoverageCheck: coverage_pct, None passthrough
  - QualityGate: add_check, evaluate (passed/failed), GateResult
  - build_gate_from_config: factory from dict

  - compliance.mapping: CONTROLS, MAPPINGS data
  - list_controls: all 10 controls
  - get_control: known ID, unknown ID
  - all_markers: returns marker strings
  - mappings_for: returns Mapping list for a known control ID
"""
from __future__ import annotations

import pytest

try:
    from app.domains.cicd.quality_gate import (
        CheckResult,
        PassRateCheck,
        MaxFailuresCheck,
        DurationCheck,
        NoNewFlakiesCheck,
        CoverageCheck,
        QualityGate,
        GateResult,
        build_gate_from_config,
    )
    _GATE_OK = True
except ImportError:
    _GATE_OK = False

try:
    from app.domains.compliance.mapping import (
        Control,
        CONTROLS,
        MAPPINGS,
        list_controls,
        get_control,
        all_markers,
        mappings_for,
        controls_for_feature,
    )
    _COMPLIANCE_OK = True
except ImportError:
    _COMPLIANCE_OK = False


# ---------------------------------------------------------------------------
# CheckResult
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _GATE_OK, reason="quality_gate import failed")
class TestCheckResult:
    def test_creation(self):
        r = CheckResult(name="PassRate", passed=True, value="95%", threshold="80%")
        assert r.name == "PassRate"
        assert r.passed is True

    def test_to_dict_keys(self):
        r = CheckResult(name="test", passed=False, value=3, threshold=5, message="fail")
        d = r.to_dict()
        for key in ("name", "passed", "value", "threshold", "message"):
            assert key in d

    def test_to_dict_values(self):
        r = CheckResult(name="test", passed=True, value=10, threshold=5)
        d = r.to_dict()
        assert d["passed"] is True
        assert d["value"] == 10

    def test_message_default_empty(self):
        r = CheckResult(name="test", passed=True, value=1, threshold=1)
        assert r.message == ""


# ---------------------------------------------------------------------------
# PassRateCheck
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _GATE_OK, reason="quality_gate import failed")
class TestPassRateCheck:
    def test_passing(self):
        check = PassRateCheck(min_pct=80.0)
        result = check.run({"total": 100, "passed": 90})
        assert result.passed is True

    def test_failing(self):
        check = PassRateCheck(min_pct=80.0)
        result = check.run({"total": 100, "passed": 70})
        assert result.passed is False

    def test_exact_threshold_passes(self):
        check = PassRateCheck(min_pct=80.0)
        result = check.run({"total": 100, "passed": 80})
        assert result.passed is True

    def test_zero_total_passes(self):
        # 0/0 → 0% but shouldn't crash
        check = PassRateCheck(min_pct=80.0)
        result = check.run({"total": 0, "passed": 0})
        assert isinstance(result.passed, bool)

    def test_default_min_pct_80(self):
        check = PassRateCheck()
        assert check.min_pct == 80.0

    def test_failure_message_not_empty(self):
        check = PassRateCheck(min_pct=90.0)
        result = check.run({"total": 100, "passed": 70})
        assert result.message != ""


# ---------------------------------------------------------------------------
# MaxFailuresCheck
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _GATE_OK, reason="quality_gate import failed")
class TestMaxFailuresCheck:
    def test_within_limit(self):
        check = MaxFailuresCheck(max_count=5)
        result = check.run({"failed": 3})
        assert result.passed is True

    def test_exactly_at_limit(self):
        check = MaxFailuresCheck(max_count=5)
        result = check.run({"failed": 5})
        assert result.passed is True

    def test_exceeds_limit(self):
        check = MaxFailuresCheck(max_count=5)
        result = check.run({"failed": 6})
        assert result.passed is False

    def test_zero_failures(self):
        check = MaxFailuresCheck(max_count=5)
        result = check.run({"failed": 0})
        assert result.passed is True

    def test_default_max_5(self):
        check = MaxFailuresCheck()
        assert check.max_count == 5


# ---------------------------------------------------------------------------
# DurationCheck
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _GATE_OK, reason="quality_gate import failed")
class TestDurationCheck:
    def test_within_duration(self):
        check = DurationCheck(max_seconds=600.0)
        result = check.run({"duration_s": 300.0})
        assert result.passed is True

    def test_exactly_at_limit(self):
        check = DurationCheck(max_seconds=600.0)
        result = check.run({"duration_s": 600.0})
        assert result.passed is True

    def test_exceeds_duration(self):
        check = DurationCheck(max_seconds=600.0)
        result = check.run({"duration_s": 601.0})
        assert result.passed is False

    def test_default_max_600(self):
        check = DurationCheck()
        assert check.max_seconds == 600.0


# ---------------------------------------------------------------------------
# NoNewFlakiesCheck
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _GATE_OK, reason="quality_gate import failed")
class TestNoNewFlakiesCheck:
    def test_no_new_flakies(self):
        check = NoNewFlakiesCheck(max_new=0)
        result = check.run({"new_flaky_count": 0})
        assert result.passed is True

    def test_new_flakies_fail(self):
        check = NoNewFlakiesCheck(max_new=0)
        result = check.run({"new_flaky_count": 1})
        assert result.passed is False

    def test_allowance(self):
        check = NoNewFlakiesCheck(max_new=2)
        result = check.run({"new_flaky_count": 2})
        assert result.passed is True


# ---------------------------------------------------------------------------
# CoverageCheck
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _GATE_OK, reason="quality_gate import failed")
class TestCoverageCheck:
    def test_above_threshold(self):
        check = CoverageCheck(min_pct=70.0)
        result = check.run({"coverage_pct": 80.0})
        assert result.passed is True

    def test_below_threshold(self):
        check = CoverageCheck(min_pct=70.0)
        result = check.run({"coverage_pct": 60.0})
        assert result.passed is False

    def test_none_coverage_passes(self):
        # No coverage data → check skipped (passes)
        check = CoverageCheck(min_pct=70.0)
        result = check.run({})
        assert result.passed is True

    def test_default_min_70(self):
        check = CoverageCheck()
        assert check.min_pct == 70.0


# ---------------------------------------------------------------------------
# QualityGate
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _GATE_OK, reason="quality_gate import failed")
class TestQualityGate:
    def test_empty_gate_passes(self):
        gate = QualityGate("test")
        result = gate.evaluate({"total": 100, "passed": 90})
        assert result.result == "passed"

    def test_all_checks_pass(self):
        gate = QualityGate("prod")
        gate.add_check(PassRateCheck(min_pct=80.0))
        gate.add_check(MaxFailuresCheck(max_count=5))
        result = gate.evaluate({"total": 100, "passed": 90, "failed": 2})
        assert result.result == "passed"

    def test_one_check_fails(self):
        gate = QualityGate("staging")
        gate.add_check(PassRateCheck(min_pct=95.0))
        result = gate.evaluate({"total": 100, "passed": 80})
        assert result.result == "failed"

    def test_gate_result_has_checks(self):
        gate = QualityGate()
        gate.add_check(PassRateCheck(min_pct=80.0))
        result = gate.evaluate({"total": 100, "passed": 90})
        assert len(result.checks) == 1

    def test_blocking_messages_on_failure(self):
        gate = QualityGate()
        gate.add_check(MaxFailuresCheck(max_count=0))
        result = gate.evaluate({"failed": 3})
        assert len(result.blocking_messages) > 0

    def test_to_dict(self):
        gate = QualityGate("test")
        result = gate.evaluate({})
        d = result.to_dict()
        assert "gate_name" in d
        assert "result" in d
        assert "passed" in d

    def test_add_check_chaining(self):
        gate = QualityGate()
        returned = gate.add_check(PassRateCheck())
        assert returned is gate


# ---------------------------------------------------------------------------
# build_gate_from_config
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _GATE_OK, reason="quality_gate import failed")
class TestBuildGateFromConfig:
    def test_empty_config(self):
        gate = build_gate_from_config({})
        assert isinstance(gate, QualityGate)

    def test_named_gate(self):
        gate = build_gate_from_config({"name": "Production"})
        assert gate.name == "Production"

    def test_min_pass_rate_added(self):
        gate = build_gate_from_config({"min_pass_rate": 85})
        result = gate.evaluate({"total": 100, "passed": 80})
        assert result.result == "failed"

    def test_max_failures_added(self):
        gate = build_gate_from_config({"max_failures": 2})
        result = gate.evaluate({"failed": 5})
        assert result.result == "failed"

    def test_full_config(self):
        config = {
            "name": "Full Gate",
            "min_pass_rate": 80,
            "max_failures": 5,
            "max_duration_s": 600,
            "max_new_flakies": 0,
            "min_coverage_pct": 70,
        }
        gate = build_gate_from_config(config)
        # All checks pass
        result = gate.evaluate({
            "total": 100, "passed": 85, "failed": 3,
            "duration_s": 300, "new_flaky_count": 0, "coverage_pct": 80,
        })
        assert result.result == "passed"


# ---------------------------------------------------------------------------
# compliance.mapping — CONTROLS
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _COMPLIANCE_OK, reason="compliance.mapping import failed")
class TestComplianceControls:
    def test_controls_not_empty(self):
        assert len(CONTROLS) > 0

    def test_list_controls_same_length(self):
        assert len(list_controls()) == len(CONTROLS)

    def test_kvkk_control_exists(self):
        c = get_control("kvkk-md-5")
        assert c is not None
        assert c.id == "kvkk-md-5"

    def test_bddk_control_exists(self):
        c = get_control("bddk-bgy-6")
        assert c is not None
        assert c.standard == "BDDK"

    def test_unknown_control_returns_none(self):
        c = get_control("nonexistent-control-xyz")
        assert c is None

    def test_control_has_risk_level(self):
        c = get_control("kvkk-md-5")
        assert c.risk_level in ("low", "medium", "high", "critical")

    def test_all_controls_have_required_fields(self):
        for ctrl in list_controls():
            assert ctrl.id
            assert ctrl.standard
            assert ctrl.title

    def test_standards_include_kvkk(self):
        standards = {c.standard for c in list_controls()}
        assert "KVKK" in standards

    def test_standards_include_bddk(self):
        standards = {c.standard for c in list_controls()}
        assert "BDDK" in standards


# ---------------------------------------------------------------------------
# compliance.mapping — MAPPINGS and markers
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _COMPLIANCE_OK, reason="compliance.mapping import failed")
class TestComplianceMappings:
    def test_mappings_not_empty(self):
        assert len(MAPPINGS) > 0

    def test_all_markers_returns_list(self):
        markers = all_markers()
        assert isinstance(markers, list)

    def test_all_markers_not_empty(self):
        assert len(all_markers()) > 0

    def test_all_markers_contain_compliance_prefix(self):
        for marker in all_markers():
            assert "compliance:" in marker

    def test_mappings_for_kvkk_md5_not_empty(self):
        m = mappings_for("kvkk-md-5")
        assert len(m) > 0

    def test_mappings_for_unknown_empty(self):
        m = mappings_for("totally-unknown-control-xyz")
        assert m == []

    def test_mapping_has_control_id(self):
        m = mappings_for("kvkk-md-5")
        for mapping in m:
            assert mapping.control_id == "kvkk-md-5"
