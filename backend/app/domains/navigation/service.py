"""Navigation service — manages app navigation tree and user bookmarks.

HTTP-agnostic. Raises ValueError/KeyError.
"""
from __future__ import annotations

from typing import Any

_NAV_TREE: list[dict[str, Any]] = []
_BOOKMARKS: dict[str, list[str]] = {}  # user_id -> list of route paths


def get_nav_tree() -> list[dict[str, Any]]:
    """Return the full navigation tree."""
    return list(_NAV_TREE)


def get_user_bookmarks(user_id: str) -> list[str]:
    """Return the bookmark list for the given user (empty list if none)."""
    return list(_BOOKMARKS.get(user_id, []))


def add_bookmark(user_id: str, path: str) -> None:
    """Add *path* to *user_id*'s bookmarks (idempotent)."""
    if not path:
        raise ValueError("Bookmark path must not be empty.")
    bookmarks = _BOOKMARKS.setdefault(user_id, [])
    if path not in bookmarks:
        bookmarks.append(path)


def remove_bookmark(user_id: str, path: str) -> None:
    """Remove *path* from *user_id*'s bookmarks.

    Raises KeyError if the bookmark is not found.
    """
    bookmarks = _BOOKMARKS.get(user_id, [])
    if path not in bookmarks:
        raise KeyError(f"Bookmark {path!r} not found for user {user_id!r}.")
    bookmarks.remove(path)
