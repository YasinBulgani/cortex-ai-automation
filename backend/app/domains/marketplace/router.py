"""Marketplace REST API — hazır senaryo şablonları."""
from __future__ import annotations

from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.deps import get_current_user
from app.infra.models import User

from .templates import (
    Template,
    get_template,
    list_categories,
    list_templates,
    search,
    stats,
)

router = APIRouter(prefix="/marketplace", tags=["marketplace"])


@router.get("/categories", response_model=List[str])
def _categories(
    _: Annotated[User, Depends(get_current_user)],
) -> List[str]:
    return list_categories()


@router.get("/stats")
def _stats(_: Annotated[User, Depends(get_current_user)]) -> dict:
    return stats()


@router.get("/templates")
def _list(
    _: Annotated[User, Depends(get_current_user)],
    category: Optional[str] = Query(default=None),
    tag: Optional[str] = Query(default=None),
) -> List[dict]:
    items = list_templates(category=category, tag=tag)
    return [t.to_dict() for t in items]


@router.get("/templates/search")
def _search(
    q: Annotated[str, Query(min_length=1, description="multi-token AND search")],
    _: Annotated[User, Depends(get_current_user)] = None,  # type: ignore[assignment]
) -> List[dict]:
    return [t.to_dict() for t in search(q)]


@router.get("/templates/{template_id}")
def _get(
    template_id: str,
    _: Annotated[User, Depends(get_current_user)],
) -> dict:
    t = get_template(template_id)
    if t is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template yok")
    return t.to_dict()
