"""Realtime collaboration endpoints (presence WS + mention preview)."""

from __future__ import annotations

import logging
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.deps import get_current_user
from app.domains.auth.service import decode_token
from app.infra.database import get_db
from app.infra.models import User

from . import schemas as domain_schemas  # noqa: F401 — schemas module created for type contract use
from .mentions import extract_handles, parse_and_resolve
from .presence import presence

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/collab", tags=["collaboration"])


@router.websocket("/ws/presence")
async def ws_presence(websocket: WebSocket, room: str = Query(...), token: str = Query("")):
    """Connect a user to a room; broadcast member snapshot on every change."""
    if not token:
        token = websocket.cookies.get("bgts_access_token", "")
    try:
        payload = decode_token(token)
        user_id = payload["sub"]
    except (jwt.PyJWTError, KeyError):
        await websocket.close(code=4001)
        return

    # Optionally load display info synchronously
    from app.infra.database import SessionLocal
    display: dict = {}
    with SessionLocal() as db:
        u = db.get(User, user_id)
        if u:
            display = {"email": u.email, "full_name": u.full_name}

    await presence.join(room, user_id, websocket, display=display)
    try:
        while True:
            # Heartbeat — ignore messages, just keep open
            msg = await websocket.receive_text()
            if msg == "ping":
                await websocket.send_text('{"type":"pong"}')
    except WebSocketDisconnect:
        pass
    finally:
        await presence.leave(room, user_id, websocket)


@router.get("/presence/{room}")
def get_presence(
    room: str,
    user: Annotated[User, Depends(get_current_user)],
):
    return {"room": room, "members": presence.members(room)}


@router.post("/mentions/preview")
def preview_mentions(
    body: dict,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    text = body.get("body", "")
    handles = extract_handles(text)
    users = parse_and_resolve(db, text)
    return {
        "handles": handles,
        "resolved": [{"id": u.id, "email": u.email, "full_name": u.full_name} for u in users],
    }
