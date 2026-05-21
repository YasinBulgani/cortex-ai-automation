"""Requirements and coverage matrix tests."""

import pytest

from config.constants import FastAPIPaths
from helpers.data_factory import random_requirement, random_uuid, random_scenario_title


@pytest.mark.critical
class TestRequirementCRUD:

    def test_create_requirement(self, api, project_id):
        path = FastAPIPaths.TSPM_REQUIREMENTS.format(project_id=project_id)
        payload = random_requirement()
        resp = api.post(path, json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["external_id"] == payload["external_id"]
        assert data["title"] == payload["title"]

    def test_list_requirements(self, api, project_id):
        path = FastAPIPaths.TSPM_REQUIREMENTS.format(project_id=project_id)
        resp = api.get(path)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_update_requirement(self, api, project_id):
        path = FastAPIPaths.TSPM_REQUIREMENTS.format(project_id=project_id)
        create_resp = api.post(path, json=random_requirement())
        req_id = create_resp.json()["id"]

        update_path = FastAPIPaths.TSPM_REQUIREMENT_DETAIL.format(
            project_id=project_id, requirement_id=req_id
        )
        resp = api.put(update_path, json={"title": "Güncellenmiş Gereksinim"})
        assert resp.status_code == 200

    def test_delete_requirement(self, api, project_id):
        path = FastAPIPaths.TSPM_REQUIREMENTS.format(project_id=project_id)
        create_resp = api.post(path, json=random_requirement())
        req_id = create_resp.json()["id"]

        delete_path = FastAPIPaths.TSPM_REQUIREMENT_DETAIL.format(
            project_id=project_id, requirement_id=req_id
        )
        resp = api.delete(delete_path)
        assert resp.status_code == 204

    @pytest.mark.negative
    def test_create_requirement_empty_external_id(self, api, project_id):
        path = FastAPIPaths.TSPM_REQUIREMENTS.format(project_id=project_id)
        resp = api.post(path, json={"external_id": "", "title": "test"})
        assert resp.status_code == 422

    @pytest.mark.negative
    def test_create_requirement_empty_title(self, api, project_id):
        path = FastAPIPaths.TSPM_REQUIREMENTS.format(project_id=project_id)
        resp = api.post(path, json={"external_id": "REQ-1", "title": ""})
        assert resp.status_code == 422


class TestCoverageMatrix:

    def test_coverage_matrix(self, api, project_id):
        path = FastAPIPaths.TSPM_COVERAGE_MATRIX.format(project_id=project_id)
        resp = api.get(path)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_requirements" in data
        assert "covered_count" in data
        assert "coverage_percent" in data

    def test_coverage_gaps(self, api, project_id):
        path = FastAPIPaths.TSPM_COVERAGE_GAPS.format(project_id=project_id)
        resp = api.get(path)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestScenarioRequirementLink:

    def test_link_and_unlink(self, api, project_id):
        req_path = FastAPIPaths.TSPM_REQUIREMENTS.format(project_id=project_id)
        req_resp = api.post(req_path, json=random_requirement())
        req_id = req_resp.json()["id"]

        sc_path = FastAPIPaths.TSPM_SCENARIOS.format(project_id=project_id)
        sc_resp = api.post(sc_path, json={"title": random_scenario_title()})
        sc_id = sc_resp.json()["id"]

        link_path = FastAPIPaths.TSPM_SCENARIO_REQUIREMENTS.format(
            project_id=project_id, scenario_id=sc_id
        )
        link_resp = api.post(link_path, json={"requirement_ids": [req_id]})
        assert link_resp.status_code == 201

        unlink_path = f"{link_path}/{req_id}"
        unlink_resp = api.delete(unlink_path)
        assert unlink_resp.status_code == 204
