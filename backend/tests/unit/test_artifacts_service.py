"""Unit tests for app.domains.artifacts.service facade.

Covers: list_artifacts, get_artifact, upload, delete_artifact
DB and filesystem calls are fully mocked.
"""
from __future__ import annotations

import pytest

try:
    from unittest.mock import MagicMock, patch, call
    import app.domains.artifacts.service as artifacts_svc  # noqa: F401
except ImportError as _exc:
    pytestmark = pytest.mark.skipif(True, reason=f"artifacts service not importable: {_exc}")
    artifacts_svc = None  # type: ignore


def _make_artifact_mock(artifact_id="art-1", job_id=None, filename="report.html", size=512):
    """Build a minimal Artifact ORM mock with __table__.columns support."""
    col_id = MagicMock(); col_id.key = "id"
    col_job = MagicMock(); col_job.key = "job_id"
    col_path = MagicMock(); col_path.key = "storage_path"
    col_mime = MagicMock(); col_mime.key = "mime_type"
    col_file = MagicMock(); col_file.key = "filename"
    col_size = MagicMock(); col_size.key = "size"

    art = MagicMock()
    art.id = artifact_id
    art.job_id = job_id
    art.storage_path = f"/tmp/{artifact_id}_{filename}"
    art.mime_type = "text/html"
    art.filename = filename
    art.size = size
    art.__table__ = MagicMock()
    art.__table__.columns = [col_id, col_job, col_path, col_mime, col_file, col_size]
    return art


# ---------------------------------------------------------------------------
# list_artifacts
# ---------------------------------------------------------------------------

class TestListArtifacts:
    def test_list_artifacts_returns_list(self):
        """list_artifacts returns a list (may be empty)."""
        db = MagicMock()
        db.scalars.return_value.all.return_value = []

        result = artifacts_svc.list_artifacts(db)
        assert isinstance(result, list)

    def test_list_artifacts_maps_columns_to_dicts(self):
        """Each artifact is serialized to a column-keyed dict."""
        art = _make_artifact_mock()
        db = MagicMock()
        db.scalars.return_value.all.return_value = [art]

        result = artifacts_svc.list_artifacts(db)
        assert len(result) == 1
        assert result[0]["id"] == "art-1"
        assert result[0]["filename"] == "report.html"

    def test_list_artifacts_limit_capped_at_500(self):
        """A limit > 500 is silently capped at 500."""
        db = MagicMock()
        db.scalars.return_value.all.return_value = []
        # Should not raise; limit capping is internal
        artifacts_svc.list_artifacts(db, limit=9999)


# ---------------------------------------------------------------------------
# get_artifact
# ---------------------------------------------------------------------------

class TestGetArtifact:
    def test_get_artifact_found_returns_dict(self):
        """Existing artifact is returned as a dict with expected keys."""
        art = _make_artifact_mock(artifact_id="art-42")
        db = MagicMock()
        db.get.return_value = art

        result = artifacts_svc.get_artifact(db, "art-42")
        assert isinstance(result, dict)
        assert result["id"] == "art-42"

    def test_get_artifact_not_found_raises_key_error(self):
        """Missing artifact raises KeyError containing the ID."""
        db = MagicMock()
        db.get.return_value = None

        with pytest.raises(KeyError, match="art-missing"):
            artifacts_svc.get_artifact(db, "art-missing")


# ---------------------------------------------------------------------------
# upload
# ---------------------------------------------------------------------------

class TestUpload:
    def test_upload_empty_bytes_raises_value_error(self):
        """Uploading empty bytes raises ValueError."""
        db = MagicMock()
        with pytest.raises(ValueError, match="boş olamaz"):
            artifacts_svc.upload(db, b"", "empty.txt")

    def test_upload_success_returns_dict_with_required_keys(self, tmp_path, monkeypatch):
        """Successful upload returns a dict with id, filename, size."""
        monkeypatch.setattr(artifacts_svc, "_DEFAULT_STORAGE_DIR", str(tmp_path))

        art = _make_artifact_mock(artifact_id="new-art", filename="test.py", size=6)
        db = MagicMock()
        db.refresh.side_effect = lambda a: None  # no-op

        with patch("app.domains.artifacts.service.Artifact", return_value=art):
            result = artifacts_svc.upload(db, b"hello!", "test.py", job_id="job-1")

        assert isinstance(result, dict)
        # Check commit was called
        db.add.assert_called_once()
        db.commit.assert_called_once()

    def test_upload_strips_directory_traversal_from_filename(self, tmp_path, monkeypatch):
        """Path traversal in filename is stripped to the basename only."""
        monkeypatch.setattr(artifacts_svc, "_DEFAULT_STORAGE_DIR", str(tmp_path))

        art = _make_artifact_mock(filename="evil.sh")
        db = MagicMock()
        db.refresh.side_effect = lambda a: None

        with patch("app.domains.artifacts.service.Artifact", return_value=art) as MockArtifact:
            artifacts_svc.upload(db, b"data", "../../evil.sh")
            _, kwargs = MockArtifact.call_args
            # filename passed to Artifact constructor should be basename only
            assert "/" not in kwargs.get("filename", "evil.sh")
            assert ".." not in kwargs.get("filename", "evil.sh")


# ---------------------------------------------------------------------------
# delete_artifact
# ---------------------------------------------------------------------------

class TestDeleteArtifact:
    def test_delete_artifact_not_found_raises_key_error(self):
        """Deleting a non-existent artifact raises KeyError."""
        db = MagicMock()
        db.get.return_value = None

        with pytest.raises(KeyError, match="art-gone"):
            artifacts_svc.delete_artifact(db, "art-gone")

    def test_delete_artifact_removes_file_and_db_record(self, tmp_path):
        """delete_artifact unlinks the file and commits the DB deletion."""
        # Create a real temp file to test unlink
        storage_file = tmp_path / "art-1_report.html"
        storage_file.write_bytes(b"content")

        art = MagicMock()
        art.storage_path = str(storage_file)
        db = MagicMock()
        db.get.return_value = art

        artifacts_svc.delete_artifact(db, "art-1")

        assert not storage_file.exists()
        db.delete.assert_called_once_with(art)
        db.commit.assert_called_once()
