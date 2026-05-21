"""Execution lifecycle tests."""

import pytest

from config.constants import FastAPIPaths
from helpers.data_factory import random_scenario_title, random_uuid


@pytest.mark.executions
class TestExecutionCreate:

    def test_create_execution_empty(self, api, project_id):
        path = FastAPIPaths.TSPM_EXECUTIONS.format(project_id=project_id)
        resp = api.post(path, json={})
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["status"] in ("pending", "running", "completed")

    def test_create_execution_with_scenarios(self, api, project_id):
        sc_path = FastAPIPaths.TSPM_SCENARIOS.format(project_id=project_id)
        sc1 = api.post(sc_path, json={"title": random_scenario_title()}).json()
        sc2 = api.post(sc_path, json={"title": random_scenario_title()}).json()

        exe_path = FastAPIPaths.TSPM_EXECUTIONS.format(project_id=project_id)
        resp = api.post(exe_path, json={
            "name": "Test Run",
            "scenario_ids": [sc1["id"], sc2["id"]],
        })
        assert resp.status_code == 201

    @pytest.mark.negative
    def test_create_execution_nonexistent_project(self, api):
        path = FastAPIPaths.TSPM_EXECUTIONS.format(project_id=random_uuid())
        resp = api.post(path, json={})
        assert resp.status_code == 404


@pytest.mark.executions
class TestExecutionList:

    def test_list_executions(self, api, project_id):
        path = FastAPIPaths.TSPM_EXECUTIONS.format(project_id=project_id)
        resp = api.get(path)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


@pytest.mark.executions
class TestExecutionDetail:

    def test_get_execution_detail(self, api, project_id):
        exe_path = FastAPIPaths.TSPM_EXECUTIONS.format(project_id=project_id)
        create_resp = api.post(exe_path, json={"name": "Detail Test"})
        run_id = create_resp.json()["id"]

        detail_path = FastAPIPaths.TSPM_EXECUTION_DETAIL.format(
            project_id=project_id, run_id=run_id
        )
        resp = api.get(detail_path)
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data

    @pytest.mark.negative
    def test_get_nonexistent_execution(self, api, project_id):
        path = FastAPIPaths.TSPM_EXECUTION_DETAIL.format(
            project_id=project_id, run_id=random_uuid()
        )
        resp = api.get(path)
        assert resp.status_code == 404


@pytest.mark.executions
class TestExecutionTrends:

    def test_execution_trends_default(self, api, project_id):
        path = f"/api/v1/tspm/projects/{project_id}/execution-trends"
        resp = api.get(path)
        assert resp.status_code == 200
        data = resp.json()
        assert "data_points" in data

    @pytest.mark.boundary
    def test_execution_trends_custom_days(self, api, project_id):
        path = f"/api/v1/tspm/projects/{project_id}/execution-trends"
        resp = api.get(path, params={"days": 7})
        assert resp.status_code == 200

    def test_execution_stats(self, api, project_id):
        path = f"/api/v1/tspm/projects/{project_id}/execution-stats"
        resp = api.get(path)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_executions" in data
        assert "avg_pass_rate" in data

    def test_flaky_tests(self, api, project_id):
        path = f"/api/v1/tspm/projects/{project_id}/flaky-tests"
        resp = api.get(path)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
