"""Integration tests for the standalone API Testing domain router."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.domains.api_testing import service as api_testing_service
from app.domains.api_testing.request_executor import ExecutionResult, TimingBreakdown
from app.domains.tspm.models import TspmApiCollection
from app.infra.database import SessionLocal


class _RequiresDb:
    @pytest.fixture(autouse=True)
    def _require_db(self, db_ready: bool) -> None:
        if not db_ready:
            pytest.skip("DB yok")


def _prefix(project_id: str) -> str:
    return f"/api/v1/api-testing/projects/{project_id}"


def _minimal_openapi_spec() -> str:
    return json.dumps(
        {
            "openapi": "3.0.3",
            "info": {"title": "Bank API", "version": "1.0.0"},
            "security": [{"bearerAuth": []}],
            "components": {
                "securitySchemes": {
                    "bearerAuth": {"type": "http", "scheme": "bearer"}
                }
            },
            "paths": {
                "/auth/login": {
                    "post": {
                        "summary": "Login",
                        "security": [],
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "username": {"type": "string"},
                                            "password": {"type": "string"},
                                        },
                                    }
                                }
                            }
                        },
                        "responses": {"200": {"description": "ok"}},
                    }
                },
                "/accounts/{account_id}": {
                    "get": {
                        "summary": "Get account details",
                        "parameters": [
                            {
                                "name": "account_id",
                                "in": "path",
                                "required": True,
                                "schema": {"type": "string"},
                            }
                        ],
                        "responses": {"200": {"description": "ok"}},
                    }
                },
                "/payments/transfer": {
                    "post": {
                        "summary": "Transfer payment",
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "iban": {"type": "string"},
                                            "amount": {"type": "number"},
                                            "email": {"type": "string"},
                                        },
                                    }
                                }
                            }
                        },
                        "responses": {"200": {"description": "ok"}},
                    }
                },
            },
        }
    )


def _create_environment(
    client: TestClient,
    auth_headers: dict[str, str],
    project_id: str,
    *,
    name: str = "staging",
    base_url: str = "https://api.example.test",
) -> str:
    r = client.post(
        f"{_prefix(project_id)}/environments",
        json={
            "name": name,
            "variables": {"base_url": base_url, "token": "secret"},
            "sensitive_keys": ["token"],
            "is_default": True,
        },
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _import_spec(
    client: TestClient,
    auth_headers: dict[str, str],
    project_id: str,
    *,
    name: str = "Bank Spec",
) -> str:
    r = client.post(
        f"{_prefix(project_id)}/specs/import",
        json={"name": name, "content": _minimal_openapi_spec()},
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _get_spec_detail(
    client: TestClient,
    auth_headers: dict[str, str],
    project_id: str,
    spec_id: str,
) -> dict:
    r = client.get(
        f"{_prefix(project_id)}/specs/{spec_id}",
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text
    return r.json()


def _create_test_case(
    client: TestClient,
    auth_headers: dict[str, str],
    project_id: str,
    *,
    title: str = "Get account test",
    endpoint_id: str | None = None,
    request_path: str = "/accounts/123",
    test_type: str = "positive",
    collection_id: str | None = None,
) -> str:
    if collection_id is None:
        collection_id = _seed_collection(project_id)

    r = client.post(
        f"{_prefix(project_id)}/test-cases",
        json={
            "title": title,
            "description": "integration",
            "test_type": test_type,
            "priority": "P1",
            "endpoint_id": endpoint_id,
            "collection_id": collection_id,
            "request_method": "GET",
            "request_path": request_path,
            "request_headers": {},
            "request_params": {},
            "assertions": [],
        },
        headers=auth_headers,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _seed_collection(project_id: str, name: str = "Seed Collection") -> str:
    with SessionLocal() as db:
        collection = TspmApiCollection(
            project_id=project_id,
            name=name,
            description="integration seed",
            base_url="https://api.example.test",
            headers={},
        )
        db.add(collection)
        db.commit()
        db.refresh(collection)
        return collection.id


async def _fake_execute_request(**kwargs) -> ExecutionResult:
    result = ExecutionResult(
        method=kwargs["method"],
        url=kwargs["url"],
        headers_sent=kwargs.get("headers") or {},
        body_sent=kwargs.get("body"),
        status_code=500 if "fail" in kwargs["url"] else 200,
        response_headers={"content-type": "application/json"},
        response_body='{"ok": true}',
        response_size_bytes=12,
        timing=TimingBreakdown(total_ms=12.5),
        assertion_report=None,
        schema_valid=True,
        schema_errors=[],
        extracted_variables={"token": "abc123"} if "login" in kwargs["url"] else {},
        error=None,
        success=True,
    )
    return result


class TestEnvironments(_RequiresDb):
    def test_environment_requires_auth(self, client: TestClient, project_id: str) -> None:
        r = client.get(f"{_prefix(project_id)}/environments")
        assert r.status_code == 401

    def test_environment_requires_project_membership(
        self, client: TestClient, viewer_headers: dict[str, str], project_id: str
    ) -> None:
        r = client.get(f"{_prefix(project_id)}/environments", headers=viewer_headers)
        assert r.status_code == 403

    def test_create_environment(
        self, client: TestClient, auth_headers: dict[str, str], project_id: str
    ) -> None:
        r = client.post(
            f"{_prefix(project_id)}/environments",
            json={
                "name": "dev",
                "description": "Development",
                "variables": {"base_url": "https://dev.api"},
                "sensitive_keys": ["base_url"],
                "is_default": True,
            },
            headers=auth_headers,
        )
        assert r.status_code == 201
        assert r.json()["name"] == "dev"

    def test_list_environments(
        self, client: TestClient, auth_headers: dict[str, str], project_id: str
    ) -> None:
        env_id = _create_environment(client, auth_headers, project_id, name="list-env")
        r = client.get(f"{_prefix(project_id)}/environments", headers=auth_headers)
        assert r.status_code == 200
        assert env_id in [item["id"] for item in r.json()]

    def test_update_environment(
        self, client: TestClient, auth_headers: dict[str, str], project_id: str
    ) -> None:
        env_id = _create_environment(client, auth_headers, project_id, name="update-env")
        r = client.put(
            f"{_prefix(project_id)}/environments/{env_id}",
            json={"description": "Updated", "is_default": False},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["description"] == "Updated"
        assert r.json()["is_default"] is False

    def test_delete_environment(
        self, client: TestClient, auth_headers: dict[str, str], project_id: str
    ) -> None:
        env_id = _create_environment(client, auth_headers, project_id, name="delete-env")
        delete = client.delete(
            f"{_prefix(project_id)}/environments/{env_id}",
            headers=auth_headers,
        )
        assert delete.status_code == 204

        listing = client.get(f"{_prefix(project_id)}/environments", headers=auth_headers)
        assert env_id not in [item["id"] for item in listing.json()]


class TestOpenApiSpecsAndEndpoints(_RequiresDb):
    def test_specs_require_auth(self, client: TestClient, project_id: str) -> None:
        r = client.get(f"{_prefix(project_id)}/specs")
        assert r.status_code == 401

    def test_import_spec_inline(
        self, client: TestClient, auth_headers: dict[str, str], project_id: str
    ) -> None:
        spec_id = _import_spec(client, auth_headers, project_id)
        detail = _get_spec_detail(client, auth_headers, project_id, spec_id)
        assert detail["id"] == spec_id
        assert len(detail["endpoints"]) == 3

    def test_upload_spec_file(
        self, client: TestClient, auth_headers: dict[str, str], project_id: str
    ) -> None:
        r = client.post(
            f"{_prefix(project_id)}/specs/upload",
            files={"file": ("bank-api.json", _minimal_openapi_spec(), "application/json")},
            headers=auth_headers,
        )
        assert r.status_code == 201
        assert r.json()["source_file"] == "bank-api.json"

    def test_list_specs(
        self, client: TestClient, auth_headers: dict[str, str], project_id: str
    ) -> None:
        spec_id = _import_spec(client, auth_headers, project_id, name="List Spec")
        r = client.get(f"{_prefix(project_id)}/specs", headers=auth_headers)
        assert r.status_code == 200
        assert spec_id in [item["id"] for item in r.json()]

    def test_get_spec_detail_includes_test_case_counts(
        self, client: TestClient, auth_headers: dict[str, str], project_id: str
    ) -> None:
        spec_id = _import_spec(client, auth_headers, project_id, name="Detail Spec")
        detail = _get_spec_detail(client, auth_headers, project_id, spec_id)
        endpoint_id = detail["endpoints"][0]["id"]
        _create_test_case(client, auth_headers, project_id, endpoint_id=endpoint_id)

        refreshed = _get_spec_detail(client, auth_headers, project_id, spec_id)
        matching = [ep for ep in refreshed["endpoints"] if ep["id"] == endpoint_id]
        assert matching and matching[0]["test_case_count"] >= 1

    def test_delete_spec(
        self, client: TestClient, auth_headers: dict[str, str], project_id: str
    ) -> None:
        spec_id = _import_spec(client, auth_headers, project_id, name="Delete Spec")
        delete = client.delete(f"{_prefix(project_id)}/specs/{spec_id}", headers=auth_headers)
        assert delete.status_code == 204

        get = client.get(f"{_prefix(project_id)}/specs/{spec_id}", headers=auth_headers)
        assert get.status_code == 404

    def test_invalid_spec_rejected(
        self, client: TestClient, auth_headers: dict[str, str], project_id: str
    ) -> None:
        r = client.post(
            f"{_prefix(project_id)}/specs/import",
            json={"name": "Bad Spec", "content": "not-a-valid-spec"},
            headers=auth_headers,
        )
        assert r.status_code == 422

    def test_list_endpoints_filters_by_risk_level(
        self, client: TestClient, auth_headers: dict[str, str], project_id: str
    ) -> None:
        _import_spec(client, auth_headers, project_id, name="Risk Spec")
        r = client.get(
            f"{_prefix(project_id)}/endpoints?risk_level=critical",
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()
        assert all(item["risk_level"] == "critical" for item in r.json())

    def test_list_endpoints_filters_by_has_pii(
        self, client: TestClient, auth_headers: dict[str, str], project_id: str
    ) -> None:
        _import_spec(client, auth_headers, project_id, name="PII Spec")
        r = client.get(
            f"{_prefix(project_id)}/endpoints?has_pii=true",
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()
        assert all(item["has_pii"] is True for item in r.json())


class TestCasesAndChains(_RequiresDb):
    def test_test_cases_require_auth(self, client: TestClient, project_id: str) -> None:
        r = client.get(f"{_prefix(project_id)}/test-cases")
        assert r.status_code == 401

    def test_create_test_case(
        self, client: TestClient, auth_headers: dict[str, str], project_id: str
    ) -> None:
        tc_id = _create_test_case(client, auth_headers, project_id)
        assert tc_id

    def test_list_test_cases_with_filters(
        self, client: TestClient, auth_headers: dict[str, str], project_id: str
    ) -> None:
        _create_test_case(client, auth_headers, project_id, title="Positive Case", test_type="positive")
        _create_test_case(client, auth_headers, project_id, title="Security Case", test_type="security")
        r = client.get(
            f"{_prefix(project_id)}/test-cases?test_type=security",
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()
        assert all(item["test_type"] == "security" for item in r.json())

    def test_get_test_case(
        self, client: TestClient, auth_headers: dict[str, str], project_id: str
    ) -> None:
        tc_id = _create_test_case(client, auth_headers, project_id, title="Get Case")
        r = client.get(f"{_prefix(project_id)}/test-cases/{tc_id}", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["id"] == tc_id

    def test_update_test_case_review_status(
        self, client: TestClient, auth_headers: dict[str, str], project_id: str
    ) -> None:
        tc_id = _create_test_case(client, auth_headers, project_id, title="Review Case")
        r = client.put(
            f"{_prefix(project_id)}/test-cases/{tc_id}",
            json={"review_status": "approved", "reviewer_note": "ok"},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["review_status"] == "approved"
        assert r.json()["reviewer_note"] == "ok"

    def test_delete_test_case(
        self, client: TestClient, auth_headers: dict[str, str], project_id: str
    ) -> None:
        tc_id = _create_test_case(client, auth_headers, project_id, title="Delete Case")
        delete = client.delete(f"{_prefix(project_id)}/test-cases/{tc_id}", headers=auth_headers)
        assert delete.status_code == 204

        get = client.get(f"{_prefix(project_id)}/test-cases/{tc_id}", headers=auth_headers)
        assert get.status_code == 404

    def test_create_and_get_chain(
        self, client: TestClient, auth_headers: dict[str, str], project_id: str
    ) -> None:
        create = client.post(
            f"{_prefix(project_id)}/chains",
            json={
                "name": "Login Chain",
                "nodes": [{"id": "n1", "type": "request"}],
                "edges": [],
                "global_variables": {"token": ""},
            },
            headers=auth_headers,
        )
        assert create.status_code == 201
        chain_id = create.json()["id"]

        get = client.get(f"{_prefix(project_id)}/chains/{chain_id}", headers=auth_headers)
        assert get.status_code == 200
        assert get.json()["id"] == chain_id

    def test_list_and_delete_chain(
        self, client: TestClient, auth_headers: dict[str, str], project_id: str
    ) -> None:
        create = client.post(
            f"{_prefix(project_id)}/chains",
            json={"name": "Delete Chain", "nodes": [], "edges": []},
            headers=auth_headers,
        )
        chain_id = create.json()["id"]

        listing = client.get(f"{_prefix(project_id)}/chains", headers=auth_headers)
        assert listing.status_code == 200
        assert chain_id in [item["id"] for item in listing.json()]

        delete = client.delete(f"{_prefix(project_id)}/chains/{chain_id}", headers=auth_headers)
        assert delete.status_code == 204


class TestExecutionAndAnalytics(_RequiresDb):
    def test_ai_generate_tests_with_mocked_service(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        monkeypatch,
    ) -> None:
        def _fake_generate(db, pid, **kwargs):
            return {
                "mode": kwargs["mode"],
                "generated_count": 1,
                "test_case_ids": [],
                "security_findings": None,
                "chains": [{"id": "chain-1", "name": "Generated Chain"}],
                "warnings": [],
                "ai_model": "mock-model",
                "duration_ms": 12,
            }

        monkeypatch.setattr(api_testing_service, "generate_tests_with_ai", _fake_generate)

        r = client.post(
            f"{_prefix(project_id)}/ai/generate",
            json={"mode": "chain_builder"},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["mode"] == "chain_builder"
        assert r.json()["generated_count"] == 1

    def test_execute_single_request_with_mocked_executor(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        monkeypatch,
    ) -> None:
        from app.domains.api_testing import request_executor as request_executor_module

        monkeypatch.setattr(request_executor_module, "execute_request", _fake_execute_request)

        r = client.post(
            f"{_prefix(project_id)}/execute/single",
            json={"method": "GET", "url": "https://api.example.test/health"},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["status_code"] == 200
        assert r.json()["passed"] is True

    def test_execute_single_request_rejects_unsafe_target(
        self, client: TestClient, auth_headers: dict[str, str], project_id: str
    ) -> None:
        r = client.post(
            f"{_prefix(project_id)}/execute/single",
            json={"method": "GET", "url": "http://127.0.0.1:22/internal"},
            headers=auth_headers,
        )
        assert r.status_code == 400

    def test_execute_test_cases_creates_history_and_detail(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        monkeypatch,
    ) -> None:
        env_id = _create_environment(client, auth_headers, project_id, base_url="https://api.example.test")
        tc1 = _create_test_case(client, auth_headers, project_id, title="Pass Case", request_path="/health")
        tc2 = _create_test_case(client, auth_headers, project_id, title="Fail Case", request_path="/fail")

        monkeypatch.setattr(api_testing_service, "execute_request", _fake_execute_request)
        monkeypatch.setattr(api_testing_service, "learn_from_execution", lambda db, run_id, pid: None)

        execute = client.post(
            f"{_prefix(project_id)}/execute/test-cases",
            json={"test_case_ids": [tc1, tc2], "environment_id": env_id, "stop_on_failure": False},
            headers=auth_headers,
        )
        assert execute.status_code == 200
        body = execute.json()
        assert body["total"] == 2
        run_id = body["run_id"]

        history = client.get(f"{_prefix(project_id)}/executions", headers=auth_headers)
        assert history.status_code == 200
        assert run_id in [item["run_id"] for item in history.json()["items"]]

        detail = client.get(f"{_prefix(project_id)}/executions/{run_id}", headers=auth_headers)
        assert detail.status_code == 200
        assert detail.json()["run_id"] == run_id
        assert len(detail.json()["details"]) == 2

    def test_stats_endpoint_counts_created_records(
        self, client: TestClient, auth_headers: dict[str, str], project_id: str
    ) -> None:
        _create_environment(client, auth_headers, project_id, name="stats-env")
        _import_spec(client, auth_headers, project_id, name="stats-spec")
        _create_test_case(client, auth_headers, project_id, title="stats-case")
        client.post(
            f"{_prefix(project_id)}/chains",
            json={"name": "stats-chain", "nodes": [], "edges": []},
            headers=auth_headers,
        )

        r = client.get(f"{_prefix(project_id)}/stats", headers=auth_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["specs"] >= 1
        assert body["test_cases"] >= 1
        assert body["chains"] >= 1
        assert body["environments"] >= 1

    def test_trends_endpoint_returns_aggregated_shape(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        monkeypatch,
    ) -> None:
        env_id = _create_environment(client, auth_headers, project_id, name="trend-env")
        tc_id = _create_test_case(client, auth_headers, project_id, title="Trend Case", request_path="/health")
        monkeypatch.setattr(api_testing_service, "execute_request", _fake_execute_request)
        monkeypatch.setattr(api_testing_service, "learn_from_execution", lambda db, run_id, pid: None)

        execute = client.post(
            f"{_prefix(project_id)}/execute/test-cases",
            json={"test_case_ids": [tc_id], "environment_id": env_id},
            headers=auth_headers,
        )
        assert execute.status_code == 200

        trends = client.get(f"{_prefix(project_id)}/trends?days=7", headers=auth_headers)
        assert trends.status_code == 200
        assert isinstance(trends.json()["days"], list)
        assert trends.json()["total_runs"] >= 1


class TestCoverageFlakyAssertionsAndSecurity(_RequiresDb):
    def test_coverage_analysis_with_mocked_analyzer(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        monkeypatch,
    ) -> None:
        from app.domains.api_testing import coverage_analyzer

        monkeypatch.setattr(
            coverage_analyzer,
            "analyze_coverage",
            lambda db, pid, spec_id=None: {
                "summary": {
                    "total_endpoints": 3,
                    "covered_endpoints": 2,
                    "coverage_percent": 66.7,
                    "untested_endpoints": 1,
                },
                "gaps": [
                    {
                        "endpoint_id": "ep-1",
                        "method": "POST",
                        "path": "/payments/transfer",
                        "risk_level": "critical",
                        "missing_test_types": ["security"],
                        "gap_severity": "critical",
                        "reason": "no security tests",
                    }
                ],
                "by_risk_level": {
                    "critical": {"total": 1, "covered": 0, "coverage_percent": 0.0},
                    "high": {"total": 1, "covered": 1, "coverage_percent": 100.0},
                },
                "by_test_type": {
                    "security": {"count": 0, "endpoints_covered": 0},
                    "positive": {"count": 2, "endpoints_covered": 2},
                },
            },
        )

        r = client.get(f"{_prefix(project_id)}/coverage-analysis", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["summary"]["coverage_percent"] == 66.7

    def test_quarantine_endpoints_with_mocked_detector(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        monkeypatch,
    ) -> None:
        from app.domains.api_testing import flaky_detector

        tc_id = _create_test_case(client, auth_headers, project_id, title="Flaky Case")
        monkeypatch.setattr(
            flaky_detector,
            "quarantine_test",
            lambda db, test_case_id, reason: {
                "test_case_id": test_case_id,
                "quarantined": True,
                "reason": reason,
                "message": "ok",
            },
        )
        monkeypatch.setattr(
            flaky_detector,
            "unquarantine_test",
            lambda db, test_case_id: {
                "test_case_id": test_case_id,
                "quarantined": False,
                "reason": None,
                "message": "ok",
            },
        )
        monkeypatch.setattr(
            flaky_detector,
            "get_quarantine_list",
            lambda db, pid: [
                {
                    "test_case_id": tc_id,
                    "title": "Flaky Case",
                    "test_type": "positive",
                    "quarantine_reason": "intermittent",
                    "quarantined_at": None,
                    "flaky_score": 0.8,
                }
            ],
        )

        quarantine = client.post(
            f"{_prefix(project_id)}/flaky/{tc_id}/quarantine",
            json={"reason": "intermittent"},
            headers=auth_headers,
        )
        assert quarantine.status_code == 200
        assert quarantine.json()["quarantined"] is True

        listing = client.get(f"{_prefix(project_id)}/quarantine", headers=auth_headers)
        assert listing.status_code == 200
        assert listing.json()["total_count"] == 1

        unquarantine = client.delete(
            f"{_prefix(project_id)}/flaky/{tc_id}/quarantine",
            headers=auth_headers,
        )
        assert unquarantine.status_code == 200
        assert unquarantine.json()["quarantined"] is False

    def test_assertion_suggestion_for_missing_test_case_returns_404(
        self, client: TestClient, auth_headers: dict[str, str], project_id: str
    ) -> None:
        r = client.get(
            f"{_prefix(project_id)}/assertions/00000000-0000-0000-0000-000000000000/suggest",
            headers=auth_headers,
        )
        assert r.status_code == 404

    def test_assertion_stats_with_mocked_service(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        monkeypatch,
    ) -> None:
        from app.domains.api_testing import assertion_suggester

        monkeypatch.setattr(
            assertion_suggester,
            "get_assertion_stats",
            lambda db, pid: {
                "total_tests": 4,
                "total_assertions": 10,
                "avg_assertions_per_test": 2.5,
                "tests_with_no_assertions": 1,
                "tests_below_threshold": 2,
                "assertion_type_distribution": {"status_code": 5},
                "suggestion_potential": 3,
            },
        )

        r = client.get(f"{_prefix(project_id)}/assertions/stats", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["total_tests"] == 4

    def test_scan_endpoint_and_generate_security_tests_with_mocks(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        monkeypatch,
    ) -> None:
        from app.domains.api_testing import security_scanner

        spec_id = _import_spec(client, auth_headers, project_id, name="Security Spec")
        detail = _get_spec_detail(client, auth_headers, project_id, spec_id)
        endpoint_id = next(ep["id"] for ep in detail["endpoints"] if ep["path"] == "/payments/transfer")

        monkeypatch.setattr(
            security_scanner,
            "scan_endpoint",
            lambda db, eid: {
                "endpoint_id": eid,
                "method": "POST",
                "path": "/payments/transfer",
                "risk_level": "critical",
                "findings": [
                    {
                        "title": "Missing auth check",
                        "severity": "high",
                        "owasp_category": "API2",
                        "description": "desc",
                        "recommendation": "fix",
                    }
                ],
                "security_score": 42.0,
                "test_suggestions": [
                    {
                        "title": "Unauthorized transfer attempt",
                        "test_type": "security",
                        "owasp_category": "API2",
                        "priority": "P0",
                        "description": "desc",
                    }
                ],
            },
        )
        monkeypatch.setattr(
            security_scanner,
            "generate_security_tests",
            lambda db, pid, eid, owasp_categories=None: {
                "endpoint_id": eid,
                "generated_count": 1,
                "test_cases": [
                    {
                        "id": "sec-1",
                        "project_id": project_id,
                        "endpoint_id": endpoint_id,
                        "collection_id": None,
                        "title": "Security Case",
                        "description": "desc",
                        "test_type": "security",
                        "priority": "P0",
                        "owasp_category": "API2",
                        "regulation": None,
                        "cwe_id": None,
                        "request_method": "POST",
                        "request_path": "/payments/transfer",
                        "request_headers": {},
                        "request_params": {},
                        "request_body": None,
                        "pre_request_vars": None,
                        "setup_chain": None,
                        "assertions": [],
                        "ai_generated": False,
                        "ai_model": None,
                        "ai_confidence": None,
                        "ai_reasoning": None,
                        "review_status": "pending",
                        "reviewer_note": None,
                        "last_run_status": None,
                        "last_run_at": None,
                        "run_count": 0,
                        "pass_count": 0,
                        "fail_count": 0,
                        "quarantined": False,
                        "quarantine_reason": None,
                        "created_at": None,
                        "updated_at": None,
                    }
                ],
                "scan_summary": {
                    "total_findings": 1,
                    "security_score": 42.0,
                    "risk_level": "critical",
                },
            },
        )

        scan = client.post(
            f"{_prefix(project_id)}/security/scan/endpoint/{endpoint_id}",
            headers=auth_headers,
        )
        assert scan.status_code == 200
        assert scan.json()["risk_level"] == "critical"

        generate = client.post(
            f"{_prefix(project_id)}/security/generate-tests",
            json={"endpoint_id": endpoint_id, "owasp_categories": ["API2"]},
            headers=auth_headers,
        )
        assert generate.status_code == 200
        assert generate.json()["generated_count"] == 1
