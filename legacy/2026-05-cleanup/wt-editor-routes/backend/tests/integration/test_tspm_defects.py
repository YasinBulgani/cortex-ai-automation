"""TSPM integration tests for AI test-case review and debug/reporting endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.domains.tspm import router as tspm_router
from app.domains.tspm.models import TspmAiBatch, TspmTestCase
from app.infra.database import SessionLocal


class _RequiresDb:
    @pytest.fixture(autouse=True)
    def _require_db(self, db_ready: bool) -> None:
        if not db_ready:
            pytest.skip("DB yok")


def _seed_batch_with_cases(project_id: str, total: int = 2) -> tuple[str, list[str]]:
    with SessionLocal() as db:
        batch = TspmAiBatch(
            project_id=project_id,
            source_type="document",
            source_name="integration-seed",
            status="ready",
            total_generated=total,
        )
        db.add(batch)
        db.flush()

        case_ids = []
        for idx in range(total):
            tc = TspmTestCase(
                project_id=project_id,
                batch_id=batch.id,
                title=f"Seed Test Case {idx + 1}",
                description="seed",
                module_name="auth",
                test_type="functional",
                priority="medium",
                risk_level="medium",
                steps=[{"order": 1, "action": "Adim", "expected": "Sonuc"}],
                expected_result="Tamam",
                tags=["seed"],
                review_status="pending",
            )
            db.add(tc)
            db.flush()
            case_ids.append(tc.id)

        db.commit()
        return batch.id, case_ids


class TestAiTestCaseEndpoints(_RequiresDb):
    PREFIX = "/api/v1/tspm"

    def test_generate_test_cases_success_contract(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        monkeypatch,
    ) -> None:
        def _fake_generate(db, pid, body):
            assert pid == project_id
            return {
                "batch_id": "batch-123",
                "total_generated": 1,
                "ai_provider": "fake-ai",
                "message": "1 test case created",
                "test_cases": [
                    {
                        "id": "tc-1",
                        "project_id": project_id,
                        "batch_id": "batch-123",
                        "title": "Generated TC",
                        "description": "generated",
                        "module_name": "auth",
                        "feature_area": "login",
                        "test_type": "functional",
                        "priority": "high",
                        "risk_level": "medium",
                        "preconditions": [],
                        "steps": [{"order": 1, "action": "Login", "expected": "Success"}],
                        "expected_result": "Success",
                        "tags": ["ai"],
                        "review_status": "pending",
                        "reviewer_note": None,
                        "scenario_id": None,
                        "created_at": None,
                        "updated_at": None,
                    }
                ],
            }

        monkeypatch.setattr(tspm_router.tc_svc, "generate_test_cases_for_project", _fake_generate)

        r = client.post(
            f"{self.PREFIX}/projects/{project_id}/test-cases/generate",
            json={"analysis_text": "Bu dokuman en az on karakterden uzun.", "source_type": "document"},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["batch_id"] == "batch-123"
        assert r.json()["total_generated"] == 1

    def test_generate_test_cases_runtime_error_maps_to_503(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        monkeypatch,
    ) -> None:
        def _boom(db, pid, body):
            raise RuntimeError("gateway offline")

        monkeypatch.setattr(tspm_router.tc_svc, "generate_test_cases_for_project", _boom)

        r = client.post(
            f"{self.PREFIX}/projects/{project_id}/test-cases/generate",
            json={"analysis_text": "Bu dokuman en az on karakterden uzun.", "source_type": "document"},
            headers=auth_headers,
        )
        assert r.status_code == 503

    def test_list_batches_returns_seeded_batch(
        self, client: TestClient, auth_headers: dict[str, str], project_id: str
    ) -> None:
        batch_id, _ = _seed_batch_with_cases(project_id)
        r = client.get(
            f"{self.PREFIX}/projects/{project_id}/test-cases/batches",
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert batch_id in [item["id"] for item in r.json()]

    def test_get_batch_detail_returns_cases(
        self, client: TestClient, auth_headers: dict[str, str], project_id: str
    ) -> None:
        batch_id, case_ids = _seed_batch_with_cases(project_id)
        r = client.get(
            f"{self.PREFIX}/projects/{project_id}/test-cases/batches/{batch_id}",
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["batch"]["id"] == batch_id
        returned_ids = [item["id"] for item in r.json()["test_cases"]]
        assert set(case_ids).issubset(set(returned_ids))

    def test_get_missing_batch_returns_404(
        self, client: TestClient, auth_headers: dict[str, str], project_id: str
    ) -> None:
        r = client.get(
            f"{self.PREFIX}/projects/{project_id}/test-cases/batches/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert r.status_code == 404

    def test_delete_batch_removes_it(
        self, client: TestClient, auth_headers: dict[str, str], project_id: str
    ) -> None:
        batch_id, _ = _seed_batch_with_cases(project_id)
        delete = client.delete(
            f"{self.PREFIX}/projects/{project_id}/test-cases/batches/{batch_id}",
            headers=auth_headers,
        )
        assert delete.status_code == 204

        listing = client.get(
            f"{self.PREFIX}/projects/{project_id}/test-cases/batches",
            headers=auth_headers,
        )
        assert batch_id not in [item["id"] for item in listing.json()]

    def test_list_test_cases_filters_by_review_status(
        self, client: TestClient, auth_headers: dict[str, str], project_id: str
    ) -> None:
        _, case_ids = _seed_batch_with_cases(project_id)
        review = client.post(
            f"{self.PREFIX}/projects/{project_id}/test-cases/{case_ids[0]}/review",
            json={"action": "approve", "reviewer_note": "ok"},
            headers=auth_headers,
        )
        assert review.status_code == 200

        r = client.get(
            f"{self.PREFIX}/projects/{project_id}/test-cases?review_status=approved",
            headers=auth_headers,
        )
        assert r.status_code == 200
        ids = [item["id"] for item in r.json()]
        assert case_ids[0] in ids

    def test_get_test_case_detail(
        self, client: TestClient, auth_headers: dict[str, str], project_id: str
    ) -> None:
        _, case_ids = _seed_batch_with_cases(project_id, total=1)
        r = client.get(
            f"{self.PREFIX}/projects/{project_id}/test-cases/{case_ids[0]}",
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["id"] == case_ids[0]

    def test_update_test_case_marks_it_edited(
        self, client: TestClient, auth_headers: dict[str, str], project_id: str
    ) -> None:
        _, case_ids = _seed_batch_with_cases(project_id, total=1)
        r = client.put(
            f"{self.PREFIX}/projects/{project_id}/test-cases/{case_ids[0]}",
            json={"title": "Edited Title"},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["title"] == "Edited Title"
        assert r.json()["review_status"] == "edited"

    def test_review_approve_creates_linked_scenario(
        self, client: TestClient, auth_headers: dict[str, str], project_id: str
    ) -> None:
        _, case_ids = _seed_batch_with_cases(project_id, total=1)
        r = client.post(
            f"{self.PREFIX}/projects/{project_id}/test-cases/{case_ids[0]}/review",
            json={"action": "approve", "reviewer_note": "approved"},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["review_status"] == "approved"
        assert r.json()["scenario_id"]

    def test_bulk_review_invalid_action_returns_400(
        self, client: TestClient, auth_headers: dict[str, str], project_id: str
    ) -> None:
        _, case_ids = _seed_batch_with_cases(project_id, total=2)
        r = client.post(
            f"{self.PREFIX}/projects/{project_id}/test-cases/bulk-review",
            json={"ids": case_ids, "action": "archive"},
            headers=auth_headers,
        )
        assert r.status_code == 400


class TestDebugAndAllureEndpoints(_RequiresDb):
    PREFIX = "/api/v1/tspm"

    def test_run_debug_loop_with_supplied_results(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        monkeypatch,
    ) -> None:
        def _fake_debug_loop(execution_id, project_id, results, generate_allure):
            return {
                "debug_analysis": {
                    "analyses": [
                        {
                            "test_id": results[0]["test_id"],
                            "root_cause_category": "TEST_ISSUE",
                            "root_cause_subcategory": "selector",
                            "confidence": 0.9,
                            "fix_steps": ["locator guncelle"],
                            "estimated_fix_time": "15m",
                            "risk_level": "medium",
                            "similar_tests_at_risk": [],
                            "explanation": "Mock debug",
                        }
                    ],
                    "overall_health": "at_risk",
                    "key_patterns": ["selector"],
                    "recommended_actions": ["heal locators"],
                    "ai_provider": "mock",
                    "fallback_used": False,
                },
                "summary": {"failed_count": 1},
                "generated_at": "2026-04-16T12:00:00Z",
                "allure_results": [{"name": "result.json"}],
            }

        monkeypatch.setattr(tspm_router.debug_svc, "run_debug_loop", _fake_debug_loop)

        r = client.post(
            f"{self.PREFIX}/projects/{project_id}/executions/exec-123/debug",
            json={
                "execution_id": "exec-123",
                "generate_allure": True,
                "results": [
                    {
                        "test_id": "tc-1",
                        "scenario_id": "sc-1",
                        "title": "Login fails",
                        "module": "auth",
                        "status": "failed",
                        "severity": "high",
                        "error_message": "timeout",
                        "steps": [],
                        "tags": [],
                    }
                ],
            },
            headers=auth_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["overall_health"] == "at_risk"
        assert body["analyses"][0]["root_cause_category"] == "TEST_ISSUE"

    def test_run_debug_loop_missing_execution_returns_404(
        self, client: TestClient, auth_headers: dict[str, str], project_id: str
    ) -> None:
        r = client.post(
            f"{self.PREFIX}/projects/{project_id}/executions/00000000-0000-0000-0000-000000000000/debug",
            json={"execution_id": "00000000-0000-0000-0000-000000000000", "generate_allure": True},
            headers=auth_headers,
        )
        assert r.status_code == 404

    def test_export_allure_returns_mocked_payload(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        project_id: str,
        create_scenario,
        monkeypatch,
    ) -> None:
        scenario_id = create_scenario(project_id, "Allure Scenario")
        create = client.post(
            f"{self.PREFIX}/projects/{project_id}/executions",
            json={"name": "Allure Run", "scenario_ids": [scenario_id]},
            headers=auth_headers,
        )
        assert create.status_code == 201
        execution_id = create.json()["id"]

        monkeypatch.setattr(
            tspm_router.debug_svc,
            "build_allure_results",
            lambda execution_id, results: [{"name": "result.json", "status": "passed"}],
        )
        monkeypatch.setattr(
            tspm_router.debug_svc,
            "build_allure_environment",
            lambda project_name, base_url: "ENV=mock",
        )
        monkeypatch.setattr(
            tspm_router.debug_svc,
            "build_allure_executor",
            lambda execution_id, execution_name, project_id: {"name": execution_name, "type": "mock"},
        )

        r = client.get(
            f"{self.PREFIX}/projects/{project_id}/executions/{execution_id}/allure",
            headers=auth_headers,
        )
        assert r.status_code == 200
        body = r.json()
        assert body["execution_id"] == execution_id
        assert body["file_count"] == 1
        assert body["executor_json"]["type"] == "mock"
