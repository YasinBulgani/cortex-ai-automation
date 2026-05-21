"""A11y REST API — axe-core rapor ingest + history + aggregate.

Raporlar in-memory tutulur (ring buffer 500). Persist sonraki commit'te
``a11y_reports`` tablosu ile (coverup healing history pattern'i).
"""
from __future__ import annotations

import threading
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Annotated, Any, Deque, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.deps import get_current_user, require_permission
from app.infra.models import User

from .service import A11yReport, aggregate_reports, parse_axe_report

router = APIRouter(prefix="/a11y", tags=["a11y"])


_ADMIN_PERM = "admin.a11y"

_HISTORY_MAX = 500
_history: Deque[Dict[str, Any]] = deque(maxlen=_HISTORY_MAX)
_history_lock = threading.RLock()


def _record(report: A11yReport, *, submitted_by: Optional[str]) -> str:
    report_id = uuid.uuid4().hex
    with _history_lock:
        _history.append(
            {
                "id": report_id,
                "submitted_by": submitted_by,
                "submitted_at": datetime.now(timezone.utc),
                "report": report,
            }
        )
    return report_id


def _recent(limit: int) -> List[Dict[str, Any]]:
    with _history_lock:
        items = list(_history)
    items.reverse()
    return items[:limit]


class IngestResponse(BaseModel):
    id: str
    score: int
    violations_count: int


@router.post("/reports", response_model=IngestResponse)
def _ingest(
    payload: Annotated[Dict[str, Any], Body(description="Raw axe-core JSON")],
    user: Annotated[User, Depends(get_current_user)],
) -> IngestResponse:
    try:
        report = parse_axe_report(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    rid = _record(report, submitted_by=str(user.id))
    return IngestResponse(
        id=rid, score=report.score, violations_count=len(report.violations)
    )


@router.get("/reports")
def _list(
    _: Annotated[User, Depends(require_permission(_ADMIN_PERM))],
    limit: int = Query(default=50, ge=1, le=500),
) -> List[Dict[str, Any]]:
    items = _recent(limit)
    # Pydantic -> dict için model_dump
    return [
        {
            "id": i["id"],
            "submitted_by": i["submitted_by"],
            "submitted_at": i["submitted_at"].isoformat(),
            "report": i["report"].model_dump(),
        }
        for i in items
    ]


@router.get("/aggregate")
def _agg(
    _: Annotated[User, Depends(require_permission(_ADMIN_PERM))],
    limit: int = Query(default=50, ge=1, le=500),
) -> Dict[str, Any]:
    items = _recent(limit)
    reports = [i["report"] for i in items]
    agg = aggregate_reports(reports)
    return {
        "total_reports": agg.total_reports,
        "avg_score": agg.avg_score,
        "worst_score": agg.worst_score,
        "severity_totals": agg.severity_totals,
        "most_common_violations": [
            {"rule_id": r, "occurrences": c} for r, c in agg.most_common_violations
        ],
    }
