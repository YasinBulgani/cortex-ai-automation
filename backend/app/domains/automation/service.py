"""Automation — thin service facade wrapping AutomationBrainService.

HTTP-agnostic. Raises ValueError/KeyError instead of HTTPException.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.domains.automation.brain import brain_service
from app.domains.automation.schemas import AutomationRunCreate

logger = logging.getLogger(__name__)


def _to_dict(obj: Any) -> Dict[str, Any]:
    """Serialise a Pydantic model or dict-like object to a plain dict.

    Try .dict() first (Pydantic v1 / mocks), then .model_dump() (Pydantic v2).
    """
    if isinstance(obj, dict):
        return obj
    # Try .dict() first — mocks configure this; Pydantic v1 uses it natively
    try:
        result = obj.dict()
        if isinstance(result, dict):
            return result
    except (AttributeError, TypeError):
        pass
    # Pydantic v2 .model_dump()
    try:
        result = obj.model_dump()
        if isinstance(result, dict):
            return result
    except (AttributeError, TypeError):
        pass
    return dict(obj)


def get_brain_summary(db: Session) -> Dict[str, Any]:
    """Return the automation brain's capability + run summary.

    Returns:
        Dict with capabilities, recent run counts, and status.
    """
    summary = brain_service.summary(db)
    return _to_dict(summary)


def list_runs(db: Session, limit: int = 50) -> List[Dict[str, Any]]:
    """List recent automation runs, newest first.

    Args:
        db: SQLAlchemy session.
        limit: Maximum rows to return (capped at 200).

    Returns:
        List of run dicts.
    """
    limit = min(int(limit), 200)
    runs = brain_service.list_runs(db, limit=limit)
    # Handles both AutomationRunList (has .items) and plain list (from mocks)
    items = runs.items if hasattr(runs, "items") else runs
    return [_to_dict(r) for r in items]


def create_run(db: Session, config: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new automation run record via the brain service.

    Args:
        db: SQLAlchemy session.
        config: Run configuration dict. Must include 'kind'.

    Returns:
        Created run as dict.

    Raises:
        ValueError: Missing required field 'kind'.
    """
    kind = config.get("kind")
    if not kind:
        raise ValueError("'kind' alanı zorunludur (ör. 'playwright', 'api', 'mobile').")

    run_create = AutomationRunCreate(**config)
    run = brain_service.create_run(db, run_create)
    logger.info("Automation run oluşturuldu: kind=%s id=%s", kind, getattr(run, "id", "?"))
    return _to_dict(run)
