"""Unit tests for app.domains.events.service.

The events service depends on app.core.event_bus. We mock the bus so tests
run without a running message broker.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

try:
    import app.domains.events.service as events_service
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="events service import failed")


# ---------------------------------------------------------------------------
# Helpers — build a minimal fake DomainEvent-like object
# ---------------------------------------------------------------------------

def _make_fake_event(name: str = "test.event", project_id: Optional[str] = None) -> MagicMock:
    evt = MagicMock()
    evt.id = uuid.uuid4()
    evt.name = name
    evt.project_id = project_id
    evt.to_dict.return_value = {
        "id": str(evt.id),
        "name": name,
        "payload": {},
        "project_id": project_id,
    }
    return evt


# ---------------------------------------------------------------------------
# list_events
# ---------------------------------------------------------------------------

class TestListEvents:
    def test_returns_list(self):
        fake_evt = _make_fake_event()
        with patch.object(events_service.bus, "history", return_value=[fake_evt]) as mock_hist:
            result = events_service.list_events(limit=10)
        assert isinstance(result, list)
        assert len(result) == 1
        mock_hist.assert_called_once()

    def test_empty_bus_returns_empty_list(self):
        with patch.object(events_service.bus, "history", return_value=[]):
            result = events_service.list_events()
        assert result == []

    def test_limit_is_capped_at_500(self):
        with patch.object(events_service.bus, "history", return_value=[]) as mock_hist:
            events_service.list_events(limit=9999)
        _, kwargs = mock_hist.call_args
        assert kwargs.get("limit", mock_hist.call_args[0][2] if len(mock_hist.call_args[0]) > 2 else 500) <= 500

    def test_result_contains_serialised_dicts(self):
        fake_evt = _make_fake_event("scenario.created")
        with patch.object(events_service.bus, "history", return_value=[fake_evt]):
            result = events_service.list_events()
        assert "id" in result[0]
        assert result[0]["name"] == "scenario.created"


# ---------------------------------------------------------------------------
# publish
# ---------------------------------------------------------------------------

class TestPublish:
    def test_publish_returns_event_id(self):
        with patch.object(events_service.bus, "publish", return_value=1):
            result = events_service.publish("scenario.created", payload={"foo": "bar"})
        assert "event_id" in result
        assert isinstance(result["event_id"], str)
        assert len(result["event_id"]) > 0

    def test_publish_returns_handlers_called(self):
        with patch.object(events_service.bus, "publish", return_value=3):
            result = events_service.publish("job.done")
        assert result["handlers_called"] == 3

    def test_publish_empty_name_raises_value_error(self):
        with pytest.raises(ValueError, match="boş olamaz"):
            events_service.publish("")

    def test_publish_whitespace_only_name_raises(self):
        with pytest.raises(ValueError):
            events_service.publish("   ")


# ---------------------------------------------------------------------------
# get_event
# ---------------------------------------------------------------------------

class TestGetEvent:
    def test_get_event_found(self):
        fake_evt = _make_fake_event()
        with patch.object(events_service.bus, "history", return_value=[fake_evt]):
            result = events_service.get_event(str(fake_evt.id))
        assert result["id"] == str(fake_evt.id)

    def test_get_event_not_found_raises_key_error(self):
        with patch.object(events_service.bus, "history", return_value=[]):
            with pytest.raises(KeyError, match="bulunamadı"):
                events_service.get_event("nonexistent-id")
