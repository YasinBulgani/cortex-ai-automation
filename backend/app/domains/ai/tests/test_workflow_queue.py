from __future__ import annotations

import pytest


def test_production_like_auto_queue_is_rq_fail_closed(monkeypatch):
    from app.config import settings
    from app.domains.ai.workflow_queue import enqueue_ai_workflow

    class Background:
        def add_task(self, *args, **kwargs):  # pragma: no cover - should not be called
            raise AssertionError("production-like auto queue must not fall back to background")

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AGENTS_V2_RUN_STORE", "memory")
    monkeypatch.setattr(settings, "agents_v2_queue_backend", "auto")
    monkeypatch.setattr(settings, "redis_url", "redis://127.0.0.1:1/0")
    monkeypatch.setattr("app.domains.ai.workflow_queue.Redis.from_url", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("redis down")))

    with pytest.raises(RuntimeError, match="redis down"):
        enqueue_ai_workflow(
            run_id="run-1",
            state={"run_id": "run-1", "project_id": "p1", "user_id": "u1", "tenant_id": "t1"},
            background=Background(),  # type: ignore[arg-type]
        )
