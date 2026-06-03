"""Pure unit tests — events domain ve onboarding domain.

Events testleri:
    * test_event_publish             — event yayınlanıyor
    * test_event_subscribe           — event alınıyor
    * test_event_payload_validation  — geçersiz payload reddediliyor
    * test_event_bus_isolation       — farklı tenant olayları karışmıyor

Onboarding testleri:
    * test_onboarding_step_1_start       — ilk adım (ilk tamamlama)
    * test_onboarding_step_completion    — adım tamamlama (progress hesabı)
    * test_onboarding_skip               — isteğe bağlı adımı atla
    * test_onboarding_reset              — proje state sıfırla
"""
from __future__ import annotations

import pytest


# ── Events ────────────────────────────────────────────────────────────────────


def test_event_publish():
    """publish() başarılı olduğunda event_id ve handlers_called döner."""
    from app.domains.events.service import publish

    result = publish(name="test.published", payload={"key": "value"}, project_id="proj-001")

    assert "event_id" in result
    assert isinstance(result["event_id"], str)
    assert result["event_id"].startswith("evt-")
    assert "handlers_called" in result
    assert isinstance(result["handlers_called"], int)


def test_event_subscribe():
    """subscribe() kaydedilen handler, event yayınlanınca tetiklenir."""
    from app.core.event_bus import bus, DomainEvent

    received: list[DomainEvent] = []

    def handler(evt: DomainEvent) -> None:
        received.append(evt)

    unsubscribe = bus.subscribe("unit.test_subscribe", handler)
    try:
        evt = DomainEvent(name="unit.test_subscribe", payload={"ping": True})
        bus.publish(evt)

        assert len(received) == 1
        assert received[0].name == "unit.test_subscribe"
        assert received[0].payload["ping"] is True
    finally:
        unsubscribe()


def test_event_payload_validation():
    """publish() boş event adı aldığında ValueError fırlatır."""
    from app.domains.events.service import publish

    with pytest.raises(ValueError, match="boş olamaz"):
        publish(name="", payload={"data": 1})

    with pytest.raises(ValueError):
        publish(name="   ")


def test_event_bus_isolation():
    """project_id filtresi farklı tenant eventlerini birbirine karıştırmaz."""
    from app.core.event_bus import bus, DomainEvent

    evt_a = DomainEvent(name="tenant.event", payload={"tenant": "A"}, project_id="tenant-A")
    evt_b = DomainEvent(name="tenant.event", payload={"tenant": "B"}, project_id="tenant-B")

    bus.publish(evt_a)
    bus.publish(evt_b)

    history_a = bus.history(project_id="tenant-A", limit=50)
    history_b = bus.history(project_id="tenant-B", limit=50)

    # Her tenant yalnızca kendi eventini görür
    ids_a = {e.id for e in history_a}
    ids_b = {e.id for e in history_b}

    assert evt_a.id in ids_a
    assert evt_b.id not in ids_a

    assert evt_b.id in ids_b
    assert evt_a.id not in ids_b


# ── Onboarding ────────────────────────────────────────────────────────────────


def test_onboarding_step_1_start():
    """İlk adım tamamlanmadan önce completion_pct sıfır ve is_fully_onboarded False."""
    from app.domains.onboarding.service import compute_progress, DEFAULT_STEPS

    project_id = "proj-onb-start"
    completed: dict[str, bool] = {}

    progress = compute_progress(project_id=project_id, completed=completed, steps=DEFAULT_STEPS)

    assert progress.project_id == project_id
    assert progress.completion_pct == 0.0
    assert progress.completed_required == 0
    assert progress.is_fully_onboarded is False
    # İlk adım kataloğu yüklenmiş olmalı
    assert len(progress.steps) == len(DEFAULT_STEPS)
    # İlk adım id'si 'create_project'
    assert progress.steps[0].id == "create_project"
    assert progress.completed.get("create_project") is False


def test_onboarding_step_completion():
    """Zorunlu adımlar tamamlandıkça completion_pct artar; hepsi bitince is_fully_onboarded True."""
    from app.domains.onboarding.service import (
        compute_progress,
        DEFAULT_STEPS,
        progress_store,
    )

    project_id = "proj-onb-completion"
    progress_store.reset(project_id)

    required_steps = [s for s in DEFAULT_STEPS if not s.is_optional]

    # Adım adım tamamla
    for step in required_steps:
        progress_store.set(project_id, step.id, True)

    completed_state = progress_store.get(project_id)
    progress = compute_progress(project_id=project_id, completed=completed_state, steps=DEFAULT_STEPS)

    assert progress.completion_pct == 100.0
    assert progress.completed_required == len(required_steps)
    assert progress.is_fully_onboarded is True

    # Temizle
    progress_store.reset(project_id)


def test_onboarding_skip():
    """İsteğe bağlı (is_optional=True) adım atlanabilir, is_fully_onboarded etkilenmez."""
    from app.domains.onboarding.service import (
        compute_progress,
        DEFAULT_STEPS,
        progress_store,
    )

    project_id = "proj-onb-skip"
    progress_store.reset(project_id)

    optional_steps = [s for s in DEFAULT_STEPS if s.is_optional]
    required_steps = [s for s in DEFAULT_STEPS if not s.is_optional]

    # Yalnızca zorunlu adımları tamamla, isteğe bağlı adımları atla (done=False bırak)
    for step in required_steps:
        progress_store.set(project_id, step.id, True)
    # İsteğe bağlı adımları hiç işaretleme (skip)

    completed_state = progress_store.get(project_id)
    progress = compute_progress(project_id=project_id, completed=completed_state, steps=DEFAULT_STEPS)

    assert progress.is_fully_onboarded is True, (
        "Zorunlu adımlar tamam olduğunda opsiyonel adımlar atlanabilmeli"
    )
    # İsteğe bağlı adımlar False olarak gösterilmeli
    for step in optional_steps:
        assert progress.completed.get(step.id) is False

    progress_store.reset(project_id)


def test_onboarding_reset():
    """reset() çağrıldıktan sonra proje state tamamen temizlenir."""
    from app.domains.onboarding.service import (
        compute_progress,
        DEFAULT_STEPS,
        progress_store,
    )

    project_id = "proj-onb-reset"

    # Birkaç adım tamamla
    for step in DEFAULT_STEPS[:3]:
        progress_store.set(project_id, step.id, True)

    before = progress_store.get(project_id)
    assert any(v is True for v in before.values()), "Tamamlama kaydedilmeli"

    # Sıfırla
    progress_store.reset(project_id)

    after = progress_store.get(project_id)
    assert after == {}, "Reset sonrası state boş olmalı"

    # compute_progress sıfır noktaya dönmeli
    progress = compute_progress(project_id=project_id, completed=after, steps=DEFAULT_STEPS)
    assert progress.completion_pct == 0.0
    assert progress.is_fully_onboarded is False
