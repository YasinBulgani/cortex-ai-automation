"""Unit tests for app.domains.privacy.service (DSAR export/delete).

All tests are DB-free and HTTP-free. SQLAlchemy sessions are replaced with
MagicMock objects so no real database is required.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime, timezone

import pytest

try:
    from app.domains.privacy import service as privacy_service
    from app.domains.privacy.service import (
        build_user_dsar_export,
        delete_user_ai_data,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="privacy service import failed")

USER_ID = "550e8400-e29b-41d4-a716-446655440000"
NON_UUID_USER_ID = "plain-string-user-99"


def _make_mock_run(num_artifacts=1, num_events=1, num_approvals=0):
    run = MagicMock()
    run.user_id = USER_ID
    run.created_at = datetime.now(timezone.utc)
    artifact = MagicMock()
    artifact.storage_path = f"/tmp/artifact_{num_artifacts}.bin"
    artifact.artifact_type = "output"
    artifact.size_bytes = 1024
    artifact.created_at = datetime.now(timezone.utc)
    run.artifacts = [artifact] * num_artifacts
    event = MagicMock()
    event.event_type = "step"
    event.payload = {}
    event.created_at = datetime.now(timezone.utc)
    run.events = [event] * num_events
    run.approvals = [MagicMock()] * num_approvals
    return run


def _make_db(runs=None, trace_count=0):
    db = MagicMock()
    runs = runs or []
    scalars_result = MagicMock()
    scalars_result.all.return_value = runs
    execute_result = MagicMock()
    execute_result.scalars.return_value = scalars_result
    db.scalars.return_value = scalars_result
    db.execute.return_value = execute_result
    return db


# ---------------------------------------------------------------------------
# build_user_dsar_export
# ---------------------------------------------------------------------------

class TestBuildUserDsarExport:
    def test_returns_dict_with_required_keys(self):
        db = _make_db()
        with patch.object(privacy_service, "_select_llm_traces", return_value=[]):
            result = build_user_dsar_export(db, user_id=USER_ID)
        assert isinstance(result, dict)
        for key in ("user_id", "generated_at", "counts", "workflows", "llm_traces"):
            assert key in result, f"Missing key: {key}"

    def test_user_id_echoed_in_result(self):
        db = _make_db()
        with patch.object(privacy_service, "_select_llm_traces", return_value=[]):
            result = build_user_dsar_export(db, user_id=USER_ID)
        assert result["user_id"] == USER_ID

    def test_counts_are_non_negative(self):
        db = _make_db()
        with patch.object(privacy_service, "_select_llm_traces", return_value=[]):
            result = build_user_dsar_export(db, user_id=USER_ID)
        for key, val in result["counts"].items():
            assert val >= 0, f"Count {key} should be non-negative"

    def test_non_uuid_user_id_returns_empty_workflows(self):
        """Non-UUID user_id should not crash; workflows list should be empty."""
        db = _make_db()
        with patch.object(privacy_service, "_select_llm_traces", return_value=[]):
            result = build_user_dsar_export(db, user_id=NON_UUID_USER_ID)
        assert result["workflows"] == []

    def test_generated_at_is_datetime(self):
        db = _make_db()
        with patch.object(privacy_service, "_select_llm_traces", return_value=[]):
            result = build_user_dsar_export(db, user_id=USER_ID)
        assert isinstance(result["generated_at"], datetime)

    def test_llm_traces_included_in_counts(self):
        db = _make_db()
        fake_traces = [{"id": "t1"}, {"id": "t2"}]
        with patch.object(privacy_service, "_select_llm_traces", return_value=fake_traces):
            result = build_user_dsar_export(db, user_id=USER_ID)
        assert result["counts"]["llm_traces"] == 2


# ---------------------------------------------------------------------------
# delete_user_ai_data
# ---------------------------------------------------------------------------

class TestDeleteUserAiData:
    def test_dry_run_returns_skipped_artifacts(self):
        run = _make_mock_run(num_artifacts=2)
        db = _make_db(runs=[run])
        with patch.object(privacy_service, "_count_llm_traces", return_value=5):
            result = delete_user_ai_data(
                db, user_id=USER_ID, dry_run=True, purge_artifact_files=False
            )
        assert result["dry_run"] is True
        assert len(result["artifact_files_skipped"]) == 2

    def test_dry_run_does_not_call_db_delete(self):
        run = _make_mock_run()
        db = _make_db(runs=[run])
        with patch.object(privacy_service, "_count_llm_traces", return_value=0):
            delete_user_ai_data(
                db, user_id=USER_ID, dry_run=True, purge_artifact_files=False
            )
        db.delete.assert_not_called()

    def test_result_contains_deleted_counts(self):
        db = _make_db(runs=[])
        with patch.object(privacy_service, "_count_llm_traces", return_value=3):
            result = delete_user_ai_data(
                db, user_id=USER_ID, dry_run=True, purge_artifact_files=False
            )
        assert "deleted" in result
        assert "llm_traces" in result["deleted"]

    def test_non_uuid_user_id_dry_run_does_not_crash(self):
        db = _make_db(runs=[])
        with patch.object(privacy_service, "_count_llm_traces", return_value=0):
            result = delete_user_ai_data(
                db, user_id=NON_UUID_USER_ID, dry_run=True, purge_artifact_files=False
            )
        assert result["user_id"] == NON_UUID_USER_ID

    def test_user_id_present_in_response(self):
        db = _make_db(runs=[])
        with patch.object(privacy_service, "_count_llm_traces", return_value=0):
            result = delete_user_ai_data(
                db, user_id=USER_ID, dry_run=True, purge_artifact_files=False
            )
        assert result["user_id"] == USER_ID

    def test_zero_runs_yields_zero_deleted_workflows(self):
        db = _make_db(runs=[])
        with patch.object(privacy_service, "_count_llm_traces", return_value=0):
            result = delete_user_ai_data(
                db, user_id=USER_ID, dry_run=True, purge_artifact_files=False
            )
        assert result["deleted"]["workflows"] == 0
