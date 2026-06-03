"""SQLAlchemy models for the Kiwi TCMS integration (import-only, phase 1)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infra.crypto import EncryptedString
from app.infra.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class KiwiConnection(Base):
    """Per-project Kiwi TCMS connection. One connection per Neurex project."""

    __tablename__ = "kiwi_connections"
    __table_args__ = (UniqueConstraint("project_id", name="uq_kiwi_connections_project"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("test_management_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    base_url: Mapped[str] = mapped_column(String(500), nullable=False)
    username: Mapped[str] = mapped_column(String(200), nullable=False)
    # Fernet-encrypted at-rest (API token or password). Transparent via EncryptedString.
    secret: Mapped[Optional[str]] = mapped_column(EncryptedString(1024), nullable=True)
    kiwi_product_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    verify_ssl: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default="unconfigured", server_default="unconfigured", nullable=False
    )  # unconfigured | ok | error
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_tested_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), ForeignKey("sd_users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    jobs: Mapped[list["KiwiSyncJob"]] = relationship(back_populates="connection", cascade="all, delete-orphan")
    id_maps: Mapped[list["KiwiIdMap"]] = relationship(back_populates="connection", cascade="all, delete-orphan")


class KiwiSyncJob(Base):
    """A single import-sync run (foreground preview or RQ-backed full sync)."""

    __tablename__ = "kiwi_sync_jobs"
    __table_args__ = (Index("ix_kiwi_sync_jobs_project_created", "project_id", "created_at"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    connection_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("kiwi_connections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("test_management_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    mode: Mapped[str] = mapped_column(String(16), default="import", server_default="import", nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), default="queued", server_default="queued", nullable=False
    )  # queued | running | succeeded | failed
    dry_run: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    # totals: {entity_type: {created, updated, skipped, errors}}
    totals: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}", nullable=False)
    rq_job_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), ForeignKey("sd_users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    connection: Mapped[KiwiConnection] = relationship(back_populates="jobs")


class KiwiIdMap(Base):
    """External (Kiwi) id ↔ internal (Neurex) id mapping for idempotent upserts."""

    __tablename__ = "kiwi_id_maps"
    __table_args__ = (
        UniqueConstraint("connection_id", "entity_type", "external_id", name="uq_kiwi_id_maps_conn_type_ext"),
        Index("ix_kiwi_id_maps_internal", "entity_type", "internal_id"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    connection_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("kiwi_connections.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    # entity_type: suite | case | plan | run | execution | defect
    external_id: Mapped[str] = mapped_column(String(64), nullable=False)
    internal_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    fingerprint: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    connection: Mapped[KiwiConnection] = relationship(back_populates="id_maps")
