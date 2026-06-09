"""Read-Replica + Sticky Read-After-Write pattern.

Problem: Async replicas have ~100ms replication lag.
         Write then immediate read → stale data from replica.

Solution: Sticky read-after-write flag in request.state.
          For 5s after any write, force reads to use primary.
"""

import time
from contextlib import contextmanager
from typing import Optional

from fastapi import Request


class ReadReplicaConfig:
    """Configuration for read replica behavior."""

    def __init__(
        self,
        sticky_duration_seconds: float = 5.0,
        enabled: bool = True,
    ):
        """Initialize read replica config.

        Args:
            sticky_duration_seconds: How long to force primary reads after write.
            enabled: Whether read replica routing is enabled.
        """
        self.sticky_duration_seconds = sticky_duration_seconds
        self.enabled = enabled


# Global config instance
_config = ReadReplicaConfig()


def set_read_replica_config(config: ReadReplicaConfig) -> None:
    """Set the global read replica configuration."""
    global _config
    _config = config


def get_read_replica_config() -> ReadReplicaConfig:
    """Get the current read replica configuration."""
    return _config


def mark_write_occurred(request: Request) -> None:
    """Mark that a write occurred on this request.

    Sets request.state.last_write_time to current timestamp.
    Subsequent reads within sticky_duration_seconds will use primary DB.
    """
    request.state.last_write_time = time.time()


def should_force_primary(request: Request) -> bool:
    """Check if reads should use primary DB instead of replica.

    Returns True if:
    1. A write occurred on this request AND
    2. Less than sticky_duration_seconds have passed since the write

    Args:
        request: FastAPI Request object

    Returns:
        True if primary DB should be forced for reads, False otherwise
    """
    if not _config.enabled:
        return False

    last_write_time = getattr(request.state, "last_write_time", None)
    if last_write_time is None:
        return False

    elapsed = time.time() - last_write_time
    return elapsed < _config.sticky_duration_seconds


@contextmanager
def sticky_read_after_write(request: Request, duration: Optional[float] = None):
    """Context manager to enable sticky read-after-write for a request.

    Usage:
        with sticky_read_after_write(request):
            db.commit()
        # Now for next ~5s, all reads use primary

    Args:
        request: FastAPI Request object
        duration: Override sticky duration for this context (seconds).
                 If None, uses config default.
    """
    mark_write_occurred(request)
    if duration is not None:
        old_duration = _config.sticky_duration_seconds
        _config.sticky_duration_seconds = duration
        try:
            yield
        finally:
            _config.sticky_duration_seconds = old_duration
    else:
        yield
