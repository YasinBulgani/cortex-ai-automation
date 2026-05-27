"""Unit tests for privacy service and workflow export pure helpers.

No DB, no HTTP, no LLM — pure Python only.

Covers:
  app/domains/privacy/service.py:
    _uuid_or_none, _workflow_export
"""

from __future__ import annotations

import types
from datetime import datetime, timezone

import pytest

from app.domains.privacy.service import _uuid_or_none, _workflow_export


# ── Helpers ───────────────────────────────────────────────────────────────────


def _dt(year: int = 2024, month: int = 1, day: int = 15) -> datetime:
    return datetime(year, month, day, 10, 0, 0, tzinfo=timezone.utc)


def _make_event(event_type: str = "step", agent: str = "agent1", msg: str = "done") -> types.SimpleNamespace:
    return types.SimpleNamespace(
        event_type=event_type,
        agent_name=agent,
        message=msg,
        created_at=_dt(),
    )


def _make_artifact(kind: str = "report", name: str = "report.html") -> types.SimpleNamespace:
    return types.SimpleNamespace(
        id="art-111",
        kind=kind,
        name=name,
        storage_path=f"/artifacts/{name}",
        mime_type="text/html",
        size_bytes=1024,
        created_at=_dt(),
    )


def _make_approval(decision: str = "approved") -> types.SimpleNamespace:
    return types.SimpleNamespace(
        id="apv-222",
        decision=decision,
        created_at=_dt(),
    )


def _make_run(**kwargs) -> types.SimpleNamespace:
    defaults = {
        "id": "run-123",
        "project_id": "proj-456",
        "workflow_type": "test_generation",
        "status": "completed",
        "input_source": "upload",
        "created_at": _dt(2024, 1, 15),
        "completed_at": _dt(2024, 1, 15),
        "cost_usd": 0.05,
        "tokens_used": 1200,
        "events": [],
        "artifacts": [],
        "approvals": [],
    }
    defaults.update(kwargs)
    return types.SimpleNamespace(**defaults)


# ── _uuid_or_none ─────────────────────────────────────────────────────────────


class TestPrivacyUuidOrNone:
    VALID = "550e8400-e29b-41d4-a716-446655440000"

    def test_valid_uuid(self) -> None:
        assert _uuid_or_none(self.VALID) == self.VALID

    def test_invalid_returns_none(self) -> None:
        assert _uuid_or_none("not-a-uuid") is None

    def test_empty_string_returns_none(self) -> None:
        assert _uuid_or_none("") is None

    def test_returns_string_type(self) -> None:
        result = _uuid_or_none(self.VALID)
        assert isinstance(result, str)


# ── _workflow_export ──────────────────────────────────────────────────────────


class TestWorkflowExport:
    def test_returns_dict(self) -> None:
        run = _make_run()
        result = _workflow_export(run)
        assert isinstance(result, dict)

    def test_run_id_as_string(self) -> None:
        run = _make_run(id="run-abc")
        result = _workflow_export(run)
        assert result["run_id"] == "run-abc"

    def test_project_id_as_string(self) -> None:
        run = _make_run(project_id="proj-xyz")
        result = _workflow_export(run)
        assert result["project_id"] == "proj-xyz"

    def test_workflow_type_preserved(self) -> None:
        run = _make_run(workflow_type="regression_test")
        result = _workflow_export(run)
        assert result["workflow_type"] == "regression_test"

    def test_status_preserved(self) -> None:
        run = _make_run(status="failed")
        result = _workflow_export(run)
        assert result["status"] == "failed"

    def test_cost_is_float(self) -> None:
        run = _make_run(cost_usd=0.12)
        result = _workflow_export(run)
        assert isinstance(result["cost_usd"], float)
        assert result["cost_usd"] == pytest.approx(0.12)

    def test_cost_none_defaults_zero(self) -> None:
        run = _make_run(cost_usd=None)
        result = _workflow_export(run)
        assert result["cost_usd"] == 0.0

    def test_tokens_is_int(self) -> None:
        run = _make_run(tokens_used=500)
        result = _workflow_export(run)
        assert isinstance(result["tokens_used"], int)
        assert result["tokens_used"] == 500

    def test_tokens_none_defaults_zero(self) -> None:
        run = _make_run(tokens_used=None)
        result = _workflow_export(run)
        assert result["tokens_used"] == 0

    def test_events_list(self) -> None:
        event = _make_event("step_complete", "orchestrator", "Step 1 done")
        run = _make_run(events=[event])
        result = _workflow_export(run)
        assert len(result["events"]) == 1
        assert result["events"][0]["event_type"] == "step_complete"
        assert result["events"][0]["agent_name"] == "orchestrator"

    def test_artifacts_list(self) -> None:
        artifact = _make_artifact("screenshot", "screen.png")
        run = _make_run(artifacts=[artifact])
        result = _workflow_export(run)
        assert len(result["artifacts"]) == 1
        assert result["artifacts"][0]["kind"] == "screenshot"
        assert result["artifacts"][0]["name"] == "screen.png"

    def test_approvals_list(self) -> None:
        approval = _make_approval("rejected")
        run = _make_run(approvals=[approval])
        result = _workflow_export(run)
        assert len(result["approvals"]) == 1
        assert result["approvals"][0]["decision"] == "rejected"

    def test_created_at_as_iso_string(self) -> None:
        run = _make_run(created_at=_dt(2024, 6, 1))
        result = _workflow_export(run)
        assert isinstance(result["created_at"], str)
        assert "2024-06-01" in result["created_at"]

    def test_none_created_at(self) -> None:
        run = _make_run(created_at=None, completed_at=None)
        result = _workflow_export(run)
        assert result["created_at"] is None
        assert result["completed_at"] is None

    def test_empty_events_and_artifacts(self) -> None:
        run = _make_run(events=[], artifacts=[], approvals=[])
        result = _workflow_export(run)
        assert result["events"] == []
        assert result["artifacts"] == []
        assert result["approvals"] == []

    def test_all_expected_keys_present(self) -> None:
        run = _make_run()
        result = _workflow_export(run)
        expected_keys = {
            "run_id", "project_id", "workflow_type", "status",
            "input_source", "created_at", "completed_at",
            "cost_usd", "tokens_used", "events", "artifacts", "approvals",
        }
        assert expected_keys.issubset(result.keys())

    def test_events_sorted_by_created_at(self) -> None:
        # Events must be sorted by created_at
        e1 = types.SimpleNamespace(
            event_type="first", agent_name="a", message="m",
            created_at=datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc)
        )
        e2 = types.SimpleNamespace(
            event_type="second", agent_name="b", message="m",
            created_at=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
        )
        run = _make_run(events=[e2, e1])  # deliberately reversed
        result = _workflow_export(run)
        assert result["events"][0]["event_type"] == "first"
        assert result["events"][1]["event_type"] == "second"
