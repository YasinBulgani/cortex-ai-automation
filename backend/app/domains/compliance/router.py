"""Compliance REST API — kontrol listesi + evidence pack."""
from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse

from app.deps import require_permission
from app.infra.models import User

from .mapping import (
    build_evidence_pack,
    export_evidence,
    get_control,
    list_controls,
    mappings_for,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/compliance", tags=["compliance"])


_ADMIN_PERM = "admin.compliance"


@router.get("/controls")
def _list(
    _: Annotated[User, Depends(require_permission(_ADMIN_PERM))],
    standard: Optional[str] = Query(default=None, description="KVKK|BDDK|ISO27001|SOC2"),
) -> List[dict]:
    try:
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error("compliance list_controls failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/controls/{control_id}")
def _get(
    control_id: str,
    _: Annotated[User, Depends(require_permission(_ADMIN_PERM))],
) -> dict:
    try:
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error("compliance get_control(%s) failed: %s", control_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/coverage")
def _coverage(
    _: Annotated[User, Depends(require_permission(_ADMIN_PERM))],
) -> dict:
    try:
        pack = build_evidence_pack()
        return {
            "total_controls": len(pack["controls"]),
            "total_mappings": len(pack["mappings"]),
            "unmapped": [c for c in pack["unmapped"]],
            "coverage_pct": pack["coverage_pct"],
            "standards": pack["generated_standards"],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error("compliance coverage failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/evidence-pack.json")
def _evidence_json(
    _: Annotated[User, Depends(require_permission(_ADMIN_PERM))],
) -> dict:
    try:
        return build_evidence_pack()
    except HTTPException:
        raise
    except Exception as e:
        logger.error("compliance evidence_pack.json failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/evidence-pack.download")
def _evidence_download(
    _: Annotated[User, Depends(require_permission(_ADMIN_PERM))],
) -> FileResponse:
    try:
        tmp = Path(tempfile.gettempdir()) / "testwright_evidence_pack.json"
        export_evidence(tmp)
        return FileResponse(
            path=tmp,
            filename="testwright_evidence_pack.json",
            media_type="application/json",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("compliance evidence_pack.download failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
