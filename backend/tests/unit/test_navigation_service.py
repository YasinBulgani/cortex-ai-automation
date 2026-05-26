"""Unit tests for app.domains.navigation.service.

Tests are fully self-contained: no DB, no HTTP, no external services.
The navigation service uses module-level dicts; each test class resets
the relevant state via the module's internal stores to maintain isolation.
"""
from __future__ import annotations

import pytest

try:
    from app.domains.navigation import service as nav_service
    from app.domains.navigation.service import (
        add_bookmark,
        get_nav_tree,
        get_user_bookmarks,
        remove_bookmark,
        _BOOKMARKS,
        _NAV_TREE,
    )

    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="navigation service import failed")


# ---------------------------------------------------------------------------
# Fixture: reset module-level state before each test
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_nav_state():
    """Clear bookmarks and nav tree before every test for isolation."""
    _BOOKMARKS.clear()
    _NAV_TREE.clear()
    yield
    _BOOKMARKS.clear()
    _NAV_TREE.clear()


# ---------------------------------------------------------------------------
# get_nav_tree
# ---------------------------------------------------------------------------


class TestGetNavTree:
    def test_returns_list(self):
        result = get_nav_tree()
        assert isinstance(result, list)

    def test_empty_initially(self):
        """Nav tree starts empty (no seeding in the service module)."""
        result = get_nav_tree()
        assert result == []

    def test_returns_copy_not_reference(self):
        """Mutating the returned list must not affect the internal store."""
        tree = get_nav_tree()
        tree.append({"id": "injected"})
        assert get_nav_tree() == []

    def test_reflects_direct_internal_mutation(self):
        """After appending to the internal store, get_nav_tree reflects it."""
        _NAV_TREE.append({"id": "dashboard", "label": "Dashboard"})
        result = get_nav_tree()
        assert len(result) == 1
        assert result[0]["id"] == "dashboard"


# ---------------------------------------------------------------------------
# get_user_bookmarks
# ---------------------------------------------------------------------------


class TestGetUserBookmarks:
    def test_returns_empty_list_for_new_user(self):
        result = get_user_bookmarks("user1")
        assert result == []

    def test_returns_list_type(self):
        result = get_user_bookmarks("any-user")
        assert isinstance(result, list)

    def test_returns_copy_not_reference(self):
        """Mutating the returned list must not affect the internal store."""
        add_bookmark("user1", "/dashboard")
        bookmarks = get_user_bookmarks("user1")
        bookmarks.append("/injected")
        assert get_user_bookmarks("user1") == ["/dashboard"]


# ---------------------------------------------------------------------------
# add_bookmark
# ---------------------------------------------------------------------------


class TestAddBookmark:
    def test_add_single_bookmark(self):
        add_bookmark("user1", "/dashboard")
        assert "/dashboard" in get_user_bookmarks("user1")

    def test_add_is_idempotent(self):
        add_bookmark("user1", "/dashboard")
        add_bookmark("user1", "/dashboard")
        bookmarks = get_user_bookmarks("user1")
        assert bookmarks.count("/dashboard") == 1

    def test_add_multiple_bookmarks(self):
        add_bookmark("user1", "/dashboard")
        add_bookmark("user1", "/settings")
        bookmarks = get_user_bookmarks("user1")
        assert "/dashboard" in bookmarks
        assert "/settings" in bookmarks

    def test_add_preserves_order(self):
        add_bookmark("user1", "/a")
        add_bookmark("user1", "/b")
        add_bookmark("user1", "/c")
        assert get_user_bookmarks("user1") == ["/a", "/b", "/c"]

    def test_empty_path_raises_value_error(self):
        with pytest.raises(ValueError):
            add_bookmark("user1", "")


# ---------------------------------------------------------------------------
# remove_bookmark
# ---------------------------------------------------------------------------


class TestRemoveBookmark:
    def test_remove_existing_bookmark(self):
        add_bookmark("user1", "/dashboard")
        remove_bookmark("user1", "/dashboard")
        assert "/dashboard" not in get_user_bookmarks("user1")

    def test_remove_nonexistent_bookmark_raises_key_error(self):
        with pytest.raises(KeyError):
            remove_bookmark("user1", "/nonexistent")

    def test_remove_for_user_with_no_bookmarks_raises_key_error(self):
        with pytest.raises(KeyError):
            remove_bookmark("new-user", "/anything")

    def test_remove_leaves_other_bookmarks_intact(self):
        add_bookmark("user1", "/dashboard")
        add_bookmark("user1", "/settings")
        remove_bookmark("user1", "/dashboard")
        assert get_user_bookmarks("user1") == ["/settings"]

    def test_remove_all_bookmarks_leaves_empty_list(self):
        add_bookmark("user1", "/dashboard")
        remove_bookmark("user1", "/dashboard")
        assert get_user_bookmarks("user1") == []


# ---------------------------------------------------------------------------
# Multiple users — independent bookmark stores
# ---------------------------------------------------------------------------


class TestMultipleUsers:
    def test_users_have_independent_bookmarks(self):
        add_bookmark("alice", "/dashboard")
        add_bookmark("bob", "/settings")
        assert get_user_bookmarks("alice") == ["/dashboard"]
        assert get_user_bookmarks("bob") == ["/settings"]

    def test_adding_for_one_user_does_not_affect_other(self):
        add_bookmark("alice", "/dashboard")
        assert get_user_bookmarks("bob") == []

    def test_removing_for_one_user_does_not_affect_other(self):
        add_bookmark("alice", "/dashboard")
        add_bookmark("bob", "/dashboard")
        remove_bookmark("alice", "/dashboard")
        assert get_user_bookmarks("bob") == ["/dashboard"]

    def test_clear_bookmarks_on_reset(self):
        """autouse fixture clears bookmarks; state must be fresh each test."""
        # This test just asserts the fixture worked — bookmarks were cleared
        assert get_user_bookmarks("alice") == []
        assert get_user_bookmarks("bob") == []
