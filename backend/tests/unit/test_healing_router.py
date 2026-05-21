"""healing_router — webhook ingest + history + status.

Orchestrator'u mock'layıp endpoint davranışını izole ederiz. Böylece
integration test backend'in bütününü ayağa kaldırmak zorunda kalmaz.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.domains.coverup import healing_router as hr
from app.domains.coverup.healing.schemas import FailureEvent, HealingRun


class _StubUser:
    def __init__(self, id: str = "u1", tenant_id: str | None = None) -> None:
        self.id = id
        self.tenant_id = tenant_id
        self.email = f"{id}@x"


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Auth dependency'leri bypass et; orchestrator'ı mock'la."""
    from app.deps import get_current_user, require_permission

    # Auth bypass
    app_ = FastAPI()
    # reset module state
    hr._history.clear()
    hr.reset_orchestrator_for_testing()

    app_.include_router(hr.router, prefix="/api/v1")
    app_.dependency_overrides[get_current_user] = lambda: _StubUser(id="u1")
    # require_permission decorator factory döndürür; her çağrı yeni fn —
    # tüm çağrılar için aynı bypass function'ı enjekte et
    def _admin_bypass():
        return _StubUser(id="admin")

    # dep overrides: require_permission("X") çağrıları için, factory'nin
    # döndürdüğü tüm dependency'ler admin bypass'a map'lensin
    # Workaround: healing_router.router'ın scan'inde o factory çağrılarını
    # kap ve global override ile eşle
    for route in app_.routes:
        if hasattr(route, "dependant"):
            for dep in route.dependant.dependencies:  # type: ignore[attr-defined]
                if getattr(dep.call, "__qualname__", "").startswith("require_permission"):
                    app_.dependency_overrides[dep.call] = _admin_bypass

    return TestClient(app_)


def _build_run(event: FailureEvent, status: str = "succeeded") -> HealingRun:
    run = HealingRun(id="run-xyz", event=event)
    run.status = status  # type: ignore[assignment]
    run.pr_url = "https://github.com/acme/proj/pull/99"
    run.pr_number = 99
    run.draft = False
    run.finished_at = datetime.now(timezone.utc)
    return run


def _sample_event(**overrides) -> dict:
    base = {
        "run_id": "abcd1234-ffff-eeee-dddd-cccccccccccc",
        "test_file_path": "tests/login.spec.ts",
        "locator": ".submit-btn",
        "dom_snapshot": "<button data-testid='s'>X</button>",
        "error_message": "Timeout",
    }
    base.update(overrides)
    return base


# ── Tests ────────────────────────────────────────────────────────────────


def test_ingest_triggers_orchestrator_and_records(
    app: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict = {}

    class _FakeOrch:
        def run(self, event: FailureEvent) -> HealingRun:
            captured["event"] = event
            return _build_run(event)

    monkeypatch.setattr(hr, "_get_orchestrator", lambda: _FakeOrch())

    payload = _sample_event()
    resp = app.post("/api/v1/coverup/heal/events", json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "succeeded"
    assert data["pr_url"].endswith("/pull/99")
    # Tenant id boşsa user'dan düşmeli
    assert captured["event"].tenant_id == "u1"


def test_ingest_preserves_explicit_tenant(
    app: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _FakeOrch:
        def run(self, event: FailureEvent) -> HealingRun:
            assert event.tenant_id == "explicit-tenant"
            return _build_run(event)

    monkeypatch.setattr(hr, "_get_orchestrator", lambda: _FakeOrch())
    resp = app.post(
        "/api/v1/coverup/heal/events",
        json=_sample_event(tenant_id="explicit-tenant"),
    )
    assert resp.status_code == 200


def test_ingest_rejects_path_traversal(
    app: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(hr, "_get_orchestrator", lambda: MagicMock())
    resp = app.post(
        "/api/v1/coverup/heal/events",
        json=_sample_event(test_file_path="../etc/passwd"),
    )
    assert resp.status_code == 422  # pydantic validation


def test_list_runs_reverse_chronological(
    app: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _FakeOrch:
        def __init__(self) -> None:
            self.i = 0

        def run(self, event: FailureEvent) -> HealingRun:
            self.i += 1
            r = _build_run(event)
            r.id = f"r{self.i:02d}"
            return r

    fake = _FakeOrch()
    monkeypatch.setattr(hr, "_get_orchestrator", lambda: fake)
    for i in range(3):
        resp = app.post(
            "/api/v1/coverup/heal/events",
            json=_sample_event(
                run_id=f"run-{i:03d}" * 4,  # en az 1 char yeter, uzun da OK
                test_file_path=f"tests/spec{i}.spec.ts",
            ),
        )
        assert resp.status_code == 200

    list_resp = app.get("/api/v1/coverup/heal/runs?limit=10")
    assert list_resp.status_code == 200
    ids = [r["id"] for r in list_resp.json()]
    # En son ingest en başta
    assert ids == ["r03", "r02", "r01"]


def test_list_runs_filter_by_status(
    app: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    seq = ["succeeded", "no_proposal", "succeeded"]

    class _FakeOrch:
        def __init__(self) -> None:
            self.i = 0

        def run(self, event: FailureEvent) -> HealingRun:
            r = _build_run(event, status=seq[self.i])
            r.id = f"r{self.i}"
            self.i += 1
            return r

    fake = _FakeOrch()
    monkeypatch.setattr(hr, "_get_orchestrator", lambda: fake)
    for i in range(3):
        app.post(
            "/api/v1/coverup/heal/events",
            json=_sample_event(run_id=f"r-{i}" * 5),
        )
    resp = app.get("/api/v1/coverup/heal/runs?status=succeeded")
    assert resp.status_code == 200
    ids = [r["id"] for r in resp.json()]
    assert sorted(ids) == ["r0", "r2"]


def test_get_run_by_id(
    app: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _FakeOrch:
        def run(self, event: FailureEvent) -> HealingRun:
            r = _build_run(event)
            r.id = "unique-id-42"
            return r

    monkeypatch.setattr(hr, "_get_orchestrator", lambda: _FakeOrch())
    app.post("/api/v1/coverup/heal/events", json=_sample_event())
    resp = app.get("/api/v1/coverup/heal/runs/unique-id-42")
    assert resp.status_code == 200
    assert resp.json()["id"] == "unique-id-42"


def test_get_run_404(app: TestClient) -> None:
    resp = app.get("/api/v1/coverup/heal/runs/ghost")
    assert resp.status_code == 404


def test_status_reflects_wiring(
    app: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    resp = app.get("/api/v1/coverup/heal/status")
    assert resp.status_code == 200
    body = resp.json()
    assert "llm_bound" in body
    assert "github_configured" in body
    assert "repo_root" in body
    assert body["feature_flag_key"] == "coverup.auto_heal.enabled"


def test_history_ring_buffer_bounded() -> None:
    hr._history.clear()
    # 210 ekleyelim, max 200 olmalı
    for i in range(210):
        ev = FailureEvent(
            run_id=f"r-{i}",
            test_file_path="tests/a.spec.ts",
            locator=".x",
        )
        r = _build_run(ev)
        r.id = f"id-{i}"
        hr._record(r)
    assert len(hr._history) == 200
    latest = hr._recent(5)
    assert latest[0].id == "id-209"
