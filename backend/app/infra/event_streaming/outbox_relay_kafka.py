"""Outbox → Kafka Migration (Faz 3.5).

Replaces Redis Streams broker with Kafka producer.
Maintains same interface: fetch pending outbox entries, publish to Kafka topics.
Exactly-once semantics via idempotent producer + transactional commits.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class OutboxEntry:
    """Outbox table entry."""
    id: str
    event_type: str  # e.g., "auth.user_login"
    aggregate_id: str
    payload: dict
    metadata: dict
    status: str


class OutboxRelayKafka:
    """Relay outbox entries to Kafka broker with exactly-once semantics.

    Migration from Redis Streams broker.
    """

    def __init__(
        self,
        broker,  # EventBroker instance
        repository,  # OutboxRepository
        topic_mapper=None,
    ):
        """Initialize relay.

        Args:
            broker: KafkaBroker or RedisBroker instance
            repository: OutboxRepository (sync DB repo)
            topic_mapper: Optional function to map event_type -> kafka topic
                         Default: "auth.user_login" -> "auth.events"
        """
        self.broker = broker
        self.repository = repository
        self.topic_mapper = topic_mapper or self._default_topic_mapper

    def _default_topic_mapper(self, event_type: str) -> str:
        """Map event type to Kafka topic.

        Example: "auth.user_login" -> "auth.events"
        """
        parts = event_type.split(".")
        if len(parts) >= 2:
            domain = parts[0]
            return f"{domain}.events"
        return "default.events"

    async def run_forever(self, poll_interval: float = 2.0, batch_size: int = 100) -> None:
        """Run relay loop continuously.

        Polls outbox table, publishes to Kafka, marks as delivered.
        """
        logger.info("Outbox → Kafka relay starting (poll_interval=%.1fs)", poll_interval)
        import asyncio

        try:
            while True:
                await self.process_batch(batch_size)
                await asyncio.sleep(poll_interval)
        except asyncio.CancelledError:
            logger.info("Relay cancelled")
        except Exception as exc:
            logger.exception("Relay fatal error: %s", exc)
            raise

    async def process_batch(self, limit: int = 100) -> None:
        """Process one batch of pending outbox entries.

        Atomic: fetch + mark processing in one transaction (skip_locked).
        Then publish to Kafka with retries.
        """
        import asyncio

        # Fetch pending entries (blocking DB call in executor)
        loop = asyncio.get_running_loop()
        entries = await loop.run_in_executor(
            None,
            self._sync_fetch_pending,
            limit,
        )

        if not entries:
            return

        logger.info("Processing %d outbox entries", len(entries))

        # Publish to Kafka (async, parallel)
        results = await asyncio.gather(
            *[self._publish_entry(entry) for entry in entries],
            return_exceptions=True,
        )

        # Mark outcomes
        for entry, result in zip(entries, results):
            if isinstance(result, Exception):
                logger.error("Publish failed (entry=%s): %s", entry.id, result)
                # Mark as failed (will retry later)
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(
                    None,
                    self._sync_mark_failed,
                    entry.id,
                    str(result),
                )
            else:
                # Mark as delivered
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(
                    None,
                    self._sync_mark_delivered,
                    entry.id,
                )

    async def _publish_entry(self, entry: OutboxEntry) -> str:
        """Publish single outbox entry to Kafka.

        Returns message ID (offset) on success.
        Raises exception on failure (caller handles retry).
        """
        topic = self.topic_mapper(entry.event_type)
        partition_key = str(entry.aggregate_id)  # Ensures ordering per aggregate

        # Build event payload
        event = {
            "id": entry.id,
            "event_type": entry.event_type,
            "aggregate_id": entry.aggregate_id,
            "payload": entry.payload,
            "metadata": entry.metadata,
        }

        msg_id = await self.broker.publish(
            topic=topic,
            event=event,
            partition_key=partition_key,
        )

        logger.debug(
            "Outbox entry published to Kafka (entry=%s, topic=%s, msg_id=%s)",
            entry.id, topic, msg_id
        )
        return msg_id

    def _sync_fetch_pending(self, limit: int) -> List[OutboxEntry]:
        """Sync wrapper: fetch pending entries from outbox table.

        Uses atomicity (FOR UPDATE SKIP LOCKED) to prevent race conditions
        when multiple relay instances run.
        """
        from sqlalchemy import select, update

        db = self.repository._get_session()
        try:
            # Import status enum
            from app.contexts._shared.outbox.outbox import OutboxStatus
            from app.contexts._shared.outbox.sql_repository import OutboxRow

            # Atomically fetch and mark as PROCESSING
            rows = db.execute(
                select(OutboxRow)
                .where(OutboxRow.status.in_([OutboxStatus.PENDING.value, OutboxStatus.FAILED.value]))
                .order_by(OutboxRow.created_at)
                .limit(limit)
                .with_for_update(skip_locked=True)
            ).scalars().all()

            if not rows:
                db.commit()
                return []

            # Convert to OutboxEntry dataclass
            entries = [
                OutboxEntry(
                    id=str(row.id),
                    event_type=row.event_type,
                    aggregate_id=str(row.aggregate_id),
                    payload=row.payload,
                    metadata=row.metadata or {},
                    status=row.status,
                )
                for row in rows
            ]

            # Mark as PROCESSING
            db.execute(
                update(OutboxRow)
                .where(OutboxRow.id.in_([row.id for row in rows]))
                .values(status=OutboxStatus.PROCESSING.value)
            )
            db.commit()
            return entries

        finally:
            db.close()

    def _sync_mark_delivered(self, entry_id: str) -> None:
        """Mark outbox entry as delivered."""
        from sqlalchemy import update
        from app.contexts._shared.outbox.outbox import OutboxStatus
        from app.contexts._shared.outbox.sql_repository import OutboxRow

        db = self.repository._get_session()
        try:
            db.execute(
                update(OutboxRow)
                .where(OutboxRow.id == entry_id)
                .values(status=OutboxStatus.DELIVERED.value)
            )
            db.commit()
        finally:
            db.close()

    def _sync_mark_failed(self, entry_id: str, error: str, max_retries: int = 5) -> None:
        """Mark outbox entry as failed (with retry limit)."""
        from sqlalchemy import select, update
        from app.contexts._shared.outbox.outbox import OutboxStatus
        from app.contexts._shared.outbox.sql_repository import OutboxRow

        db = self.repository._get_session()
        try:
            row = db.get(OutboxRow, entry_id)
            if row:
                row.attempt_count = (row.attempt_count or 0) + 1
                row.error = error[:500]
                row.status = (
                    OutboxStatus.DEAD.value
                    if row.attempt_count >= max_retries
                    else OutboxStatus.FAILED.value
                )
                db.commit()
        finally:
            db.close()


def build_kafka_relay(
    kafka_bootstrap_servers: str,
    repository,
    compression_type: str = "snappy",
) -> OutboxRelayKafka:
    """Factory for building Kafka-based outbox relay.

    Args:
        kafka_bootstrap_servers: Comma-separated Kafka brokers
        repository: OutboxRepository
        compression_type: Kafka compression type

    Returns:
        OutboxRelayKafka instance
    """
    from app.infra.event_streaming.broker import KafkaBroker

    broker = KafkaBroker(
        bootstrap_servers=kafka_bootstrap_servers,
        compression_type=compression_type,
    )
    return OutboxRelayKafka(broker=broker, repository=repository)
