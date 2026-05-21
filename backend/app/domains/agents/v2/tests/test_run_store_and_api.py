"""Run store + API endpoint testleri."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.domains.agents.v2.run_store import RunStore, get_run_store


# ═══════════════════════════════════════════════════════════════════════════
# RunStore
# ═══════════════════════════════════════════════════════════════════════════


class TestRunStore:
    def test_create_and_get(self):
        store = RunStore()
        run_id, state = store.create(
            project_id="p1",
            user_id="u1",
            tenant_id="t1",
            input_source="url",
            input_payload={"url": "https://example.com"},
        )
        rec = store.get(run_id)
        assert rec is not None
        assert rec.project_id == "p1"
        assert rec.state["input_source"] == "url"

    def test_list_filter_by_project(self):
        store = RunStore()
        id1, _ = store.create(
            project_id="p1", user_id="u", tenant_id="t",
            input_source="text", input_payload={"text": "a"},
        )
        id2, _ = store.create(
            project_id="p2", user_id="u", tenant_id="t",
            input_source="text", input_payload={"text": "b"},
        )
        items = store.list(project_id="p1")
        assert len(items) == 1
        assert items[0].run_id == id1

    def test_status_transitions(self):
        store = RunStore()
        run_id, _ = store.create(
            project_id="p", user_id="u", tenant_id="t",
            input_source="text", input_payload={"text": "x"},
        )
        store.update_status(run_id, "running")
        assert store.get(run_id).status == "running"
        store.update_status(run_id, "completed")
        rec = store.get(run_id)
        assert rec.status == "completed"
        assert rec.completed_at is not None

    def test_pub_sub(self):
        store = RunStore()
        run_id, _ = store.create(
            project_id="p", user_id="u", tenant_id="t",
            input_source="text", input_payload={"text": "x"},
        )
        q = store.subscribe(run_id)
        store.publish(run_id, {"event_type": "started", "run_id": run_id})
        assert not q.empty()
        evt = q.get_nowait()
        assert evt["event_type"] == "started"

    def test_production_like_auto_mode_resolves_to_postgres(self, monkeypatch):
        monkeypatch.setenv("APP_ENV", "production")
        monkeypatch.delenv("AGENTS_V2_RUN_STORE", raising=False)

        store = RunStore()

        assert store._persist_mode == "postgres"


# ═══════════════════════════════════════════════════════════════════════════
# API
# ═══════════════════════════════════════════════════════════════════════════


@pytest.fixture
def api_client(monkeypatch):
    """FastAPI test client. DB bağımlılıkları olmadan sadece v2 router test."""
    monkeypatch.setenv("AGENTS_V2_RUN_STORE", "memory")

    from fastapi import FastAPI
    from app.domains.agents.v2.router import router as v2_router

    app = FastAPI()
    app.include_router(v2_router, prefix="/api/v1")

    import app.domains.agents.v2.run_store as rs_mod
    rs_mod._singleton = None

    yield TestClient(app)

    rs_mod._singleton = None


class TestAPI:
    def test_run_requires_source(self, api_client):
        resp = api_client.post(
            "/api/v1/agents/v2/run",
            json={"project_id": "p1", "input_source": "text"},
        )
        assert resp.status_code == 400
        assert "Kaynak" in resp.text or "gerekli" in resp.text

    def test_run_create_queues(self, api_client, monkeypatch):
        # _execute_pipeline'i mock'la — gerçekten çalışmasın
        async def _fake_exec(run_id, state):
            return None
        monkeypatch.setattr(
            "app.domains.agents.v2.router._execute_pipeline", _fake_exec
        )
        resp = api_client.post(
            "/api/v1/agents/v2/run",
            json={
                "project_id": "p1",
                "input_source": "text",
                "text": "Kullanıcı giriş yapabilmeli",
            },
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "queued"
        assert "run_id" in data
        assert "stream_url" in data

    def test_runs_list_empty(self, api_client):
        resp = api_client.get("/api/v1/agents/v2/runs?page=1&page_size=10")
        assert resp.status_code == 200
        data = resp.json()
        assert data["runs"] == []
        assert data["total"] == 0

    def test_get_run_not_found(self, api_client):
        resp = api_client.get("/api/v1/agents/v2/runs/nonexistent-id")
        assert resp.status_code == 404

    def test_cancel_not_found(self, api_client):
        resp = api_client.post("/api/v1/agents/v2/runs/nope/cancel")
        assert resp.status_code == 404

    def test_health_endpoint(self, api_client):
        resp = api_client.get("/api/v1/agents/v2/health")
        assert resp.status_code == 200
        data = resp.json()
        assert "langgraph_available" in data
        assert "ai_gateway_reachable" in data


@pytest.mark.asyncio
async def test_execute_pipeline_marks_structured_validation_terminal(monkeypatch):
    import app.domains.agents.v2.run_store as rs_mod
    from app.domains.agents.v2 import router as router_mod

    rs_mod._singleton = None
    store = get_run_store()
    run_id, state = store.create(
        project_id="p1",
        user_id="u1",
        tenant_id="default",
        input_source="text",
        input_payload={"text": "schema fail"},
    )

    async def _fake_manual(_run_id, _state):
        raise router_mod.WorkflowValidationError("Structured output validation failed")

    monkeypatch.setattr(router_mod, "_execute_manual", _fake_manual)

    await router_mod._execute_pipeline(run_id, state)

    rec = store.get(run_id)
    assert rec is not None
    assert rec.status == "failed_validation"
    assert rec.error == "Structured output validation failed"
    assert rec.events[-1]["event_type"] == "failed_validation"


@pytest.mark.asyncio
async def test_execute_pipeline_marks_registry_cancel_terminal(monkeypatch):
    import app.domains.agents.v2.run_store as rs_mod
    from app.domains.agents.v2 import router as router_mod
    from app.domains.agents.v2.budget_guard import is_cancelled, request_cancel

    rs_mod._singleton = None
    store = get_run_store()
    run_id, state = store.create(
        project_id="p1",
        user_id="u1",
        tenant_id="default",
        input_source="text",
        input_payload={"text": "cancel me"},
    )
    request_cancel(run_id)

    await router_mod._execute_pipeline(run_id, state)

    rec = store.get(run_id)
    assert rec is not None
    assert rec.status == "cancelled"
    assert rec.state["cancelled"] is True
    assert rec.events[-1]["event_type"] == "cancelled"
    assert is_cancelled(run_id) is False
