"""Unit tests for app.domains.jobs.service.

The jobs service depends on SQLAlchemy Session, Redis/RQ, and ORM models.
All external dependencies are mocked so these tests run without infra.
"""
from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

try:
    import app.domains.jobs.service as jobs_service
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="jobs service import failed")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_job(status: str = "queued") -> MagicMock:
    """Return a mock GenerationJob ORM object."""
    job = MagicMock()
    job.id = str(uuid.uuid4())
    job.status = status
    job.rq_job_id = None
    job.dataset_version_id = "dv-001"
    job.rule_set_id = None
    job.created_by = "user-1"

    col_id = SimpleNamespace(key="id")
    col_status = SimpleNamespace(key="status")
    col_rq = SimpleNamespace(key="rq_job_id")
    col_dsv = SimpleNamespace(key="dataset_version_id")
    col_rs = SimpleNamespace(key="rule_set_id")
    col_cb = SimpleNamespace(key="created_by")

    job.__table__ = SimpleNamespace(columns=[col_id, col_status, col_rq, col_dsv, col_rs, col_cb])
    return job


def _make_db(job=None):
    """Return a minimal mock SQLAlchemy Session."""
    db = MagicMock()
    db.get.return_value = job
    return db


# ---------------------------------------------------------------------------
# enqueue
# ---------------------------------------------------------------------------

class TestEnqueue:
    def test_enqueue_returns_dict_with_id_and_status(self):
        job = _make_job("queued")
        db = _make_db()

        fake_ver = MagicMock()
        fake_ver.dataset_id = "ds-001"

        rq_job = MagicMock()
        rq_job.id = "rq-abc"
        fake_queue = MagicMock()
        fake_queue.enqueue.return_value = rq_job

        def db_get_side(model, pk):
            from app.infra.models import DatasetVersion
            if model is DatasetVersion:
                return fake_ver
            return None

        db.get.side_effect = db_get_side
        db.flush.return_value = None
        db.commit.return_value = None
        db.refresh.return_value = None
        # After db.add, the job object exists on the session
        db.add.return_value = None

        with patch("app.domains.jobs.service._get_queue", return_value=fake_queue), \
             patch("app.domains.jobs.service.GenerationJob", return_value=job), \
             patch("app.domains.jobs.tasks.run_generation_job", create=True):
            result = jobs_service.enqueue(db, dataset_version_id="dv-001", created_by="user-1")

        assert isinstance(result, dict)
        assert "id" in result
        assert "status" in result

    def test_enqueue_raises_key_error_for_missing_dataset_version(self):
        db = _make_db(job=None)

        def db_get_side(model, pk):
            return None  # DatasetVersion not found

        db.get.side_effect = db_get_side

        with pytest.raises(KeyError, match="bulunamadı"):
            jobs_service.enqueue(db, dataset_version_id="nonexistent")


# ---------------------------------------------------------------------------
# get_job
# ---------------------------------------------------------------------------

class TestGetJob:
    def test_get_job_returns_dict(self):
        job = _make_job()
        db = _make_db(job=job)
        result = jobs_service.get_job(db, job.id)
        assert isinstance(result, dict)
        assert result["id"] == job.id

    def test_get_job_raises_key_error_when_not_found(self):
        db = _make_db(job=None)
        with pytest.raises(KeyError, match="bulunamadı"):
            jobs_service.get_job(db, "nonexistent-job-id")


# ---------------------------------------------------------------------------
# list_jobs
# ---------------------------------------------------------------------------

class TestListJobs:
    def test_list_jobs_returns_list(self):
        job = _make_job()
        db = MagicMock()
        db.scalars.return_value.all.return_value = [job]
        result = jobs_service.list_jobs(db)
        assert isinstance(result, list)

    def test_list_jobs_empty(self):
        db = MagicMock()
        db.scalars.return_value.all.return_value = []
        result = jobs_service.list_jobs(db)
        assert result == []


# ---------------------------------------------------------------------------
# cancel_job
# ---------------------------------------------------------------------------

class TestCancelJob:
    def test_cancel_queued_job_sets_cancelled(self):
        job = _make_job(status="queued")
        db = _make_db(job=job)
        db.commit.return_value = None
        db.refresh.return_value = None

        result = jobs_service.cancel_job(db, job.id)
        assert job.status == "cancelled"
        assert isinstance(result, dict)

    def test_cancel_raises_key_error_when_not_found(self):
        db = _make_db(job=None)
        with pytest.raises(KeyError, match="bulunamadı"):
            jobs_service.cancel_job(db, "ghost-job")

    def test_cancel_raises_value_error_for_terminal_status(self):
        for terminal in ("done", "failed", "cancelled"):
            job = _make_job(status=terminal)
            db = _make_db(job=job)
            with pytest.raises(ValueError, match="terminal"):
                jobs_service.cancel_job(db, job.id)
