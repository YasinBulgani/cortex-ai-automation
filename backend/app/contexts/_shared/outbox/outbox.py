"""
Outbox Pattern implementation.

Akış:
1. Aggregate command handler içinde event'ler üretir
2. Repository.save() event'leri "outbox" tablosuna yazar (DB tx içinde)
3. OutboxRelay worker periodically pending entries okur, broker'a iter
4. İşlenen entry'ler "delivered" işaretlenir (idempotency için)
5. N kez başarısız olan entry'ler dead-letter'a düşer

Bu pattern olmadan event'ler kaybolabilir.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Protocol
from uuid import UUID, uuid4

from app.contexts._shared.kernel.events import DomainEvent


class OutboxStatus(str, Enum):
    PENDING    = "pending"
    PROCESSING = "processing"
    DELIVERED  = "delivered"
    FAILED     = "failed"
    DEAD       = "dead"   # Max retry exceeded


@dataclass
class OutboxEntry:
    id: UUID
    event_type: str
    aggregate_id: UUID
    payload: dict
    metadata: dict
    status: OutboxStatus
    attempt_count: int
    created_at: datetime
    last_attempted_at: datetime | None = None
    error: str | None = None

    @classmethod
    def from_event(cls, event: DomainEvent) -> "OutboxEntry":
        # Event'i serialize et (dataclass __dict__ uyarlı, datetime ISO)
        payload = {}
        for field_name in event.__dataclass_fields__:
            if field_name in ("event_id", "occurred_at", "metadata", "aggregate_id"):
                continue
            val = getattr(event, field_name)
            payload[field_name] = val.isoformat() if isinstance(val, datetime) else (
                str(val) if isinstance(val, UUID) else val
            )
        return cls(
            id=event.event_id,
            event_type=event.event_type,
            aggregate_id=event.aggregate_id,
            payload=payload,
            metadata=event.metadata,
            status=OutboxStatus.PENDING,
            attempt_count=0,
            created_at=event.occurred_at,
        )

    def to_json(self) -> str:
        return json.dumps({
            "id": str(self.id),
            "event_type": self.event_type,
            "aggregate_id": str(self.aggregate_id),
            "payload": self.payload,
            "metadata": self.metadata,
            "occurred_at": self.created_at.isoformat(),
        })


class OutboxRepository(Protocol):
    """Persistence için contract."""
    async def append(self, entry: OutboxEntry) -> None: ...
    async def fetch_pending(self, limit: int = 100) -> list[OutboxEntry]: ...
    async def mark_processing(self, ids: list[UUID]) -> None: ...
    async def mark_delivered(self, id: UUID) -> None: ...
    async def mark_failed(self, id: UUID, error: str, max_retries: int = 5) -> None: ...


class EventBroker(Protocol):
    """Generic broker — Redis Streams, Kafka, RabbitMQ implement edebilir."""
    async def publish(self, topic: str, message: str) -> None: ...


class InMemoryOutboxRepository:
    """In-memory outbox — for unit tests and dev mode."""

    def __init__(self) -> None:
        self._entries: list[OutboxEntry] = []

    async def append(self, entry: OutboxEntry) -> None:
        self._entries.append(entry)

    async def fetch_pending(self, limit: int = 100) -> list[OutboxEntry]:
        return [e for e in self._entries if e.status == OutboxStatus.PENDING][:limit]

    async def mark_processing(self, ids: list[UUID]) -> None:
        id_set = set(ids)
        for e in self._entries:
            if e.id in id_set:
                e.status = OutboxStatus.PROCESSING

    async def mark_delivered(self, id: UUID) -> None:
        for e in self._entries:
            if e.id == id:
                e.status = OutboxStatus.DELIVERED

    async def mark_failed(self, id: UUID, error: str, max_retries: int = 5) -> None:
        for e in self._entries:
            if e.id == id:
                e.attempt_count += 1
                e.error = error
                e.status = OutboxStatus.DEAD if e.attempt_count >= max_retries else OutboxStatus.FAILED


class OutboxRelay:
    """
    Background worker — outbox entries → broker.

    Çalıştırma:
        relay = OutboxRelay(repo, broker)
        async with relay:
            await relay.run_forever(poll_interval=1.0)
    """

    def __init__(
        self,
        repository: OutboxRepository,
        broker: EventBroker,
        batch_size: int = 50,
        max_retries: int = 5,
    ):
        self.repository = repository
        self.broker = broker
        self.batch_size = batch_size
        self.max_retries = max_retries
        self._stopped = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        self._stopped = True

    async def run_forever(self, poll_interval: float = 1.0) -> None:
        """Sürekli pending entries işle."""
        import asyncio
        while not self._stopped:
            await self.process_batch()
            await asyncio.sleep(poll_interval)

    async def process_batch(self) -> int:
        """Bir batch işle. Sayı döner."""
        pending = await self.repository.fetch_pending(self.batch_size)
        if not pending:
            return 0
        ids = [e.id for e in pending]
        await self.repository.mark_processing(ids)
        delivered = 0
        for entry in pending:
            try:
                await self.broker.publish(entry.event_type, entry.to_json())
                await self.repository.mark_delivered(entry.id)
                delivered += 1
            except Exception as e:
                await self.repository.mark_failed(entry.id, str(e), self.max_retries)
        return delivered
