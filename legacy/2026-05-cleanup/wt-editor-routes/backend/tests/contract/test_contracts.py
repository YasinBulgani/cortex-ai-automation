"""API Contract Tests: validates response schemas, status codes, and formats.

Each test verifies that the API response conforms to the documented contract
(field presence, types, HTTP codes) without testing business logic.
"""

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_uuid(val: str) -> bool:
    parts = val.split("-")
    return len(parts) == 5 and all(parts)


def _is_iso_datetime(val) -> bool:
    if val is None:
        return True
    return isinstance(val, str) and ("T" in val or "Z" in val or "+" in val)


# ---------------------------------------------------------------------------
# Auth contracts
# ---------------------------------------------------------------------------

class TestAuthContract:

    def test_login_response_shape(self, client: TestClient, db_ready):
        r = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "admin123"},
        )
        body = r.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert isinstance(body["access_token"], str)

    def test_me_response_shape(self, client: TestClient, auth_headers):
        r = client.get("/api/v1/auth/me", headers=auth_headers)
        body = r.json()
        assert isinstance(body["id"], str)
        assert isinstance(body["email"], str)
        assert isinstance(body["roles"], list)
        assert isinstance(body["permissions"], list)

    def test_401_response_shape(self, client: TestClient, db_ready):
        r = client.post("/api/v1/auth/login", json={"email": "x@x.com", "password": "x"})
        assert r.status_code == 401
        assert "detail" in r.json()

    def test_422_response_shape(self, client: TestClient):
        r = client.post("/api/v1/auth/login", json={"email": "", "password": ""})
        assert r.status_code == 422
        body = r.json()
        assert "detail" in body
        assert isinstance(body["detail"], list)


# ---------------------------------------------------------------------------
# Project contracts
# ---------------------------------------------------------------------------

class TestProjectContract:

    def test_project_list_is_array(self, client: TestClient, auth_headers):
        r = client.get("/api/v1/tspm/projects", headers=auth_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_project_create_shape(self, client: TestClient, auth_headers):
        r = client.post(
            "/api/v1/tspm/projects",
            json={"name": "Contract Test"},
            headers=auth_headers,
        )
        assert r.status_code == 201
        body = r.json()
        assert _is_uuid(body["id"])
        assert isinstance(body["name"], str)
        assert isinstance(body["archived"], bool)
        assert body["archived"] is False


# ---------------------------------------------------------------------------
# Scenario contracts
# ---------------------------------------------------------------------------

class TestScenarioContract:

    @pytest.fixture(autouse=True)
    def _setup(self, client, auth_headers):
        r = client.post(
            "/api/v1/tspm/projects",
            json={"name": "Scenario Contract Proj"},
            headers=auth_headers,
        )
        self.pid = r.json()["id"]
        self.client = client
        self.headers = auth_headers

    def test_scenario_create_shape(self):
        r = self.client.post(
            f"/api/v1/tspm/projects/{self.pid}/scenarios",
            json={"title": "Contract Scenario"},
            headers=self.headers,
        )
        assert r.status_code == 201
        body = r.json()
        assert _is_uuid(body["id"])
        assert body["status"] == "draft"
        assert body["current_version"] == 1
        assert isinstance(body.get("steps"), (list, type(None)))

    def test_scenario_list_is_array(self):
        r = self.client.get(
            f"/api/v1/tspm/projects/{self.pid}/scenarios",
            headers=self.headers,
        )
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_404_response_has_detail(self):
        r = self.client.get(
            f"/api/v1/tspm/projects/{self.pid}/scenarios/00000000-0000-0000-0000-000000000000",
            headers=self.headers,
        )
        assert r.status_code == 404
        assert "detail" in r.json()


# ---------------------------------------------------------------------------
# Execution contracts
# ---------------------------------------------------------------------------

class TestExecutionContract:

    @pytest.fixture(autouse=True)
    def _setup(self, client, auth_headers):
        r = client.post(
            "/api/v1/tspm/projects",
            json={"name": "Exec Contract Proj"},
            headers=auth_headers,
        )
        self.pid = r.json()["id"]
        self.client = client
        self.headers = auth_headers

    def test_execution_create_shape(self):
        r = self.client.post(
            f"/api/v1/tspm/projects/{self.pid}/executions",
            json={"name": "Contract Run", "scenario_ids": []},
            headers=self.headers,
        )
        body = r.json()
        assert r.status_code == 201
        assert body["status"] == "running"
        assert isinstance(body["scenario_total"], int)
        assert isinstance(body["passed_count"], int)
        assert isinstance(body["failed_count"], int)

    def test_execution_detail_shape(self):
        ex = self.client.post(
            f"/api/v1/tspm/projects/{self.pid}/executions",
            json={"name": "Detail Run", "scenario_ids": []},
            headers=self.headers,
        )
        eid = ex.json()["id"]
        r = self.client.get(
            f"/api/v1/tspm/projects/{self.pid}/executions/{eid}",
            headers=self.headers,
        )
        body = r.json()
        assert isinstance(body["results"], list)
        assert "name" in body
        assert "status" in body


# ---------------------------------------------------------------------------
# Dashboard contract
# ---------------------------------------------------------------------------

class TestDashboardContract:

    def test_dashboard_shape(self, client: TestClient, auth_headers):
        r = client.post(
            "/api/v1/tspm/projects",
            json={"name": "Dash Contract"},
            headers=auth_headers,
        )
        pid = r.json()["id"]
        dash = client.get(
            f"/api/v1/tspm/projects/{pid}/dashboard",
            headers=auth_headers,
        )
        body = dash.json()
        for field in ("scenario_count", "pending_approvals", "import_count",
                      "execution_count", "latest_run_pass_rate"):
            assert field in body


# ---------------------------------------------------------------------------
# Coverage matrix contract
# ---------------------------------------------------------------------------

class TestCoverageContract:

    def test_coverage_matrix_shape(self, client: TestClient, auth_headers):
        r = client.post(
            "/api/v1/tspm/projects",
            json={"name": "Cov Contract"},
            headers=auth_headers,
        )
        pid = r.json()["id"]
        cov = client.get(
            f"/api/v1/tspm/projects/{pid}/coverage-matrix",
            headers=auth_headers,
        )
        body = cov.json()
        assert "total_requirements" in body
        assert "covered_count" in body
        assert "coverage_percent" in body
        assert isinstance(body["rows"], list)


# ---------------------------------------------------------------------------
# Regression set contract
# ---------------------------------------------------------------------------

class TestRegressionContract:

    def test_regression_set_create_shape(self, client: TestClient, auth_headers):
        r = client.post(
            "/api/v1/tspm/projects",
            json={"name": "Reg Contract"},
            headers=auth_headers,
        )
        pid = r.json()["id"]
        rs = client.post(
            f"/api/v1/tspm/projects/{pid}/regression-sets",
            json={"name": "Contract Set"},
            headers=auth_headers,
        )
        body = rs.json()
        assert rs.status_code == 201
        assert "scenario_count" in body
        assert body["scenario_count"] == 0


# ---------------------------------------------------------------------------
# Schedule contract
# ---------------------------------------------------------------------------

class TestScheduleContract:

    def test_schedule_create_shape(self, client: TestClient, auth_headers):
        r = client.post(
            "/api/v1/tspm/projects",
            json={"name": "Sched Contract"},
            headers=auth_headers,
        )
        pid = r.json()["id"]
        sc = client.post(
            f"/api/v1/tspm/projects/{pid}/schedules",
            json={"name": "Cron", "cron_expression": "0 * * * *"},
            headers=auth_headers,
        )
        body = sc.json()
        assert sc.status_code == 201
        assert body["is_active"] is True
        assert "cron_expression" in body


# ---------------------------------------------------------------------------
# General API contracts
# ---------------------------------------------------------------------------

class TestGeneralContract:

    def test_health_endpoint(self, client: TestClient):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_all_responses_are_json(self, client: TestClient, auth_headers):
        for path in ["/api/v1/tspm/projects", "/health", "/ready"]:
            r = client.get(path, headers=auth_headers)
            assert r.headers.get("content-type", "").startswith("application/json")

    def test_404_returns_json(self, client: TestClient, auth_headers):
        r = client.get("/api/v1/tspm/projects/nonexistent/dashboard", headers=auth_headers)
        assert r.status_code == 404
        assert "detail" in r.json()
