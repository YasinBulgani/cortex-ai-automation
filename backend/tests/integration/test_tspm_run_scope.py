"""Project-scope regression tests for TSPM run metrics/status endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient


class TestTspmRunScope:
    PREFIX = "/api/v1/tspm"

    def test_execution_metrics_rejects_execution_from_other_project(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        create_project,
        create_scenario,
        create_execution,
    ) -> None:
        source_project_id = create_project("run-scope-source")
        other_project_id = create_project("run-scope-other")
        scenario_id = create_scenario(source_project_id, "Run scope scenario")
        execution_id = create_execution(
            source_project_id,
            name="Run Scope Execution",
            scenario_ids=[scenario_id],
        )

        response = client.get(
            f"{self.PREFIX}/projects/{other_project_id}/executions/{execution_id}/metrics",
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_execution_metrics_requires_project_membership(
        self,
        client: TestClient,
        viewer_headers: dict[str, str],
        project_id: str,
        create_scenario,
        create_execution,
    ) -> None:
        scenario_id = create_scenario(project_id, "Viewer forbidden scenario")
        execution_id = create_execution(
            project_id,
            name="Viewer forbidden execution",
            scenario_ids=[scenario_id],
        )

        response = client.get(
            f"{self.PREFIX}/projects/{project_id}/executions/{execution_id}/metrics",
            headers=viewer_headers,
        )
        assert response.status_code == 403

    def test_run_status_requires_project_membership(
        self,
        client: TestClient,
        viewer_headers: dict[str, str],
        project_id: str,
        create_scenario,
        create_execution,
    ) -> None:
        scenario_id = create_scenario(project_id, "Run status scope scenario")
        execution_id = create_execution(
            project_id,
            name="Run status scope execution",
            scenario_ids=[scenario_id],
        )

        response = client.get(
            f"{self.PREFIX}/projects/{project_id}/executions/{execution_id}/run-status/fake-run-id",
            headers=viewer_headers,
        )
        assert response.status_code == 403
