"""Outbox Relay CLI — Standalone event delivery service (Faz 3.5).

Run as separate Docker container to decouple event publishing from request/response.

Usage:
    python -m app.infra.event_streaming.outbox_relay_cli

Environment:
    OUTBOX_RELAY_POLL_INTERVAL_SECONDS=2
    OUTBOX_RELAY_BATCH_SIZE=100
    KAFKA_ENABLED=true|false (auto-selected)
    KAFKA_BOOTSTRAP_SERVERS=localhost:9092
    REDIS_STREAMS_ENABLED=true|false
    REDIS_URL=redis://localhost:6379/0
"""

import asyncio
import logging
import os
import sys
from typing import Optional

logger = logging.getLogger(__name__)


async def main() -> None:
    """Run the outbox relay with configurable broker (Kafka or Redis)."""
    from app.config import settings

    # Load configuration
    poll_interval = float(os.getenv("OUTBOX_RELAY_POLL_INTERVAL_SECONDS", "2.0"))
    batch_size = int(os.getenv("OUTBOX_RELAY_BATCH_SIZE", "100"))
    broker_type = os.getenv("OUTBOX_RELAY_BROKER", "auto")  # auto | kafka | redis

    logger.info("Starting Outbox Relay (broker=%s, poll=%fs, batch=%d)",
               broker_type, poll_interval, batch_size)

    # Validate production settings
    if settings.is_production_like:
        if not settings.outbox_relay_enabled:
            logger.error("Production: OUTBOX_RELAY_ENABLED must be true")
            sys.exit(1)

    # Build broker (Kafka or Redis)
    broker = None
    try:
        if broker_type == "kafka":
            from app.infra.event_streaming.broker import KafkaBroker

            kafka_servers = os.getenv(
                "KAFKA_BOOTSTRAP_SERVERS",
                os.getenv("KAFKA_BROKERS", "localhost:9092"),
            )
            broker = KafkaBroker(bootstrap_servers=kafka_servers)
            logger.info("Using Kafka broker (%s)", kafka_servers)

        elif broker_type == "redis":
            from app.infra.event_streaming.broker import RedisBroker

            redis_url = os.getenv("REDIS_URL", settings.redis_url)
            broker = RedisBroker(redis_url=redis_url)
            logger.info("Using Redis Streams broker (%s)", redis_url)

        elif broker_type == "auto":
            # Auto-detect: Kafka if configured, else Redis
            kafka_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
            if kafka_servers:
                from app.infra.event_streaming.broker import KafkaBroker
                broker = KafkaBroker(bootstrap_servers=kafka_servers)
                logger.info("Auto-selected Kafka broker (%s)", kafka_servers)
            else:
                from app.infra.event_streaming.broker import RedisBroker
                redis_url = os.getenv("REDIS_URL", settings.redis_url)
                broker = RedisBroker(redis_url=redis_url)
                logger.info("Auto-selected Redis Streams broker (%s)", redis_url)
        else:
            raise ValueError(f"Unknown broker type: {broker_type}")

    except Exception as exc:
        logger.error("Failed to initialize broker: %s", exc)
        if settings.is_production_like:
            sys.exit(1)
        else:
            logger.warning("Broker unavailable (dev mode). Exiting gracefully.")
            return

    # Build relay
    relay = None
    try:
        if broker_type in ("kafka", "auto") and isinstance(broker, KafkaBroker):
            # Kafka relay
            from app.infra.event_streaming.outbox_relay_kafka import OutboxRelayKafka
            from app.contexts._shared.outbox.sql_repository import OutboxRepository

            repo = OutboxRepository()
            relay = OutboxRelayKafka(broker=broker, repository=repo)
            logger.info("Using Kafka outbox relay")
        else:
            # Redis relay (legacy)
            from app.infra.outbox_bootstrap import build_outbox_relay
            relay = build_outbox_relay()
            if relay is None:
                logger.error("Failed to build outbox relay")
                sys.exit(1) if settings.is_production_like else None

    except Exception as exc:
        logger.exception("Failed to build relay: %s", exc)
        if settings.is_production_like:
            sys.exit(1)
        return

    # Run relay loop
    logger.info("Outbox relay running...")
    try:
        await relay.run_forever(poll_interval=poll_interval)
    except KeyboardInterrupt:
        logger.info("Relay shutting down (SIGINT)...")
    except Exception as exc:
        logger.exception("Relay fatal error: %s", exc)
        if settings.is_production_like:
            sys.exit(1)
    finally:
        # Cleanup
        if broker:
            try:
                await broker.close()
                logger.info("Broker closed")
            except Exception as exc:
                logger.exception("Error closing broker: %s", exc)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    try:
        asyncio.run(main())
    except Exception as exc:
        logger.exception("Failed to start relay: %s", exc)
        sys.exit(1)
