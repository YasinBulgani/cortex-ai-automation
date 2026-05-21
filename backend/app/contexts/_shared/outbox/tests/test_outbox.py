"""Outbox tests — in-memory mock repository ile."""

import pytest
from dataclasses import dataclass
from uuid import UUID, uuid4

from app.contexts._shared.kernel.events import DomainEvent
from app.contexts._shared.outbox.outbox import (
    EventBroker,
    OutboxEntry,
    OutboxRelay,
    OutboxRepository,
    OutboxStatus,
)


@dataclass(frozen=True, slots=True)
class SampleEvent(DomainEvent):
    actor: str = ""
    note: str = ""


# ─── In-memory test doubles ──────────────────────────────────────────────

class InMemoryOutboxRepo:
    def __init__(self):
        self.entries: dict[UUID, OutboxEntry] = {}

    async def append(self, entry: OutboxEntry) -> None:
        self.entries[entry.id] = entry

    async def fetch_pending(self, limit: int = 100) -> list[OutboxEntry]:
        out = [e for e in self.entries.values() if e.status in (OutboxStatus.PENDING, OutboxStatus.FAILED)]
        return out[:limit]

    async def mark_processing(self, ids: list[UUID]) -> None:
        for i in ids:
            if i in self.entries:
                self.entries[i].status = OutboxStatus.PROCESSING

    async def mark_delivered(self, id: UUID) -> None:
        if id in self.entries:
            self.entries[id].status = OutboxStatus.DELIVERED

    async def mark_failed(self, id: UUID, error: str, max_retries: int = 5) -> None:
        if id not in self.entries:
            return
        e = self.entries[id]
        e.attempt_count += 1
        e.error = error
        e.status = OutboxStatus.DEAD if e.attempt_count >= max_retries else OutboxStatus.FAILED


class InMemoryBroker:
    def __init__(self, fail_on_topics: set[str] | None = None):
        self.published: list[tuple[str, str]] = []
        self.fail_on_topics = fail_on_topics or set()

    async def publish(self, topic: str, message: str) -> None:
        if topic in self.fail_on_topics:
            raise RuntimeError(f"Broker error for {topic}")
        self.published.append((topic, message))


# ─── Tests ───────────────────────────────────────────────────────────────

class TestOutboxEntry:
    def test_from_event_extracts_payload(self):
        event = SampleEvent(aggregate_id=uuid4(), actor="alice", note="hello")
        entry = OutboxEntry.from_event(event)
        assert entry.event_type == "sample.event"
        assert entry.payload["actor"] == "alice"
        assert entry.payload["note"] == "hello"
        assert entry.status == OutboxStatus.PENDING

    def test_to_json_serializable(self):
        event = SampleEvent(aggregate_id=uuid4(), actor="x", note="y")
        entry = OutboxEntry.from_event(event)
        import json
        parsed = json.loads(entry.to_json())
        assert parsed["event_type"] == "sample.event"
        assert parsed["payload"]["actor"] == "x"


@pytest.mark.asyncio
class TestOutboxRelay:
    async def test_process_empty_batch(self):
        repo = InMemoryOutboxRepo()
        broker = InMemoryBroker()
        relay = OutboxRelay(repo, broker)
        delivered = await relay.process_batch()
        assert delivered == 0

    async def test_process_pending_entries(self):
        repo = InMemoryOutboxRepo()
        broker = InMemoryBroker()
        relay = OutboxRelay(repo, broker)

        # Add 3 pending events
        for i in range(3):
            event = SampleEvent(aggregate_id=uuid4(), actor=f"user{i}")
            await repo.append(OutboxEntry.from_event(event))

        delivered = await relay.process_batch()
        assert delivered == 3
        assert len(broker.published) == 3
        # All entries marked delivered
        for entry in repo.entries.values():
            assert entry.status == OutboxStatus.DELIVERED

    async def test_failed_entry_moves_to_failed_status(self):
        repo = InMemoryOutboxRepo()
        broker = InMemoryBroker(fail_on_topics={"sample.event"})
        relay = OutboxRelay(repo, broker, max_retries=3)

        event = SampleEvent(aggregate_id=uuid4(), actor="x")
        await repo.append(OutboxEntry.from_event(event))

        delivered = await relay.process_batch()
        assert delivered == 0
        entry = list(repo.entries.values())[0]
        assert entry.status == OutboxStatus.FAILED
        assert entry.attempt_count == 1
        assert "Broker error" in entry.error

    async def test_max_retries_marks_dead(self):
        repo = InMemoryOutboxRepo()
        broker = InMemoryBroker(fail_on_topics={"sample.event"})
        relay = OutboxRelay(repo, broker, max_retries=2)

        event = SampleEvent(aggregate_id=uuid4(), actor="x")
        await repo.append(OutboxEntry.from_event(event))

        # 1st attempt
        await relay.process_batch()
        # 2nd attempt → max_retries hit → dead
        await relay.process_batch()

        entry = list(repo.entries.values())[0]
        assert entry.status == OutboxStatus.DEAD
        assert entry.attempt_count == 2
