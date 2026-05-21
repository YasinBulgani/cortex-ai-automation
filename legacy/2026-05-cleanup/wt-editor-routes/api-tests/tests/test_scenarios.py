"""TSPM Scenario CRUD, BDD generation, and bulk operations."""

import pytest

from config.constants import FastAPIPaths
from helpers.data_factory import random_scenario_title, random_uuid


@pytest.mark.scenarios
class TestScenarioCreate:

    def test_create_scenario_minimal(self, api, project_id):
        path = FastAPIPaths.TSPM_SCENARIOS.format(project_id=project_id)
        resp = api.post(path, json={"title": random_scenario_title()})
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert data["status"] == "draft"

    def test_create_scenario_with_all_fields(self, api, project_id):
        path = FastAPIPaths.TSPM_SCENARIOS.format(project_id=project_id)
        resp = api.post(path, json={
            "title": random_scenario_title(),
            "description": "Detaylı açıklama",
            "status": "draft",
            "steps": [{"action": "given", "text": "kullanıcı giriş yapmış"}],
        })
        assert resp.status_code == 201

    @pytest.mark.negative
    def test_create_scenario_empty_title(self, api, project_id):
        path = FastAPIPaths.TSPM_SCENARIOS.format(project_id=project_id)
        resp = api.post(path, json={"title": ""})
        assert resp.status_code == 422

    @pytest.mark.negative
    def test_create_scenario_missing_title(self, api, project_id):
        path = FastAPIPaths.TSPM_SCENARIOS.format(project_id=project_id)
        resp = api.post(path, json={"description": "no title"})
        assert resp.status_code == 422

    @pytest.mark.negative
    def test_create_scenario_invalid_project(self, api):
        path = FastAPIPaths.TSPM_SCENARIOS.format(project_id=random_uuid())
        resp = api.post(path, json={"title": "test"})
        assert resp.status_code == 404


@pytest.mark.scenarios
class TestScenarioList:

    def test_list_scenarios(self, api, project_id):
        path = FastAPIPaths.TSPM_SCENARIOS.format(project_id=project_id)
        resp = api.get(path)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_search_scenarios_with_query(self, api, project_id):
        title = random_scenario_title()
        path = FastAPIPaths.TSPM_SCENARIOS.format(project_id=project_id)
        api.post(path, json={"title": title})
        resp = api.get(path, params={"q": title[:10]})
        assert resp.status_code == 200


@pytest.mark.scenarios
class TestScenarioUpdate:

    def test_update_scenario_title(self, api, project_id):
        list_path = FastAPIPaths.TSPM_SCENARIOS.format(project_id=project_id)
        create_resp = api.post(list_path, json={"title": random_scenario_title()})
        scenario_id = create_resp.json()["id"]

        detail_path = FastAPIPaths.TSPM_SCENARIO_DETAIL.format(
            project_id=project_id, scenario_id=scenario_id
        )
        resp = api.put(detail_path, json={"title": "Güncellenmiş Başlık"})
        assert resp.status_code == 200
        assert resp.json()["title"] == "Güncellenmiş Başlık"

    def test_update_scenario_status(self, api, project_id):
        list_path = FastAPIPaths.TSPM_SCENARIOS.format(project_id=project_id)
        create_resp = api.post(list_path, json={"title": random_scenario_title()})
        scenario_id = create_resp.json()["id"]

        detail_path = FastAPIPaths.TSPM_SCENARIO_DETAIL.format(
            project_id=project_id, scenario_id=scenario_id
        )
        resp = api.put(detail_path, json={"status": "approved"})
        assert resp.status_code == 200

    @pytest.mark.negative
    def test_update_nonexistent_scenario(self, api, project_id):
        path = FastAPIPaths.TSPM_SCENARIO_DETAIL.format(
            project_id=project_id, scenario_id=random_uuid()
        )
        resp = api.put(path, json={"title": "X"})
        assert resp.status_code == 404


@pytest.mark.scenarios
class TestScenarioBulkDelete:

    def test_bulk_delete_scenarios(self, api, project_id):
        list_path = FastAPIPaths.TSPM_SCENARIOS.format(project_id=project_id)
        ids = []
        for _ in range(3):
            r = api.post(list_path, json={"title": random_scenario_title()})
            ids.append(r.json()["id"])

        delete_path = FastAPIPaths.TSPM_SCENARIOS_BULK_DELETE.format(project_id=project_id)
        resp = api.post(delete_path, json={"ids": ids})
        assert resp.status_code == 204

    def test_bulk_delete_nonexistent_ids(self, api, project_id):
        delete_path = FastAPIPaths.TSPM_SCENARIOS_BULK_DELETE.format(project_id=project_id)
        resp = api.post(delete_path, json={"ids": [random_uuid()]})
        assert resp.status_code in (204, 404)


@pytest.mark.scenarios
@pytest.mark.ai
class TestBddGeneration:

    def test_generate_bdd_valid(self, api, project_id):
        path = FastAPIPaths.TSPM_SCENARIOS_GENERATE_BDD.format(project_id=project_id)
        resp = api.post(path, json={
            "analysis_text": "Kullanıcı sisteme email ve şifre ile giriş yapabilmeli. Başarısız girişlerde hata mesajı gösterilmeli.",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "scenarios" in data

    @pytest.mark.negative
    def test_generate_bdd_short_text(self, api, project_id):
        path = FastAPIPaths.TSPM_SCENARIOS_GENERATE_BDD.format(project_id=project_id)
        resp = api.post(path, json={"analysis_text": "kısa"})
        assert resp.status_code == 422

    @pytest.mark.boundary
    def test_generate_bdd_exactly_10_chars(self, api, project_id):
        path = FastAPIPaths.TSPM_SCENARIOS_GENERATE_BDD.format(project_id=project_id)
        resp = api.post(path, json={"analysis_text": "1234567890"})
        assert resp.status_code in (200, 500)

    @pytest.mark.negative
    def test_generate_bdd_empty_text(self, api, project_id):
        path = FastAPIPaths.TSPM_SCENARIOS_GENERATE_BDD.format(project_id=project_id)
        resp = api.post(path, json={"analysis_text": ""})
        assert resp.status_code == 422
