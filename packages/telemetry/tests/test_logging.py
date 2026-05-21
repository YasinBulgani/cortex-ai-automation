"""Tests for neurex_telemetry.logging JSON formatter."""

from __future__ import annotations

import json
import logging
import sys
from io import StringIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from neurex_telemetry.logging import _JsonFormatter, configure_logging


def _capture_log(service: str, message: str, level: str = "INFO", **extra) -> dict:
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(_JsonFormatter(service=service))
    logger = logging.getLogger(f"test.{service}")
    logger.handlers = [handler]
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    method = getattr(logger, level.lower())
    method(message, extra=extra if extra else None)

    output = stream.getvalue().strip()
    return json.loads(output)


class TestJsonFormatter:
    def test_emits_valid_json(self):
        entry = _capture_log("test-svc", "hello world")
        assert isinstance(entry, dict)

    def test_required_fields_present(self):
        entry = _capture_log("my-service", "test message")
        assert entry["level"] == "INFO"
        assert entry["service"] == "my-service"
        assert entry["msg"] == "test message"
        assert "ts" in entry
        assert "logger" in entry

    def test_extra_fields_included(self):
        entry = _capture_log("svc", "msg", request_id="abc123", user_id="u1")
        assert entry.get("request_id") == "abc123"
        assert entry.get("user_id") == "u1"

    def test_error_level(self):
        entry = _capture_log("svc", "boom", level="ERROR")
        assert entry["level"] == "ERROR"

    def test_exception_formatting(self):
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(_JsonFormatter(service="exc-svc"))
        logger = logging.getLogger("test.exc")
        logger.handlers = [handler]
        logger.setLevel(logging.DEBUG)
        logger.propagate = False

        try:
            raise ValueError("test exception")
        except ValueError:
            logger.exception("caught error")

        output = stream.getvalue().strip()
        entry = json.loads(output)
        assert "exc_info" in entry
        assert "ValueError" in entry["exc_info"]


class TestConfigureLogging:
    def test_configure_logging_does_not_raise(self):
        configure_logging(service="test-configure", level="WARNING", force_json=True)

    def test_configure_logging_sets_level(self):
        configure_logging(service="test-level", level="DEBUG", force_json=True)
        root = logging.getLogger()
        assert root.level == logging.DEBUG
