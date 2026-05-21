"""
SQLAlchemy implementation of OutboxRepository.

Postgres-backed reliable event delivery. Outbox tablosu domain
event'leri tutar; OutboxRelay worker periyodik olarak pending entry'leri
broker'a (Redis Streams) iter.

Usage:
    from sqlalchemy.ext.asyncio import AsyncSession

    repo = SqlAlchemyOutboxRepository(session)
    await repo.append(entry)
    pending = await repo.fetch_pending(limit=100)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    Text,
    select,
    update,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import declarative_base

from .outbox import OutboxEntry, OutboxStatus

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


Base = declarative_base()


class OutboxRow(Base):
    """
    Outbox tablosu — append-only event store.

    Index'ler:
      - (status, created_at) — pending fetch için
      - aggregate_id — debugging için
    """

    __tablename__ = "outbox"

    id                = Column(PG_UUID(as_uuid=True), primary_key=True)
    event_type        = Column(String(200), nullable=False, index=True)
    aggregate_id      = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    payload           = Column(JSONB, nullable=False)
    metadata_         = Column("metadata", JSONB, nullable=False, default=dict)
    status            = Column(String(20), nullable=False, default=OutboxStatus.PENDING.value)
    attempt_count     = Column(Integer, nullable=False, default=0)
    created_at        = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_attempted_at = Column(DateTime(timezone=True), nullable=True)
    error             = Column(Text, nullable=True)

    @classmethod
    def from_entry(cls, entry: OutboxEntry) -> "OutboxRow":
        return cls(
            id=entry.id,
            event_type=entry.event_type,
            aggregate_id=entry.aggregate_id,
            payload=entry.payload,
            metadata_=entry.metadata,
            status=entry.status.value,
            attempt_count=entry.attempt_count,
            created_at=entry.created_at,
            last_attempted_at=entry.last_attempted_at,
            error=entry.error,
        )

    def to_entry(self) -> OutboxEntry:
        return OutboxEntry(
            id=self.id,
            event_type=self.event_type,
            aggregate_id=self.aggregate_id,
            payload=self.payload or {},
            metadata=self.metadata_ or {},
            status=OutboxStatus(self.status),
            attempt_count=self.attempt_count,
            created_at=self.created_at,
            last_attempted_at=self.last_attempted_at,
            error=self.error,
        )


class SqlAlchemyOutboxRepository:
    """OutboxRepository protocol implementation — PostgreSQL via SQLAlchemy async."""

    def __init__(self, session: "AsyncSession"):
        self.session = session

    async def append(self, entry: OutboxEntry) -> None:
        row = OutboxRow.from_entry(entry)
        self.session.add(row)
        # Note: commit caller'ın sorumluluğunda — aggregate save ile aynı tx'te

    async def fetch_pending(self, limit: int = 100) -> list[OutboxEntry]:
        stmt = (
            select(OutboxRow)
            .where(OutboxRow.status.in_([OutboxStatus.PENDING.value, OutboxStatus.FAILED.value]))
            .order_by(OutboxRow.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        result = await self.session.execute(stmt)
        return [row.to_entry() for row in result.scalars().all()]

    async def mark_processing(self, ids: list[UUID]) -> None:
        if not ids:
            return
        await self.session.execute(
            update(OutboxRow)
            .where(OutboxRow.id.in_(ids))
            .values(
                status=OutboxStatus.PROCESSING.value,
                last_attempted_at=datetime.now(timezone.utc),
            )
        )

    async def mark_delivered(self, id: UUID) -> None:
        await self.session.execute(
            update(OutboxRow)
            .where(OutboxRow.id == id)
            .values(status=OutboxStatus.DELIVERED.value)
        )
        await self.session.commit()

    async def mark_failed(self, id: UUID, error: str, max_retries: int = 5) -> None:
        row = await self.session.get(OutboxRow, id)
        if row is None:
            return
        row.attempt_count += 1
        row.last_attempted_at = datetime.now(timezone.utc)
        row.error = error
        row.status = (
            OutboxStatus.DEAD.value
            if row.attempt_count >= max_retries
            else OutboxStatus.FAILED.value
        )
        await self.session.commit()
