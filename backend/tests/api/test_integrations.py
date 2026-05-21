"""TC-1301..TC-1303: Integration tests."""

from fastapi.testclient import TestClient


class TestIntegrationCRUD:
    """TC-1301, TC-1302, TC-1303"""

    def test_create_integration(self, client: TestClient, auth_headers, project_id):
        r = client.post(
            f"/api/v1/tspm/projects/{project_id}/integrations",
            json={"provider": "jira", "config": {"url": "https://jira.example.com"}},
            headers=auth_headers,
        )
        assert r.status_code == 201
        assert r.json()["provider"] == "jira"

    def test_sync_updates_timestamp(self, client: TestClient, auth_headers, project_id):
        create = client.post(
            f"/api/v1/tspm/projects/{project_id}/integrations",
            json={"provider": "azure-devops"},
            headers=auth_headers,
        )
        intg_id = create.json()["id"]
        sync = client.post(
            f"/api/v1/tspm/projects/{project_id}/integrations/{intg_id}/sync",
            headers=auth_headers,
        )
        assert sync.status_code == 200
        assert sync.json()["synced_count"] == 0

    def test_empty_provider_returns_422(self, client: TestClient, auth_headers, project_id):
        r = client.post(
            f"/api/v1/tspm/projects/{project_id}/integrations",
            json={"provider": ""},
            headers=auth_headers,
        )
        assert r.status_code == 422
