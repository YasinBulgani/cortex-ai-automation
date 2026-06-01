"""Unit tests for app.domains.ai.correlation — Correlation ID propagation.

Tests are fully self-contained: no DB, no real HTTP.
Covers: get_correlation_id, set_correlation_id, ensure_correlation_id.
"""
from __future__ import annotations

import uuid
import pytest

try:
    from app.domains.ai.correlation import (
        get_correlation_id,
        set_correlation_id,
        ensure_correlation_id,
        HEADER_NAME,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="correlation module import failed")


@pytest.fixture(autouse=True)
def _reset_correlation():
    """Reset ContextVar to None before and after each test."""
    set_correlation_id(None)
    yield
    set_correlation_id(None)


# ---------------------------------------------------------------------------
# get_correlation_id / set_correlation_id
# ---------------------------------------------------------------------------

class TestGetSetCorrelationId:
    def test_default_is_none(self):
        assert get_correlation_id() is None

    def test_set_and_get(self):
        set_correlation_id("test-id-123")
        assert get_correlation_id() == "test-id-123"

    def test_set_none_clears(self):
        set_correlation_id("some-id")
        set_correlation_id(None)
        assert get_correlation_id() is None

    def test_overwrite_existing(self):
        set_correlation_id("first-id")
        set_correlation_id("second-id")
        assert get_correlation_id() == "second-id"

    def test_uuid_roundtrip(self):
        uid = str(uuid.uuid4())
        set_correlation_id(uid)
        assert get_correlation_id() == uid


# ---------------------------------------------------------------------------
# ensure_correlation_id
# ---------------------------------------------------------------------------

class TestEnsureCorrelationId:
    def test_returns_string(self):
        result = ensure_correlation_id()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_generates_uuid_when_none(self):
        result = ensure_correlation_id()
        # Must be a valid UUID4
        parsed = uuid.UUID(result, version=4)
        assert str(parsed) == result

    def test_returns_existing_when_set(self):
        set_correlation_id("existing-id")
        result = ensure_correlation_id()
        assert result == "existing-id"

    def test_idempotent_repeated_calls(self):
        first = ensure_correlation_id()
        second = ensure_correlation_id()
        assert first == second

    def test_two_different_contexts_are_independent(self):
        """Different tests (different calls) generate different IDs."""
        set_correlation_id(None)
        id1 = ensure_correlation_id()
        set_correlation_id(None)
        id2 = ensure_correlation_id()
        # Both should be valid UUIDs but different
        assert id1 != id2

    def test_persists_in_context(self):
        uid = ensure_correlation_id()
        assert get_correlation_id() == uid


# ---------------------------------------------------------------------------
# HEADER_NAME constant
# ---------------------------------------------------------------------------

class TestHeaderName:
    def test_header_name_is_x_correlation_id(self):
        assert HEADER_NAME == "X-Correlation-ID"

    def test_header_name_is_string(self):
        assert isinstance(HEADER_NAME, str)
