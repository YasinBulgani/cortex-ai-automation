"""TC-1401..TC-1404: API test collection tests."""

from fastapi.testclient import TestClient


class TestApiCollection:
    """TC-1401, TC-1402, TC-1403, TC-1404"""

    def test_create_collection(self, client: TestClient, auth_headers, project_id):
        r = client.post(
            f"/api/v1/tspm/projects/{project_id}/api-tests/collections",
            json={"name": "Auth API", "base_url": "http://localhost:8000"},
            headers=auth_headers,
        )
        assert r.status_code == 201
        assert r.json()["request_count"] == 0

    def test_add_request_to_collection(self, client: TestClient, auth_headers, project_id):
        col = client.post(
            f"/api/v1/tspm/projects/{project_id}/api-tests/collections",
            json={"name": "Health Col"},
            headers=auth_headers,
        )
        col_id = col.json()["id"]
        req = client.post(
            f"/api/v1/tspm/projects/{project_id}/api-tests/collections/{col_id}/requests",
            json={"name": "Health Check", "method": "GET", "path": "/health"},
            headers=auth_headers,
        )
        assert req.status_code == 201

    def test_run_collection(self, client: TestClient, auth_headers, project_id):
        col = client.post(
            f"/api/v1/tspm/projects/{project_id}/api-tests/collections",
            json={"name": "Run Col", "base_url": "http://127.0.0.1:8000"},
            headers=auth_headers,
        )
        col_id = col.json()["id"]
        client.post(
            f"/api/v1/tspm/projects/{project_id}/api-tests/collections/{col_id}/requests",
            json={"name": "Health", "method": "GET", "path": "/health"},
            headers=auth_headers,
        )
        run = client.post(
            f"/api/v1/tspm/projects/{project_id}/api-tests/collections/{col_id}/run",
            headers=auth_headers,
        )
        assert run.status_code == 200
        results = run.json()["results"]
        assert len(results) >= 1
        assert results[0]["passed"] is True

    def test_unreachable_url_returns_error(
        self, client: TestClient, auth_headers, project_id
    ):
        col = client.post(
            f"/api/v1/tspm/projects/{project_id}/api-tests/collections",
            json={"name": "Bad Col", "base_url": "http://unreachable.invalid:9999"},
            headers=auth_headers,
        )
        col_id = col.json()["id"]
        client.post(
            f"/api/v1/tspm/projects/{project_id}/api-tests/collections/{col_id}/requests",
            json={"name": "Fail", "method": "GET", "path": "/"},
            headers=auth_headers,
        )
        run = client.post(
            f"/api/v1/tspm/projects/{project_id}/api-tests/collections/{col_id}/run",
            headers=auth_headers,
        )
        assert run.status_code == 200
        assert run.json()["results"][0]["passed"] is False

    def test_run_collection_respects_assertions(self, client: TestClient, auth_headers, project_id):
        col = client.post(
            f"/api/v1/tspm/projects/{project_id}/api-tests/collections",
            json={"name": "Assert Col", "base_url": "http://127.0.0.1:8000"},
            headers=auth_headers,
        )
        col_id = col.json()["id"]
        client.post(
            f"/api/v1/tspm/projects/{project_id}/api-tests/collections/{col_id}/requests",
            json={
                "name": "Ready Assertion",
                "method": "GET",
                "path": "/ready",
                "assertions": [
                    {"type": "status_code", "operator": "equals", "expected": 200},
                    {"type": "body_contains", "expected": "ready"},
                ],
            },
            headers=auth_headers,
        )
        run = client.post(
            f"/api/v1/tspm/projects/{project_id}/api-tests/collections/{col_id}/run",
            headers=auth_headers,
        )
        assert run.status_code == 200
        result = run.json()["results"][0]
        assert result["passed"] is True
        assert len(result["assertions"]) == 2

    def test_import_postman_collection(self, client: TestClient, auth_headers, project_id):
        payload = {
            "collection": {
                "info": {"name": "Imported Auth Suite"},
                "variable": [{"key": "baseUrl", "value": "http://127.0.0.1:8000"}],
                "item": [
                    {
                        "name": "Health Folder",
                        "item": [
                            {
                                "name": "Ready Check",
                                "request": {
                                    "method": "GET",
                                    "url": {"raw": "{{baseUrl}}/ready", "path": ["ready"]},
                                    "header": [{"key": "Accept", "value": "application/json"}],
                                },
                                "event": [
                                    {
                                        "listen": "test",
                                        "script": {
                                            "exec": [
                                                "pm.response.to.have.status(200)",
                                                "pm.response.text().to.include(\"ready\")",
                                            ]
                                        },
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        }
        imported = client.post(
            f"/api/v1/tspm/projects/{project_id}/api-tests/import-postman",
            json=payload,
            headers=auth_headers,
        )
        assert imported.status_code == 201
        body = imported.json()
        assert body["imported_request_count"] == 1
        collection_id = body["collection"]["id"]

        detail = client.get(
            f"/api/v1/tspm/projects/{project_id}/api-tests/collections/{collection_id}",
            headers=auth_headers,
        )
        assert detail.status_code == 200
        requests = detail.json()["requests"]
        assert len(requests) == 1
        assert requests[0]["method"] == "GET"
        assert requests[0]["path"] == "/ready"
        assert len(requests[0]["assertions"]) == 2
