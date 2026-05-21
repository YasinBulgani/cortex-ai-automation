"""Wire up OutboxRelay with SqlAlchemy repo + Redis Streams broker.

Returns None if Redis is not available (graceful degradation for local dev
without Docker). When None is returned the outbox relay is simply not started;
events accumulate in the DB and can be replayed later.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class _RedisStreamBroker:
    """EventBroker implementation backed by Redis Streams."""

    def __init__(self, redis_url: str) -> None:
        import redis.asyncio as aioredis  # type: ignore
        self._client = aioredis.from_url(redis_url, decode_responses=True)

    async def publish(self, topic: str, message: str) -> None:
        stream_key = f"events:{topic}"
        await self._client.xadd(stream_key, {"data": message}, maxlen=10_000)

    async def close(self) -> None:
        await self._client.aclose()


class _AsyncSyncOutboxRepo:
    """Thin async wrapper over the sync SqlAlchemy outbox repo.

    The main app uses sync SQLAlchemy. The outbox relay expects async.
    We run the sync calls in a thread executor.
    """

    def __init__(self) -> None:
        pass

    def _get_session(self):
        from app.infra.database import SessionLocal
        return SessionLocal()

    async def append(self, entry) -> None:
        import asyncio
        from app.contexts._shared.outbox.sql_repository import SqlAlchemyOutboxRepository
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._sync_append, entry)

    def _sync_append(self, entry) -> None:
        from app.contexts._shared.outbox.sql_repository import OutboxRow
        db = self._get_session()
        try:
            db.add(OutboxRow.from_entry(entry))
            db.commit()
        finally:
            db.close()

    async def fetch_pending(self, limit: int = 100):
        import asyncio
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._sync_fetch_pending, limit)

    def _sync_fetch_pending(self, limit: int):
        from app.contexts._shared.outbox.sql_repository import OutboxRow
        from app.contexts._shared.outbox.outbox import OutboxStatus
        from sqlalchemy import select
        db = self._get_session()
        try:
            rows = db.execute(
                select(OutboxRow)
                .where(OutboxRow.status.in_([OutboxStatus.PENDING.value, OutboxStatus.FAILED.value]))
                .order_by(OutboxRow.created_at)
                .limit(limit)
            ).scalars().all()
            return [r.to_entry() for r in rows]
        finally:
            db.close()

    async def mark_processing(self, ids):
        import asyncio
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._sync_mark_processing, ids)

    def _sync_mark_processing(self, ids):
        from app.contexts._shared.outbox.sql_repository import OutboxRow
        from app.contexts._shared.outbox.outbox import OutboxStatus
        from sqlalchemy import update
        db = self._get_session()
        try:
            db.execute(
                update(OutboxRow)
                .where(OutboxRow.id.in_(ids))
                .values(status=OutboxStatus.PROCESSING.value)
            )
            db.commit()
        finally:
            db.close()

    async def mark_delivered(self, id):
        import asyncio
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._sync_mark_delivered, id)

    def _sync_mark_delivered(self, id):
        from app.contexts._shared.outbox.sql_repository import OutboxRow
        from app.contexts._shared.outbox.outbox import OutboxStatus
        db = self._get_session()
        try:
            row = db.get(OutboxRow, id)
            if row:
                row.status = OutboxStatus.DELIVERED.value
                db.commit()
        finally:
            db.close()

    async def mark_failed(self, id, error: str, max_retries: int = 5):
        import asyncio
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._sync_mark_failed, id, error, max_retries)

    def _sync_mark_failed(self, id, error: str, max_retries: int):
        from app.contexts._shared.outbox.sql_repository import OutboxRow
        from app.contexts._shared.outbox.outbox import OutboxStatus
        db = self._get_session()
        try:
            row = db.get(OutboxRow, id)
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


def build_outbox_relay() -> Optional[object]:
    """Build OutboxRelay. Returns None if Redis is unavailable."""
    from app.config import settings
    from app.contexts._shared.outbox import OutboxRelay

    try:
        broker = _RedisStreamBroker(settings.redis_url)
    except Exception as exc:
        logger.warning("outbox: Redis bağlantısı kurulamadı — relay devre dışı: %s", exc)
        return None

    repo = _AsyncSyncOutboxRepo()
    return OutboxRelay(repository=repo, broker=broker)
