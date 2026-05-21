"""email_service ünite testleri.

Şifre sıfırlama akışı için kritik:
- Kullanıcı mevcutsa gerçekten bir e-posta üretiliyor.
- Konu ve body Türkçe ve doğru URL içeriyor.
- Console backend asla exception fırlatmıyor.
"""

from __future__ import annotations

import pytest

from app.services.email_service import (
    ConsoleEmailBackend,
    EmailMessageData,
    MemoryEmailBackend,
    build_password_reset_email,
    get_email_backend,
    send_email,
    set_email_backend,
)


def test_build_password_reset_email_contains_url_and_tr_text() -> None:
    msg = build_password_reset_email(
        to="user@example.com",
        reset_url="https://app.example.com/reset-password?token=abc123",
        full_name="Ayşe Demir",
    )
    assert msg.to == "user@example.com"
    assert "Şifre sıfırlama" in msg.subject
    assert "Ayşe Demir" in msg.body_text
    assert "https://app.example.com/reset-password?token=abc123" in msg.body_text
    assert msg.body_html is not None
    assert "https://app.example.com/reset-password?token=abc123" in msg.body_html


def test_build_password_reset_email_without_name_uses_generic_greeting() -> None:
    msg = build_password_reset_email(
        to="x@y.com", reset_url="https://x/y?token=t"
    )
    assert "Merhaba," in msg.body_text
    assert "Merhaba None" not in msg.body_text


def test_memory_backend_records_sent_messages() -> None:
    backend = MemoryEmailBackend()
    set_email_backend(backend)
    try:
        send_email(
            EmailMessageData(
                to="a@b.com", subject="Test", body_text="merhaba"
            )
        )
        assert len(backend.outbox) == 1
        assert backend.outbox[0].to == "a@b.com"
    finally:
        set_email_backend(ConsoleEmailBackend())


def test_send_email_swallows_exceptions(monkeypatch: pytest.MonkeyPatch) -> None:
    """Backend fırlatırsa send_email log'a yazıp yutmalı — API çökmesin."""

    class Boom:
        def send(self, _msg):
            raise RuntimeError("smtp down")

    set_email_backend(Boom())
    try:
        # Raise etmemeli
        send_email(EmailMessageData(to="x@y.com", subject="s", body_text="b"))
    finally:
        set_email_backend(ConsoleEmailBackend())


def test_get_email_backend_is_cached() -> None:
    set_email_backend(ConsoleEmailBackend())
    a = get_email_backend()
    b = get_email_backend()
    assert a is b
