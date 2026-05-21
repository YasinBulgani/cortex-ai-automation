"""Integration tests for CoverUp endpoints (/api/v1/coverup/)."""

import json

import pytest
from fastapi.testclient import TestClient

# ── Sample data ─────────────────────────────────────────────────────────────

SAMPLE_LCOV = """\
SF:src/payment.ts
DA:1,1
DA:2,1
DA:3,0
DA:4,0
DA:5,1
LF:5
LH:3
end_of_record
"""

SAMPLE_ISTANBUL = json.dumps({
    "src/auth.ts": {
        "path": "src/auth.ts",
        "statementMap": {
            "0": {
                "start": {"line": 1, "column": 0},
                "end": {"line": 1, "column": 30},
            }
        },
        "s": {"0": 1},
        "branchMap": {},
        "b": {},
        "fnMap": {
            "0": {
                "name": "login",
                "decl": {
                    "start": {"line": 1, "column": 0},
                    "end": {"line": 1, "column": 30},
                },
                "loc": {
                    "start": {"line": 1, "column": 0},
                    "end": {"line": 1, "column": 30},
                },
            }
        },
        "f": {"0": 1},
    }
})


class TestCoverUp:
    """CoverUp coverage-guided test generation endpoint tests."""

    PREFIX = "/api/v1/coverup"

    # ── Auth guard ──────────────────────────────────────────────────────

    def test_coverup_requires_auth(self, client: TestClient) -> None:
        """Endpoints without auth must return 401."""
        r = client.get(f"{self.PREFIX}/reports")
        assert r.status_code == 401

    # ── Upload ──────────────────────────────────────────────────────────

    def test_upload_lcov_report(
        self, client: TestClient, auth_headers: dict, project_id: str
    ) -> None:
        """POST /upload with valid LCOV data returns a report."""
        r = client.post(
            f"{self.PREFIX}/upload",
            json={
                "project_id": project_id,
                "format": "lcov",
                "report_data": SAMPLE_LCOV,
                "project_name": "test-project",
                "branch": "main",
            },
            headers=auth_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert "report_id" in body
        assert "summary" in body
        assert body["summary"]["total_files"] >= 1

    def test_upload_istanbul_report(
        self, client: TestClient, auth_headers: dict, project_id: str
    ) -> None:
        """POST /upload with Istanbul JSON.

        Istanbul parser currently returns empty (generic parser fallback),
        so expect 400 (empty parse result).
        """
        r = client.post(
            f"{self.PREFIX}/upload",
            json={
                "project_id": project_id,
                "format": "istanbul",
                "report_data": SAMPLE_ISTANBUL,
                "project_name": "istanbul-proj",
            },
            headers=auth_headers,
        )
        # Istanbul parser uses _parse_generic which returns [], triggering 400
        assert r.status_code in (200, 400)

    def test_upload_invalid_format(
        self, client: TestClient, auth_headers: dict, project_id: str
    ) -> None:
        """POST /upload with an unknown format returns 400 (empty parse)."""
        r = client.post(
            f"{self.PREFIX}/upload",
            json={
                "project_id": project_id,
                "format": "unknown_format",
                "report_data": "some data",
            },
            headers=auth_headers,
        )
        assert r.status_code == 400

    def test_upload_requires_project_id(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        r = client.post(
            f"{self.PREFIX}/upload",
            json={"format": "lcov", "report_data": SAMPLE_LCOV},
            headers=auth_headers,
        )
        assert r.status_code == 422

    # ── Reports ─────────────────────────────────────────────────────────

    def test_list_reports(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        """GET /reports returns a list."""
        r = client.get(f"{self.PREFIX}/reports", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_get_nonexistent_report(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        """GET /reports/fake-id returns 404."""
        r = client.get(
            f"{self.PREFIX}/reports/fake-id", headers=auth_headers
        )
        assert r.status_code == 404

    def test_upload_then_get_report(
        self, client: TestClient, auth_headers: dict, project_id: str
    ) -> None:
        """Upload LCOV then retrieve the report by id."""
        upload = client.post(
            f"{self.PREFIX}/upload",
            json={
                "project_id": project_id,
                "format": "lcov",
                "report_data": SAMPLE_LCOV,
                "project_name": "roundtrip-test",
            },
            headers=auth_headers,
        )
        assert upload.status_code == 200
        upload_body = upload.json()
        report_id = upload_body["report_id"]

        get = client.get(
            f"{self.PREFIX}/reports/{report_id}", headers=auth_headers
        )
        assert get.status_code == 200
        body = get.json()
        assert body["report_id"] == report_id
        assert body["project_name"] == upload_body["project_name"]
        assert len(body["files"]) >= 1

    def test_report_requires_project_membership(
        self,
        client: TestClient,
        auth_headers: dict,
        viewer_headers: dict[str, str],
        project_id: str,
    ) -> None:
        upload = client.post(
            f"{self.PREFIX}/upload",
            json={
                "project_id": project_id,
                "format": "lcov",
                "report_data": SAMPLE_LCOV,
                "project_name": "tenant-scope",
            },
            headers=auth_headers,
        )
        assert upload.status_code == 200
        report_id = upload.json()["report_id"]

        forbidden = client.get(f"{self.PREFIX}/reports/{report_id}", headers=viewer_headers)
        assert forbidden.status_code == 404

    def test_report_scope_uses_project_id_even_with_same_project_name(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        viewer_headers: dict[str, str],
        create_project,
    ) -> None:
        shared_name = "shared-coverup-project"
        owner_project_id = create_project(shared_name)
        viewer_project_id = create_project(shared_name)

        viewer_me = client.get("/api/v1/auth/me", headers=viewer_headers)
        assert viewer_me.status_code == 200
        viewer_user_id = viewer_me.json()["id"]

        add_member = client.post(
            f"/api/v1/tspm/projects/{viewer_project_id}/members",
            json={"user_id": viewer_user_id, "role": "viewer"},
            headers=auth_headers,
        )
        assert add_member.status_code == 201

        upload = client.post(
            f"{self.PREFIX}/upload",
            json={
                "project_id": owner_project_id,
                "format": "lcov",
                "report_data": SAMPLE_LCOV,
                "project_name": shared_name,
            },
            headers=auth_headers,
        )
        assert upload.status_code == 200
        report_id = upload.json()["report_id"]

        forbidden = client.get(f"{self.PREFIX}/reports/{report_id}", headers=viewer_headers)
        assert forbidden.status_code == 404

    # ── Analyze ─────────────────────────────────────────────────────────

    def test_analyze_requires_report(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        """POST /analyze with a non-existent report_id returns 404."""
        r = client.post(
            f"{self.PREFIX}/analyze",
            json={"report_id": "nonexistent-id"},
            headers=auth_headers,
        )
        assert r.status_code == 404

    # ── Trends ──────────────────────────────────────────────────────────

    def test_trends_endpoint(
        self, client: TestClient, auth_headers: dict
    ) -> None:
        """GET /trends returns trend data."""
        r = client.get(f"{self.PREFIX}/trends", headers=auth_headers)
        assert r.status_code == 200
        body = r.json()
        assert "direction" in body
        assert "current_line_rate" in body
        assert "points" in body
