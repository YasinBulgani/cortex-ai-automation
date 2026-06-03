"""Standart sayfalama bağımlılıkları ve yardımcıları.

Kullanım::

    @router.get("", response_model=PagedResponse[ItemOut])
    def list_items(
        db: Annotated[Session, Depends(get_db)],
        _: Annotated[User, Depends(get_current_user)],
        page: Annotated[PaginationParams, Depends()],
    ) -> dict:
        q = select(Item).order_by(Item.created_at.desc())
        return paginate(db, q, page)
"""

from __future__ import annotations

from typing import Any, Generic, List, Literal, Optional, TypeVar

from fastapi import Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

T = TypeVar("T")


class PaginationParams:
    """FastAPI Depends() ile kullanılan sayfalama parametreleri."""

    def __init__(
        self,
        limit: int = Query(50, ge=1, le=500, description="Sayfa başına kayıt"),
        offset: int = Query(0, ge=0, description="Atlanan kayıt sayısı"),
        sort_order: Literal["asc", "desc"] = Query("desc", description="Sıralama yönü"),
    ) -> None:
        self.limit = limit
        self.offset = offset
        self.sort_order = sort_order


class PagedResponse(Generic[T]):
    """Sayfalanmış yanıt modeli — response_model için Pydantic değil, dict döner.

    ``paginate()`` helper'ı bu sınıfı otomatik oluşturur.
    """

    def __init__(
        self,
        items: List[T],
        total: int,
        limit: int,
        offset: int,
    ) -> None:
        self.items = items
        self.total = total
        self.limit = limit
        self.offset = offset
        self.has_more = offset + len(items) < total

    def as_dict(self) -> dict[str, Any]:
        return {
            "items": self.items,
            "total": self.total,
            "limit": self.limit,
            "offset": self.offset,
            "has_more": self.has_more,
        }


def paginate(db: Session, query: Any, page: PaginationParams) -> dict[str, Any]:
    """Verilen SQLAlchemy sorgusunu sayfalayarak dict döner.

    Kullanım::
        q = select(Item).where(Item.active.is_(True))
        return paginate(db, q, page)
    """
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = list(db.scalars(query.offset(page.offset).limit(page.limit)).all())
    return PagedResponse(items=items, total=total, limit=page.limit, offset=page.offset).as_dict()
