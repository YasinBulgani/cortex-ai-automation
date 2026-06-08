"""Products domain SQLAlchemy models.

web_vitals_samples — ham Core Web Vitals ölçümleri (RUM beacon veya sentetik
perf koşumlarından beslenir). `GET /products/web/perf-metrics` bu tablodan
sayfa başı p75 toplulaştırması yapar; tablo boşsa demo veriye düşülür.

Proje opsiyoneldir (nullable) — tenant-genel RUM örnekleri de kabul edilir.
"""
from __future__ import annotations

from datetime import datetime, timezone as _tz
from typing import Optional

from sqlalchemy import DateTime, Float, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.models import Base


def _utcnow() -> datetime:
    return datetime.now(_tz.utc)


def _uuid() -> str:
    import uuid
    return str(uuid.uuid4())


class WebVitalsSample(Base):
    """Tek bir sayfa görüntülemesinin Core Web Vitals ölçümü."""

    __tablename__ = "web_vitals_samples"
    __table_args__ = (
        Index("ix_web_vitals_samples_page_time", "page_url", "sampled_at"),
        Index("ix_web_vitals_samples_project", "project_id"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    project_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True)
    page_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    page_label: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    # Core Web Vitals — lcp/inp/fcp/tbt milisaniye, cls birimsiz (0-1 skala).
    lcp: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    inp: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cls: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fcp: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    tbt: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sampled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
