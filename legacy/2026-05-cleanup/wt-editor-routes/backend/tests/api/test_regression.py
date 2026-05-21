"""TC-0901..TC-0906: Regression set tests."""

from fastapi.testclient import TestClient


class TestCreateRegressionSet:
    """TC-0901"""

    def test_create_set(self, client: TestClient, auth_headers, project_id):
        r = client.post(
            f"/api/v1/tspm/projects/{project_id}/regression-sets",
            json={"name": "Smoke Seti"},
            headers=auth_headers,
        )
        assert r.status_code == 201
        assert r.json()["scenario_count"] == 0


class TestAddScenarios:
    """TC-0902, TC-0903"""

    def test_add_scenarios_to_set(
        self, client: TestClient, auth_headers, project_id,
        create_scenario, create_regression_set
    ):
        s1 = create_scenario(project_id)
        s2 = create_scenario(project_id)
        set_id = create_regression_set(project_id)
        r = client.post(
            f"/api/v1/tspm/projects/{project_id}/regression-sets/{set_id}/add",
            json={"scenario_ids": [s1, s2]},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["count"] == 2

    def test_duplicate_add_is_idempotent(
        self, client: TestClient, auth_headers, project_id,
        create_scenario, create_regression_set
    ):
        s1 = create_scenario(project_id)
        set_id = create_regression_set(project_id)
        for _ in range(2):
            client.post(
                f"/api/v1/tspm/projects/{project_id}/regression-sets/{set_id}/add",
                json={"scenario_ids": [s1]},
                headers=auth_headers,
            )
        detail = client.get(
            f"/api/v1/tspm/projects/{project_id}/regression-sets/{set_id}",
            headers=auth_headers,
        )
        assert len(detail.json()["scenario_ids"]) == 1


class TestAISuggestion:
    """TC-0904, TC-0905"""

    def test_suggest_requires_scenarios(
        self, client: TestClient, auth_headers, create_project
    ):
        empty_pid = create_project("Boş Proje")
        r = client.post(
            f"/api/v1/tspm/projects/{empty_pid}/regression-sets/suggest",
            json={},
            headers=auth_headers,
        )
        assert r.status_code == 400

    def test_suggest_with_scenarios(
        self, client: TestClient, auth_headers, project_id, create_scenario
    ):
        for i in range(3):
            create_scenario(project_id, f"Reg-Senaryo-{i}")
        r = client.post(
            f"/api/v1/tspm/projects/{project_id}/regression-sets/suggest",
            json={},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert len(r.json()["sets"]) >= 1


class TestAcceptSuggestions:
    """TC-0906"""

    def test_accept_suggested_sets(
        self, client: TestClient, auth_headers, project_id, create_scenario
    ):
        sid = create_scenario(project_id)
        r = client.post(
            f"/api/v1/tspm/projects/{project_id}/regression-sets/accept-suggestions",
            json={"sets": [{"name": "Kabul Seti", "scenario_ids": [sid], "priority": "high"}]},
            headers=auth_headers,
        )
        assert r.status_code == 201
        assert len(r.json()) == 1
