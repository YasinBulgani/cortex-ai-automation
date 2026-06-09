"""Request correlation ID tracking for distributed tracing.

A-MED-1: Correlation ID propagation across async service boundaries.

Pattern:
    req: X-Correlation-ID: uuid → extracted in middleware
    → stored in contextvars (thread-safe, async-safe)
    → available in all service layers (db, cache, external calls)
    → logged in all events/spans
    → propagated to downstream services
"""

import contextvars
import uuid
from typing import Optional

# Context variable holds correlation ID (thread-local + async-safe)
correlation_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    'correlation_id', default=None
)


def get_correlation_id() -> str:
    """Get current request's correlation ID, or generate new one."""
    current = correlation_id.get()
    if current:
        return current
    # Fallback: generate new ID if not set (defensive)
    return str(uuid.uuid4())


def set_correlation_id(corr_id: str) -> Optional[str]:
    """Set correlation ID for current request context.

    Returns previous value (for reset_token pattern).
    """
    return correlation_id.set(corr_id)


def reset_correlation_id(token: Optional[str]) -> None:
    """Reset correlation ID from token (async cleanup)."""
    if token is not None:
        correlation_id.set(token)
    else:
        correlation_id.set(None)


def generate_correlation_id() -> str:
    """Generate new correlation ID (uuid4)."""
    return str(uuid.uuid4())
