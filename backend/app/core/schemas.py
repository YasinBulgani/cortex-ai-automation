"""Paylaşılan Pydantic base sınıfları — tüm domain schema'ları buradan türer."""

from __future__ import annotations

from datetime import datetime
from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field


class OrmBase(BaseModel):
    """ORM mode varsayılan olarak açık."""

    model_config = ConfigDict(from_attributes=True)


class TimestampedBase(OrmBase):
    """id + oluşturma/güncelleme zaman damgaları — neredeyse her Out schema'sında bulunur."""

    id: str
    created_at: datetime
    updated_at: datetime


class NamedBase(OrmBase):
    """İsimli kaynaklar için ortak alanlar."""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class NamedTimestampedBase(NamedBase, TimestampedBase):
    """İsimli + zaman damgalı tam base — çoğu domain Out schema'sı için."""


# ─── Pagination ───────────────────────────────────────────────────────────────

T = TypeVar("T")


class PagedResponse(OrmBase, Generic[T]):
    """Standart sayfalanmış liste yanıtı.

    Kullanım::

        @router.get("", response_model=PagedResponse[ItemOut])
        def list_items(page: PaginationParams = Depends()) -> PagedResponse[ItemOut]:
            ...
    """

    items: List[T]
    total: int
    limit: int
    offset: int
    has_more: bool

    @classmethod
    def build(cls, items: list, total: int, limit: int, offset: int) -> "PagedResponse[T]":
        return cls(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
            has_more=offset + len(items) < total,
        )
