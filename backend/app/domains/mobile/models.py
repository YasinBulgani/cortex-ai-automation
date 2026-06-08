"""Mobile SQLAlchemy models.

Mobil koşum (session) kayıtlarını kalıcı tutar. Eski in-memory ``SessionStore``
pod restart'ında tüm geçmişi kaybediyordu; bu tablo session metadatasını +
adım sonuçlarını (JSONB) kalıcılaştırır, böylece geçmiş, denetim izi ve
disk'teki artifact'larla ilişki korunur.

Canlı SSE kuyruğu kalıcılaştırılmaz (doğası gereği ephemeral) — yalnızca
serileştirilebilir Session/Step kaydı saklanır.

Tablo global'dir (mevcut store davranışıyla uyumlu), RLS uygulanmaz.
"""
from __future__ import annotations

from datetime import datetime, timezone as _tz
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.models import Base


def _utcnow() -> datetime:
    return datetime.now(_tz.utc)


class MobileSession(Base):
    """Mobil otomasyon koşum kaydı — durum, sonuç ve adım detayları."""

    __tablename__ = "mobile_sessions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    device_id: Mapped[str] = mapped_column(String(64), nullable=False)
    scenario_name: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    mode: Mapped[str] = mapped_column(String(16), nullable=False, default="simulation")
    failure_category: Mapped[Optional[str]] = mapped_column(String(48), nullable=True)
    failure_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    healed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    steps: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
