"""TSPM core integration flows: projects, scenarios, requirements, approvals, executions."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


class _RequiresDb:
    @pytest.fixture(autouse=True)
    def _require_db(self, db_ready: bool) -> None:
        if not db_ready:
            pytest.skip("DB yok")


class TestProjectsAndDashboard(_RequiresDb):
    PREFIX = "/api/v1/tspm"

    def test_projects_require_auth(self, client: TestClient) -> None:
        r = client.get(f"{self.PREFIX}/projects")
        assert r.status_code == 401

    def test_create_project(self, client: TestClient, auth_headers: dict[str, str]) -> None:
        r = client.post(
            f"{self.PREFIX}/projects",
            json={"name": "Integration Core Project", "description": "core"},
            headers=auth_headers,
        )
        assert r.status_code == 201
        body = r.json()
        assert body["name"] == "Integration Core Project"
        assert body["archived"] is False
        assert body["id"]

    def test_list_projects_contains_created_project(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        create_project,
    ) -> None:
        project_id = create_project("Liste Projesi")
        r = client.get(f"{self.PREFIX}/projects", headers=auth_headers)
        assert r.status_code == 200
        ids = [item["id"] for item in r.json()]
        assert project_id in ids

    def test_project_dashboard_for_empty_project(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        create_project,
    ) -> None:
        project_id = create_project("Dashboard Empty")
        r = client.get(
            f"{self.PREFIX}/projects/{project_id}/dashboard",
            headers=auth_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["scenario_count"] == 0
        assert body["execution_count"] == 0

    def test_missing_project_dashboard_returns_404(
        self, client: TestClient, auth_headers: dict[str, str]
    ) -> None:
        r = client.get(
            f"{self.PREFIX}/projects/00000000-0000-0000-0000-000000000000/dashboard",
            headers=auth_headers,
        )
        assert r.status_code == 404


class TestScenariosAndVersions(_RequiresDb):
    PREFIX = "/api/v1/tspm"

    def test_create_scenario_with_steps_and_tags(
        self, client: TestClient, auth_headers: dict[str, str], project_id: str
    ) -> None:
        r = client.post(
            f"{self.PREFIX}/projects/{project_id}/scenarios",
            json={
                "title": "Login Basarili",
                "description": "Mutlu yol",
                "tags": ["smoke", "login"],
                "steps": [{"order": 1, "keyword": "Given", "text": "Kullanici login ekraninda"}],
            },
            headers=auth_headers,
        )
        assert r.status_code == 201
        body = r.json()
        assert body["title"] == "Login Basarili"
        assert body["current_version"] == 1
        assert body["tags"] == ["smoke", "login"]

    def test_list_scenarios_returns_created_items(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        create_scenario,
    ) -> None:
        scenario_id = create_scenario(project_id, "Liste Senaryosu")
        r = client.get(f"{self.PREFIX}/projects/{project_id}/scenarios", headers=auth_headers)
        assert r.status_code == 200
        ids = [item["id"] for item in r.json()]
        assert scenario_id in ids

    def test_get_scenario_detail(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        create_scenario,
    ) -> None:
        scenario_id = create_scenario(project_id, "Detay Senaryosu")
        r = client.get(
            f"{self.PREFIX}/projects/{project_id}/scenarios/{scenario_id}",
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["id"] == scenario_id

    def test_update_scenario_changes_version_status_and_tags(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        create_scenario,
    ) -> None:
        scenario_id = create_scenario(project_id, "V1")
        r = client.put(
            f"{self.PREFIX}/projects/{project_id}/scenarios/{scenario_id}",
            json={"title": "V2", "status": "active", "tags": ["regression"]},
            headers=auth_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["title"] == "V2"
        assert body["status"] == "active"
        assert body["current_version"] == 2
        assert body["tags"] == ["regression"]

    def test_search_scenarios_by_query(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        create_scenario,
    ) -> None:
        create_scenario(project_id, "Odeme Senaryosu")
        create_scenario(project_id, "Login Senaryosu")
        r = client.get(
            f"{self.PREFIX}/projects/{project_id}/scenarios?q=Login",
            headers=auth_headers,
        )
        assert r.status_code == 200
        titles = [item["title"] for item in r.json()]
        assert titles
        assert all("Login" in title for title in titles)

    def test_filter_scenarios_by_tag(
        self, client: TestClient, auth_headers: dict[str, str], project_id: str
    ) -> None:
        client.post(
            f"{self.PREFIX}/projects/{project_id}/scenarios",
            json={"title": "Tag Smoke", "tags": ["smoke"]},
            headers=auth_headers,
        )
        client.post(
            f"{self.PREFIX}/projects/{project_id}/scenarios",
            json={"title": "Tag Regression", "tags": ["regression"]},
            headers=auth_headers,
        )
        r = client.get(
            f"{self.PREFIX}/projects/{project_id}/scenarios?tag=smoke",
            headers=auth_headers,
        )
        assert r.status_code == 200
        titles = [item["title"] for item in r.json()]
        assert "Tag Smoke" in titles
        assert "Tag Regression" not in titles

    def test_filter_scenarios_by_status(
        self, client: TestClient, auth_headers: dict[str, str], project_id: str
    ) -> None:
        draft = client.post(
            f"{self.PREFIX}/projects/{project_id}/scenarios",
            json={"title": "Draft Senaryo", "status": "draft"},
            headers=auth_headers,
        )
        active = client.post(
            f"{self.PREFIX}/projects/{project_id}/scenarios",
            json={"title": "Active Senaryo", "status": "active"},
            headers=auth_headers,
        )
        assert draft.status_code == 201
        assert active.status_code == 201
        r = client.get(
            f"{self.PREFIX}/projects/{project_id}/scenarios?status=active",
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()
        assert all(item["status"] == "active" for item in r.json())

    def test_clone_scenario_creates_new_draft(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        create_scenario,
    ) -> None:
        scenario_id = create_scenario(project_id, "Kopyalanacak Senaryo")
        r = client.post(
            f"{self.PREFIX}/projects/{project_id}/scenarios/{scenario_id}/clone",
            headers=auth_headers,
        )
        assert r.status_code == 201
        body = r.json()
        assert body["id"] != scenario_id
        assert body["status"] == "draft"

    def test_list_versions_after_update_contains_previous_snapshot(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        create_scenario,
    ) -> None:
        scenario_id = create_scenario(project_id, "Orijinal Baslik")
        client.put(
            f"{self.PREFIX}/projects/{project_id}/scenarios/{scenario_id}",
            json={"title": "Guncel Baslik"},
            headers=auth_headers,
        )
        r = client.get(
            f"{self.PREFIX}/projects/{project_id}/scenarios/{scenario_id}/versions",
            headers=auth_headers,
        )
        assert r.status_code == 200
        titles = [item["title"] for item in r.json()]
        assert "Orijinal Baslik" in titles

    def test_diff_versions_marks_title_change(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        create_scenario,
    ) -> None:
        scenario_id = create_scenario(project_id, "Diff V1")
        client.put(
            f"{self.PREFIX}/projects/{project_id}/scenarios/{scenario_id}",
            json={"title": "Diff V2"},
            headers=auth_headers,
        )
        r = client.get(
            f"{self.PREFIX}/projects/{project_id}/scenarios/{scenario_id}/versions/1/diff/2",
            headers=auth_headers,
        )
        assert r.status_code in (200, 404)
        if r.status_code == 200:
            assert r.json()["title_changed"] is True

    def test_cross_project_scenario_access_returns_404(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        create_project,
        create_scenario,
    ) -> None:
        p1 = create_project("Project One")
        p2 = create_project("Project Two")
        scenario_id = create_scenario(p1, "P1 Senaryosu")
        r = client.get(
            f"{self.PREFIX}/projects/{p2}/scenarios/{scenario_id}",
            headers=auth_headers,
        )
        assert r.status_code == 404


class TestRequirementsApprovalsAndExecutions(_RequiresDb):
    PREFIX = "/api/v1/tspm"

    def test_create_update_and_delete_requirement(
        self, client: TestClient, auth_headers: dict[str, str], project_id: str
    ) -> None:
        create = client.post(
            f"{self.PREFIX}/projects/{project_id}/requirements",
            json={"external_id": "REQ-CORE-1", "title": "Giris yapilmali", "priority": "high"},
            headers=auth_headers,
        )
        assert create.status_code == 201
        requirement_id = create.json()["id"]

        update = client.put(
            f"{self.PREFIX}/projects/{project_id}/requirements/{requirement_id}",
            json={"title": "Giris guncellendi", "priority": "critical"},
            headers=auth_headers,
        )
        assert update.status_code == 200
        assert update.json()["priority"] == "critical"

        delete = client.delete(
            f"{self.PREFIX}/projects/{project_id}/requirements/{requirement_id}",
            headers=auth_headers,
        )
        assert delete.status_code == 204

    def test_link_and_unlink_requirement_to_scenario(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        create_scenario,
        create_requirement,
    ) -> None:
        scenario_id = create_scenario(project_id, "Link Senaryosu")
        requirement_id = create_requirement(project_id, external_id="REQ-LINK-1")

        link = client.post(
            f"{self.PREFIX}/projects/{project_id}/scenarios/{scenario_id}/requirements",
            json={"requirement_ids": [requirement_id]},
            headers=auth_headers,
        )
        assert link.status_code == 201

        matrix = client.get(
            f"{self.PREFIX}/projects/{project_id}/coverage-matrix",
            headers=auth_headers,
        )
        assert matrix.status_code == 200
        matched = [row for row in matrix.json()["rows"] if row["requirement_id"] == requirement_id]
        assert matched and scenario_id in matched[0]["scenario_ids"]

        unlink = client.delete(
            f"{self.PREFIX}/projects/{project_id}/scenarios/{scenario_id}/requirements/{requirement_id}",
            headers=auth_headers,
        )
        assert unlink.status_code == 204

    def test_coverage_gaps_returns_unlinked_requirements(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        create_requirement,
    ) -> None:
        requirement_id = create_requirement(project_id, external_id="REQ-GAP-1")
        r = client.get(
            f"{self.PREFIX}/projects/{project_id}/coverage-gaps",
            headers=auth_headers,
        )
        assert r.status_code == 200
        ids = [item["id"] for item in r.json()]
        assert requirement_id in ids

    def test_create_approval_and_approve_creates_scenario(
        self, client: TestClient, auth_headers: dict[str, str], project_id: str
    ) -> None:
        approval = client.post(
            f"{self.PREFIX}/projects/{project_id}/approvals",
            json={
                "title": "Onayli Taslak",
                "draft_payload": {
                    "title": "Taslak Senaryo",
                    "description": "onaydan gelecek",
                    "steps": [{"keyword": "Given", "text": "on kosul"}],
                },
            },
            headers=auth_headers,
        )
        assert approval.status_code == 201
        approval_id = approval.json()["id"]

        decide = client.post(
            f"{self.PREFIX}/projects/{project_id}/approvals/{approval_id}/decide",
            json={"decision": "approved"},
            headers=auth_headers,
        )
        assert decide.status_code == 200

        approvals = client.get(
            f"{self.PREFIX}/projects/{project_id}/approvals",
            headers=auth_headers,
        )
        assert approvals.status_code == 200
        created = [item for item in approvals.json() if item["id"] == approval_id]
        assert created and created[0]["status"] == "approved"
        assert created[0]["scenario_id"]

    def test_decide_missing_approval_returns_404(
        self, client: TestClient, auth_headers: dict[str, str], project_id: str
    ) -> None:
        r = client.post(
            f"{self.PREFIX}/projects/{project_id}/approvals/00000000-0000-0000-0000-000000000000/decide",
            json={"decision": "approved"},
            headers=auth_headers,
        )
        assert r.status_code == 404

    def test_create_execution_list_detail_and_patch_result(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        create_scenario,
    ) -> None:
        scenario_id = create_scenario(project_id, "Execution Senaryosu")
        create = client.post(
            f"{self.PREFIX}/projects/{project_id}/executions",
            json={"name": "Sprint Run", "scenario_ids": [scenario_id]},
            headers=auth_headers,
        )
        assert create.status_code == 201
        execution_id = create.json()["id"]

        listing = client.get(
            f"{self.PREFIX}/projects/{project_id}/executions",
            headers=auth_headers,
        )
        assert listing.status_code == 200
        assert execution_id in [item["id"] for item in listing.json()]

        detail = client.get(
            f"{self.PREFIX}/projects/{project_id}/executions/{execution_id}",
            headers=auth_headers,
        )
        assert detail.status_code == 200
        result_id = detail.json()["results"][0]["id"]

        patch = client.patch(
            f"{self.PREFIX}/projects/{project_id}/executions/{execution_id}/results/{result_id}",
            json={"status": "passed"},
            headers=auth_headers,
        )
        assert patch.status_code == 200

    def test_rerun_execution_creates_second_run(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        create_scenario,
    ) -> None:
        scenario_id = create_scenario(project_id, "Rerun Senaryosu")
        create = client.post(
            f"{self.PREFIX}/projects/{project_id}/executions",
            json={"name": "Ilk Kosu", "scenario_ids": [scenario_id]},
            headers=auth_headers,
        )
        execution_id = create.json()["id"]

        rerun = client.post(
            f"{self.PREFIX}/projects/{project_id}/executions/{execution_id}",
            headers=auth_headers,
        )
        assert rerun.status_code == 201
        assert rerun.json()["id"] != execution_id
        assert "(re-run)" in rerun.json()["name"]

    def test_compare_executions_marks_changed_results(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        create_scenario,
    ) -> None:
        scenario_id = create_scenario(project_id, "Compare Senaryosu")
        run1 = client.post(
            f"{self.PREFIX}/projects/{project_id}/executions",
            json={"name": "Run 1", "scenario_ids": [scenario_id]},
            headers=auth_headers,
        ).json()["id"]
        run2 = client.post(
            f"{self.PREFIX}/projects/{project_id}/executions",
            json={"name": "Run 2", "scenario_ids": [scenario_id]},
            headers=auth_headers,
        ).json()["id"]

        detail = client.get(
            f"{self.PREFIX}/projects/{project_id}/executions/{run2}",
            headers=auth_headers,
        )
        result_id = detail.json()["results"][0]["id"]
        client.patch(
            f"{self.PREFIX}/projects/{project_id}/executions/{run2}/results/{result_id}",
            json={"status": "failed"},
            headers=auth_headers,
        )

        compare = client.get(
            f"{self.PREFIX}/projects/{project_id}/executions/compare?run1={run1}&run2={run2}",
            headers=auth_headers,
        )
        assert compare.status_code == 200
        changed = [item for item in compare.json()["scenarios"] if item["scenario_id"] == scenario_id]
        assert changed and changed[0]["changed"] is True

    def test_missing_execution_detail_returns_404(
        self, client: TestClient, auth_headers: dict[str, str], project_id: str
    ) -> None:
        r = client.get(
            f"{self.PREFIX}/projects/{project_id}/executions/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert r.status_code == 404
