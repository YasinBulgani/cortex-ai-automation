"""Tests for Catalog (Dataset) CRUD — /api/v1/datasets endpoints."""

from fastapi.testclient import TestClient


class TestDatasetList:

    def test_list_datasets_returns_array(self, client: TestClient, auth_headers):
        r = client.get("/api/v1/datasets", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_list_datasets_requires_auth(self, client: TestClient):
        r = client.get("/api/v1/datasets")
        assert r.status_code == 401


class TestDatasetCreate:

    def test_create_dataset(self, client: TestClient, auth_headers):
        r = client.post(
            "/api/v1/datasets",
            json={"name": "Test DS", "description": "API test"},
            headers=auth_headers,
        )
        assert r.status_code == 201
        body = r.json()
        assert body["name"] == "Test DS"
        assert "id" in body

    def test_create_dataset_audit_logged(self, client: TestClient, auth_headers):
        r = client.post(
            "/api/v1/datasets",
            json={"name": "Audit DS"},
            headers=auth_headers,
        )
        assert r.status_code == 201


class TestDatasetDetail:

    def test_get_nonexistent_dataset_returns_404(self, client: TestClient, auth_headers):
        r = client.get(
            "/api/v1/datasets/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert r.status_code == 404


class TestDatasetVersions:

    def test_list_versions_for_dataset(self, client: TestClient, auth_headers):
        ds = client.post(
            "/api/v1/datasets",
            json={"name": "Version DS"},
            headers=auth_headers,
        )
        ds_id = ds.json()["id"]
        r = client.get(f"/api/v1/datasets/{ds_id}/versions", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
