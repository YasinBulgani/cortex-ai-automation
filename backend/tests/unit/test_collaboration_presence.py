"""
Collaboration presence birim testleri — 6 test.

PresenceManager'ın saf in-memory davranislarini dogrular.
Gercek WebSocket baglantisi gerekmez; WebSocket mock ile test edilir.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

try:
    from app.domains.collaboration.presence import PresenceManager
    _IMPORT_OK = True
except Exception:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="collaboration presence import failed")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ws() -> MagicMock:
    """Kabul edilmis bir WebSocket mock olusturur."""
    ws = MagicMock()
    ws.accept = AsyncMock()
    ws.send_text = AsyncMock()
    return ws


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestPresenceManagerInit:
    def test_presence_manager_init(self):
        """PresenceManager bos odalar ve kullanici sozluguyle baslar."""
        pm = PresenceManager()
        assert hasattr(pm, "_rooms")
        assert hasattr(pm, "_users")
        assert len(pm._rooms) == 0
        assert len(pm._users) == 0


class TestJoinRoom:
    @pytest.mark.asyncio
    async def test_join_room(self):
        """Kullanici odaya katildiginda websocket kabul edilir ve oda kaydedilir."""
        pm = PresenceManager()
        ws = _make_ws()

        await pm.join("room-1", "user-1", ws, display={"name": "Alice"})

        ws.accept.assert_awaited_once()
        members = pm.members("room-1")
        assert len(members) == 1
        assert members[0]["user_id"] == "user-1"
        assert members[0]["name"] == "Alice"

    @pytest.mark.asyncio
    async def test_join_room_multiple_users(self):
        """Birden fazla kullanici ayni odaya katilabilir."""
        pm = PresenceManager()
        ws1, ws2 = _make_ws(), _make_ws()

        await pm.join("room-1", "user-1", ws1)
        await pm.join("room-1", "user-2", ws2)

        members = pm.members("room-1")
        user_ids = {m["user_id"] for m in members}
        assert user_ids == {"user-1", "user-2"}


class TestLeaveRoom:
    @pytest.mark.asyncio
    async def test_leave_room(self):
        """Kullanici odadan ciktiginda listeden kaldirilir."""
        pm = PresenceManager()
        ws = _make_ws()

        await pm.join("room-1", "user-1", ws)
        await pm.leave("room-1", "user-1", ws)

        members = pm.members("room-1")
        assert members == []

    @pytest.mark.asyncio
    async def test_leave_room_only_target_removed(self):
        """Odadan cikan sadece ilgili kullanici; diger kullanici kalir."""
        pm = PresenceManager()
        ws1, ws2 = _make_ws(), _make_ws()

        await pm.join("room-1", "user-1", ws1)
        await pm.join("room-1", "user-2", ws2)
        await pm.leave("room-1", "user-1", ws1)

        members = pm.members("room-1")
        assert len(members) == 1
        assert members[0]["user_id"] == "user-2"


class TestGetRoomUsers:
    @pytest.mark.asyncio
    async def test_get_room_users(self):
        """members() odadaki tum kullanicilari dondurur."""
        pm = PresenceManager()
        ws1, ws2 = _make_ws(), _make_ws()

        await pm.join("room-A", "user-1", ws1, display={"name": "Alice"})
        await pm.join("room-A", "user-2", ws2, display={"name": "Bob"})

        members = pm.members("room-A")
        assert len(members) == 2
        names = {m["name"] for m in members}
        assert names == {"Alice", "Bob"}

    def test_get_room_users_empty_room(self):
        """Var olmayan oda icin bos liste donmelidir."""
        pm = PresenceManager()
        assert pm.members("nonexistent-room") == []


class TestBroadcastExcludesSender:
    @pytest.mark.asyncio
    async def test_broadcast_excludes_sender(self):
        """Presence snapshot yayini tum odalilara gider; gonderici dahil herkes alir."""
        pm = PresenceManager()
        ws_sender = _make_ws()
        ws_other = _make_ws()

        await pm.join("room-1", "user-sender", ws_sender)
        # ws_sender.send_text ilk join snapshot'i icin zaten cagrilmis olacak;
        # sayaci sifirla ve ikinci kullanicinin katilimini izle.
        ws_sender.send_text.reset_mock()
        ws_other.send_text.reset_mock()

        await pm.join("room-1", "user-other", ws_other)

        # Ikinci join'dan sonra her iki ws da snapshot almali.
        ws_sender.send_text.assert_awaited_once()
        ws_other.send_text.assert_awaited_once()

        # Payload dogru JSON ve her iki kullaniciyi icermeli.
        payload_str = ws_sender.send_text.call_args[0][0]
        payload = json.loads(payload_str)
        assert payload["type"] == "presence"
        assert payload["room"] == "room-1"
        member_ids = {m["user_id"] for m in payload["members"]}
        assert "user-sender" in member_ids
        assert "user-other" in member_ids


class TestRoomCleanupOnEmpty:
    @pytest.mark.asyncio
    async def test_room_cleanup_on_empty(self):
        """Son kullanici odadan cikinca oda sozlukten silinmeli."""
        pm = PresenceManager()
        ws = _make_ws()

        await pm.join("room-cleanup", "user-1", ws)
        assert "room-cleanup" in pm._rooms

        await pm.leave("room-cleanup", "user-1", ws)

        # Oda tamamen silinmeli, bos set kalmamali.
        assert "room-cleanup" not in pm._rooms

    @pytest.mark.asyncio
    async def test_room_not_removed_while_users_remain(self):
        """Odada hala kullanici varken oda silinmemeli."""
        pm = PresenceManager()
        ws1, ws2 = _make_ws(), _make_ws()

        await pm.join("room-keep", "user-1", ws1)
        await pm.join("room-keep", "user-2", ws2)
        await pm.leave("room-keep", "user-1", ws1)

        assert "room-keep" in pm._rooms
        assert len(pm._rooms["room-keep"]) == 1
