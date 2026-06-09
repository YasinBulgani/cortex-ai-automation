"""Unit tests for correlation ID tracking.

A-MED-1: Correlation ID propagation across async boundaries.
"""

import pytest
from unittest.mock import patch, AsyncMock

from app.infra.correlation_context import (
    get_correlation_id,
    set_correlation_id,
    reset_correlation_id,
    generate_correlation_id,
)


def test_generate_correlation_id():
    """Should generate valid UUID format."""
    corr_id = generate_correlation_id()

    assert isinstance(corr_id, str)
    assert len(corr_id) == 36  # UUID string length
    assert corr_id.count('-') == 4  # UUID format


def test_set_and_get_correlation_id():
    """Should set and retrieve correlation ID."""
    corr_id = "test-correlation-id-123"

    set_correlation_id(corr_id)
    retrieved = get_correlation_id()

    assert retrieved == corr_id


def test_get_correlation_id_generates_if_missing():
    """Should generate new ID if none set."""
    # Reset
    reset_correlation_id(None)

    retrieved = get_correlation_id()

    assert isinstance(retrieved, str)
    assert len(retrieved) > 0


def test_reset_correlation_id():
    """Should reset context variable."""
    set_correlation_id("initial-id")
    token = set_correlation_id("new-id")

    reset_correlation_id(token)
    retrieved = get_correlation_id()

    assert retrieved == "initial-id"


def test_correlation_id_async_safe():
    """Correlation ID should be thread/async safe via contextvars."""
    import asyncio

    ids_captured = []

    async def task1():
        set_correlation_id("task1-id")
        await asyncio.sleep(0.001)
        ids_captured.append(("task1", get_correlation_id()))

    async def task2():
        set_correlation_id("task2-id")
        await asyncio.sleep(0.001)
        ids_captured.append(("task2", get_correlation_id()))

    # Run concurrently
    asyncio.run(asyncio.gather(task1(), task2()))

    # Each task should have its own ID
    task1_id = next((id for name, id in ids_captured if name == "task1"), None)
    task2_id = next((id for name, id in ids_captured if name == "task2"), None)

    assert task1_id == "task1-id"
    assert task2_id == "task2-id"
    assert task1_id != task2_id
