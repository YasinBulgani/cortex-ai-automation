"""TC-0801..TC-0803: Flow editor tests."""

from fastapi.testclient import TestClient


class TestFlowCRUD:
    """TC-0801, TC-0802, TC-0803"""

    def test_create_flow(self, client: TestClient, auth_headers, project_id):
        r = client.post(
            f"/api/v1/tspm/projects/{project_id}/flows",
            json={"name": "Login Akışı", "description": "Test akışı"},
            headers=auth_headers,
        )
        assert r.status_code == 201
        assert r.json()["name"] == "Login Akışı"

    def test_update_flow_graph(
        self, client: TestClient, auth_headers, project_id, create_flow
    ):
        fid = create_flow(project_id)
        nodes = [{"id": "n1", "type": "start"}, {"id": "n2", "type": "action"}]
        edges = [{"source": "n1", "target": "n2"}]
        r = client.put(
            f"/api/v1/tspm/projects/{project_id}/flows/{fid}/graph",
            json={"nodes": nodes, "edges": edges},
            headers=auth_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert len(body["nodes"]) == 2
        assert len(body["edges"]) == 1

    def test_empty_name_returns_422(self, client: TestClient, auth_headers, project_id):
        r = client.post(
            f"/api/v1/tspm/projects/{project_id}/flows",
            json={"name": ""},
            headers=auth_headers,
        )
        assert r.status_code == 422
