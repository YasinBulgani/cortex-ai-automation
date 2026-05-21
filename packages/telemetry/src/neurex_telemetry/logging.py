"""JSON structured logging for Neurex QA services.

Configures Python's standard logging to emit JSON lines compatible with Loki.
Falls back to plain text when running in a terminal (TTY detection).

Usage:
    from neurex_telemetry.logging import configure_logging

    configure_logging(service="neurex-backend", level="INFO")

Each log line includes:
  timestamp, level, service, logger, message, trace_id (if OTel active),
  request_id (if set on contextvars), plus any extra kwargs passed to log calls.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from typing import Any, Optional


class _JsonFormatter(logging.Formatter):
    """Emit one JSON object per log record, Loki-compatible."""

    def __init__(self, service: str) -> None:
        super().__init__()
        self._service = service

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "service": self._service,
            "logger": record.name,
            "msg": record.getMessage(),
        }

        # OTel trace context
        try:
            from opentelemetry import trace
            span = trace.get_current_span()
            if span and span.is_recording():
                ctx = span.get_span_context()
                entry["trace_id"] = format(ctx.trace_id, "032x")
                entry["span_id"] = format(ctx.span_id, "016x")
        except Exception:
            pass

        # Extra fields attached via logger.info("msg", extra={...})
        skip = frozenset(logging.LogRecord.__dict__) | frozenset({
            "args", "msg", "message", "levelname", "name", "pathname",
            "filename", "module", "exc_info", "exc_text", "stack_info",
            "lineno", "funcName", "created", "msecs", "relativeCreated",
            "thread", "threadName", "processName", "process",
        })
        for k, v in record.__dict__.items():
            if k not in skip and not k.startswith("_"):
                try:
                    json.dumps(v)  # serialize check
                    entry[k] = v
                except (TypeError, ValueError):
                    entry[k] = str(v)

        if record.exc_info:
            entry["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(entry, ensure_ascii=False)


def _is_tty() -> bool:
    return hasattr(sys.stderr, "isatty") and sys.stderr.isatty()


def configure_logging(
    *,
    service: str = "neurex-service",
    level: str | None = None,
    force_json: bool = False,
) -> None:
    """Configure root logger for structured JSON or human-readable output.

    Call once at service startup, before any other log output.

    Args:
        service: Service name embedded in every log line.
        level: Log level string (DEBUG/INFO/WARNING/ERROR). Falls back to
               LOG_LEVEL env var, then INFO.
        force_json: If True, emit JSON even when stdout is a TTY.
    """
    effective_level = (
        level
        or os.environ.get("LOG_LEVEL", "").upper()
        or "INFO"
    )
    numeric_level = getattr(logging, effective_level, logging.INFO)

    use_json = force_json or not _is_tty() or os.environ.get("LOG_FORMAT", "") == "json"

    if use_json:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(_JsonFormatter(service=service))
    else:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(
            logging.Formatter(
                fmt=f"%(asctime)s [{service}] %(levelname)s %(name)s — %(message)s",
                datefmt="%H:%M:%S",
            )
        )

    root = logging.getLogger()
    root.setLevel(numeric_level)
    root.handlers.clear()
    root.addHandler(handler)

    # Quiet noisy third-party loggers
    for noisy in ("uvicorn.access", "httpx", "httpcore", "urllib3", "boto3", "botocore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
