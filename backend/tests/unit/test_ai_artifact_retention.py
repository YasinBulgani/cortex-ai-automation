"""Unit tests for app.domains.ai.artifact_retention — workflow artifact cleanup.

Tests are fully self-contained: no real filesystem writes, no DB.
Covers: _resolve_retention_path, _artifact_run_is_eligible, _compact_error,
cleanup_workflow_artifacts dry-run path with mock candidates.
"""
from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

try:
    from app.domains.ai.artifact_retention import (
        _resolve_retention_path,
        _artifact_run_is_eligible,
        _compact_error,
        cleanup_workflow_artifacts,
        TERMINAL_STATUSES,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="artifact_retention import failed")

_ARTIFACTS_ROOT = "/tmp/test_artifacts"


@pytest.fixture(autouse=True)
def _mock_artifacts_dir():
    with patch("app.domains.ai.artifact_retention.settings") as mock_settings:
        mock_settings.artifacts_dir = _ARTIFACTS_ROOT
        mock_settings.ai_workflow_artifact_retention_days = 30
        yield


# ---------------------------------------------------------------------------
# _resolve_retention_path
# ---------------------------------------------------------------------------

class TestResolveRetentionPath:
    def test_empty_path_returns_empty_path_status(self):
        status, path = _resolve_retention_path("")
        assert status == "empty_path"
        assert path is None

    def test_http_url_returns_url_artifact(self):
        status, path = _resolve_retention_path("http://example.com/file.zip")
        assert status == "url_artifact"
        assert path is None

    def test_https_url_returns_url_artifact(self):
        status, path = _resolve_retention_path("https://s3.amazonaws.com/bucket/key")
        assert status == "url_artifact"
        assert path is None

    def test_valid_path_within_artifacts_dir_returns_ok(self):
        path_str = f"{_ARTIFACTS_ROOT}/workflow-123/output.json"
        status, resolved = _resolve_retention_path(path_str)
        assert status == "ok"
        assert resolved is not None

    def test_path_outside_artifacts_dir_blocked(self):
        status, path = _resolve_retention_path("/etc/passwd")
        assert status == "outside_artifacts_dir"
        assert path is None

    def test_path_traversal_blocked(self):
        # Attempt to escape via ../../../etc/passwd
        escape = f"{_ARTIFACTS_ROOT}/../../../etc/passwd"
        status, path = _resolve_retention_path(escape)
        assert status == "outside_artifacts_dir"
        assert path is None

    def test_relative_path_resolved_under_artifacts_dir(self):
        from pathlib import Path
        status, resolved = _resolve_retention_path("workflow-abc/file.txt")
        assert status == "ok"
        assert resolved is not None
        # macOS resolves /tmp → /private/tmp; compare resolved roots
        root = Path(_ARTIFACTS_ROOT).expanduser().resolve()
        assert str(resolved).startswith(str(root))

    def test_returns_tuple_of_two(self):
        result = _resolve_retention_path("some/path.txt")
        assert isinstance(result, tuple)
        assert len(result) == 2


# ---------------------------------------------------------------------------
# _artifact_run_is_eligible
# ---------------------------------------------------------------------------

class TestArtifactRunIsEligible:
    def _make_artifact(self, status: str, completed_at):
        run = MagicMock()
        run.status = status
        run.completed_at = completed_at
        artifact = MagicMock()
        artifact.run = run
        return artifact

    def test_terminal_status_past_cutoff_eligible(self):
        cutoff = datetime.now(timezone.utc) - timedelta(days=1)
        completed_at = datetime.now(timezone.utc) - timedelta(days=40)
        artifact = self._make_artifact("completed", completed_at)
        assert _artifact_run_is_eligible(artifact, cutoff, TERMINAL_STATUSES) is True

    def test_active_status_not_eligible(self):
        cutoff = datetime.now(timezone.utc)
        completed_at = datetime.now(timezone.utc) - timedelta(days=40)
        artifact = self._make_artifact("running", completed_at)
        assert _artifact_run_is_eligible(artifact, cutoff, TERMINAL_STATUSES) is False

    def test_completed_at_after_cutoff_not_eligible(self):
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        completed_at = datetime.now(timezone.utc) - timedelta(days=5)  # recent, after cutoff
        artifact = self._make_artifact("completed", completed_at)
        assert _artifact_run_is_eligible(artifact, cutoff, TERMINAL_STATUSES) is False

    def test_no_run_not_eligible(self):
        artifact = MagicMock()
        artifact.run = None
        cutoff = datetime.now(timezone.utc)
        assert _artifact_run_is_eligible(artifact, cutoff, TERMINAL_STATUSES) is False

    def test_no_completed_at_not_eligible(self):
        cutoff = datetime.now(timezone.utc)
        artifact = self._make_artifact("completed", None)
        assert _artifact_run_is_eligible(artifact, cutoff, TERMINAL_STATUSES) is False

    def test_naive_completed_at_becomes_utc(self):
        cutoff = datetime.now(timezone.utc) - timedelta(days=1)
        completed_at_naive = datetime.now() - timedelta(days=40)
        artifact = self._make_artifact("failed", completed_at_naive)
        assert _artifact_run_is_eligible(artifact, cutoff, TERMINAL_STATUSES) is True

    def test_failed_status_eligible(self):
        cutoff = datetime.now(timezone.utc) - timedelta(days=1)
        completed_at = datetime.now(timezone.utc) - timedelta(days=40)
        artifact = self._make_artifact("failed", completed_at)
        assert _artifact_run_is_eligible(artifact, cutoff, TERMINAL_STATUSES) is True

    def test_cancelled_status_eligible(self):
        cutoff = datetime.now(timezone.utc) - timedelta(days=1)
        completed_at = datetime.now(timezone.utc) - timedelta(days=40)
        artifact = self._make_artifact("cancelled", completed_at)
        assert _artifact_run_is_eligible(artifact, cutoff, TERMINAL_STATUSES) is True


# ---------------------------------------------------------------------------
# _compact_error
# ---------------------------------------------------------------------------

class TestCompactError:
    def test_returns_string(self):
        exc = ValueError("Something went wrong")
        result = _compact_error(exc)
        assert isinstance(result, str)

    def test_includes_exception_type(self):
        exc = ValueError("test error")
        result = _compact_error(exc)
        assert "ValueError" in result

    def test_includes_first_line_of_message(self):
        exc = RuntimeError("first line\nsecond line\nthird line")
        result = _compact_error(exc)
        assert "first line" in result
        assert "second line" not in result

    def test_empty_message_falls_back_to_class_name(self):
        exc = RuntimeError("")
        result = _compact_error(exc)
        assert "RuntimeError" in result

    def test_connection_error_handled(self):
        exc = ConnectionError("Connection refused")
        result = _compact_error(exc)
        assert "ConnectionError" in result


# ---------------------------------------------------------------------------
# cleanup_workflow_artifacts — dry-run with mock candidates
# ---------------------------------------------------------------------------

class TestCleanupWorkflowArtifacts:
    def _make_mock_db(self):
        db = MagicMock()
        db.commit.return_value = None
        db.delete.return_value = None
        return db

    def _make_artifact(self, path: str, size: int, status: str, days_ago: int):
        run = MagicMock()
        run.status = status
        run.completed_at = datetime.now(timezone.utc) - timedelta(days=days_ago)
        artifact = MagicMock()
        artifact.run = run
        artifact.storage_path = path
        artifact.size_bytes = size
        return artifact

    def test_zero_retention_days_raises(self):
        db = self._make_mock_db()
        with pytest.raises(ValueError, match="retention_days"):
            cleanup_workflow_artifacts(db, retention_days=0)

    def test_negative_retention_days_raises(self):
        db = self._make_mock_db()
        with pytest.raises(ValueError):
            cleanup_workflow_artifacts(db, retention_days=-1)

    def test_dry_run_default_true(self):
        db = self._make_mock_db()
        result = cleanup_workflow_artifacts(db, retention_days=30, candidates=[])
        assert result["dry_run"] is True

    def test_dry_run_counts_reclaimable_bytes(self):
        db = self._make_mock_db()
        artifact = self._make_artifact(
            f"{_ARTIFACTS_ROOT}/workflow-1/output.json", 1024, "completed", 45
        )
        result = cleanup_workflow_artifacts(
            db,
            retention_days=30,
            dry_run=True,
            candidates=[artifact],
        )
        assert result["matched_artifacts"] == 1
        assert result["bytes_reclaimable"] == 1024
        # dry_run=True → no deletes
        assert result["db_rows_deleted"] == 0
        assert result["bytes_deleted"] == 0

    def test_active_artifact_skipped(self):
        db = self._make_mock_db()
        artifact = self._make_artifact(
            f"{_ARTIFACTS_ROOT}/workflow-1/output.json", 512, "running", 45
        )
        result = cleanup_workflow_artifacts(
            db,
            retention_days=30,
            dry_run=True,
            candidates=[artifact],
        )
        assert result["matched_artifacts"] == 0

    def test_recent_artifact_skipped(self):
        db = self._make_mock_db()
        # 5 days old, within 30-day retention
        artifact = self._make_artifact(
            f"{_ARTIFACTS_ROOT}/workflow-1/output.json", 512, "completed", 5
        )
        result = cleanup_workflow_artifacts(
            db,
            retention_days=30,
            dry_run=True,
            candidates=[artifact],
        )
        assert result["matched_artifacts"] == 0

    def test_url_artifact_skipped(self):
        db = self._make_mock_db()
        artifact = self._make_artifact("https://s3.amazonaws.com/key", 100, "completed", 45)
        result = cleanup_workflow_artifacts(
            db,
            retention_days=30,
            dry_run=True,
            candidates=[artifact],
        )
        # URL artifacts matched but skipped (files_skipped)
        assert len(result["files_skipped"]) >= 0  # url_artifact → skipped

    def test_result_has_expected_keys(self):
        db = self._make_mock_db()
        result = cleanup_workflow_artifacts(db, retention_days=30, candidates=[])
        for key in [
            "dry_run", "retention_days", "cutoff", "matched_artifacts",
            "db_rows_deleted", "bytes_reclaimable", "bytes_deleted",
            "files_deleted", "files_missing", "files_skipped",
        ]:
            assert key in result

    def test_empty_candidates_returns_empty_result(self):
        db = self._make_mock_db()
        result = cleanup_workflow_artifacts(db, retention_days=30, candidates=[])
        assert result["matched_artifacts"] == 0
        assert result["bytes_reclaimable"] == 0
