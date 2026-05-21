"""Canonical /ai/workflows API tests."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.deps import get_current_user
from app.config import settings
from app.domains.ai.workflows_router import register_state_artifacts, router as workflows_router


def _client(monkeypatch, *, user_id: str = "u1", permissions: list[str] | None = None) -> TestClient:
    def _fake_enqueue(*, run_id, state, background):
        from app.domains.agents.v2.run_store import get_run_store

        get_run_store().publish(
            run_id,
            {
                "event_type": "queue_enqueued",
                "run_id": run_id,
                "workflow_id": run_id,
                "data": {"backend": "test"},
            },
        )
        return {"backend": "test"}

    monkeypatch.setattr(
        "app.domains.ai.workflows_router.enqueue_ai_workflow",
        _fake_enqueue,
    )

    import app.domains.agents.v2.run_store as rs_mod

    rs_mod._singleton = None
    app = FastAPI()
    app.include_router(workflows_router, prefix="/api/v1")
    app.dependency_overrides[get_current_user] = lambda: _FakeUser(user_id, permissions)
    return TestClient(app)


class _FakePermission:
    def __init__(self, permission: str) -> None:
        self.permission = permission


class _FakeRole:
    def __init__(self, permissions: list[str] | None = None) -> None:
        self.permissions = [_FakePermission(item) for item in (permissions or ["admin.*"])]


class _FakeUser:
    def __init__(self, user_id: str, permissions: list[str] | None = None) -> None:
        self.id = user_id
        self.roles = [_FakeRole(permissions)]


def test_create_workflow_queues_run(monkeypatch):
    client = _client(monkeypatch)

    resp = client.post(
        "/api/v1/ai/workflows",
        json={
            "project_id": "p1",
            "input_source": "text",
            "text": "Kullanici giris yapabilmeli",
            "workflow_type": "test_generation",
        },
    )

    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] == "queued"
    assert data["workflow_id"] == data["run_id"]
    assert data["detail_url"].startswith("/api/v1/ai/workflows/")
    assert data["events_url"].endswith("/events")
    assert data["artifacts_url"].endswith("/artifacts")


def test_workflow_events_artifacts_cancel_and_approval(monkeypatch):
    client = _client(monkeypatch)

    created = client.post(
        "/api/v1/ai/workflows",
        json={
            "project_id": "p1",
            "input_source": "text",
            "text": "Sepete urun eklenebilmeli",
            "requires_approval": True,
        },
    ).json()
    workflow_id = created["workflow_id"]
    assert created["status"] == "pending_approval"

    events = client.get(f"/api/v1/ai/workflows/{workflow_id}/events")
    assert events.status_code == 200
    assert events.json()["events"][0]["event_type"] == "workflow_created"
    assert events.json()["events"][1]["event_type"] == "approval_required"

    artifacts = client.get(f"/api/v1/ai/workflows/{workflow_id}/artifacts")
    assert artifacts.status_code == 200
    assert artifacts.json()["artifacts"] == []

    self_approval = client.post(
        f"/api/v1/ai/workflows/{workflow_id}/approve",
        json={"decision": "approved", "note": "self"},
    )
    assert self_approval.status_code == 403
    assert "Maker-checker" in self_approval.text

    client.app.dependency_overrides[get_current_user] = lambda: _FakeUser(
        "u2", ["ai.workflows.approve"]
    )
    approval = client.post(
        f"/api/v1/ai/workflows/{workflow_id}/approve",
        json={"decision": "approved", "note": "go"},
    )
    assert approval.status_code == 200
    assert approval.json()["approval"]["decision"] == "approved"

    client.app.dependency_overrides[get_current_user] = lambda: _FakeUser("u1")
    cancelled = client.post(f"/api/v1/ai/workflows/{workflow_id}/cancel")
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"


def test_workflow_approval_requires_dedicated_permission(monkeypatch):
    client = _client(monkeypatch)
    created = client.post(
        "/api/v1/ai/workflows",
        json={
            "project_id": "p1",
            "input_source": "text",
            "text": "Onay yetkisi ayrilmali",
            "requires_approval": True,
        },
    ).json()

    client.app.dependency_overrides[get_current_user] = lambda: _FakeUser(
        "u2", ["ai.gateway.use"]
    )
    resp = client.post(
        f"/api/v1/ai/workflows/{created['workflow_id']}/approve",
        json={"decision": "approved"},
    )

    assert resp.status_code == 403
    assert "approval yetkisi" in resp.text


def test_workflow_artifact_download_is_scoped_to_artifacts_dir(monkeypatch, tmp_path):
    client = _client(monkeypatch)
    monkeypatch.setattr(settings, "artifacts_dir", str(tmp_path))

    created = client.post(
        "/api/v1/ai/workflows",
        json={
            "project_id": "p1",
            "input_source": "text",
            "text": "Rapor indirilebilmeli",
        },
    ).json()
    workflow_id = created["workflow_id"]

    report = tmp_path / "reports" / "run_report.xlsx"
    report.parent.mkdir(parents=True)
    report.write_bytes(b"fake-xlsx")

    from app.domains.agents.v2.run_store import get_run_store

    artifact = get_run_store().add_artifact(
        workflow_id,
        kind="excel_report",
        name="run_report.xlsx",
        storage_path=str(report),
        mime_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        size_bytes=report.stat().st_size,
    )
    assert artifact is not None
    assert artifact["metadata"]["hash_algorithm"] == "sha256"
    assert artifact["metadata"]["sha256"]

    resp = client.get(
        f"/api/v1/ai/workflows/{workflow_id}/artifacts/{artifact['artifact_id']}/download"
    )

    assert resp.status_code == 200
    assert resp.content == b"fake-xlsx"
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in resp.headers[
        "content-type"
    ]
    events = client.get(f"/api/v1/ai/workflows/{workflow_id}/events").json()["events"]
    assert events[-1]["event_type"] == "artifact_downloaded"

    tampered = tmp_path / "reports" / "tampered.txt"
    tampered.write_text("original", encoding="utf-8")
    tampered_artifact = get_run_store().add_artifact(
        workflow_id,
        kind="debug",
        name="tampered.txt",
        storage_path=str(tampered),
        mime_type="text/plain",
    )
    assert tampered_artifact is not None
    tampered.write_text("changed", encoding="utf-8")
    tampered_resp = client.get(
        f"/api/v1/ai/workflows/{workflow_id}/artifacts/{tampered_artifact['artifact_id']}/download"
    )
    assert tampered_resp.status_code == 409
    events = client.get(f"/api/v1/ai/workflows/{workflow_id}/events").json()["events"]
    assert events[-1]["event_type"] == "artifact_integrity_failed"

    legacy = tmp_path / "reports" / "legacy.txt"
    legacy.write_text("legacy", encoding="utf-8")
    legacy_artifact = get_run_store().add_artifact(
        workflow_id,
        kind="legacy",
        name="legacy.txt",
        storage_path=str(legacy),
        mime_type="text/plain",
    )
    assert legacy_artifact is not None
    rec = get_run_store().get(workflow_id)
    assert rec is not None
    for item in rec.artifacts:
        if item.artifact_id == legacy_artifact["artifact_id"]:
            item.metadata = {}
            break

    legacy_resp = client.get(
        f"/api/v1/ai/workflows/{workflow_id}/artifacts/{legacy_artifact['artifact_id']}/download"
    )
    assert legacy_resp.status_code == 409
    events = client.get(f"/api/v1/ai/workflows/{workflow_id}/events").json()["events"]
    assert events[-1]["event_type"] == "artifact_integrity_missing"

    outside = tmp_path.parent / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    blocked = get_run_store().add_artifact(
        workflow_id,
        kind="debug",
        name="outside.txt",
        storage_path=str(outside),
        mime_type="text/plain",
    )
    assert blocked is not None

    blocked_resp = client.get(
        f"/api/v1/ai/workflows/{workflow_id}/artifacts/{blocked['artifact_id']}/download"
    )
    assert blocked_resp.status_code == 403


def test_workflow_health_summary(monkeypatch, tmp_path):
    client = _client(monkeypatch)
    monkeypatch.setattr(settings, "artifacts_dir", str(tmp_path))

    created = client.post(
        "/api/v1/ai/workflows",
        json={
            "project_id": "p1",
            "input_source": "text",
            "text": "Health metrikleri gorunmeli",
            "requires_approval": True,
            "workflow_type": "review",
        },
    ).json()
    workflow_id = created["workflow_id"]

    from app.domains.agents.v2.run_store import get_run_store

    store = get_run_store()
    rec = store.get(workflow_id)
    assert rec is not None
    rec.state["cost_usd"] = 0.25
    rec.state["tokens_used"] = 1234
    rec.state["llm_calls_count"] = 3
    store.update_state(workflow_id, rec.state)
    artifact_path = tmp_path / "health.txt"
    artifact_path.write_text("ok", encoding="utf-8")
    store.add_artifact(
        workflow_id,
        kind="text_report",
        name="health.txt",
        storage_path=str(artifact_path),
        mime_type="text/plain",
    )
    store.record_dead_letter(
        run_id=workflow_id,
        queue_name="ai-workflows",
        reason="test",
        payload={"workflow_id": workflow_id},
    )

    resp = client.get("/api/v1/ai/workflows/health?limit=20")

    assert resp.status_code == 200
    data = resp.json()
    assert data["runs_total"] == 1
    assert data["active_runs"] == 1
    assert data["by_status"]["pending_approval"] == 1
    assert data["by_workflow_type"]["review"] == 1
    assert data["artifact_count"] == 1
    assert data["artifact_bytes"] == artifact_path.stat().st_size
    assert data["dead_letters_total"] == 1
    assert data["cost_usd"] == 0.25
    assert data["tokens_used"] == 1234
    assert data["llm_calls_count"] == 3


def test_workflow_health_summary_handles_aware_created_at(monkeypatch):
    client = _client(monkeypatch)

    created = client.post(
        "/api/v1/ai/workflows",
        json={
            "project_id": "p1",
            "input_source": "text",
            "text": "Aware timestamp health bugi donmemeli",
            "requires_approval": True,
            "workflow_type": "analysis",
        },
    ).json()

    from app.domains.agents.v2.run_store import get_run_store

    store = get_run_store()
    rec = store.get(created["workflow_id"])
    assert rec is not None
    rec.created_at = datetime.now(timezone.utc)

    resp = client.get("/api/v1/ai/workflows/health?limit=20")

    assert resp.status_code == 200
    data = resp.json()
    assert data["runs_total"] == 1
    assert data["active_runs"] == 1
    assert data["oldest_active_seconds"] is not None


def test_workflow_health_includes_ops_evidence(monkeypatch, tmp_path):
    client = _client(monkeypatch)

    report = tmp_path / "ai-workflow-signoff-20260518T061317Z.json"
    report.write_text(
        json.dumps(
            {
                "generated_at": "2026-05-18T06:13:17Z",
                "release_decision": "needs_external_soak_and_dr_signoff",
                "llm_quality_score": 9.89,
                "failed_required_checks": [],
                "operator_next_steps": ["Run staging soak", "Run DR drill"],
                "checks": [
                    {"name": "workflow_soak", "status": "skipped", "skipped_reason": "Pass --run-soak"},
                    {"name": "dr_restore_drill", "status": "skipped", "skipped_reason": "Pass --run-dr-drill"},
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("app.domains.ai.workflows_router._reports_dir", lambda: tmp_path)

    resp = client.get("/api/v1/ai/workflows/health?limit=20")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ops_evidence"]["release_decision"] == "needs_external_soak_and_dr_signoff"
    assert len(data["ops_evidence"]["checklist"]) == 4
    assert data["ops_evidence"]["checklist"][1]["status"] == "skipped"


def test_workflow_rejects_auto_merge(monkeypatch):
    client = _client(monkeypatch)

    resp = client.post(
        "/api/v1/ai/workflows",
        json={
            "project_id": "p1",
            "input_source": "text",
            "text": "Kod uret",
            "auto_merge": True,
        },
    )

    assert resp.status_code == 400
    assert "auto_merge" in resp.text


def test_register_state_artifacts_includes_approval_metadata(monkeypatch, tmp_path):
    import app.domains.agents.v2.run_store as rs_mod

    monkeypatch.setattr(settings, "artifacts_dir", str(tmp_path))
    rs_mod._singleton = None
    store = rs_mod.get_run_store()
    workflow_id, state = store.create(
        project_id="p1",
        user_id="u1",
        tenant_id="default",
        input_source="text",
        input_payload={"text": "login"},
    )
    junit = tmp_path / "junit.xml"
    junit.write_text("<testsuite />", encoding="utf-8")
    state.update(
        {
            "workflow_type": "test_generation",
            "run_result": {"junit_xml_path": str(junit)},
            "approvals": [
                {
                    "approval_id": "approval-1",
                    "decision": "approved",
                    "actor_id": "u1",
                }
            ],
        }
    )
    store.update_state(workflow_id, state)

    register_state_artifacts(workflow_id, state)

    artifacts = store.list_artifacts(workflow_id)
    junit_artifact = next(item for item in artifacts if item["kind"] == "junit_xml")
    assert junit_artifact["metadata"]["approval_id"] == "approval-1"
    assert junit_artifact["metadata"]["approval_decision"] == "approved"
    assert junit_artifact["metadata"]["hash_algorithm"] == "sha256"
    assert junit_artifact["metadata"]["sha256"]
