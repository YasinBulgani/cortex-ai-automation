"""Automation Suite SQLAlchemy models.

Koşum kayıtlarını kalıcı tutar (eski in-memory/Redis registry'nin yerine).
Pod restart'ında koşum geçmişi kaybolmaz.

Tablo global'dir (proje/tenant scope'u yok) — eski registry davranışıyla
uyumlu, RLS politikası uygulanmaz.
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


class AutomationSuiteRun(Base):
    """Otomasyon süiti koşum kaydı — durum, sonuç ve log kuyruğu."""

    __tablename__ = "automation_suite_runs"

    run_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    feature_path: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    framework: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    passed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    failed: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    report_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    logs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
