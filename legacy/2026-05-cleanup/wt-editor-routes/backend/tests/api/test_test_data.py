"""TC-1201..TC-1204: Test data management tests."""

from fastapi.testclient import TestClient


class TestCreateTestData:
    """TC-1201"""

    def test_create_test_data(self, client: TestClient, auth_headers, project_id):
        r = client.post(
            f"/api/v1/tspm/projects/{project_id}/test-data",
            json={
                "name": "Login Verileri",
                "columns": [{"name": "username"}, {"name": "password"}],
                "rows": [
                    {"username": "user1", "password": "pass1"},
                    {"username": "user2", "password": "pass2"},
                ],
            },
            headers=auth_headers,
        )
        assert r.status_code == 201
        assert r.json()["name"] == "Login Verileri"


class TestDataBinding:
    """TC-1202, TC-1204"""

    def test_bind_data_to_scenario(
        self, client: TestClient, auth_headers, project_id,
        create_scenario, create_test_data
    ):
        sid = create_scenario(project_id, steps=[
            {"order": 0, "keyword": "Given", "text": "Kullanıcı {{kullanici}}"}
        ])
        ds_id = create_test_data(project_id)
        r = client.post(
            f"/api/v1/tspm/projects/{project_id}/scenarios/{sid}/bind-data",
            json={"data_set_id": ds_id, "parameter_mapping": {"kullanici": "col1"}},
            headers=auth_headers,
        )
        assert r.status_code == 201

    def test_bind_nonexistent_dataset_returns_404(
        self, client: TestClient, auth_headers, project_id, create_scenario
    ):
        sid = create_scenario(project_id)
        r = client.post(
            f"/api/v1/tspm/projects/{project_id}/scenarios/{sid}/bind-data",
            json={"data_set_id": "00000000-0000-0000-0000-000000000000"},
            headers=auth_headers,
        )
        assert r.status_code == 404


class TestExpandedScenario:
    """TC-1203"""

    def test_expanded_view(
        self, client: TestClient, auth_headers, project_id,
        create_scenario, create_test_data
    ):
        sid = create_scenario(project_id, steps=[
            {"order": 0, "keyword": "Given", "text": "Değer: {{val}}"}
        ])
        ds_id = create_test_data(
            project_id,
            columns=[{"name": "val"}],
            rows=[{"val": "A"}, {"val": "B"}],
        )
        client.post(
            f"/api/v1/tspm/projects/{project_id}/scenarios/{sid}/bind-data",
            json={"data_set_id": ds_id, "parameter_mapping": {"val": "val"}},
            headers=auth_headers,
        )
        r = client.get(
            f"/api/v1/tspm/projects/{project_id}/scenarios/{sid}/expanded",
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert len(r.json()["expanded_rows"]) == 2
