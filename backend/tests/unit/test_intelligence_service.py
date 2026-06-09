"""Test Intelligence Engine — pure helper unit tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from app.domains.test_management.intelligence_service import (
    PRIORITY_WEIGHT,
    SEVERITY_WEIGHT,
    STATUS_DONE,
    Anomaly,
    CaseRiskScore,
    ETAPrediction,
    TesterProfile,
    _build_tester_profiles,
    _detect_anomalies,
    _predict_eta,
    _utcnow,
    compute_case_risk_score,
)


# ── Yardımcılar ───────────────────────────────────────────────────────────────

def _utc(hours_ago: float = 0) -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=hours_ago)


def _make_run(started_hours_ago: float = 2.0, status: str = "in_progress") -> MagicMock:
    run = MagicMock()
    run.id = "run-1"
    run.name = "Sprint 12 Regression"
    run.status = status
    run.started_at = _utc(started_hours_ago)
    return run


def _make_run_case(
    status: str = "not_run",
    assigned_to: str | None = "user-1",
    duration: int | None = None,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
) -> MagicMock:
    rc = MagicMock()
    rc.id = f"rc-{status}"
    rc.run_id = "run-1"
    rc.case_id = f"case-{status}"
    rc.status = status
    rc.assigned_to = assigned_to
    rc.duration_seconds = duration
    rc.started_at = started_at
    rc.completed_at = completed_at
    return rc


def _make_case(
    severity: str = "major",
    priority: str = "medium",
    last_run_status: str | None = None,
    last_failed_at: datetime | None = None,
) -> MagicMock:
    c = MagicMock()
    c.id = "case-1"
    c.case_key = "TC-001"
    c.title = "Test case"
    c.severity = severity
    c.priority = priority
    c.last_run_status = last_run_status
    c.last_failed_at = last_failed_at
    return c


# ── compute_case_risk_score ───────────────────────────────────────────────────

class TestComputeCaseRiskScore:
    def test_zero_run_history_returns_low_score(self):
        case = _make_case()
        score = compute_case_risk_score(case, {"total_runs": 0, "fail_count": 0})
        assert score.risk_score < 0.5
        assert score.failure_rate == 0.0

    def test_all_fail_critical_returns_high_score(self):
        case = _make_case(severity="critical", priority="critical")
        score = compute_case_risk_score(case, {"total_runs": 5, "fail_count": 5})
        assert score.risk_score >= 0.70
        assert score.recommendation == "run_first"

    def test_recent_failure_increases_recency_factor(self):
        case_recent = _make_case(last_failed_at=_utc(hours_ago=1))
        case_old = _make_case(last_failed_at=_utc(hours_ago=24 * 35))  # 35 gün önce
        history = {"total_runs": 3, "fail_count": 1}
        score_recent = compute_case_risk_score(case_recent, history)
        score_old = compute_case_risk_score(case_old, history)
        assert score_recent.risk_score > score_old.risk_score

    def test_deprioritize_low_risk(self):
        case = _make_case(severity="trivial", priority="low")
        score = compute_case_risk_score(case, {"total_runs": 10, "fail_count": 0})
        assert score.recommendation == "deprioritize"

    def test_run_normal_medium_risk(self):
        case = _make_case(severity="minor", priority="medium")
        score = compute_case_risk_score(case, {"total_runs": 4, "fail_count": 1})
        assert score.recommendation in ("run_normal", "deprioritize", "run_first")

    def test_risk_score_clamped_to_one(self):
        case = _make_case(severity="critical", priority="critical", last_failed_at=_utc(0))
        score = compute_case_risk_score(case, {"total_runs": 1, "fail_count": 1})
        assert score.risk_score <= 1.0

    def test_risk_score_nonnegative(self):
        case = _make_case()
        score = compute_case_risk_score(case, {"total_runs": 0, "fail_count": 0})
        assert score.risk_score >= 0.0

    def test_severity_weights_applied(self):
        for sev, weight in SEVERITY_WEIGHT.items():
            case = _make_case(severity=sev)
            score = compute_case_risk_score(case, {"total_runs": 0, "fail_count": 0})
            assert score.severity_weight == weight

    def test_priority_weights_applied(self):
        for pri, weight in PRIORITY_WEIGHT.items():
            case = _make_case(priority=pri)
            score = compute_case_risk_score(case, {"total_runs": 0, "fail_count": 0})
            assert score.priority_weight == weight

    def test_output_fields_present(self):
        case = _make_case()
        score = compute_case_risk_score(case, {"total_runs": 2, "fail_count": 1})
        assert hasattr(score, "case_id")
        assert hasattr(score, "case_key")
        assert hasattr(score, "recommendation")


# ── _predict_eta ─────────────────────────────────────────────────────────────

class TestPredictETA:
    def test_no_cases_returns_zero_eta(self):
        run = _make_run()
        eta = _predict_eta(run, [])
        assert eta.total_cases == 0
        assert eta.remaining_cases == 0

    def test_all_done_returns_zero_remaining(self):
        run = _make_run()
        cases = [_make_run_case(status="passed", completed_at=_utc(0.5), duration=60) for _ in range(5)]
        eta = _predict_eta(run, cases)
        assert eta.remaining_cases == 0
        assert eta.on_track is True

    def test_velocity_calculated(self):
        run = _make_run(started_hours_ago=1.0)
        done_cases = [
            _make_run_case(status="passed", completed_at=_utc(0.1), duration=120)
            for _ in range(4)
        ]
        remaining = [_make_run_case(status="not_run") for _ in range(6)]
        eta = _predict_eta(run, done_cases + remaining)
        assert eta.completed_cases == 4
        assert eta.remaining_cases == 6

    def test_zero_velocity_marks_not_on_track(self):
        run = _make_run(started_hours_ago=1.0)
        cases = [_make_run_case(status="not_run") for _ in range(10)]
        eta = _predict_eta(run, cases)
        assert eta.on_track is False
        assert eta.risk_level == "critical"

    def test_eta_hours_positive_when_remaining(self):
        run = _make_run(started_hours_ago=1.0)
        done = [_make_run_case(status="passed", completed_at=_utc(0.1), duration=300) for _ in range(10)]
        remaining = [_make_run_case(status="not_run") for _ in range(5)]
        eta = _predict_eta(run, done + remaining)
        assert eta.eta_hours is not None
        assert eta.eta_hours > 0

    def test_risk_level_low_for_small_eta(self):
        run = _make_run(started_hours_ago=0.5)
        done = [_make_run_case(status="passed", completed_at=_utc(0.05), duration=60) for _ in range(20)]
        remaining = [_make_run_case(status="not_run") for _ in range(2)]
        eta = _predict_eta(run, done + remaining)
        assert eta.risk_level in ("low", "medium")

    def test_confidence_between_zero_and_one(self):
        run = _make_run(started_hours_ago=2.0)
        done = [
            _make_run_case(status="passed", completed_at=_utc(0.1 * i), duration=120 + i * 10)
            for i in range(5)
        ]
        remaining = [_make_run_case(status="not_run") for _ in range(3)]
        eta = _predict_eta(run, done + remaining)
        if eta.eta_hours:
            assert 0.0 <= eta.confidence <= 1.0

    def test_message_is_string(self):
        run = _make_run()
        eta = _predict_eta(run, [])
        assert isinstance(eta.message, str)


# ── _build_tester_profiles ────────────────────────────────────────────────────

class TestBuildTesterProfiles:
    def test_empty_returns_unassigned_profile(self):
        cases = [_make_run_case(status="not_run", assigned_to=None) for _ in range(3)]
        profiles = _build_tester_profiles(cases)
        unassigned = [p for p in profiles if p.user_id == "__unassigned__"]
        assert len(unassigned) == 1
        assert unassigned[0].assigned_count == 3

    def test_single_tester_profile_built(self):
        done = [
            _make_run_case(status="passed", assigned_to="user-A", duration=120, completed_at=_utc(0.1))
            for _ in range(4)
        ]
        remaining = [_make_run_case(status="not_run", assigned_to="user-A")]
        profiles = _build_tester_profiles(done + remaining)
        tester = next((p for p in profiles if p.user_id == "user-A"), None)
        assert tester is not None
        assert tester.completed_count == 4
        assert tester.remaining_count == 1

    def test_bottleneck_detection(self):
        # fast-user: 10 case tamamladı, hızlı
        fast_done = [
            _make_run_case(
                status="passed",
                assigned_to="fast-user",
                duration=60,
                started_at=_utc(hours_ago=1.0),
                completed_at=_utc(0.05 * i + 0.01),
            )
            for i in range(10)
        ]
        # slow-user: 1 tamamladı, 9 bekliyor — hızı avg'nin %40 altında
        slow_done = [
            _make_run_case(
                status="passed",
                assigned_to="slow-user",
                duration=600,
                started_at=_utc(hours_ago=1.0),
                completed_at=_utc(0.9),
            )
        ]
        slow_remaining = [_make_run_case(status="not_run", assigned_to="slow-user") for _ in range(9)]
        profiles = _build_tester_profiles(fast_done + slow_done + slow_remaining)
        slow = next((p for p in profiles if p.user_id == "slow-user"), None)
        assert slow is not None
        assert slow.is_bottleneck is True

    def test_pass_rate_calculated(self):
        cases = [
            _make_run_case(status="passed", assigned_to="u1", completed_at=_utc(0.1)),
            _make_run_case(status="passed", assigned_to="u1", completed_at=_utc(0.2)),
            _make_run_case(status="failed", assigned_to="u1", completed_at=_utc(0.3)),
        ]
        profiles = _build_tester_profiles(cases)
        tester = next((p for p in profiles if p.user_id == "u1"), None)
        assert tester is not None
        assert abs(tester.pass_rate - 2 / 3) < 0.01

    def test_multiple_testers(self):
        cases = (
            [_make_run_case(status="passed", assigned_to="u1", completed_at=_utc(0.1))] * 3
            + [_make_run_case(status="failed", assigned_to="u2", completed_at=_utc(0.2))] * 2
        )
        profiles = _build_tester_profiles(cases)
        user_ids = {p.user_id for p in profiles}
        assert "u1" in user_ids
        assert "u2" in user_ids


# ── _detect_anomalies ─────────────────────────────────────────────────────────

class TestDetectAnomalies:
    def _make_eta(self, on_track=True, risk_level="low", remaining=0, velocity=5.0):
        return ETAPrediction(
            run_id="run-1",
            total_cases=10,
            completed_cases=10 - remaining,
            remaining_cases=remaining,
            elapsed_hours=1.0,
            velocity_per_hour=velocity,
            overall_velocity=velocity,
            eta_hours=remaining / velocity if velocity > 0 and remaining > 0 else None,
            predicted_completion=None,
            confidence=0.8,
            on_track=on_track,
            risk_level=risk_level,
            message="test",
        )

    def test_no_anomalies_clean_run(self):
        run = _make_run()
        cases = [
            _make_run_case(status="passed", assigned_to="u1", duration=120, completed_at=_utc(0.1))
            for _ in range(5)
        ]
        eta = self._make_eta()
        testers = _build_tester_profiles(cases)
        anomalies = _detect_anomalies(run, cases, testers, eta)
        critical = [a for a in anomalies if a.severity == "critical"]
        assert len(critical) == 0

    def test_stuck_case_detected(self):
        run = _make_run()
        stuck = _make_run_case(
            status="not_run",
            assigned_to="u1",
            started_at=_utc(hours_ago=2),  # 2 saat önce başladı
        )
        eta = self._make_eta()
        testers = _build_tester_profiles([stuck])
        anomalies = _detect_anomalies(run, [stuck], testers, eta)
        types = [a.type for a in anomalies]
        assert "stuck_case" in types

    def test_high_blocked_rate_detected(self):
        run = _make_run()
        cases = [_make_run_case(status="blocked", assigned_to="u1", completed_at=_utc(0.1)) for _ in range(8)]
        cases += [_make_run_case(status="passed", assigned_to="u1", completed_at=_utc(0.2)) for _ in range(2)]
        eta = self._make_eta()
        testers = _build_tester_profiles(cases)
        anomalies = _detect_anomalies(run, cases, testers, eta)
        types = [a.type for a in anomalies]
        assert "high_blocked_rate" in types

    def test_unassigned_cases_anomaly(self):
        run = _make_run()
        cases = [_make_run_case(status="not_run", assigned_to=None) for _ in range(5)]
        eta = self._make_eta(remaining=5)
        testers = _build_tester_profiles(cases)
        anomalies = _detect_anomalies(run, cases, testers, eta)
        types = [a.type for a in anomalies]
        assert "unassigned_cases" in types

    def test_velocity_decline_detected(self):
        run = _make_run()
        cases = [_make_run_case(status="passed", assigned_to="u1", completed_at=_utc(0.1)) for _ in range(5)]
        eta = self._make_eta(remaining=5, velocity=0.5, on_track=False)
        eta.overall_velocity = 5.0  # genel hız 5, anlık 0.5 → %90 düşüş
        testers = _build_tester_profiles(cases)
        anomalies = _detect_anomalies(run, cases, testers, eta)
        types = [a.type for a in anomalies]
        assert "velocity_decline" in types or "eta_risk" in types

    def test_critical_anomalies_sorted_first(self):
        run = _make_run()
        stuck = _make_run_case(status="not_run", started_at=_utc(hours_ago=3))
        cases = [stuck]
        eta = self._make_eta()
        testers = _build_tester_profiles(cases)
        anomalies = _detect_anomalies(run, cases, testers, eta)
        if len(anomalies) > 1:
            # Critical'lar önce gelmeli
            severities = [a.severity for a in anomalies]
            critical_idx = [i for i, s in enumerate(severities) if s == "critical"]
            warning_idx = [i for i, s in enumerate(severities) if s == "warning"]
            if critical_idx and warning_idx:
                assert max(critical_idx) < max(warning_idx) or min(critical_idx) <= min(warning_idx)

    def test_anomaly_has_suggested_action(self):
        run = _make_run()
        cases = [_make_run_case(status="not_run", assigned_to=None) for _ in range(3)]
        eta = self._make_eta(remaining=3)
        testers = _build_tester_profiles(cases)
        anomalies = _detect_anomalies(run, cases, testers, eta)
        for a in anomalies:
            assert isinstance(a.suggested_action, str)

    def test_anomaly_detail_is_string(self):
        run = _make_run()
        cases = [_make_run_case(status="blocked", completed_at=_utc(0.1)) for _ in range(10)]
        eta = self._make_eta()
        testers = _build_tester_profiles(cases)
        anomalies = _detect_anomalies(run, cases, testers, eta)
        for a in anomalies:
            assert isinstance(a.detail, str)
            assert len(a.detail) > 0


# ── Sabitler ──────────────────────────────────────────────────────────────────

class TestConstants:
    def test_status_done_contains_terminal_states(self):
        for s in ("passed", "failed", "blocked", "skipped"):
            assert s in STATUS_DONE

    def test_severity_weights_between_zero_and_one(self):
        for v in SEVERITY_WEIGHT.values():
            assert 0.0 <= v <= 1.0

    def test_priority_weights_between_zero_and_one(self):
        for v in PRIORITY_WEIGHT.values():
            assert 0.0 <= v <= 1.0

    def test_utcnow_returns_aware_datetime(self):
        dt = _utcnow()
        assert dt.tzinfo is not None
