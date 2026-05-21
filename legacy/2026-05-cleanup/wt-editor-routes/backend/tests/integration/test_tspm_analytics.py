"""TSPM analytics and data-flow integration tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


class _RequiresDb:
    @pytest.fixture(autouse=True)
    def _require_db(self, db_ready: bool) -> None:
        if not db_ready:
            pytest.skip("DB yok")


class TestDashboardsAndAnalytics(_RequiresDb):
    PREFIX = "/api/v1/tspm"

    def test_global_dashboard_includes_created_project(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        create_project,
    ) -> None:
        project_id = create_project("Global Dashboard Project")
        r = client.get(f"{self.PREFIX}/dashboard/global", headers=auth_headers)
        assert r.status_code == 200
        ids = [item["id"] for item in r.json()["projects"]]
        assert project_id in ids

    def test_project_dashboard_counts_scenarios_and_executions(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        create_scenario,
    ) -> None:
        scenario_id = create_scenario(project_id, "Dashboard Senaryo")
        execution = client.post(
            f"{self.PREFIX}/projects/{project_id}/executions",
            json={"name": "Dashboard Run", "scenario_ids": [scenario_id]},
            headers=auth_headers,
        )
        assert execution.status_code == 201

        r = client.get(
            f"{self.PREFIX}/projects/{project_id}/dashboard",
            headers=auth_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["scenario_count"] >= 1
        assert body["execution_count"] >= 1

    def test_execution_trends_endpoint_returns_shape(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
    ) -> None:
        r = client.get(
            f"{self.PREFIX}/projects/{project_id}/execution-trends?days=14",
            headers=auth_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["days"] == 14
        assert "data_points" in body

    def test_execution_stats_reflect_created_execution(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        create_scenario,
    ) -> None:
        scenario_id = create_scenario(project_id, "Stats Senaryo")
        create = client.post(
            f"{self.PREFIX}/projects/{project_id}/executions",
            json={"name": "Stats Run", "scenario_ids": [scenario_id]},
            headers=auth_headers,
        )
        assert create.status_code == 201

        stats = client.get(
            f"{self.PREFIX}/projects/{project_id}/execution-stats",
            headers=auth_headers,
        )
        assert stats.status_code == 200
        body = stats.json()
        assert body["total_executions"] >= 1
        assert body["total_scenarios_run"] >= 1

    def test_flaky_tests_detects_status_flips(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        create_scenario,
    ) -> None:
        scenario_id = create_scenario(project_id, "Flaky Senaryo")
        statuses = ["passed", "failed", "passed"]

        for index, status in enumerate(statuses, start=1):
            create = client.post(
                f"{self.PREFIX}/projects/{project_id}/executions",
                json={"name": f"Flaky Run {index}", "scenario_ids": [scenario_id]},
                headers=auth_headers,
            )
            assert create.status_code == 201
            execution_id = create.json()["id"]

            detail = client.get(
                f"{self.PREFIX}/projects/{project_id}/executions/{execution_id}",
                headers=auth_headers,
            )
            result_id = detail.json()["results"][0]["id"]
            patch = client.patch(
                f"{self.PREFIX}/projects/{project_id}/executions/{execution_id}/results/{result_id}",
                json={"status": status},
                headers=auth_headers,
            )
            assert patch.status_code == 200

        flaky = client.get(
            f"{self.PREFIX}/projects/{project_id}/flaky-tests",
            headers=auth_headers,
        )
        assert flaky.status_code == 200
        matched = [item for item in flaky.json() if item["scenario_id"] == scenario_id]
        assert matched
        assert matched[0]["flip_count"] >= 1


class TestCoverageImportsAndTestData(_RequiresDb):
    PREFIX = "/api/v1/tspm"

    def test_coverage_matrix_aggregates_linked_requirements(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        create_scenario,
        create_requirement,
    ) -> None:
        scenario_id = create_scenario(project_id, "Coverage Senaryosu")
        req1 = create_requirement(project_id, external_id="COV-1")
        req2 = create_requirement(project_id, external_id="COV-2")
        client.post(
            f"{self.PREFIX}/projects/{project_id}/scenarios/{scenario_id}/requirements",
            json={"requirement_ids": [req1]},
            headers=auth_headers,
        )

        matrix = client.get(
            f"{self.PREFIX}/projects/{project_id}/coverage-matrix",
            headers=auth_headers,
        )
        assert matrix.status_code == 200
        body = matrix.json()
        assert body["total_requirements"] >= 2
        assert body["covered_count"] >= 1
        rows = [row for row in body["rows"] if row["requirement_id"] == req1]
        assert rows and scenario_id in rows[0]["scenario_ids"]

    def test_coverage_gaps_lists_uncovered_requirement(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        create_requirement,
    ) -> None:
        requirement_id = create_requirement(project_id, external_id="GAP-REQ-1")
        r = client.get(
            f"{self.PREFIX}/projects/{project_id}/coverage-gaps",
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert requirement_id in [item["id"] for item in r.json()]

    def test_create_import_record(
        self, client: TestClient, auth_headers: dict[str, str], project_id: str
    ) -> None:
        r = client.post(
            f"{self.PREFIX}/projects/{project_id}/imports",
            json={"filename": "manual-tests.txt", "raw_text": "1. Login\n2. Logout"},
            headers=auth_headers,
        )
        assert r.status_code == 201
        body = r.json()
        assert body["filename"] == "manual-tests.txt"
        assert body["status"] == "completed"

    def test_create_test_data_set(
        self, client: TestClient, auth_headers: dict[str, str], project_id: str
    ) -> None:
        r = client.post(
            f"{self.PREFIX}/projects/{project_id}/test-data",
            json={
                "name": "Login Data",
                "columns": [{"name": "username"}, {"name": "password"}],
                "rows": [{"username": "u1", "password": "p1"}],
            },
            headers=auth_headers,
        )
        assert r.status_code == 201
        assert r.json()["name"] == "Login Data"

    def test_list_test_data_contains_created_dataset(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        create_test_data,
    ) -> None:
        data_id = create_test_data(project_id, name="List Data")
        r = client.get(
            f"{self.PREFIX}/projects/{project_id}/test-data",
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert data_id in [item["id"] for item in r.json()]

    def test_update_test_data_dataset(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        create_test_data,
    ) -> None:
        data_id = create_test_data(project_id, name="Update Data")
        r = client.put(
            f"{self.PREFIX}/projects/{project_id}/test-data/{data_id}",
            json={"name": "Updated Data", "rows": [{"col1": "updated"}]},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["name"] == "Updated Data"

    def test_delete_test_data_dataset(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        create_test_data,
    ) -> None:
        data_id = create_test_data(project_id, name="Delete Data")
        delete = client.delete(
            f"{self.PREFIX}/projects/{project_id}/test-data/{data_id}",
            headers=auth_headers,
        )
        assert delete.status_code == 204

        listing = client.get(
            f"{self.PREFIX}/projects/{project_id}/test-data",
            headers=auth_headers,
        )
        assert data_id not in [item["id"] for item in listing.json()]

    def test_update_missing_test_data_returns_404(
        self, client: TestClient, auth_headers: dict[str, str], project_id: str
    ) -> None:
        r = client.put(
            f"{self.PREFIX}/projects/{project_id}/test-data/00000000-0000-0000-0000-000000000000",
            json={"name": "Nope"},
            headers=auth_headers,
        )
        assert r.status_code == 404

    def test_bind_data_to_scenario(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        create_scenario,
        create_test_data,
    ) -> None:
        scenario_id = create_scenario(
            project_id,
            "Data Binding Scenario",
            steps=[{"order": 0, "keyword": "Given", "text": "Kullanici {{kullanici}}"}],
        )
        data_id = create_test_data(project_id)

        r = client.post(
            f"{self.PREFIX}/projects/{project_id}/scenarios/{scenario_id}/bind-data",
            json={"data_set_id": data_id, "parameter_mapping": {"kullanici": "col1"}},
            headers=auth_headers,
        )
        assert r.status_code == 201

    def test_bind_missing_dataset_returns_404(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        create_scenario,
    ) -> None:
        scenario_id = create_scenario(project_id, "Missing Data Binding")
        r = client.post(
            f"{self.PREFIX}/projects/{project_id}/scenarios/{scenario_id}/bind-data",
            json={"data_set_id": "00000000-0000-0000-0000-000000000000"},
            headers=auth_headers,
        )
        assert r.status_code == 404

    def test_expanded_scenario_materializes_all_rows(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        create_scenario,
        create_test_data,
    ) -> None:
        scenario_id = create_scenario(
            project_id,
            "Expanded Scenario",
            steps=[{"order": 0, "keyword": "Given", "text": "Deger {{val}}"}],
        )
        data_id = create_test_data(
            project_id,
            columns=[{"name": "val"}],
            rows=[{"val": "A"}, {"val": "B"}],
        )
        bind = client.post(
            f"{self.PREFIX}/projects/{project_id}/scenarios/{scenario_id}/bind-data",
            json={"data_set_id": data_id, "parameter_mapping": {"val": "val"}},
            headers=auth_headers,
        )
        assert bind.status_code == 201

        r = client.get(
            f"{self.PREFIX}/projects/{project_id}/scenarios/{scenario_id}/expanded",
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert len(r.json()["expanded_rows"]) == 2
