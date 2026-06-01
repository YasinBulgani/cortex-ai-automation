"""Events — thin service facade for the domain event bus.

HTTP-agnostic. Raises ValueError/KeyError instead of HTTPException.
Wraps app.core.event_bus internals.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.core.event_bus import bus, DomainEvent

logger = logging.getLogger(__name__)


def list_events(
    limit: int = 100,
    name_filter: Optional[str] = None,
    project_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return recent domain events from the in-process bus history.

    Args:
        limit: Maximum events to return (1–500).
        name_filter: Exact event name or 'domain.*' wildcard prefix.
        project_id: Scope to a specific project.

    Returns:
        List of serialised event dicts (newest first as stored by the bus).
    """
    limit = max(1, min(int(limit), 500))
    items = bus.history(name=name_filter, project_id=project_id, limit=limit)
    return [e.to_dict() for e in items]


def get_event(event_id: str) -> Dict[str, Any]:
    """Fetch a single event from bus history by its ID.

    Args:
        event_id: The unique DomainEvent id.

    Returns:
        Serialised event dict.

    Raises:
        KeyError: Event not found in bus history.
    """
    items = bus.history(limit=500)
    for evt in items:
        if str(evt.id) == str(event_id):
            return evt.to_dict()
    raise KeyError(f"Event '{event_id}' bus geçmişinde bulunamadı.")


def publish(name: str, payload: Optional[Dict[str, Any]] = None, project_id: Optional[str] = None) -> Dict[str, Any]:
    """Publish a domain event to the bus.

    Args:
        name: Event name (e.g. 'scenario.created').
        payload: Arbitrary event payload.
        project_id: Optional project scope.

    Returns:
        Dict with event_id and handlers_called count.

    Raises:
        ValueError: Empty event name.
    """
    name = (name or "").strip()
    if not name:
        raise ValueError("Event 'name' boş olamaz.")

    evt = DomainEvent(name=name, payload=payload or {}, project_id=project_id)
    handlers_called = bus.publish(evt)
    logger.info("Event yayınlandı: %s (handlers=%d)", name, handlers_called)
    return {"event_id": str(evt.id), "handlers_called": handlers_called}
