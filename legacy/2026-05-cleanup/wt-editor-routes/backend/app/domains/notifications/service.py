from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from fastapi import WebSocket

from app.domains.notifications.schemas import WSMessage

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str) -> None:
        await websocket.accept()
        self.active_connections.setdefault(user_id, []).append(websocket)
        logger.info("WS connected: user=%s (total=%d)", user_id, len(self.active_connections[user_id]))

    async def disconnect(self, websocket: WebSocket, user_id: str) -> None:
        conns = self.active_connections.get(user_id, [])
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            self.active_connections.pop(user_id, None)
        logger.info("WS disconnected: user=%s", user_id)

    async def notify_user(self, user_id: str, event_type: str, payload: dict) -> None:
        msg = WSMessage(
            type=event_type,
            payload=payload,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        data = msg.model_dump_json()
        for ws in self.active_connections.get(user_id, []):
            try:
                await ws.send_text(data)
            except Exception:
                logger.warning("Failed to send WS message to user=%s", user_id)

    async def broadcast(self, event_type: str, payload: dict) -> None:
        msg = WSMessage(
            type=event_type,
            payload=payload,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        data = msg.model_dump_json()
        for user_id, connections in self.active_connections.items():
            for ws in connections:
                try:
                    await ws.send_text(data)
                except Exception:
                    logger.warning("Failed to broadcast WS message to user=%s", user_id)


manager = ConnectionManager()
