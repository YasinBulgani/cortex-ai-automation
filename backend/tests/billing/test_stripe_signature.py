"""Stripe webhook signature verification — unit tests with no HTTP."""

from __future__ import annotations

import hashlib
import hmac
import json
import time

import pytest

from app.domains.billing.stripe_client import (
    StripeNotConfigured,
    verify_webhook_signature,
)


SECRET = "whsec_test_secret_for_unit_tests"


def _sign(payload: bytes, secret: str = SECRET, *, ts: int | None = None) -> tuple[str, int]:
    ts = ts or int(time.time())
    signed = f"{ts}.".encode() + payload
    sig = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
    return f"t={ts},v1={sig}", ts


def test_verify_returns_parsed_event_on_valid_signature() -> None:
    payload = json.dumps({"id": "evt_1", "type": "checkout.session.completed"}).encode()
    header, _ = _sign(payload)
    event = verify_webhook_signature(payload, header, secret=SECRET)
    assert event["id"] == "evt_1"
    assert event["type"] == "checkout.session.completed"


def test_verify_rejects_tampered_payload() -> None:
    payload = b'{"id":"evt_1","type":"x"}'
    header, _ = _sign(payload)
    with pytest.raises(ValueError, match="dogrulanamadi"):
        verify_webhook_signature(b'{"id":"evt_1","type":"y"}', header, secret=SECRET)


def test_verify_rejects_wrong_secret() -> None:
    payload = b'{"id":"evt_1"}'
    header, _ = _sign(payload, "different-secret")
    with pytest.raises(ValueError, match="dogrulanamadi"):
        verify_webhook_signature(payload, header, secret=SECRET)


def test_verify_rejects_stale_timestamp() -> None:
    payload = b'{"id":"evt_1"}'
    header, _ = _sign(payload, ts=int(time.time()) - 9999)
    with pytest.raises(ValueError, match="tolerans"):
        verify_webhook_signature(payload, header, secret=SECRET, tolerance_seconds=300)


def test_verify_rejects_missing_header() -> None:
    with pytest.raises(ValueError, match="header"):
        verify_webhook_signature(b"{}", "", secret=SECRET)


def test_verify_rejects_malformed_header() -> None:
    with pytest.raises(ValueError, match="formati"):
        verify_webhook_signature(b"{}", "garbage", secret=SECRET)


def test_verify_raises_when_secret_unconfigured(monkeypatch) -> None:
    monkeypatch.setattr("app.config.settings.stripe_webhook_secret", "")
    with pytest.raises(StripeNotConfigured):
        verify_webhook_signature(b"{}", "t=0,v1=x")
