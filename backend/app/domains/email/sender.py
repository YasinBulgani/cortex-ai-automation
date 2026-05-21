"""Email sender — provider-agnostic facade.

Provider resolution order (first ready wins):
    1. ``EMAIL_PROVIDER`` env value, if set explicitly
    2. SMTP if ``SMTP_HOST`` and ``SMTP_USER`` set
    3. Console fallback (logs the message instead of sending)

The console provider is intentionally NOT a no-op — it logs the full
payload so dev/test environments can observe what *would* go out.
"""
from __future__ import annotations

import logging
import os
import smtplib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Mapping, Optional, Protocol

from app.domains.email.templates import render

logger = logging.getLogger(__name__)


@dataclass
class EmailMessage:
    to: str
    subject: str
    html: str
    text: str
    sender: Optional[str] = None
    reply_to: Optional[str] = None
    headers: dict[str, str] = field(default_factory=dict)


@dataclass
class SendOutcome:
    provider: str
    delivered: bool
    message_id: Optional[str] = None
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class EmailProvider(Protocol):
    name: str

    def is_ready(self) -> bool: ...
    def send(self, message: EmailMessage) -> SendOutcome: ...


# ── Providers ───────────────────────────────────────────────────────────────


class ConsoleProvider:
    """Logs the message instead of delivering it. Always ready."""

    name = "console"

    def is_ready(self) -> bool:
        return True

    def send(self, message: EmailMessage) -> SendOutcome:
        logger.info(
            "email[console] to=%s subject=%r len(text)=%d",
            message.to,
            message.subject,
            len(message.text),
        )
        # Multi-line dump at DEBUG so dev can inspect without flooding INFO
        logger.debug("email[console] text:\n%s", message.text)
        return SendOutcome(
            provider=self.name,
            delivered=True,
            message_id=f"console-{datetime.now(timezone.utc).timestamp():.0f}",
        )


class SmtpProvider:
    name = "smtp"

    def __init__(self) -> None:
        self.host = os.environ.get("SMTP_HOST", "")
        self.port = int(os.environ.get("SMTP_PORT", "587") or "587")
        self.user = os.environ.get("SMTP_USER", "")
        self.password = os.environ.get("SMTP_PASSWORD", "")
        self.tls = os.environ.get("SMTP_TLS", "true").lower() in ("1", "true", "yes")
        self.default_from = (
            os.environ.get("SMTP_FROM")
            or self.user
            or "no-reply@neurexqa.com"
        )

    def is_ready(self) -> bool:
        return bool(self.host and self.user)

    def send(self, message: EmailMessage) -> SendOutcome:
        if not self.is_ready():
            return SendOutcome(
                provider=self.name,
                delivered=False,
                error="SMTP yapılandırılmamış",
            )

        sender = message.sender or self.default_from
        mime = MIMEMultipart("alternative")
        mime["From"] = sender
        mime["To"] = message.to
        mime["Subject"] = message.subject
        if message.reply_to:
            mime["Reply-To"] = message.reply_to
        for k, v in message.headers.items():
            mime[k] = v
        mime.attach(MIMEText(message.text, "plain", "utf-8"))
        mime.attach(MIMEText(message.html, "html", "utf-8"))

        try:
            with smtplib.SMTP(self.host, self.port, timeout=15) as srv:
                if self.tls:
                    srv.starttls()
                srv.login(self.user, self.password)
                srv.sendmail(sender, [message.to], mime.as_string())
        except Exception as exc:
            logger.warning("email[smtp] send failed to=%s: %s", message.to, exc)
            return SendOutcome(provider=self.name, delivered=False, error=str(exc))

        return SendOutcome(provider=self.name, delivered=True)


_PROVIDERS = {"console": ConsoleProvider, "smtp": SmtpProvider}
_SENDER_CACHE: Optional[EmailProvider] = None


def available_providers() -> list[str]:
    return [name for name, cls in _PROVIDERS.items() if cls().is_ready()]


def get_sender(force_provider: Optional[str] = None) -> EmailProvider:
    """Resolve the active provider. Caches result.

    Pass ``force_provider`` to override (used in tests).
    """
    global _SENDER_CACHE
    if force_provider:
        cls = _PROVIDERS.get(force_provider)
        if cls is None:
            raise ValueError(f"Bilinmeyen email provider: {force_provider}")
        return cls()
    if _SENDER_CACHE is not None:
        return _SENDER_CACHE
    explicit = os.environ.get("EMAIL_PROVIDER", "").strip().lower()
    if explicit and explicit in _PROVIDERS:
        provider: EmailProvider = _PROVIDERS[explicit]()
        if provider.is_ready():
            _SENDER_CACHE = provider
            return provider
    for name in ("smtp", "console"):
        provider = _PROVIDERS[name]()
        if provider.is_ready():
            _SENDER_CACHE = provider
            return provider
    _SENDER_CACHE = ConsoleProvider()
    return _SENDER_CACHE


def reset_sender_cache() -> None:
    """Clear cached provider (test helper)."""
    global _SENDER_CACHE
    _SENDER_CACHE = None


# ── Public send API ─────────────────────────────────────────────────────────


def send(message: EmailMessage, *, provider: Optional[str] = None) -> SendOutcome:
    """Send an arbitrary message via the active provider.

    Failures are caught and returned as ``SendOutcome(delivered=False, ...)``
    — we never raise from this entry point because email is best-effort.
    """
    try:
        return get_sender(provider).send(message)
    except Exception as exc:  # pragma: no cover — defensive
        logger.exception("email send unexpected error to=%s", message.to)
        return SendOutcome(
            provider=provider or "unknown", delivered=False, error=str(exc)
        )


def send_template(
    template_id: str,
    *,
    to: str,
    ctx: Mapping[str, Any],
    sender: Optional[str] = None,
    reply_to: Optional[str] = None,
    provider: Optional[str] = None,
) -> SendOutcome:
    """Render template + send. Missing context keys leave ``{key}`` literals."""
    try:
        subject, html, text = render(template_id, ctx)
    except KeyError as exc:
        return SendOutcome(provider="none", delivered=False, error=str(exc))
    message = EmailMessage(
        to=to,
        subject=subject,
        html=html,
        text=text,
        sender=sender,
        reply_to=reply_to,
    )
    return send(message, provider=provider)
