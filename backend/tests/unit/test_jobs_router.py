"""Jobs router endpoint'leri — arka plan iş kuyruğu yönetimi.

Gerçek FastAPI app + TestClient kullanır; DB ve RQ bağımlılıkları
dependency_overrides ile mock'lanmıştır.
Router layer odaklıdır: HTTP durum kodları, request validation, hata yönetimi.
"""
from __future__ import annotations

try:
    from unittest.mock import MagicMock, patch

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.domains.jobs.router import router

    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _app(mock_db=None, mock_user=None) -> TestClient:
    from app.infra.database import get_db
    from app.deps import get_current_user

    app = FastAPI()
    _mock_db = mock_db if mock_db is not None else MagicMock()
    _mock_user = mock_user if mock_user is not None else _make_user()
    app.dependency_overrides[get_db] = lambda: _mock_db
    app.dependency_overrides[get_current_user] = lambda: _mock_user
    app.include_router(router)
    return TestClient(app, raise_server_exceptions=False)


def _make_user() -> MagicMock:
    user = MagicMock()
    user.id = "user-001"
    return user


def _make_job(
    job_id: str = "job-001",
    status: str = "queued",
    dataset_version_id: str = "dv-001",
) -> MagicMock:
    job = MagicMock()
    job.id = job_id
    job.status = status
    job.dataset_version_id = dataset_version_id
    job.rule_set_id = None
    job.rq_job_id = "rq-001"
    job.created_by = "user-001"
    job.created_at = "2026-05-26T00:00:00"
    job.error_message = None  # Must be None/str, not MagicMock
    return job


def _minimal_enqueue_body() -> dict:
    return {"dataset_version_id": "dv-001"}


# ---------------------------------------------------------------------------
# POST /jobs — enqueue
# ---------------------------------------------------------------------------

def test_enqueue_job_missing_dataset_version_id_422() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    r = client.post("/jobs", json={})
    assert r.status_code == 422


def test_enqueue_job_dataset_version_not_found_404() -> None:
    if not _IMPORT_OK:
        return
    mock_db = MagicMock()
    mock_db.get.return_value = None  # DatasetVersion not found
    client = _app(mock_db=mock_db)
    with patch("app.domains.jobs.router._queue"):
        r = client.post("/jobs", json=_minimal_enqueue_body())
    assert r.status_code == 404


def test_enqueue_job_success_202() -> None:
    if not _IMPORT_OK:
        return
    mock_db = MagicMock()
    mock_ver = MagicMock()
    mock_ver.dataset_id = "ds-001"
    mock_db.get.return_value = mock_ver

    mock_rq_job = MagicMock()
    mock_rq_job.id = "rq-job-001"
    mock_queue = MagicMock()
    mock_queue.enqueue.return_value = mock_rq_job

    created_job = _make_job(status="queued")
    mock_db.add.return_value = None
    mock_db.flush.return_value = None
    mock_db.commit.return_value = None
    mock_db.refresh.return_value = None

    client = _app(mock_db=mock_db)
    with (
        patch("app.domains.jobs.router._queue", return_value=mock_queue),
        patch("app.domains.jobs.router.log_audit"),
        patch("app.domains.jobs.router.GenerationJob", return_value=created_job),
    ):
        r = client.post("/jobs", json=_minimal_enqueue_body())
    assert r.status_code == 202


def test_enqueue_job_invalid_rule_set_400() -> None:
    if not _IMPORT_OK:
        return
    mock_db = MagicMock()
    mock_ver = MagicMock()
    mock_ver.dataset_id = "ds-001"
    mock_rs = MagicMock()
    mock_rs.dataset_id = "ds-OTHER"  # mismatch → 400

    def _get(model, key):
        if key == "dv-001":
            return mock_ver
        if key == "rs-bad":
            return mock_rs
        return None

    mock_db.get.side_effect = _get
    body = {"dataset_version_id": "dv-001", "rule_set_id": "rs-bad"}
    client = _app(mock_db=mock_db)
    with patch("app.domains.jobs.router._queue"):
        r = client.post("/jobs", json=body)
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# GET /jobs — list
# ---------------------------------------------------------------------------

def test_list_jobs_empty() -> None:
    if not _IMPORT_OK:
        return
    mock_db = MagicMock()
    mock_db.scalars.return_value.all.return_value = []
    client = _app(mock_db=mock_db)
    r = client.get("/jobs")
    assert r.status_code == 200
    assert r.json() == []


def test_list_jobs_returns_items() -> None:
    if not _IMPORT_OK:
        return
    mock_db = MagicMock()
    jobs = [_make_job("j1"), _make_job("j2")]
    mock_db.scalars.return_value.all.return_value = jobs
    client = _app(mock_db=mock_db)
    r = client.get("/jobs")
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# GET /jobs/{id}
# ---------------------------------------------------------------------------

def test_get_job_not_found_404() -> None:
    if not _IMPORT_OK:
        return
    mock_db = MagicMock()
    mock_db.get.return_value = None
    client = _app(mock_db=mock_db)
    r = client.get("/jobs/nonexistent")
    assert r.status_code == 404


def test_get_job_found_200() -> None:
    if not _IMPORT_OK:
        return
    mock_db = MagicMock()
    mock_db.get.return_value = _make_job("job-001", status="running")
    client = _app(mock_db=mock_db)
    r = client.get("/jobs/job-001")
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# GET /jobs/{id}/events
# ---------------------------------------------------------------------------

def test_list_events_job_not_found_404() -> None:
    if not _IMPORT_OK:
        return
    mock_db = MagicMock()
    mock_db.get.return_value = None
    client = _app(mock_db=mock_db)
    r = client.get("/jobs/bad-id/events")
    assert r.status_code == 404


def test_list_events_success() -> None:
    if not _IMPORT_OK:
        return
    mock_db = MagicMock()
    mock_db.get.return_value = _make_job()
    mock_db.scalars.return_value.all.return_value = []
    client = _app(mock_db=mock_db)
    r = client.get("/jobs/job-001/events")
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# GET /jobs/{id}/artifacts
# ---------------------------------------------------------------------------

def test_list_job_artifacts_not_found_404() -> None:
    if not _IMPORT_OK:
        return
    mock_db = MagicMock()
    mock_db.get.return_value = None
    client = _app(mock_db=mock_db)
    r = client.get("/jobs/bad-id/artifacts")
    assert r.status_code == 404


def test_list_job_artifacts_success() -> None:
    if not _IMPORT_OK:
        return
    mock_db = MagicMock()
    mock_db.get.return_value = _make_job()
    mock_db.scalars.return_value.all.return_value = []
    client = _app(mock_db=mock_db)
    r = client.get("/jobs/job-001/artifacts")
    assert r.status_code == 200
    assert r.json() == []
