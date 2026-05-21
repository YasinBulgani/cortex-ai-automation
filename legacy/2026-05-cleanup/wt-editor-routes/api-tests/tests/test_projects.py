"""TSPM Project tests."""

import pytest

from config.constants import FastAPIPaths
from helpers.data_factory import random_project_name, random_uuid


@pytest.mark.critical
class TestProjectCreate:

    def test_create_project(self, api):
        resp = api.post(
            FastAPIPaths.TSPM_PROJECTS,
            json={"name": random_project_name(), "description": "Test projesi"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert "name" in data

    @pytest.mark.negative
    def test_create_project_empty_name(self, api):
        resp = api.post(FastAPIPaths.TSPM_PROJECTS, json={"name": ""})
        assert resp.status_code == 422

    @pytest.mark.negative
    def test_create_project_missing_name(self, api):
        resp = api.post(FastAPIPaths.TSPM_PROJECTS, json={})
        assert resp.status_code == 422

    @pytest.mark.negative
    def test_create_project_no_auth(self, api_noauth):
        resp = api_noauth.post(
            FastAPIPaths.TSPM_PROJECTS, json={"name": random_project_name()}
        )
        assert resp.status_code in (401, 403)


class TestProjectList:

    def test_list_projects(self, api):
        resp = api.get(FastAPIPaths.TSPM_PROJECTS)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestProjectDashboard:

    def test_dashboard_existing_project(self, api, project_id):
        path = FastAPIPaths.TSPM_PROJECT_DASHBOARD.format(project_id=project_id)
        resp = api.get(path)
        assert resp.status_code == 200
        data = resp.json()
        assert "scenario_count" in data
        assert "pending_approvals" in data
        assert "execution_count" in data

    @pytest.mark.negative
    def test_dashboard_nonexistent_project(self, api):
        path = FastAPIPaths.TSPM_PROJECT_DASHBOARD.format(project_id=random_uuid())
        resp = api.get(path)
        assert resp.status_code == 404
