"""AI workflow artifact retention tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from sqlalchemy.exc import SQLAlchemyError

from app.domains.ai import artifact_retention


class _FakeDb:
    def __init__(self) -> None:
        self.deleted = []
        self.committed = False

    def delete(self, row) -> None:
        self.deleted.append(row)

    def commit(self) -> None:
        self.committed = True


class _BrokenDb(_FakeDb):
    def scalars(self, _stmt):
        raise SQLAlchemyError("missing workflow artifact table")


def _artifact(path: str, *, completed_at, status: str = "completed", size: int = 0):
    return SimpleNamespace(
        storage_path=path,
        size_bytes=size,
        run=SimpleNamespace(status=status, completed_at=completed_at),
    )


def test_retention_dry_run_does_not_delete_files_or_rows(tmp_path, monkeypatch):
    root = tmp_path / "artifacts"
    root.mkdir()
    old_file = root / "agents_v2" / "run-1" / "report.xlsx"
    old_file.parent.mkdir(parents=True)
    old_file.write_bytes(b"xlsx")
    now = datetime(2026, 5, 17, tzinfo=timezone.utc)
    db = _FakeDb()

    monkeypatch.setattr(artifact_retention.settings, "artifacts_dir", str(root))

    result = artifact_retention.cleanup_workflow_artifacts(
        db,  # type: ignore[arg-type]
        retention_days=30,
        dry_run=True,
        now=now,
        candidates=[
            _artifact(
                str(old_file),
                completed_at=now - timedelta(days=45),
                size=old_file.stat().st_size,
            )
        ],
    )

    assert result["matched_artifacts"] == 1
    assert result["db_rows_deleted"] == 0
    assert result["bytes_reclaimable"] == old_file.stat().st_size
    assert result["files_skipped"] == [{"path": str(old_file), "reason": "dry_run"}]
    assert old_file.exists()
    assert db.deleted == []
    assert db.committed is False


def test_retention_apply_deletes_only_old_terminal_artifacts_under_root(tmp_path, monkeypatch):
    root = tmp_path / "artifacts"
    root.mkdir()
    old_file = root / "old" / "report.xlsx"
    old_file.parent.mkdir()
    old_file.write_bytes(b"old")
    recent_file = root / "recent" / "report.xlsx"
    recent_file.parent.mkdir()
    recent_file.write_bytes(b"recent")
    running_file = root / "running" / "report.xlsx"
    running_file.parent.mkdir()
    running_file.write_bytes(b"running")
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("outside", encoding="utf-8")
    now = datetime(2026, 5, 17, tzinfo=timezone.utc)

    old_artifact = _artifact(
        str(old_file),
        completed_at=now - timedelta(days=45),
        size=old_file.stat().st_size,
    )
    db = _FakeDb()
    monkeypatch.setattr(artifact_retention.settings, "artifacts_dir", str(root))

    result = artifact_retention.cleanup_workflow_artifacts(
        db,  # type: ignore[arg-type]
        retention_days=30,
        dry_run=False,
        now=now,
        candidates=[
            old_artifact,
            _artifact(
                str(recent_file),
                completed_at=now - timedelta(days=3),
                size=recent_file.stat().st_size,
            ),
            _artifact(
                str(running_file),
                completed_at=now - timedelta(days=45),
                status="running",
                size=running_file.stat().st_size,
            ),
            _artifact(
                str(outside_file),
                completed_at=now - timedelta(days=45),
                size=outside_file.stat().st_size,
            ),
            _artifact(
                "https://example.com/trace.zip",
                completed_at=now - timedelta(days=45),
            ),
        ],
    )

    assert result["matched_artifacts"] == 3
    assert result["db_rows_deleted"] == 1
    assert result["files_deleted"] == [str(old_file)]
    assert result["files_skipped"] == [
        {"path": str(outside_file), "reason": "outside_artifacts_dir"},
        {"path": "https://example.com/trace.zip", "reason": "url_artifact"},
    ]
    assert not old_file.exists()
    assert recent_file.exists()
    assert running_file.exists()
    assert outside_file.exists()
    assert db.deleted == [old_artifact]
    assert db.committed is True


def test_retention_reports_missing_tables_without_mutation(tmp_path, monkeypatch):
    root = tmp_path / "artifacts"
    root.mkdir()
    now = datetime(2026, 5, 17, tzinfo=timezone.utc)
    db = _BrokenDb()

    monkeypatch.setattr(artifact_retention.settings, "artifacts_dir", str(root))

    result = artifact_retention.cleanup_workflow_artifacts(
        db,  # type: ignore[arg-type]
        retention_days=30,
        dry_run=True,
        now=now,
    )

    assert result["matched_artifacts"] == 0
    assert result["skipped_reason"] == "artifact_tables_unavailable"
    assert "missing workflow artifact table" in result["query_error"]
    assert db.deleted == []
    assert db.committed is False
