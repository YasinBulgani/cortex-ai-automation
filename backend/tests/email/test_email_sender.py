"""Email sender — provider resolution + best-effort send semantics."""

from __future__ import annotations

import pytest

from app.domains.email.sender import (
    ConsoleProvider,
    EmailMessage,
    SendOutcome,
    SmtpProvider,
    available_providers,
    get_sender,
    reset_sender_cache,
    send,
    send_template,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    reset_sender_cache()
    yield
    reset_sender_cache()


def test_console_provider_is_always_ready() -> None:
    assert ConsoleProvider().is_ready() is True


def test_smtp_provider_needs_host_and_user(monkeypatch) -> None:
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_USER", raising=False)
    assert SmtpProvider().is_ready() is False

    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_USER", "user@example.com")
    assert SmtpProvider().is_ready() is True


def test_get_sender_prefers_explicit_env(monkeypatch) -> None:
    monkeypatch.setenv("EMAIL_PROVIDER", "console")
    sender = get_sender()
    assert sender.name == "console"


def test_get_sender_falls_back_to_console_when_smtp_unconfigured(monkeypatch) -> None:
    monkeypatch.delenv("EMAIL_PROVIDER", raising=False)
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_USER", raising=False)
    assert get_sender().name == "console"


def test_force_provider_overrides_default() -> None:
    sender = get_sender(force_provider="console")
    assert sender.name == "console"


def test_console_send_returns_delivered() -> None:
    outcome = send(
        EmailMessage(
            to="user@example.com",
            subject="Hi",
            html="<p>x</p>",
            text="x",
        ),
        provider="console",
    )
    assert outcome.delivered is True
    assert outcome.provider == "console"
    assert outcome.message_id is not None


def test_send_template_renders_and_dispatches(caplog) -> None:
    with caplog.at_level("INFO"):
        outcome = send_template(
            "welcome",
            to="new@example.com",
            ctx={
                "full_name": "Test User",
                "dashboard_url": "https://app.example.com",
            },
            provider="console",
        )
    assert outcome.delivered is True
    assert outcome.provider == "console"
    # Log line should reference the recipient
    assert any("new@example.com" in rec.getMessage() for rec in caplog.records)


def test_send_template_unknown_id_returns_failure() -> None:
    outcome = send_template(
        "no_such_template",
        to="x@y.com",
        ctx={},
        provider="console",
    )
    assert outcome.delivered is False
    assert "no_such_template" in (outcome.error or "")


def test_available_providers_lists_at_least_console() -> None:
    assert "console" in available_providers()


def test_smtp_unconfigured_returns_outcome_not_raises(monkeypatch) -> None:
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_USER", raising=False)
    outcome = SmtpProvider().send(
        EmailMessage(to="x@y.com", subject="s", html="h", text="t")
    )
    assert outcome.delivered is False
    assert "yapılandırılmamış" in (outcome.error or "")
