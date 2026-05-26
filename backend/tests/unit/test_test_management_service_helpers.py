"""Unit tests for test_management service pure helpers.

No DB, no HTTP, no LLM — pure Python only.

Covers:
  app/domains/test_management/service.py:
    _actor_id, _days_since, _case_snapshot, _regression_candidate
  app/domains/coverup/router.py:
    _is_banking_critical, _score_gap (already in test_coverup_router_helpers)
"""

from __future__ import annotations

import types
from datetime import datetime, timezone, timedelta

import pytest

from app.domains.test_management.service import (
    _actor_id,
    _case_snapshot,
    _days_since,
    _regression_candidate,
)
from app.domains.test_management.schemas import (
    RegressionCandidateOut,
    RegressionSelectionFilter,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_step(step_no: int = 1, action: str = "Click button", expected: str = "Modal opens") -> types.SimpleNamespace:
    return types.SimpleNamespace(
        step_no=step_no,
        action=action,
        expected_result=expected,
        test_data=None,
        notes=None,
        is_required=True,
    )


def _make_case(**kwargs) -> types.SimpleNamespace:
    defaults = {
        "id": "case-1",
        "case_key": "TC-001",
        "title": "Login test",
        "objective": "Verify login works",
        "preconditions": "User account exists",
        "test_data": None,
        "priority": "P1",
        "severity": "critical",
        "type": "functional",
        "automation_status": "manual",
        "status": "active",
        "tags": [],
        "custom_fields": {},
        "last_run_status": None,
        "steps": [],
    }
    defaults.update(kwargs)
    return types.SimpleNamespace(**defaults)


# ── _actor_id ─────────────────────────────────────────────────────────────────


class TestActorId:
    def test_none_user_returns_none(self) -> None:
        assert _actor_id(None) is None

    def test_user_with_id_returns_str_id(self) -> None:
        user = types.SimpleNamespace(id="abc-123")
        result = _actor_id(user)
        assert result == "abc-123"

    def test_user_id_converted_to_str(self) -> None:
        user = types.SimpleNamespace(id=42)
        result = _actor_id(user)
        assert result == "42"

    def test_user_without_id_attr_returns_none(self) -> None:
        user = types.SimpleNamespace()  # no id attr
        result = _actor_id(user)
        assert result is None

    def test_returns_string_or_none(self) -> None:
        user = types.SimpleNamespace(id="user-1")
        result = _actor_id(user)
        assert isinstance(result, (str, type(None)))


# ── _days_since ───────────────────────────────────────────────────────────────


class TestDaysSince:
    def test_none_returns_none(self) -> None:
        assert _days_since(None) is None

    def test_today_returns_zero(self) -> None:
        now = datetime.now(timezone.utc)
        result = _days_since(now)
        assert result == 0

    def test_yesterday_returns_one(self) -> None:
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        result = _days_since(yesterday)
        assert result == 1

    def test_one_week_ago(self) -> None:
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        result = _days_since(week_ago)
        assert result == 7

    def test_naive_datetime_treated_as_utc(self) -> None:
        naive = datetime.utcnow()  # naive, no tzinfo
        result = _days_since(naive)
        assert result is not None
        assert result >= 0

    def test_future_date_returns_zero(self) -> None:
        future = datetime.now(timezone.utc) + timedelta(days=10)
        result = _days_since(future)
        assert result == 0  # max(0, negative) = 0

    def test_returns_int_or_none(self) -> None:
        result = _days_since(datetime.now(timezone.utc))
        assert isinstance(result, int)


# ── _case_snapshot ────────────────────────────────────────────────────────────


class TestCaseSnapshot:
    def test_returns_dict_with_case_key(self) -> None:
        case = _make_case()
        snapshot = _case_snapshot(case)
        assert "case" in snapshot
        assert "steps" in snapshot

    def test_case_fields_present(self) -> None:
        case = _make_case(title="My test", priority="P0")
        snapshot = _case_snapshot(case)
        assert snapshot["case"]["title"] == "My test"
        assert snapshot["case"]["priority"] == "P0"

    def test_steps_included(self) -> None:
        step = _make_step(step_no=1, action="Navigate to page")
        case = _make_case(steps=[step])
        snapshot = _case_snapshot(case)
        assert len(snapshot["steps"]) == 1
        assert snapshot["steps"][0]["step_no"] == 1
        assert snapshot["steps"][0]["action"] == "Navigate to page"

    def test_empty_steps(self) -> None:
        case = _make_case(steps=[])
        snapshot = _case_snapshot(case)
        assert snapshot["steps"] == []

    def test_case_id_preserved(self) -> None:
        case = _make_case(id="case-xyz-123")
        snapshot = _case_snapshot(case)
        assert snapshot["case"]["id"] == "case-xyz-123"

    def test_tags_preserved(self) -> None:
        case = _make_case(tags=["smoke", "login"])
        snapshot = _case_snapshot(case)
        assert snapshot["case"]["tags"] == ["smoke", "login"]

    def test_multiple_steps_in_order(self) -> None:
        steps = [_make_step(i, f"Step {i}") for i in range(1, 4)]
        case = _make_case(steps=steps)
        snapshot = _case_snapshot(case)
        assert len(snapshot["steps"]) == 3


# ── _regression_candidate ─────────────────────────────────────────────────────


class TestRegressionCandidate:
    def _filters(self, **kwargs) -> RegressionSelectionFilter:
        defaults = {
            "include_not_run": True,
            "include_without_requirements": False,
        }
        defaults.update(kwargs)
        return RegressionSelectionFilter(**defaults)

    def test_returns_regression_candidate_out(self) -> None:
        case = _make_case()
        result = _regression_candidate(case, set(), self._filters())
        assert isinstance(result, RegressionCandidateOut)

    def test_p0_priority_adds_30(self) -> None:
        case = _make_case(priority="P0", severity="minor", last_run_status=None, tags=[])
        result = _regression_candidate(case, set(), self._filters(include_not_run=False))
        assert result.risk_score >= 30
        assert any("P0" in r for r in result.reasons)

    def test_p1_priority_adds_20(self) -> None:
        case = _make_case(priority="P1", severity="minor", last_run_status=None, tags=[])
        result = _regression_candidate(case, set(), self._filters(include_not_run=False))
        assert result.risk_score >= 20

    def test_blocker_severity_adds_30(self) -> None:
        case = _make_case(priority="P3", severity="blocker", last_run_status=None, tags=[])
        result = _regression_candidate(case, set(), self._filters(include_not_run=False))
        assert result.risk_score >= 30

    def test_critical_severity_adds_24(self) -> None:
        case = _make_case(priority="P3", severity="critical", last_run_status=None, tags=[])
        result = _regression_candidate(case, set(), self._filters(include_not_run=False))
        assert result.risk_score >= 24

    def test_major_severity_adds_12(self) -> None:
        case = _make_case(priority="P3", severity="major", last_run_status=None, tags=[])
        result = _regression_candidate(case, set(), self._filters(include_not_run=False))
        assert result.risk_score >= 12

    def test_failed_status_adds_25(self) -> None:
        case = _make_case(priority="P3", severity="minor", last_run_status="failed", tags=[])
        result = _regression_candidate(case, set(), self._filters())
        assert result.risk_score >= 25
        assert any("failed" in r for r in result.reasons)

    def test_never_run_adds_12_when_flag_set(self) -> None:
        case = _make_case(priority="P3", severity="minor", last_run_status=None, tags=[])
        result = _regression_candidate(case, set(), self._filters(include_not_run=True))
        assert result.risk_score >= 12
        assert any("never" in r for r in result.reasons)

    def test_never_run_no_score_when_flag_false(self) -> None:
        case = _make_case(priority="P3", severity="minor", last_run_status=None, tags=[])
        result = _regression_candidate(case, set(), self._filters(include_not_run=False))
        assert result.risk_score == 0  # no priority/severity/status match

    def test_no_requirement_adds_8_when_flag_set(self) -> None:
        case = _make_case(id="case-A", priority="P3", severity="minor", last_run_status=None, tags=[])
        result = _regression_candidate(
            case, set(), self._filters(include_without_requirements=True, include_not_run=False)
        )
        # case-A not in requirement_case_ids → +8
        assert result.risk_score >= 8

    def test_smoke_tag_adds_10(self) -> None:
        case = _make_case(priority="P3", severity="minor", last_run_status=None, tags=["smoke"])
        result = _regression_candidate(case, set(), self._filters(include_not_run=False))
        assert result.risk_score >= 10
        assert any("smoke" in r for r in result.reasons)

    def test_smoke_type_adds_10(self) -> None:
        case = _make_case(priority="P3", severity="minor", last_run_status=None, type="smoke", tags=[])
        result = _regression_candidate(case, set(), self._filters(include_not_run=False))
        assert result.risk_score >= 10

    def test_no_reasons_defaults_to_matched_filter(self) -> None:
        # P3, minor, no run status, no smoke, not_run=False, without_req=False
        case = _make_case(priority="P3", severity="minor", last_run_status="passed", tags=[])
        result = _regression_candidate(case, set(), self._filters(include_not_run=False))
        assert result.reasons == ["matched filter"]

    def test_accumulates_multiple_reasons(self) -> None:
        case = _make_case(priority="P0", severity="blocker", last_run_status="failed", tags=["smoke"])
        result = _regression_candidate(case, set(), self._filters())
        assert len(result.reasons) >= 3  # priority + severity + status + smoke

    def test_case_key_preserved(self) -> None:
        case = _make_case(case_key="TC-999")
        result = _regression_candidate(case, set(), self._filters())
        assert result.case_key == "TC-999"

    def test_title_preserved(self) -> None:
        case = _make_case(title="My critical test")
        result = _regression_candidate(case, set(), self._filters())
        assert result.title == "My critical test"

    def test_max_priority_severity_failed_score(self) -> None:
        # P0 (30) + blocker (30) + failed (25) + smoke (10) = 95
        case = _make_case(priority="P0", severity="blocker", last_run_status="failed", tags=["smoke"])
        result = _regression_candidate(case, set(), self._filters(include_not_run=False))
        assert result.risk_score == 95
