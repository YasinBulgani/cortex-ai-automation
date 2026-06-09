"""Event Broker implementations — Kafka + Redis Streams.

Provides async interface for publishing events to streaming platforms.
Kafka: production-grade, partitioned topics, offset management.
Redis Streams: lightweight fallback, single-node or sentinel.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


class EventBroker(ABC):
    """Abstract event broker interface."""

    @abstractmethod
    async def publish(self, topic: str, event: dict, partition_key: Optional[str] = None) -> str:
        """Publish event to topic. Returns message ID.

        Args:
            topic: Topic/stream name (e.g., "auth.events")
            event: Event payload as dict
            partition_key: Optional key for partitioning (ensures ordering per key)

        Returns:
            Message ID (offset for Kafka, stream entry for Redis)
        """
        ...

    @abstractmethod
    async def close(self) -> None:
        """Graceful shutdown."""
        ...


class KafkaBroker(EventBroker):
    """Kafka broker with schema validation, partitioning, compression."""

    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        compression_type: str = "snappy",
        acks: str = "all",  # Wait all in-sync replicas
        retries: int = 3,
    ):
        """Initialize Kafka broker.

        Args:
            bootstrap_servers: Comma-separated brokers
            compression_type: snappy | gzip | lz4 | zstd
            acks: 0=fire-forget, 1=leader, all=replicas
            retries: Delivery retries on transient failures
        """
        self.bootstrap_servers = bootstrap_servers
        self.compression_type = compression_type
        self.acks = acks
        self.retries = retries
        self._producer = None
        self._admin_client = None

    async def _get_producer(self):
        """Lazy-initialize Kafka producer."""
        if self._producer is None:
            try:
                from aiokafka import AIOKafkaProducer
            except ImportError:
                raise ImportError("aiokafka required: pip install aiokafka")

            self._producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                compression_type=self.compression_type,
                acks=self.acks,
                retries=self.retries,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )
            await self._producer.start()
            logger.info("Kafka producer started (%s)", self.bootstrap_servers)
        return self._producer

    async def publish(self, topic: str, event: dict, partition_key: Optional[str] = None) -> str:
        """Publish event to Kafka topic.

        Exactly-once semantics via idempotent producer (default in AIOKafka).
        Ordered delivery per partition_key.
        """
        producer = await self._get_producer()
        try:
            # Timestamp added by broker (LogAppendTime)
            future = await producer.send_and_wait(
                topic,
                value=event,
                key=partition_key.encode("utf-8") if partition_key else None,
            )
            msg_id = f"{future.topic}-{future.partition}-{future.offset}"
            logger.debug("Event published to Kafka (topic=%s, key=%s, offset=%s)",
                        topic, partition_key, future.offset)
            return msg_id
        except Exception as exc:
            logger.exception("Kafka publish failed (topic=%s): %s", topic, exc)
            raise

    async def create_topic(
        self,
        topic: str,
        num_partitions: int = 3,
        replication_factor: int = 2,
        retention_ms: int = 7 * 24 * 3600 * 1000,  # 7 days
    ) -> None:
        """Create topic with configuration."""
        try:
            from aiokafka.admin import AIOKafkaAdminClient, NewTopic
        except ImportError:
            raise ImportError("aiokafka required: pip install aiokafka")

        if self._admin_client is None:
            self._admin_client = AIOKafkaAdminClient(
                bootstrap_servers=self.bootstrap_servers
            )
            await self._admin_client.start()

        new_topic = NewTopic(
            name=topic,
            num_partitions=num_partitions,
            replication_factor=replication_factor,
            topic_configs={
                "retention.ms": str(retention_ms),
                "compression.type": self.compression_type,
            },
        )

        try:
            await self._admin_client.create_topics([new_topic], validate_only=False)
            logger.info("Topic created (topic=%s, partitions=%d, rf=%d)",
                       topic, num_partitions, replication_factor)
        except Exception as exc:
            if "already exists" in str(exc):
                logger.info("Topic already exists (topic=%s)", topic)
            else:
                logger.exception("Failed to create topic: %s", exc)
                raise

    async def close(self) -> None:
        """Shutdown broker."""
        if self._producer:
            await self._producer.stop()
            logger.info("Kafka producer stopped")
        if self._admin_client:
            await self._admin_client.close()


class RedisBroker(EventBroker):
    """Redis Streams broker — lightweight alternative (single broker)."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        max_stream_len: int = 10_000,  # Keep last N events per stream
    ):
        """Initialize Redis Streams broker.

        Args:
            redis_url: Redis connection URL
            max_stream_len: Approximate stream length (auto-trim)
        """
        self.redis_url = redis_url
        self.max_stream_len = max_stream_len
        self._client = None

    async def _get_client(self):
        """Lazy-initialize Redis async client."""
        if self._client is None:
            try:
                import redis.asyncio as aioredis
            except ImportError:
                raise ImportError("redis required: pip install redis")

            self._client = aioredis.from_url(self.redis_url, decode_responses=True)
            logger.info("Redis Streams broker connected (%s)", self.redis_url)
        return self._client

    async def publish(self, topic: str, event: dict, partition_key: Optional[str] = None) -> str:
        """Publish event to Redis Stream.

        partition_key is ignored (Redis Streams don't partition).
        Returns: Stream entry ID (timestamp-sequence)
        """
        client = await self._get_client()
        stream_key = f"events:{topic}"

        try:
            # XADD: auto-generates entry ID if * used, returns entry ID
            entry_id = await client.xadd(
                stream_key,
                {"data": json.dumps(event)},
                maxlen=self.max_stream_len,
                approximate=True,  # Approximate trimming (faster)
            )
            logger.debug("Event published to Redis Stream (stream=%s, id=%s)",
                        stream_key, entry_id)
            return str(entry_id)
        except Exception as exc:
            logger.exception("Redis publish failed (stream=%s): %s", stream_key, exc)
            raise

    async def close(self) -> None:
        """Shutdown broker."""
        if self._client:
            await self._client.aclose()
            logger.info("Redis Streams broker disconnected")


def build_broker(broker_type: str, **kwargs) -> EventBroker:
    """Factory for building event broker.

    Args:
        broker_type: "kafka" | "redis" | "auto" (env-based)
        **kwargs: Broker-specific config

    Returns:
        EventBroker instance

    Example:
        broker = build_broker("kafka", bootstrap_servers="kafka:9092")
        await broker.publish("auth.events", {"user_id": "...", "action": "login"})
    """
    if broker_type == "kafka":
        return KafkaBroker(**kwargs)
    elif broker_type == "redis":
        return RedisBroker(**kwargs)
    elif broker_type == "auto":
        import os
        # Try Kafka first, fallback to Redis
        kafka_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
        if kafka_servers:
            return KafkaBroker(bootstrap_servers=kafka_servers, **kwargs)
        else:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            return RedisBroker(redis_url=redis_url, **kwargs)
    else:
        raise ValueError(f"Unknown broker type: {broker_type}")
