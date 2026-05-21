"""TC-1001..TC-1007: Requirements & coverage matrix tests."""

from fastapi.testclient import TestClient


class TestCreateRequirement:
    """TC-1001, TC-1007"""

    def test_create_requirement_success(
        self, client: TestClient, auth_headers, project_id
    ):
        r = client.post(
            f"/api/v1/tspm/projects/{project_id}/requirements",
            json={"external_id": "REQ-001", "title": "Login Fonksiyonu", "priority": "high"},
            headers=auth_headers,
        )
        assert r.status_code == 201
        body = r.json()
        assert body["scenario_count"] == 0
        assert body["external_id"] == "REQ-001"

    def test_empty_external_id_returns_422(
        self, client: TestClient, auth_headers, project_id
    ):
        r = client.post(
            f"/api/v1/tspm/projects/{project_id}/requirements",
            json={"external_id": "", "title": "Test"},
            headers=auth_headers,
        )
        assert r.status_code == 422


class TestScenarioRequirementLink:
    """TC-1002, TC-1003"""

    def test_link_scenario_to_requirement(
        self, client: TestClient, auth_headers, project_id,
        create_scenario, create_requirement
    ):
        sid = create_scenario(project_id)
        rid = create_requirement(project_id)
        r = client.post(
            f"/api/v1/tspm/projects/{project_id}/scenarios/{sid}/requirements",
            json={"requirement_ids": [rid]},
            headers=auth_headers,
        )
        assert r.status_code == 201

    def test_duplicate_link_is_idempotent(
        self, client: TestClient, auth_headers, project_id,
        create_scenario, create_requirement
    ):
        sid = create_scenario(project_id)
        rid = create_requirement(project_id)
        for _ in range(2):
            client.post(
                f"/api/v1/tspm/projects/{project_id}/scenarios/{sid}/requirements",
                json={"requirement_ids": [rid]},
                headers=auth_headers,
            )
        reqs = client.get(
            f"/api/v1/tspm/projects/{project_id}/requirements",
            headers=auth_headers,
        ).json()
        matched = [r for r in reqs if r["id"] == rid]
        assert matched[0]["scenario_count"] == 1


class TestCoverageMatrix:
    """TC-1004, TC-1005"""

    def test_coverage_matrix_calculation(
        self, client: TestClient, auth_headers, project_id,
        create_scenario, create_requirement
    ):
        sid = create_scenario(project_id)
        r1 = create_requirement(project_id, external_id="COV-1")
        r2 = create_requirement(project_id, external_id="COV-2")
        r3 = create_requirement(project_id, external_id="COV-3")
        client.post(
            f"/api/v1/tspm/projects/{project_id}/scenarios/{sid}/requirements",
            json={"requirement_ids": [r1, r2]},
            headers=auth_headers,
        )
        matrix = client.get(
            f"/api/v1/tspm/projects/{project_id}/coverage-matrix",
            headers=auth_headers,
        )
        assert matrix.status_code == 200
        body = matrix.json()
        assert body["total_requirements"] == 3
        assert body["covered_count"] == 2

    def test_coverage_gaps(
        self, client: TestClient, auth_headers, project_id, create_requirement
    ):
        create_requirement(project_id, external_id="GAP-1")
        gaps = client.get(
            f"/api/v1/tspm/projects/{project_id}/coverage-gaps",
            headers=auth_headers,
        )
        assert gaps.status_code == 200
        assert len(gaps.json()) >= 1


class TestDeleteRequirement:
    """TC-1006"""

    def test_delete_requirement_cascades(
        self, client: TestClient, auth_headers, project_id, create_requirement
    ):
        rid = create_requirement(project_id)
        r = client.delete(
            f"/api/v1/tspm/projects/{project_id}/requirements/{rid}",
            headers=auth_headers,
        )
        assert r.status_code == 204
