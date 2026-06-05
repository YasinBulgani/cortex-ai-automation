"""Navigation domain router — prefix /navigation."""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.deps import get_current_user
from app.infra.models import User

from .service import add_bookmark, get_nav_tree, get_user_bookmarks, remove_bookmark

router = APIRouter(prefix="/navigation", tags=["navigation"])

CurrentUser = Annotated[User, Depends(get_current_user)]


# ── Request models ────────────────────────────────────────────────────────


class AddBookmarkRequest(BaseModel):
    path: str


# ── Endpoints ─────────────────────────────────────────────────────────────


@router.get("/tree", summary="Get the full navigation tree")
def navigation_tree() -> list[dict[str, Any]]:
    """Return the application navigation tree. Public endpoint — no auth required."""
    return get_nav_tree()


@router.get("/bookmarks/{user_id}", summary="Get bookmarks for a user")
def user_bookmarks(user_id: str, user: CurrentUser) -> list[str]:
    """Return the list of bookmarked paths for *user_id*."""
    if user.id != user_id:
        raise HTTPException(403, "Başka kullanıcının bookmark'larına erişemezsiniz")
    return get_user_bookmarks(user_id)


@router.post("/bookmarks/{user_id}", summary="Add a bookmark for a user")
def create_bookmark(user_id: str, body: AddBookmarkRequest, user: CurrentUser) -> dict[str, bool]:
    """Add *path* to *user_id*'s bookmarks. Idempotent."""
    if user.id != user_id:
        raise HTTPException(403, "Başka kullanıcının bookmark'larına erişemezsiniz")
    try:
        add_bookmark(user_id, body.path)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True}


@router.delete(
    "/bookmarks/{user_id}/{path:path}",
    summary="Remove a bookmark for a user",
)
def delete_bookmark(user_id: str, path: str, user: CurrentUser) -> dict[str, bool]:
    """Remove the bookmark at *path* for *user_id*.

    Returns 404 if the bookmark is not found.
    """
    if user.id != user_id:
        raise HTTPException(403, "Başka kullanıcının bookmark'larına erişemezsiniz")
    try:
        remove_bookmark(user_id, path)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True}
