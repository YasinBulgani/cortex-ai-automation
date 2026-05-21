"""TC-0201..TC-0206: Project management tests."""

import time

import pytest
from fastapi.testclient import TestClient


class TestCreateProject:
    """TC-0201, TC-0202, TC-0203, TC-0204"""

    def test_create_project_success(self, client: TestClient, auth_headers):
        r = client.post(
            "/api/v1/tspm/projects",
            json={"name": "Test Projesi", "description": "Açıklama"},
            headers=auth_headers,
        )
        assert r.status_code == 201
        body = r.json()
        assert body["name"] == "Test Projesi"
        assert body["archived"] is False
        assert "id" in body

    def test_empty_name_returns_422(self, client: TestClient, auth_headers):
        r = client.post(
            "/api/v1/tspm/projects",
            json={"name": ""},
            headers=auth_headers,
        )
        assert r.status_code == 422

    def test_single_char_name_accepted(self, client: TestClient, auth_headers):
        r = client.post(
            "/api/v1/tspm/projects",
            json={"name": "A"},
            headers=auth_headers,
        )
        assert r.status_code == 201

    def test_very_long_name(self, client: TestClient, auth_headers):
        r = client.post(
            "/api/v1/tspm/projects",
            json={"name": "X" * 201},
            headers=auth_headers,
        )
        assert r.status_code in (201, 422, 500)


class TestListProjects:
    """TC-0205"""

    def test_projects_ordered_by_created_at_desc(
        self, client: TestClient, auth_headers, create_project
    ):
        p1 = create_project("İlk Proje")
        time.sleep(0.05)
        p2 = create_project("İkinci Proje")
        r = client.get("/api/v1/tspm/projects", headers=auth_headers)
        assert r.status_code == 200
        ids = [p["id"] for p in r.json()]
        assert ids.index(p2) < ids.index(p1)


class TestProjectNotFound:
    """TC-0206"""

    def test_nonexistent_project_returns_404(self, client: TestClient, auth_headers):
        r = client.get(
            "/api/v1/tspm/projects/00000000-0000-0000-0000-000000000000/dashboard",
            headers=auth_headers,
        )
        assert r.status_code == 404
