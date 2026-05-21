"""TSPM advanced integration flows: bulk scenario ops, flows, regression sets, schedules, members."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


class _RequiresDb:
    @pytest.fixture(autouse=True)
    def _require_db(self, db_ready: bool) -> None:
        if not db_ready:
            pytest.skip("DB yok")


def _current_user_id(client: TestClient, auth_headers: dict[str, str]) -> str:
    me = client.get("/api/v1/auth/me", headers=auth_headers)
    assert me.status_code == 200
    return me.json()["id"]


class TestAdvancedScenarioOps(_RequiresDb):
    PREFIX = "/api/v1/tspm"

    def test_bulk_delete_removes_selected_scenarios(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        create_scenario,
    ) -> None:
        s1 = create_scenario(project_id, "Silinecek 1")
        s2 = create_scenario(project_id, "Silinecek 2")
        survivor = create_scenario(project_id, "Kalacak")

        r = client.post(
            f"{self.PREFIX}/projects/{project_id}/scenarios/bulk-delete",
            json={"ids": [s1, s2]},
            headers=auth_headers,
        )
        assert r.status_code == 204

        listing = client.get(
            f"{self.PREFIX}/projects/{project_id}/scenarios",
            headers=auth_headers,
        )
        assert listing.status_code == 200
        ids = [item["id"] for item in listing.json()]
        assert survivor in ids
        assert s1 not in ids
        assert s2 not in ids

    def test_bulk_delete_ignores_foreign_project_ids(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        create_project,
        create_scenario,
    ) -> None:
        p1 = create_project("Bulk Delete P1")
        p2 = create_project("Bulk Delete P2")
        foreign = create_scenario(p2, "Yabanci")

        r = client.post(
            f"{self.PREFIX}/projects/{p1}/scenarios/bulk-delete",
            json={"ids": [foreign]},
            headers=auth_headers,
        )
        assert r.status_code == 204

        check = client.get(
            f"{self.PREFIX}/projects/{p2}/scenarios/{foreign}",
            headers=auth_headers,
        )
        assert check.status_code == 200


class TestFlows(_RequiresDb):
    PREFIX = "/api/v1/tspm"

    def test_create_flow(self, client: TestClient, auth_headers: dict[str, str], project_id: str) -> None:
        r = client.post(
            f"{self.PREFIX}/projects/{project_id}/flows",
            json={"name": "Login Flow", "description": "Mutlu yol"},
            headers=auth_headers,
        )
        assert r.status_code == 201
        assert r.json()["name"] == "Login Flow"

    def test_list_flows_contains_created_flow(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        create_flow,
    ) -> None:
        flow_id = create_flow(project_id, "Liste Flow")
        r = client.get(f"{self.PREFIX}/projects/{project_id}/flows", headers=auth_headers)
        assert r.status_code == 200
        assert flow_id in [item["id"] for item in r.json()]

    def test_get_flow_detail(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        create_flow,
    ) -> None:
        flow_id = create_flow(project_id, "Detay Flow")
        r = client.get(
            f"{self.PREFIX}/projects/{project_id}/flows/{flow_id}",
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["id"] == flow_id

    def test_update_flow_graph(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        create_flow,
    ) -> None:
        flow_id = create_flow(project_id, "Graph Flow")
        r = client.put(
            f"{self.PREFIX}/projects/{project_id}/flows/{flow_id}/graph",
            json={
                "nodes": [{"id": "n1", "type": "start"}, {"id": "n2", "type": "action"}],
                "edges": [{"source": "n1", "target": "n2"}],
            },
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert len(r.json()["nodes"]) == 2
        assert len(r.json()["edges"]) == 1

    def test_create_flow_with_empty_name_returns_422(
        self, client: TestClient, auth_headers: dict[str, str], project_id: str
    ) -> None:
        r = client.post(
            f"{self.PREFIX}/projects/{project_id}/flows",
            json={"name": ""},
            headers=auth_headers,
        )
        assert r.status_code == 422


class TestRegressionSets(_RequiresDb):
    PREFIX = "/api/v1/tspm"

    def test_create_and_list_regression_set(
        self, client: TestClient, auth_headers: dict[str, str], project_id: str
    ) -> None:
        create = client.post(
            f"{self.PREFIX}/projects/{project_id}/regression-sets",
            json={"name": "Smoke Set"},
            headers=auth_headers,
        )
        assert create.status_code == 201
        set_id = create.json()["id"]

        listing = client.get(
            f"{self.PREFIX}/projects/{project_id}/regression-sets",
            headers=auth_headers,
        )
        assert listing.status_code == 200
        assert set_id in [item["id"] for item in listing.json()]

    def test_get_regression_set_detail(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        create_regression_set,
    ) -> None:
        set_id = create_regression_set(project_id, "Detail Set")
        r = client.get(
            f"{self.PREFIX}/projects/{project_id}/regression-sets/{set_id}",
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["id"] == set_id

    def test_add_scenarios_to_regression_set(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        create_scenario,
        create_regression_set,
    ) -> None:
        s1 = create_scenario(project_id, "Reg 1")
        s2 = create_scenario(project_id, "Reg 2")
        set_id = create_regression_set(project_id, "Add Set")
        r = client.post(
            f"{self.PREFIX}/projects/{project_id}/regression-sets/{set_id}/add",
            json={"scenario_ids": [s1, s2]},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["count"] == 2

    def test_duplicate_add_to_regression_set_is_idempotent(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        create_scenario,
        create_regression_set,
    ) -> None:
        scenario_id = create_scenario(project_id, "Tekrarli Reg")
        set_id = create_regression_set(project_id, "Idempotent Set")
        for _ in range(2):
            client.post(
                f"{self.PREFIX}/projects/{project_id}/regression-sets/{set_id}/add",
                json={"scenario_ids": [scenario_id]},
                headers=auth_headers,
            )
        detail = client.get(
            f"{self.PREFIX}/projects/{project_id}/regression-sets/{set_id}",
            headers=auth_headers,
        )
        assert detail.status_code == 200
        assert detail.json()["scenario_ids"] == [scenario_id]

    def test_accept_suggested_sets_creates_records(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        create_scenario,
    ) -> None:
        scenario_id = create_scenario(project_id, "Oneri Senaryosu")
        r = client.post(
            f"{self.PREFIX}/projects/{project_id}/regression-sets/accept-suggestions",
            json={"sets": [{"name": "Oneri Set", "scenario_ids": [scenario_id], "priority": "high"}]},
            headers=auth_headers,
        )
        assert r.status_code == 201
        assert len(r.json()) == 1
        assert r.json()[0]["name"] == "Oneri Set"


class TestSchedules(_RequiresDb):
    PREFIX = "/api/v1/tspm"

    def test_create_and_list_schedule(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        create_scenario,
    ) -> None:
        scenario_id = create_scenario(project_id, "Schedule Senaryo")
        create = client.post(
            f"{self.PREFIX}/projects/{project_id}/schedules",
            json={"name": "Gece Kosusu", "cron_expression": "0 2 * * *", "scenario_ids": [scenario_id]},
            headers=auth_headers,
        )
        assert create.status_code == 201
        schedule_id = create.json()["id"]

        listing = client.get(
            f"{self.PREFIX}/projects/{project_id}/schedules",
            headers=auth_headers,
        )
        assert listing.status_code == 200
        assert schedule_id in [item["id"] for item in listing.json()]

    def test_update_schedule_cron_and_toggle(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        create_schedule,
    ) -> None:
        schedule_id = create_schedule(project_id, name="Update Schedule")
        r = client.put(
            f"{self.PREFIX}/projects/{project_id}/schedules/{schedule_id}",
            json={"cron_expression": "0 3 * * *", "is_active": False},
            headers=auth_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["cron_expression"] == "0 3 * * *"
        assert body["is_active"] is False

    def test_delete_schedule_removes_it(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        create_schedule,
    ) -> None:
        schedule_id = create_schedule(project_id, name="Sil Schedule")
        delete = client.delete(
            f"{self.PREFIX}/projects/{project_id}/schedules/{schedule_id}",
            headers=auth_headers,
        )
        assert delete.status_code == 204

        listing = client.get(
            f"{self.PREFIX}/projects/{project_id}/schedules",
            headers=auth_headers,
        )
        assert listing.status_code == 200
        assert schedule_id not in [item["id"] for item in listing.json()]

    def test_trigger_schedule_creates_execution(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        create_scenario,
        create_schedule,
    ) -> None:
        scenario_id = create_scenario(project_id, "Trigger Senaryosu")
        schedule_id = create_schedule(project_id, scenario_ids=[scenario_id])
        r = client.post(
            f"{self.PREFIX}/projects/{project_id}/schedules/{schedule_id}/trigger",
            headers=auth_headers,
        )
        assert r.status_code == 201
        assert "Scheduled:" in r.json()["name"]
        assert r.json()["scenario_total"] >= 1

    def test_trigger_schedule_uses_regression_set_fallback(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        create_scenario,
        create_regression_set,
    ) -> None:
        scenario_id = create_scenario(project_id, "Fallback Senaryo")
        set_id = create_regression_set(project_id, "Fallback Set")
        add = client.post(
            f"{self.PREFIX}/projects/{project_id}/regression-sets/{set_id}/add",
            json={"scenario_ids": [scenario_id]},
            headers=auth_headers,
        )
        assert add.status_code == 200

        schedule = client.post(
            f"{self.PREFIX}/projects/{project_id}/schedules",
            json={"name": "Fallback Schedule", "cron_expression": "0 4 * * *", "regression_set_id": set_id},
            headers=auth_headers,
        )
        assert schedule.status_code == 201
        schedule_id = schedule.json()["id"]

        trigger = client.post(
            f"{self.PREFIX}/projects/{project_id}/schedules/{schedule_id}/trigger",
            headers=auth_headers,
        )
        assert trigger.status_code == 201
        assert trigger.json()["scenario_total"] >= 1

    def test_mobile_schedule_keeps_platform_fields(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        create_scenario,
    ) -> None:
        scenario_id = create_scenario(project_id, "Mobile Schedule Senaryo")
        r = client.post(
            f"{self.PREFIX}/projects/{project_id}/schedules",
            json={
                "name": "iOS Schedule",
                "cron_expression": "0 6 * * *",
                "scenario_ids": [scenario_id],
                "platform": "ios",
                "device_name": "iPhone 14",
            },
            headers=auth_headers,
        )
        assert r.status_code == 201
        assert r.json()["platform"] == "ios"
        assert r.json()["device_name"] == "iPhone 14"


class TestProjectMembers(_RequiresDb):
    PREFIX = "/api/v1/tspm"

    def test_add_list_and_remove_member(
        self, client: TestClient, auth_headers: dict[str, str], project_id: str
    ) -> None:
        user_id = _current_user_id(client, auth_headers)

        add = client.post(
            f"{self.PREFIX}/projects/{project_id}/members",
            json={"user_id": user_id, "role": "operator"},
            headers=auth_headers,
        )
        assert add.status_code == 201
        member_id = add.json()["id"]

        listing = client.get(
            f"{self.PREFIX}/projects/{project_id}/members",
            headers=auth_headers,
        )
        assert listing.status_code == 200
        ids = [item["id"] for item in listing.json()]
        assert member_id in ids

        delete = client.delete(
            f"{self.PREFIX}/projects/{project_id}/members/{member_id}",
            headers=auth_headers,
        )
        assert delete.status_code == 204

    def test_add_member_defaults_to_viewer(
        self, client: TestClient, auth_headers: dict[str, str], project_id: str
    ) -> None:
        user_id = _current_user_id(client, auth_headers)
        r = client.post(
            f"{self.PREFIX}/projects/{project_id}/members",
            json={"user_id": user_id},
            headers=auth_headers,
        )
        assert r.status_code == 201
        assert r.json()["role"] == "viewer"
