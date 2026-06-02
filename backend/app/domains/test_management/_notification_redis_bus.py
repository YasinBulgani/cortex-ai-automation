"""Redis pub/sub adapter for the M-45 SSE notification bus.

When ``REDIS_URL`` is set we route in-app notification fan-out through
Redis so multiple FastAPI workers can deliver events to whichever
worker happens to hold the user's open SSE connection.

The persistent ``mgmt_notifications`` table remains the source of
truth — Redis is purely a hot-path delivery channel.

This module is loaded lazily by :func:`comments_service._get_notification_bus`;
import-time failures fall back to the in-process bus.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, AsyncIterator, Optional

logger = logging.getLogger(__name__)

_CHANNEL_PREFIX = "mgmt:notif:"


class RedisNotificationBus:
    """Cross-process pub/sub keyed by ``user_id``.

    The public surface mirrors :class:`comments_service._NotificationBus`
    so it can be swapped behind the ``_bus`` global without callers
    having to know which backend is active. Subscription consumes from
    a local ``asyncio.Queue`` fed by a background pubsub listener task.
    """

    _singleton: "Optional[RedisNotificationBus]" = None

    def __init__(self, url: Optional[str] = None) -> None:
        from redis import asyncio as redis_asyncio  # type: ignore

        self._url = url or os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        self._async_redis = redis_asyncio.from_url(self._url, decode_responses=True)
        # Sync redis only used for the fire-and-forget publish path so we
        # don't have to await inside _broadcast (called from sync code).
        import redis  # type: ignore

        self._sync_redis = redis.Redis.from_url(self._url, decode_responses=True)
        self._subscribers: dict[str, set[asyncio.Queue[dict[str, Any]]]] = {}
        self._listeners: dict[str, asyncio.Task[None]] = {}
        self._lock = asyncio.Lock()

    @classmethod
    def instance(cls) -> "RedisNotificationBus":
        if cls._singleton is None:
            cls._singleton = cls()
        return cls._singleton

    # ── publish ──────────────────────────────────────────────────────────────

    def publish(self, user_id: str, payload: dict[str, Any]) -> None:
        """Synchronous fan-out — used from sync request handlers."""
        try:
            self._sync_redis.publish(
                _CHANNEL_PREFIX + user_id, json.dumps(payload, default=str)
            )
        except Exception as exc:  # pragma: no cover — transient redis errors
            logger.warning("RedisNotificationBus.publish failed: %s", exc)

    async def apublish(self, user_id: str, payload: dict[str, Any]) -> None:
        """Async variant for code paths inside the event loop."""
        try:
            await self._async_redis.publish(
                _CHANNEL_PREFIX + user_id, json.dumps(payload, default=str)
            )
        except Exception as exc:  # pragma: no cover
            logger.warning("RedisNotificationBus.apublish failed: %s", exc)

    # ── subscribe ────────────────────────────────────────────────────────────

    async def subscribe(self, user_id: str) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=256)
        async with self._lock:
            self._subscribers.setdefault(user_id, set()).add(queue)
            if user_id not in self._listeners:
                self._listeners[user_id] = asyncio.create_task(
                    self._listen(user_id), name=f"mgmt-notif-listen-{user_id[:8]}"
                )
        return queue

    async def unsubscribe(
        self, user_id: str, queue: asyncio.Queue[dict[str, Any]]
    ) -> None:
        async with self._lock:
            queues = self._subscribers.get(user_id)
            if queues is None:
                return
            queues.discard(queue)
            if queues:
                return
            self._subscribers.pop(user_id, None)
            task = self._listeners.pop(user_id, None)
        if task is not None:
            task.cancel()

    async def _listen(self, user_id: str) -> None:
        """Background coroutine: subscribe in Redis, fan-out to local queues."""
        try:
            pubsub = self._async_redis.pubsub()
            await pubsub.subscribe(_CHANNEL_PREFIX + user_id)
            async for message in pubsub.listen():
                if not message or message.get("type") != "message":
                    continue
                data = message.get("data")
                if not data:
                    continue
                try:
                    payload = json.loads(data) if isinstance(data, str) else data
                except (TypeError, json.JSONDecodeError):
                    continue
                queues = list(self._subscribers.get(user_id, ()))
                for q in queues:
                    try:
                        q.put_nowait(payload)
                    except asyncio.QueueFull:
                        try:
                            q.get_nowait()
                            q.put_nowait(payload)
                        except Exception:
                            pass
        except asyncio.CancelledError:  # pragma: no cover — task cancellation
            raise
        except Exception as exc:  # pragma: no cover — defensive
            logger.warning(
                "RedisNotificationBus listen loop for %s failed: %s", user_id, exc
            )

    async def aiter_events(self, user_id: str) -> AsyncIterator[dict[str, Any]]:
        """Convenience: yield events for a single subscriber until cancelled."""
        queue = await self.subscribe(user_id)
        try:
            while True:
                payload = await queue.get()
                yield payload
        finally:
            await self.unsubscribe(user_id, queue)
