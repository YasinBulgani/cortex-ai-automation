"""Marketplace REST API — hazır senaryo şablonları."""
from __future__ import annotations

import logging
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.deps import get_current_user
from app.infra.models import User

from .templates import (
    get_template,
    list_categories,
    list_templates,
    search,
    stats,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/marketplace", tags=["marketplace"])


@router.get("/categories", response_model=List[str])
def _categories(
    _: Annotated[User, Depends(get_current_user)],
) -> List[str]:
    try:
        return list_categories()
    except Exception as e:
        logger.error("marketplace list_categories failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
def _stats(_: Annotated[User, Depends(get_current_user)]) -> dict:
    try:
        return stats()
    except Exception as e:
        logger.error("marketplace stats failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates")
def _list(
    _: Annotated[User, Depends(get_current_user)],
    category: Optional[str] = Query(default=None),
    tag: Optional[str] = Query(default=None),
) -> List[dict]:
    try:
        items = list_templates(category=category, tag=tag)
        return [t.to_dict() for t in items]
    except HTTPException:
        raise
    except Exception as e:
        logger.error("marketplace list_templates failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates/search")
def _search(
    q: Annotated[str, Query(min_length=1, description="multi-token AND search")],
    _: Annotated[User, Depends(get_current_user)],
) -> List[dict]:
    try:
        return [t.to_dict() for t in search(q)]
    except HTTPException:
        raise
    except Exception as e:
        logger.error("marketplace search failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/templates/{template_id}")
def _get(
    template_id: str,
    _: Annotated[User, Depends(get_current_user)],
) -> dict:
    try:
        t = get_template(template_id)
        if t is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template yok")
        return t.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        logger.error("marketplace get_template(%s) failed: %s", template_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
