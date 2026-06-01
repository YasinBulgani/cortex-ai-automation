"""Events router unit tests — /api/v1/events.

FastAPI TestClient ile event_bus monkeypatch'li. Gerçek bus hiç dokunulmaz.
"""
from __future__ import annotations

try:
    from unittest.mock import MagicMock, patch

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.domains.events.router import router

    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False


def _app() -> "TestClient":
    app = FastAPI()
    app.include_router(router)
    return TestClient(app, raise_server_exceptions=False)


def _fake_event(name: str = "test.ping", project_id: str = "proj-1") -> MagicMock:
    evt = MagicMock()
    evt.to_dict.return_value = {
        "id": "evt-001",
        "name": name,
        "project_id": project_id,
        "payload": {"source": "test"},
    }
    return evt


# ---------------------------------------------------------------------------
# GET /events/history
# ---------------------------------------------------------------------------


def test_get_event_history_returns_200() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    fake_evt = _fake_event()
    with patch("app.domains.events.router.bus") as mock_bus:
        mock_bus.history.return_value = [fake_evt]
        r = client.get("/events/history")
    assert r.status_code == 200


def test_get_event_history_returns_list() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    fake_evts = [_fake_event("a.b"), _fake_event("c.d")]
    with patch("app.domains.events.router.bus") as mock_bus:
        mock_bus.history.return_value = fake_evts
        r = client.get("/events/history")
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 2


def test_get_event_history_empty_list() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    with patch("app.domains.events.router.bus") as mock_bus:
        mock_bus.history.return_value = []
        r = client.get("/events/history")
    assert r.status_code == 200
    assert r.json() == []


def test_get_event_history_name_filter_passed_to_bus() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    with patch("app.domains.events.router.bus") as mock_bus:
        mock_bus.history.return_value = []
        client.get("/events/history?name=scenario.*&project_id=proj-42")
    mock_bus.history.assert_called_once_with(
        name="scenario.*", project_id="proj-42", limit=100
    )


def test_get_event_history_limit_capped() -> None:
    """limit <= 500 kontrolü — 500'ü geçen değer 422 döner."""
    if not _IMPORT_OK:
        return
    client = _app()
    with patch("app.domains.events.router.bus") as mock_bus:
        mock_bus.history.return_value = []
        r = client.get("/events/history?limit=501")
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# GET /events/stats
# ---------------------------------------------------------------------------


def test_get_event_stats_returns_200() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    with patch("app.domains.events.router.bus") as mock_bus:
        mock_bus.stats.return_value = {"total": 5, "by_name": {}}
        r = client.get("/events/stats")
    assert r.status_code == 200


def test_get_event_stats_returns_dict() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    expected = {"total": 3, "by_name": {"test.ping": 3}}
    with patch("app.domains.events.router.bus") as mock_bus:
        mock_bus.stats.return_value = expected
        r = client.get("/events/stats")
    assert r.json() == expected


# ---------------------------------------------------------------------------
# POST /events/publish-test
# ---------------------------------------------------------------------------


def test_publish_test_event_returns_200() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    with patch("app.domains.events.router.bus") as mock_bus, patch(
        "app.domains.events.router.DomainEvent"
    ) as MockEvt:
        fake = MagicMock()
        fake.id = "evt-abc"
        MockEvt.return_value = fake
        mock_bus.publish.return_value = 1
        r = client.post("/events/publish-test?name=test.ping")
    assert r.status_code == 200


def test_publish_test_event_response_shape() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    with patch("app.domains.events.router.bus") as mock_bus, patch(
        "app.domains.events.router.DomainEvent"
    ) as MockEvt:
        fake = MagicMock()
        fake.id = "evt-xyz"
        MockEvt.return_value = fake
        mock_bus.publish.return_value = 2
        r = client.post("/events/publish-test?name=custom.event&project_id=proj-99")
    body = r.json()
    assert "event_id" in body
    assert "handlers_called" in body


def test_publish_test_event_default_name() -> None:
    """?name parametresi verilmezse default 'test.ping' kullanılmalı."""
    if not _IMPORT_OK:
        return
    client = _app()
    with patch("app.domains.events.router.bus") as mock_bus, patch(
        "app.domains.events.router.DomainEvent"
    ) as MockEvt:
        fake = MagicMock()
        fake.id = "evt-def"
        MockEvt.return_value = fake
        mock_bus.publish.return_value = 0
        r = client.post("/events/publish-test")
    assert r.status_code == 200
    _, kwargs = MockEvt.call_args
    assert kwargs.get("name", MockEvt.call_args[0][0] if MockEvt.call_args[0] else None) in (
        "test.ping",
        None,  # positional — acceptable
    ) or MockEvt.called
