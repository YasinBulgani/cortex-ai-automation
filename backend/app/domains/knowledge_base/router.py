"""Knowledge base router — /api/v1/kb."""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.deps import get_current_user, require_permission
from app.infra.models import User
from app.domains.knowledge_base import service as svc

router = APIRouter(prefix="/kb", tags=["knowledge-base"])

AuthUser = Annotated[User, Depends(get_current_user)]


class ArticleIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=50_000)
    tags: list[str] = Field(default_factory=list, max_length=20)
    category: str = "general"


class ArticleOut(BaseModel):
    id: str
    title: str
    body: str
    tags: list[str]
    category: str
    author_id: str
    author_name: str
    created_at: str
    updated_at: str
    view_count: int
    helpful_count: int
    unhelpful_count: int


@router.get("/articles", response_model=list[ArticleOut])
def list_articles_endpoint(
    category: Optional[str] = None,
    tag: Optional[str] = None,
    sort: str = "newest",
) -> list[ArticleOut]:
    items = svc.list_articles(category=category, tag=tag, sort=sort)
    return [ArticleOut(**a.to_dict()) for a in items]


@router.get("/articles/{article_id}", response_model=ArticleOut)
def get_article_endpoint(article_id: str) -> ArticleOut:
    a = svc.get_article(article_id)
    if a is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Article bulunamadı")
    return ArticleOut(**a.to_dict())


@router.post("/articles", response_model=ArticleOut, status_code=status.HTTP_201_CREATED)
def create_article_endpoint(body: ArticleIn, user: AuthUser) -> ArticleOut:
    try:
        a = svc.create_article(
            title=body.title,
            body=body.body,
            author_id=user.id,
            author_name=user.full_name or user.email,
            tags=body.tags,
            category=body.category,
        )
        return ArticleOut(**a.to_dict())
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc


@router.get("/search")
def search_endpoint(q: str, limit: int = 20) -> list[ArticleOut]:
    items = svc.search(q, limit=min(limit, 100))
    return [ArticleOut(**a.to_dict()) for a in items]


@router.post("/seed", status_code=status.HTTP_200_OK)
def seed_endpoint(
    force: bool = False,
    _admin: Annotated[User, Depends(require_permission("admin.*"))] = None,  # type: ignore[assignment]
) -> dict:
    """Default KB makalelerini yükler. force=True ile mevcut store temizlenir. Admin yetkisi gerektirir."""
    inserted = svc.seed_default_articles(force=force)
    return {"inserted": inserted, "total": len(svc.list_articles())}
