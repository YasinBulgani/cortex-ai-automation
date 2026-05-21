"""Security: SSRF protection for API test runner."""

from fastapi.testclient import TestClient


class TestSSRFProtection:

    def test_api_runner_does_not_access_internal(self, client: TestClient, auth_headers):
        """API test collections should not allow access to internal services."""
        pid = client.post(
            "/api/v1/tspm/projects", json={"name": "SSRF Test"}, headers=auth_headers,
        ).json()["id"]
        col = client.post(
            f"/api/v1/tspm/projects/{pid}/api-tests/collections",
            json={"name": "SSRF Col", "base_url": "http://169.254.169.254"},
            headers=auth_headers,
        )
        col_id = col.json()["id"]
        client.post(
            f"/api/v1/tspm/projects/{pid}/api-tests/collections/{col_id}/requests",
            json={"name": "Metadata", "method": "GET", "path": "/latest/meta-data/"},
            headers=auth_headers,
        )
        run = client.post(
            f"/api/v1/tspm/projects/{pid}/api-tests/collections/{col_id}/run",
            headers=auth_headers,
        )
        assert run.status_code == 200
        results = run.json()["results"]
        assert len(results) == 1
        assert results[0]["passed"] is False

    def test_api_runner_handles_localhost(self, client: TestClient, auth_headers):
        pid = client.post(
            "/api/v1/tspm/projects", json={"name": "Localhost Test"}, headers=auth_headers,
        ).json()["id"]
        col = client.post(
            f"/api/v1/tspm/projects/{pid}/api-tests/collections",
            json={"name": "Local", "base_url": "http://127.0.0.1:8000"},
            headers=auth_headers,
        )
        col_id = col.json()["id"]
        client.post(
            f"/api/v1/tspm/projects/{pid}/api-tests/collections/{col_id}/requests",
            json={"name": "Health", "method": "GET", "path": "/health"},
            headers=auth_headers,
        )
        run = client.post(
            f"/api/v1/tspm/projects/{pid}/api-tests/collections/{col_id}/run",
            headers=auth_headers,
        )
        assert run.status_code == 200

    def test_single_execute_blocks_internal_targets(self, client: TestClient, auth_headers):
        pid = client.post(
            "/api/v1/tspm/projects", json={"name": "Single Execute SSRF"}, headers=auth_headers,
        ).json()["id"]
        r = client.post(
            f"/api/v1/api-testing/projects/{pid}/execute/single",
            json={"method": "GET", "url": "http://169.254.169.254/latest/meta-data"},
            headers=auth_headers,
        )
        assert r.status_code == 400
        assert "guvensiz" in r.json()["detail"].lower()

    def test_single_execute_blocks_localhost_targets(self, client: TestClient, auth_headers):
        pid = client.post(
            "/api/v1/tspm/projects", json={"name": "Single Execute Localhost"}, headers=auth_headers,
        ).json()["id"]
        r = client.post(
            f"/api/v1/api-testing/projects/{pid}/execute/single",
            json={"method": "GET", "url": "http://127.0.0.1:8000/health"},
            headers=auth_headers,
        )
        assert r.status_code == 400
        assert "guvensiz" in r.json()["detail"].lower()

    def test_spec_import_blocks_internal_source_urls(self, client: TestClient, auth_headers):
        pid = client.post(
            "/api/v1/tspm/projects", json={"name": "Spec Import SSRF"}, headers=auth_headers,
        ).json()["id"]
        r = client.post(
            f"/api/v1/api-testing/projects/{pid}/specs/import",
            json={"source_url": "http://127.0.0.1:8000/openapi.json"},
            headers=auth_headers,
        )
        assert r.status_code == 400
        assert "guvensiz" in r.json()["detail"].lower()
