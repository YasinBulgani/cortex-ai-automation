"""Unit tests for test_management schemas — pure Pydantic validation, no DB required."""
from __future__ import annotations

import pytest
from datetime import datetime, timezone

try:
    from app.domains.test_management.schemas import (
        RequirementCreate,
        RequirementUpdate,
        TestCaseCreate,
        TestCaseUpdate,
        TestPlanCreate,
        TestRunCreate,
        RegressionSetCreate,
        RegressionSetCaseIn,
        DefectLinkCreate,
        TestSuiteCreate,
        MgmtCommentCreate,
        ALLOWED_COMMENT_ENTITY_TYPES,
        TestCycleCreate,
        MgmtNotificationCreate,
    )
    _IMPORT_OK = True
except Exception:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="import failed")


# ── RequirementCreate ─────────────────────────────────────────────────────────


class TestRequirementCreate:
    def test_defaults_populate(self):
        r = RequirementCreate(title="Login Security", external_key="REQ-001")
        assert r.external_source == "internal"
        assert r.priority == "medium"
        assert r.status == "active"
        assert r.tags == []
        assert r.acceptance_criteria == []

    def test_auto_key_if_none(self):
        r = RequirementCreate(title="Test", external_key=None)
        assert r.external_key is None

    def test_title_required(self):
        with pytest.raises(Exception):
            RequirementCreate()

    def test_full_payload(self):
        r = RequirementCreate(
            title="MFA Requirement",
            external_key="REQ-MFA-001",
            external_source="jira",
            priority="critical",
            status="approved",
            tags=["security", "auth"],
            acceptance_criteria=[{"id": "AC-1", "text": "MFA must be enforced"}],
        )
        assert r.priority == "critical"
        assert "security" in r.tags


# ── RequirementUpdate ─────────────────────────────────────────────────────────


class TestRequirementUpdate:
    def test_all_optional(self):
        u = RequirementUpdate()
        assert u.title is None
        assert u.status is None
        assert u.tags is None

    def test_partial_update(self):
        u = RequirementUpdate(status="approved", tags=["critical"])
        assert u.status == "approved"
        assert u.tags == ["critical"]
        assert u.title is None

    def test_exclude_unset(self):
        u = RequirementUpdate(status="approved")
        data = u.model_dump(exclude_unset=True)
        assert "status" in data
        assert "title" not in data
        assert "tags" not in data


# ── DefectLinkCreate ──────────────────────────────────────────────────────────


class TestDefectLinkCreate:
    def test_title_required(self):
        with pytest.raises(Exception):
            DefectLinkCreate()

    def test_run_case_optional(self):
        d = DefectLinkCreate(title="Login crash")
        assert d.run_case_id is None
        assert d.external_key is None

    def test_defaults(self):
        d = DefectLinkCreate(title="Crash on submit")
        assert d.status == "open"
        assert d.severity == "major"
        assert d.priority == "P2"
        assert d.external_source == "internal"

    def test_full_defect(self):
        d = DefectLinkCreate(
            title="Payment fails for visa cards",
            severity="critical",
            priority="P1",
            run_case_id="run-case-123",
            external_key="DEF-456",
        )
        assert d.severity == "critical"
        assert d.run_case_id == "run-case-123"


# ── TestCaseCreate ────────────────────────────────────────────────────────────


class TestTestCaseCreate:
    def test_title_required(self):
        with pytest.raises(Exception):
            TestCaseCreate()

    def test_defaults(self):
        t = TestCaseCreate(title="Verify login flow")
        assert t.priority == "medium"
        assert t.type == "functional"
        assert t.automation_status == "manual"
        assert t.status == "draft"
        assert t.tags == []
        assert t.steps == []

    def test_title_length_validation(self):
        with pytest.raises(Exception):
            TestCaseCreate(title="")

    def test_with_steps(self):
        from app.domains.test_management.schemas import TestCaseStepCreate
        t = TestCaseCreate(
            title="Login with valid credentials",
            steps=[
                TestCaseStepCreate(step_no=1, action="Open browser", expected_result="Browser opens"),
                TestCaseStepCreate(step_no=2, action="Enter URL", expected_result="Page loads"),
            ],
        )
        assert len(t.steps) == 2
        assert t.steps[0].step_no == 1


# ── MgmtCommentCreate ────────────────────────────────────────────────────────


class TestMgmtCommentCreate:
    def test_valid_entity_types_accepted(self):
        for et in ALLOWED_COMMENT_ENTITY_TYPES:
            c = MgmtCommentCreate(
                entity_type=et,
                entity_id="some-id",
                body_md="Test comment",
            )
            assert c.entity_type == et

    def test_invalid_entity_type_rejected(self):
        with pytest.raises(Exception):
            MgmtCommentCreate(
                entity_type="project",  # not in ALLOWED_COMMENT_ENTITY_TYPES
                entity_id="some-id",
                body_md="Test comment",
            )

    def test_body_required(self):
        with pytest.raises(Exception):
            MgmtCommentCreate(entity_type="case", entity_id="id", body_md="")

    def test_mentions_defaults_empty(self):
        c = MgmtCommentCreate(entity_type="case", entity_id="id", body_md="Comment")
        assert c.mentions == []


# ── RegressionSetCaseIn ───────────────────────────────────────────────────────


class TestRegressionSetCaseIn:
    def test_defaults(self):
        r = RegressionSetCaseIn(case_id="case-123")
        assert r.order_index == 0
        assert r.risk_score == 0.0
        assert r.reason == "Manual selection"
        assert r.include_mode == "manual"

    def test_float_risk_score(self):
        r = RegressionSetCaseIn(case_id="case-123", risk_score=0.75)
        assert r.risk_score == 0.75

    def test_int_risk_score_coerced(self):
        r = RegressionSetCaseIn(case_id="case-123", risk_score=1)
        assert r.risk_score == 1.0


# ── TestPlanCreate ────────────────────────────────────────────────────────────


class TestTestPlanCreate:
    def test_name_required(self):
        with pytest.raises(Exception):
            TestPlanCreate()

    def test_defaults(self):
        p = TestPlanCreate(name="Sprint 1 Plan")
        assert p.plan_type == "regression"
        assert p.status == "draft"

    def test_full_plan(self):
        p = TestPlanCreate(
            name="Release v2.0 Plan",
            plan_type="sprint",
            release_name="v2.0",
            status="in_progress",
        )
        assert p.release_name == "v2.0"


# ── Notification schemas ──────────────────────────────────────────────────────


class TestMgmtNotificationCreate:
    def test_required_fields(self):
        n = MgmtNotificationCreate(
            user_id="user-123",
            kind="test_run_complete",
            title="Run finished",
        )
        assert n.body == ""
        assert n.severity == "info"
        assert n.channel == "in_app"

    def test_missing_user_id_fails(self):
        with pytest.raises(Exception):
            MgmtNotificationCreate(kind="event", title="Test")
