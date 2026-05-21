"""Thin Stripe API wrapper — direct HTTP calls, no SDK dependency.

We hit the Stripe REST API with the secret key in a Bearer header. This
keeps the dependency surface minimal and lets us mock easily in tests.
The wrapper is intentionally narrow: only the endpoints billing needs.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import time
from typing import Any, Optional
from urllib.parse import urlencode

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


STRIPE_BASE = "https://api.stripe.com/v1"


class StripeNotConfigured(RuntimeError):
    """Raised when a Stripe call is attempted without secret_key set."""


class StripeError(RuntimeError):
    """Stripe API returned a non-2xx response."""

    def __init__(self, status_code: int, payload: Any):
        self.status_code = status_code
        self.payload = payload
        message = (
            payload.get("error", {}).get("message")
            if isinstance(payload, dict)
            else str(payload)
        )
        super().__init__(f"Stripe {status_code}: {message}")


def _require_key() -> str:
    if not settings.stripe_secret_key:
        raise StripeNotConfigured(
            "STRIPE_SECRET_KEY ortam degiskeni ayarlanmamis. "
            "Stripe panelinden anahtar alip ortam degiskeni olarak girin."
        )
    return settings.stripe_secret_key


def _post(path: str, form: dict[str, Any]) -> dict:
    key = _require_key()
    flat = _flatten_form(form)
    with httpx.Client(timeout=15.0) as client:
        resp = client.post(
            f"{STRIPE_BASE}{path}",
            content=urlencode(flat),
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
    try:
        payload = resp.json()
    except Exception:
        payload = {"raw": resp.text}
    if resp.status_code >= 400:
        raise StripeError(resp.status_code, payload)
    return payload


def _flatten_form(form: dict[str, Any], parent: str = "") -> dict[str, Any]:
    """Stripe expects ``customer[email]`` style keys. Flatten nested dicts."""
    flat: dict[str, Any] = {}
    for k, v in form.items():
        key = f"{parent}[{k}]" if parent else k
        if isinstance(v, dict):
            flat.update(_flatten_form(v, key))
        elif v is None:
            continue
        else:
            flat[key] = v
    return flat


# ── Public ops ──────────────────────────────────────────────────────────────


def create_checkout_session(
    *,
    price_id: str,
    customer_email: Optional[str],
    customer_id: Optional[str],
    tenant_id: str,
    plan_code: str,
    success_url: str,
    cancel_url: str,
) -> dict:
    """Create a Checkout Session for a subscription. Returns ``{id, url, ...}``."""
    form: dict[str, Any] = {
        "mode": "subscription",
        "success_url": success_url,
        "cancel_url": cancel_url,
        "line_items[0][price]": price_id,
        "line_items[0][quantity]": 1,
        "metadata[tenant_id]": tenant_id,
        "metadata[plan_code]": plan_code,
        "subscription_data[metadata][tenant_id]": tenant_id,
        "subscription_data[metadata][plan_code]": plan_code,
    }
    if customer_id:
        form["customer"] = customer_id
    elif customer_email:
        form["customer_email"] = customer_email
    return _post("/checkout/sessions", form)


def create_billing_portal_session(*, customer_id: str, return_url: str) -> dict:
    return _post(
        "/billing_portal/sessions",
        {"customer": customer_id, "return_url": return_url},
    )


# ── Webhook signature verification ──────────────────────────────────────────


def verify_webhook_signature(
    payload: bytes,
    sig_header: str,
    *,
    secret: Optional[str] = None,
    tolerance_seconds: int = 300,
) -> dict:
    """Validate ``Stripe-Signature`` and return the parsed event.

    Implements Stripe's spec: ``t=<timestamp>,v1=<hex_hmac>``. We do not
    pull in ``stripe`` SDK; one HMAC + constant-time compare is enough.
    """
    import json

    secret = secret or settings.stripe_webhook_secret
    if not secret:
        raise StripeNotConfigured("STRIPE_WEBHOOK_SECRET ayarlanmamis")
    if not sig_header:
        raise ValueError("Stripe-Signature header eksik")

    parts = dict(seg.split("=", 1) for seg in sig_header.split(",") if "=" in seg)
    timestamp = parts.get("t")
    sig = parts.get("v1")
    if not timestamp or not sig:
        raise ValueError("Stripe-Signature formati hatali")

    if abs(time.time() - int(timestamp)) > tolerance_seconds:
        raise ValueError("Stripe-Signature timestamp tolerans disinda")

    signed_payload = f"{timestamp}.".encode() + payload
    expected = hmac.new(
        secret.encode("utf-8"), signed_payload, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, sig):
        raise ValueError("Stripe-Signature dogrulanamadi")

    return json.loads(payload.decode("utf-8"))
