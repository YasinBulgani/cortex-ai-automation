"""TC-1501..TC-1503: Project member tests."""

from fastapi.testclient import TestClient


class TestProjectMembers:
    """TC-1501, TC-1502, TC-1503"""

    def test_add_member(self, client: TestClient, auth_headers, project_id, admin_token):
        me = client.get("/api/v1/auth/me", headers=auth_headers)
        user_id = me.json()["id"]
        r = client.post(
            f"/api/v1/tspm/projects/{project_id}/members",
            json={"user_id": user_id, "role": "operator"},
            headers=auth_headers,
        )
        assert r.status_code == 201
        assert r.json()["role"] == "operator"

    def test_default_role_is_viewer(self, client: TestClient, auth_headers, project_id):
        me = client.get("/api/v1/auth/me", headers=auth_headers)
        user_id = me.json()["id"]
        r = client.post(
            f"/api/v1/tspm/projects/{project_id}/members",
            json={"user_id": user_id},
            headers=auth_headers,
        )
        assert r.status_code == 201
        assert r.json()["role"] == "viewer"

    def test_remove_member(self, client: TestClient, auth_headers, project_id):
        me = client.get("/api/v1/auth/me", headers=auth_headers)
        user_id = me.json()["id"]
        add = client.post(
            f"/api/v1/tspm/projects/{project_id}/members",
            json={"user_id": user_id, "role": "viewer"},
            headers=auth_headers,
        )
        member_id = add.json()["id"]
        r = client.delete(
            f"/api/v1/tspm/projects/{project_id}/members/{member_id}",
            headers=auth_headers,
        )
        assert r.status_code == 204
