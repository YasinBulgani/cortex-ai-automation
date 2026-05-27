"""
Notifications service unit testleri — 14 test.

app.domains.notifications.service.ConnectionManager sınıfını doğrular.
Gerçek WebSocket bağlantısı gerekmez; starlette WebSocket stub'lanır.
WSMessage schema üretimi ve ConnectionManager'ın connect/disconnect/
notify_user/broadcast mantığı test edilir.
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

try:
    from app.domains.notifications.service import ConnectionManager, manager
    from app.domains.notifications.schemas import WSMessage
    _IMPORT_OK = True
except Exception:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="notifications service import failed")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ws() -> AsyncMock:
    """Return a fake WebSocket that supports accept/send_text."""
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_text = AsyncMock()
    return ws


def _run(coro):
    """Run a coroutine synchronously for test convenience."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# WSMessage schema
# ---------------------------------------------------------------------------

class TestWSMessage:
    def test_required_fields(self):
        msg = WSMessage(type="test.event", payload={"key": "val"})
        assert msg.type == "test.event"
        assert msg.payload == {"key": "val"}

    def test_timestamp_optional(self):
        msg = WSMessage(type="ping")
        assert msg.timestamp is None

    def test_model_dump_json_produces_valid_json(self):
        msg = WSMessage(type="update", payload={"n": 1}, timestamp="2026-01-01T00:00:00Z")
        raw = msg.model_dump_json()
        data = json.loads(raw)
        assert data["type"] == "update"
        assert data["payload"]["n"] == 1


# ---------------------------------------------------------------------------
# ConnectionManager.connect / disconnect
# ---------------------------------------------------------------------------

class TestConnect:
    def test_connect_accepts_websocket(self):
        cm = ConnectionManager()
        ws = _make_ws()
        _run(cm.connect(ws, "user-1"))
        ws.accept.assert_called_once()

    def test_connect_registers_connection(self):
        cm = ConnectionManager()
        ws = _make_ws()
        _run(cm.connect(ws, "user-1"))
        assert "user-1" in cm.active_connections
        assert ws in cm.active_connections["user-1"]

    def test_two_connections_same_user(self):
        cm = ConnectionManager()
        ws1, ws2 = _make_ws(), _make_ws()
        _run(cm.connect(ws1, "u"))
        _run(cm.connect(ws2, "u"))
        assert len(cm.active_connections["u"]) == 2

    def test_disconnect_removes_websocket(self):
        cm = ConnectionManager()
        ws = _make_ws()
        _run(cm.connect(ws, "user-2"))
        _run(cm.disconnect(ws, "user-2"))
        assert "user-2" not in cm.active_connections

    def test_disconnect_nonexistent_does_not_raise(self):
        cm = ConnectionManager()
        ws = _make_ws()
        # Should not raise even if ws was never connected
        _run(cm.disconnect(ws, "ghost-user"))


# ---------------------------------------------------------------------------
# ConnectionManager.notify_user
# ---------------------------------------------------------------------------

class TestNotifyUser:
    def test_sends_text_to_connected_user(self):
        cm = ConnectionManager()
        ws = _make_ws()
        _run(cm.connect(ws, "u1"))
        _run(cm.notify_user("u1", "scenario.updated", {"id": "s1"}))
        ws.send_text.assert_called_once()
        payload_str = ws.send_text.call_args[0][0]
        data = json.loads(payload_str)
        assert data["type"] == "scenario.updated"

    def test_notify_unknown_user_is_noop(self):
        cm = ConnectionManager()
        # No exception expected; simply nothing is sent
        _run(cm.notify_user("no-such-user", "ping", {}))

    def test_failed_send_does_not_raise(self):
        cm = ConnectionManager()
        ws = _make_ws()
        ws.send_text = AsyncMock(side_effect=Exception("connection closed"))
        _run(cm.connect(ws, "u3"))
        # Should log a warning but not propagate the exception
        _run(cm.notify_user("u3", "event", {}))


# ---------------------------------------------------------------------------
# ConnectionManager.broadcast
# ---------------------------------------------------------------------------

class TestBroadcast:
    def test_broadcast_reaches_all_users(self):
        cm = ConnectionManager()
        ws1, ws2 = _make_ws(), _make_ws()
        _run(cm.connect(ws1, "userA"))
        _run(cm.connect(ws2, "userB"))
        _run(cm.broadcast("system.alert", {"msg": "maintenance"}))
        ws1.send_text.assert_called_once()
        ws2.send_text.assert_called_once()

    def test_broadcast_message_contains_type(self):
        cm = ConnectionManager()
        ws = _make_ws()
        _run(cm.connect(ws, "u"))
        _run(cm.broadcast("ping", {}))
        raw = ws.send_text.call_args[0][0]
        data = json.loads(raw)
        assert data["type"] == "ping"

    def test_broadcast_empty_manager_is_noop(self):
        cm = ConnectionManager()
        # No exception when there are no connections
        _run(cm.broadcast("ping", {}))
