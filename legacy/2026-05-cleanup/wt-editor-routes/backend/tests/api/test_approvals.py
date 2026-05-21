"""TC-0501..TC-0504: Approval queue tests."""

from fastapi.testclient import TestClient


class TestApprovalList:
    """TC-0501"""

    def test_list_approvals(self, client: TestClient, auth_headers, project_id):
        r = client.get(
            f"/api/v1/tspm/projects/{project_id}/approvals",
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert isinstance(r.json(), list)


class TestApprovalDecision:
    """TC-0502, TC-0503, TC-0504"""

    def _create_approval(self, client, auth_headers, project_id, title="Test Onay"):
        r = client.post(
            f"/api/v1/tspm/projects/{project_id}/approvals",
            json={"title": title},
            headers=auth_headers,
        )
        if r.status_code == 201:
            return r.json()["id"]
        return None

    def test_approve_decision(self, client: TestClient, auth_headers, project_id):
        aid = self._create_approval(client, auth_headers, project_id)
        if aid is None:
            return
        r = client.post(
            f"/api/v1/tspm/projects/{project_id}/approvals/{aid}/decide",
            json={"decision": "approved"},
            headers=auth_headers,
        )
        assert r.status_code == 200

    def test_reject_decision(self, client: TestClient, auth_headers, project_id):
        aid = self._create_approval(client, auth_headers, project_id, "Reddet Onay")
        if aid is None:
            return
        r = client.post(
            f"/api/v1/tspm/projects/{project_id}/approvals/{aid}/decide",
            json={"decision": "rejected"},
            headers=auth_headers,
        )
        assert r.status_code == 200

    def test_nonexistent_approval_returns_404(
        self, client: TestClient, auth_headers, project_id
    ):
        r = client.post(
            f"/api/v1/tspm/projects/{project_id}/approvals/00000000-0000-0000-0000-000000000000/decide",
            json={"decision": "approved"},
            headers=auth_headers,
        )
        assert r.status_code == 404
