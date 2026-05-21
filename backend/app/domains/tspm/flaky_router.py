"""Flaky test karantinası REST API'si.

Endpoints:
    POST  /tspm/flaky/ingest      → CI batch push (500'e kadar event)
    GET   /tspm/flaky/top         → en flaky N test
    GET   /tspm/flaky/quarantined → sadece karantinadakiler
    GET   /tspm/flaky/stability   → tek test detayı
    GET   /tspm/flaky/is-quarantined → runner fast-path
"""
from __future__ import annotations

from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.deps import get_current_user, require_permission
from app.infra.models import User

from .flaky_service import (
    IngestRequest,
    StabilityRow,
    get_stability,
    ingest_events,
    is_quarantined,
    list_top_flaky,
)

router = APIRouter(prefix="/tspm/flaky", tags=["tspm-flaky"])

_ADMIN_PERM = "admin.flaky"


@router.post("/ingest")
def ingest(
    payload: IngestRequest,
    _: Annotated[User, Depends(get_current_user)],
) -> dict:
    n = ingest_events(payload.events)
    return {"ingested": n}


@router.get("/top", response_model=List[StabilityRow])
def top(
    _: Annotated[User, Depends(require_permission(_ADMIN_PERM))],
    limit: int = Query(default=10, ge=1, le=200),
) -> List[StabilityRow]:
    return list_top_flaky(limit=limit, only_quarantined=False)


@router.get("/quarantined", response_model=List[StabilityRow])
def quarantined(
    _: Annotated[User, Depends(require_permission(_ADMIN_PERM))],
    limit: int = Query(default=100, ge=1, le=500),
) -> List[StabilityRow]:
    return list_top_flaky(limit=limit, only_quarantined=True)


@router.get("/stability", response_model=StabilityRow)
def stability(
    test_key: str,
    _: Annotated[User, Depends(get_current_user)],
    project_id: Optional[str] = None,
    env: str = Query(default="ci"),
) -> StabilityRow:
    row = get_stability(project_id, test_key, env)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bu test için stability kaydı yok",
        )
    return row


@router.get("/is-quarantined")
def check(
    test_key: str,
    _: Annotated[User, Depends(get_current_user)],
    project_id: Optional[str] = None,
    env: str = Query(default="ci"),
) -> dict:
    return {"quarantined": is_quarantined(project_id, test_key, env)}
