"""Tests for Rules (RuleSet) CRUD — /api/v1/datasets/{id}/rule-sets endpoints."""

from fastapi.testclient import TestClient


class TestRuleSetList:

    def test_list_rule_sets_for_dataset(self, client: TestClient, auth_headers):
        ds = client.post(
            "/api/v1/datasets",
            json={"name": "Rules DS"},
            headers=auth_headers,
        )
        ds_id = ds.json()["id"]
        r = client.get(f"/api/v1/datasets/{ds_id}/rule-sets", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_rule_sets_for_nonexistent_dataset_returns_404(
        self, client: TestClient, auth_headers
    ):
        r = client.get(
            "/api/v1/datasets/00000000-0000-0000-0000-000000000000/rule-sets",
            headers=auth_headers,
        )
        assert r.status_code == 404


class TestRuleSetCreate:

    def test_create_rule_set(self, client: TestClient, auth_headers):
        ds = client.post(
            "/api/v1/datasets",
            json={"name": "RuleCreate DS"},
            headers=auth_headers,
        )
        ds_id = ds.json()["id"]
        r = client.post(
            f"/api/v1/datasets/{ds_id}/rule-sets",
            json={
                "name": "Test Rules",
                "rules_body": '{"type": "range", "min": 0, "max": 100}',
            },
            headers=auth_headers,
        )
        assert r.status_code == 201
        assert r.json()["name"] == "Test Rules"

    def test_create_rule_set_requires_auth(self, client: TestClient):
        r = client.post(
            "/api/v1/datasets/fake/rule-sets",
            json={"name": "No Auth"},
        )
        assert r.status_code == 401
