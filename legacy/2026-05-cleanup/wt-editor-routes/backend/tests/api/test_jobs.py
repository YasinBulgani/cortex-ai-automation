"""Tests for Jobs (GenerationJob) — /api/v1/jobs endpoints."""

from fastapi.testclient import TestClient


class TestJobList:

    def test_list_jobs_returns_array(self, client: TestClient, auth_headers):
        r = client.get("/api/v1/jobs", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_list_jobs_requires_auth(self, client: TestClient):
        r = client.get("/api/v1/jobs")
        assert r.status_code == 401

    def test_list_jobs_respects_limit(self, client: TestClient, auth_headers):
        r = client.get("/api/v1/jobs?limit=5", headers=auth_headers)
        assert r.status_code == 200
        assert len(r.json()) <= 5


class TestJobDetail:

    def test_get_nonexistent_job_returns_404(self, client: TestClient, auth_headers):
        r = client.get(
            "/api/v1/jobs/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert r.status_code == 404


class TestJobCreate:

    def test_create_job_with_nonexistent_dataset_returns_404(
        self, client: TestClient, auth_headers
    ):
        r = client.post(
            "/api/v1/jobs",
            json={
                "dataset_version_id": "00000000-0000-0000-0000-000000000000",
                "rule_set_id": "00000000-0000-0000-0000-000000000000",
                "row_count": 100,
            },
            headers=auth_headers,
        )
        assert r.status_code in (404, 422)
