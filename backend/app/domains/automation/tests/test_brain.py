from __future__ import annotations

from app.domains.automation.brain import AutomationBrainService, AutomationRunStore
from app.domains.automation.schemas import AutomationRunCreate


def test_create_and_list_normalized_run() -> None:
    service = AutomationBrainService(AutomationRunStore())

    run = service.create_run(
        AutomationRunCreate(
            project_id="p1",
            kind="web",
            name="Login smoke",
            target="login.feature",
        ),
        created_by="u1",
    )

    assert run.id.startswith("arun_")
    assert run.status == "queued"
    assert run.provenance == "fallback"
    assert run.next_action is not None
    assert "feature=login.feature" in run.next_action["href"]

    listed = service.list_runs(project_id="p1")
    assert listed.total == 1
    assert listed.items[0].id == run.id


def test_cancel_and_retry_run() -> None:
    service = AutomationBrainService(AutomationRunStore())
    run = service.create_run(AutomationRunCreate(project_id="p1", kind="mobile", device="Pixel 7"))

    cancelled = service.cancel_run(run.id)
    assert cancelled is not None
    assert cancelled.status == "cancelled"

    retry = service.retry_run(run.id, created_by="u2")
    assert retry is not None
    assert retry.retry_of == run.id
    assert retry.trigger == "retry"
    assert retry.device == "Pixel 7"
