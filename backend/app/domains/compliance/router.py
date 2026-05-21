"""Compliance REST API — kontrol listesi + evidence pack."""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse

from app.deps import require_permission
from app.infra.models import User

from .mapping import (
    Control,
    Mapping,
    build_evidence_pack,
    export_evidence,
    get_control,
    list_controls,
    mappings_for,
    unmapped_controls,
)

router = APIRouter(prefix="/compliance", tags=["compliance"])


_ADMIN_PERM = "admin.compliance"


@router.get("/controls")
def _list(
    _: Annotated[User, Depends(require_permission(_ADMIN_PERM))],
    standard: Optional[str] = Query(default=None, description="KVKK|BDDK|ISO27001|SOC2"),
) -> List[dict]:
    controls = list_controls(standard)
    return [
        {
            "id": c.id,
            "standard": c.standard,
            "article": c.article,
            "title": c.title,
            "description": c.description,
            "risk_level": c.risk_level,
            "mapped_features": [m.feature_name for m in mappings_for(c.id)],
        }
        for c in controls
    ]


@router.get("/controls/{control_id}")
def _get(
    control_id: str,
    _: Annotated[User, Depends(require_permission(_ADMIN_PERM))],
) -> dict:
    c = get_control(control_id)
    if c is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Kontrol yok")
    return {
        "id": c.id,
        "standard": c.standard,
        "article": c.article,
        "title": c.title,
        "description": c.description,
        "risk_level": c.risk_level,
        "mappings": [
            {
                "feature_name": m.feature_name,
                "feature_module": m.feature_module,
                "test_marker": m.test_marker,
                "test_location": m.test_location,
                "notes": m.notes,
            }
            for m in mappings_for(control_id)
        ],
    }


@router.get("/coverage")
def _coverage(
    _: Annotated[User, Depends(require_permission(_ADMIN_PERM))],
) -> dict:
    pack = build_evidence_pack()
    return {
        "total_controls": len(pack["controls"]),
        "total_mappings": len(pack["mappings"]),
        "unmapped": [c for c in pack["unmapped"]],
        "coverage_pct": pack["coverage_pct"],
        "standards": pack["generated_standards"],
    }


@router.get("/evidence-pack.json")
def _evidence_json(
    _: Annotated[User, Depends(require_permission(_ADMIN_PERM))],
) -> dict:
    return build_evidence_pack()


@router.get("/evidence-pack.download")
def _evidence_download(
    _: Annotated[User, Depends(require_permission(_ADMIN_PERM))],
) -> FileResponse:
    tmp = Path(tempfile.gettempdir()) / "testwright_evidence_pack.json"
    export_evidence(tmp)
    return FileResponse(
        path=tmp,
        filename="testwright_evidence_pack.json",
        media_type="application/json",
    )
