"""WebSocket presence — kim hangi sayfaya/projeye bakiyor.

In-memory icin tek instance varsayar; multi-instance icin Redis pub/sub
ile genisletilmeli.
# TODO(Wave-24): WebSocket rooms backend'i implement et.
# Şu an yalnızca polling tabanlı presence çalışıyor.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from typing import Optional

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class PresenceManager:
    def __init__(self) -> None:
        # room_id -> set of (user_id, websocket)
        self._rooms: dict[str, set[tuple[str, WebSocket]]] = defaultdict(set)
        # user_id -> display info for snapshots
        self._users: dict[str, dict] = {}
        self._lock = asyncio.Lock()

    async def join(
        self, room: str, user_id: str, websocket: WebSocket, *, display: Optional[dict] = None
    ) -> None:
        await websocket.accept()
        async with self._lock:
            self._rooms[room].add((user_id, websocket))
            if display:
                self._users[user_id] = display
        await self._broadcast_snapshot(room)

    async def leave(self, room: str, user_id: str, websocket: WebSocket) -> None:
        async with self._lock:
            self._rooms[room].discard((user_id, websocket))
            if not self._rooms[room]:
                self._rooms.pop(room, None)
        await self._broadcast_snapshot(room)

    def members(self, room: str) -> list[dict]:
        seen: set[str] = set()
        out: list[dict] = []
        for uid, _ in self._rooms.get(room, set()):
            if uid in seen:
                continue
            seen.add(uid)
            out.append({"user_id": uid, **self._users.get(uid, {})})
        return out

    async def _broadcast_snapshot(self, room: str) -> None:
        payload = json.dumps({"type": "presence", "room": room, "members": self.members(room)})
        targets = list(self._rooms.get(room, set()))
        for _, ws in targets:
            try:
                await ws.send_text(payload)
            except Exception:
                logger.debug("presence broadcast send failed", exc_info=True)


presence = PresenceManager()
