"""n8n integration router tests."""

from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

from app.domains.n8n import router as n8n_router
from app.domains.tspm.models import TspmN8nWorkflow
from app.infra.database import SessionLocal


def _seed_workflow(project_id: str, name: str = "n8n workflow") -> str:
    with SessionLocal() as db:
        workflow = TspmN8nWorkflow(
            project_id=project_id,
            n8n_workflow_id="wf-123",
            name=name,
            trigger_on="manual",
            is_active=True,
            webhook_path="/hook/test",
            config={},
        )
        db.add(workflow)
        db.commit()
        db.refresh(workflow)
        return workflow.id


class _FakeAsyncClient:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, headers=None):
        request = httpx.Request("GET", url)
        return httpx.Response(200, request=request, json={"data": [{"id": "1", "name": "WF A"}]})


class TestN8N:
    PREFIX = "/api/v1/n8n"

    def test_webhook_unknown_workflow(self, client: TestClient) -> None:
        r = client.post(
            f"{self.PREFIX}/webhook/00000000-0000-0000-0000-000000000000",
            json={"executionId": "e-1", "finished": True, "success": True},
        )
        assert r.status_code == 404

    def test_webhook_endpoint_creates_execution(
        self,
        client: TestClient,
        project_id: str,
        db_ready: bool,
    ) -> None:
        if not db_ready:
            pytest.skip("DB yok")

        workflow_id = _seed_workflow(project_id)
        r = client.post(
            f"{self.PREFIX}/webhook/{workflow_id}",
            json={"executionId": "exec-1", "finished": True, "success": True, "data": {"ok": True}},
        )
        assert r.status_code == 200
        assert r.json()["ok"] is True
        assert r.json()["execution_id"]

    def test_webhook_secret_required_mode(self, client: TestClient, project_id: str, monkeypatch) -> None:
        workflow_id = _seed_workflow(project_id, name="strict mode workflow")
        monkeypatch.setenv("N8N_REQUIRE_CALLBACK_SECRET", "1")
        monkeypatch.setattr(n8n_router, "N8N_CALLBACK_TOKEN", "")

        r = client.post(
            f"{self.PREFIX}/webhook/{workflow_id}",
            json={"executionId": "exec-strict", "finished": True, "success": True},
        )
        assert r.status_code == 503

    def test_webhook_invalid_token(self, client: TestClient, project_id: str, monkeypatch) -> None:
        workflow_id = _seed_workflow(project_id, name="token workflow")
        monkeypatch.setattr(n8n_router, "N8N_CALLBACK_TOKEN", "expected-token")
        r = client.post(
            f"{self.PREFIX}/webhook/{workflow_id}",
            json={"executionId": "exec-token", "finished": True, "success": True},
            headers={"X-N8N-Token": "wrong-token"},
        )
        assert r.status_code == 401

    def test_available_workflows_without_api_key_returns_note(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        monkeypatch,
    ) -> None:
        monkeypatch.setattr(n8n_router, "N8N_API_KEY", "")
        r = client.get(f"{self.PREFIX}/available-workflows", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["workflows"] == []
        assert "note" in r.json()

    def test_available_workflows_with_mocked_n8n(
        self,
        client: TestClient,
        auth_headers: dict[str, str],
        monkeypatch,
    ) -> None:
        monkeypatch.setattr(n8n_router, "N8N_API_KEY", "test-key")
        monkeypatch.setattr(n8n_router.httpx, "AsyncClient", _FakeAsyncClient)
        r = client.get(f"{self.PREFIX}/available-workflows", headers=auth_headers)
        assert r.status_code == 200
        assert len(r.json()["workflows"]) == 1
