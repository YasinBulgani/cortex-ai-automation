"""Outbox relay integration tests.

Verifies that OutboxEntry rows are picked up by the relay and published
to Redis Streams. Skips when Redis is unavailable.
"""

from __future__ import annotations

import asyncio
import time
import uuid

import pytest

pytestmark = pytest.mark.integration


def _redis_available() -> bool:
    try:
        import redis as _redis
        from app.config import settings
        r = _redis.from_url(settings.redis_url, socket_timeout=1)
        r.ping()
        return True
    except Exception:
        return False


def _db_available() -> bool:
    try:
        from app.infra.database import SessionLocal
        from sqlalchemy import text
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


class TestOutboxRelay:

    def test_relay_builds_without_crash(self) -> None:
        """build_outbox_relay() returns a relay or None — never raises."""
        from app.infra.outbox_bootstrap import build_outbox_relay
        relay = build_outbox_relay()
        # May be None if Redis isn't available — that's OK
        assert relay is None or hasattr(relay, "run_forever")

    @pytest.mark.requires_redis
    def test_redis_stream_publish(self) -> None:
        """_RedisStreamBroker publishes to the correct stream key."""
        if not _redis_available():
            pytest.skip("Redis yok")

        import redis as _redis
        from app.config import settings
        from app.infra.outbox_bootstrap import _RedisStreamBroker

        r = _redis.from_url(settings.redis_url)
        broker = _RedisStreamBroker(settings.redis_url)

        event_type = "test.integration"
        payload = {"trace": str(uuid.uuid4()), "ts": time.time()}
        stream_key = f"events:{event_type}"

        # Clear stream before test
        try:
            r.delete(stream_key)
        except Exception:
            pass

        import json as _json
        asyncio.run(broker.publish(event_type, _json.dumps(payload)))

        # Verify message landed in the stream
        messages = r.xrange(stream_key, count=10)
        assert len(messages) >= 1, "Mesaj Redis stream'e yazılmadı"
        _, fields = messages[-1]
        assert b"payload" in fields or b"type" in fields or len(fields) > 0

    @pytest.mark.requires_db
    @pytest.mark.requires_redis
    def test_outbox_entry_processed_by_relay(self) -> None:
        """End-to-end: OutboxEntry → relay.poll_once() → Redis Streams."""
        if not _db_available():
            pytest.skip("DB yok")
        if not _redis_available():
            pytest.skip("Redis yok")

        from app.infra.outbox_bootstrap import build_outbox_relay

        relay = build_outbox_relay()
        if relay is None:
            pytest.skip("Relay kurulamadı (Redis unavailable)")

        # Seed an outbox entry directly via SQL
        from app.infra.database import SessionLocal
        from sqlalchemy import text

        entry_id = str(uuid.uuid4())
        with SessionLocal() as db:
            # Check if outbox table exists
            table_exists = db.execute(text("""
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'outbox_events'
            """)).fetchone()
            if not table_exists:
                pytest.skip("outbox_events tablosu yok — migration uygulanmamış")

            db.execute(text("""
                INSERT INTO outbox_events (id, event_type, payload, status)
                VALUES (:id, 'integration.test', :payload, 'pending')
            """), {"id": entry_id, "payload": '{"test": true}'})
            db.commit()

        # Run one poll cycle
        asyncio.run(relay.poll_once())

        # Entry should now be marked as processed
        with SessionLocal() as db:
            row = db.execute(
                text("SELECT status FROM outbox_events WHERE id = :id"),
                {"id": entry_id},
            ).fetchone()
            if row:
                assert row[0] in ("sent", "processed", "delivered"), (
                    f"Outbox entry işlenmedi: status={row[0]}"
                )
