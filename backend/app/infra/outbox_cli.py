"""Standalone outbox relay CLI — run event delivery loop directly.

Usage:
    python -m app.infra.outbox_cli

This is used in production as a separate container that polls the outbox table
and publishes events to Redis Streams. Useful for decoupling event delivery from
the main app request/response loop.
"""
import asyncio
import logging
import sys
from typing import Optional

logger = logging.getLogger(__name__)


async def main() -> None:
    """Run the outbox relay event delivery loop."""
    from app.config import settings
    from app.infra.outbox_bootstrap import build_outbox_relay

    # Validate production settings
    if settings.is_production_like:
        if not settings.outbox_relay_enabled:
            raise RuntimeError(
                "Production: OUTBOX_RELAY_ENABLED must be true to run the relay."
            )

    relay = build_outbox_relay()
    if relay is None:
        logger.error(
            "Failed to build outbox relay. Redis or database connection unavailable."
        )
        if settings.is_production_like:
            sys.exit(1)
        else:
            logger.warning("Relay disabled (dev mode). Exiting gracefully.")
            return

    logger.info("Outbox relay starting (poll_interval=2.0s)...")
    try:
        # Run the relay loop until interrupted
        await relay.run_forever(poll_interval=2.0)
    except KeyboardInterrupt:
        logger.info("Outbox relay shutting down (SIGINT received)...")
    except Exception as exc:
        logger.exception("Outbox relay fatal error: %s", exc)
        if settings.is_production_like:
            sys.exit(1)


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Run the async loop
    try:
        asyncio.run(main())
    except Exception as exc:
        logger.exception("Failed to start outbox relay: %s", exc)
        sys.exit(1)
