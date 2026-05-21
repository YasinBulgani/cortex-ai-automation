"""TC-1601..TC-1602: Dashboard tests."""

from fastapi.testclient import TestClient


class TestDashboard:
    """TC-1601, TC-1602"""

    def test_dashboard_with_data(
        self, client: TestClient, auth_headers, project_id, create_scenario
    ):
        create_scenario(project_id)
        r = client.get(
            f"/api/v1/tspm/projects/{project_id}/dashboard",
            headers=auth_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["scenario_count"] >= 1
        assert "pending_approvals" in body
        assert "execution_count" in body

    def test_empty_project_dashboard(self, client: TestClient, auth_headers, create_project):
        pid = create_project("Boş Dashboard Proje")
        r = client.get(
            f"/api/v1/tspm/projects/{pid}/dashboard",
            headers=auth_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["scenario_count"] == 0
        assert body["pending_approvals"] == 0
        assert body["latest_run_pass_rate"] is None
