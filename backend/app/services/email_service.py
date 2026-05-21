"""E-posta gönderim servisi.

Amaç: Uygulamadan çıkan tüm e-postalar (şifre sıfırlama, bildirim, davet)
tek bir servis üzerinden akar. Üç backend desteklenir:

- **console** (default/dev): Mesaj stdout'a yazılır, gerçekten gönderilmez.
  Lokal geliştirme ve CI için idealdir; SMTP kimlik bilgisine ihtiyaç yoktur.
- **smtp**: Standart SMTP (TLS/STARTTLS destekli).
- **memory** (test): Gönderilen mesajlar `MemoryEmailBackend.outbox`'a
  eklenir. Ünite testlerinde assertion için kullanılır.

Seçim `EMAIL_BACKEND` ortam değişkeni ile yapılır.

Bu modül **senkrondur**: FastAPI'de kullanırken `fastapi.BackgroundTasks`
ile çağırarak isteği geciktirmeyin.
"""

from __future__ import annotations

import logging
import os
import smtplib
from dataclasses import dataclass, field
from email.message import EmailMessage
from typing import Protocol

_logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmailMessageData:
    to: str
    subject: str
    body_text: str
    body_html: str | None = None
    from_addr: str | None = None


class EmailBackend(Protocol):
    def send(self, msg: EmailMessageData) -> None: ...


class ConsoleEmailBackend:
    """E-postayı log'a basar — gerçekten göndermez.

    Yerel geliştirme için: şifre sıfırlama linki log'da görünür,
    geliştirici SMTP kurmadan akışı test edebilir.
    """

    def send(self, msg: EmailMessageData) -> None:
        _logger.info(
            "[EMAIL/console] to=%s subject=%s\n---\n%s\n---",
            msg.to,
            msg.subject,
            msg.body_text,
        )


@dataclass
class MemoryEmailBackend:
    """Test için: gönderilen mesajları bellek listesinde tutar."""

    outbox: list[EmailMessageData] = field(default_factory=list)

    def send(self, msg: EmailMessageData) -> None:
        self.outbox.append(msg)


@dataclass(frozen=True)
class SMTPEmailBackend:
    host: str
    port: int
    username: str | None
    password: str | None
    use_tls: bool
    default_from: str

    def send(self, msg: EmailMessageData) -> None:
        email = EmailMessage()
        email["From"] = msg.from_addr or self.default_from
        email["To"] = msg.to
        email["Subject"] = msg.subject
        email.set_content(msg.body_text)
        if msg.body_html:
            email.add_alternative(msg.body_html, subtype="html")

        with smtplib.SMTP(self.host, self.port, timeout=10) as server:
            if self.use_tls:
                server.starttls()
            if self.username and self.password:
                server.login(self.username, self.password)
            server.send_message(email)


# ── Backend seçim ───────────────────────────────────────────────────────────
_CACHED_BACKEND: EmailBackend | None = None


def _build_backend() -> EmailBackend:
    choice = (os.environ.get("EMAIL_BACKEND") or "console").lower()
    if choice == "memory":
        return MemoryEmailBackend()
    if choice == "smtp":
        host = os.environ.get("SMTP_HOST")
        if not host:
            _logger.warning(
                "EMAIL_BACKEND=smtp seçildi ama SMTP_HOST boş — console fallback"
            )
            return ConsoleEmailBackend()
        return SMTPEmailBackend(
            host=host,
            port=int(os.environ.get("SMTP_PORT", "587")),
            username=os.environ.get("SMTP_USERNAME") or None,
            password=os.environ.get("SMTP_PASSWORD") or None,
            use_tls=(os.environ.get("SMTP_USE_TLS", "true").lower() == "true"),
            default_from=os.environ.get("EMAIL_FROM") or "no-reply@testwright.ai",
        )
    return ConsoleEmailBackend()


def get_email_backend() -> EmailBackend:
    """Process-yaşam süresi boyunca tek bir backend örneği döndürür."""
    global _CACHED_BACKEND
    if _CACHED_BACKEND is None:
        _CACHED_BACKEND = _build_backend()
    return _CACHED_BACKEND


def set_email_backend(backend: EmailBackend) -> None:
    """Test/enjeksiyon için."""
    global _CACHED_BACKEND
    _CACHED_BACKEND = backend


def send_email(msg: EmailMessageData) -> None:
    """E-postayı aktif backend'e iletir. Hata fırlatmaz; log'a yazar."""
    try:
        get_email_backend().send(msg)
    except Exception as e:  # pragma: no cover - network/smtp failure
        _logger.exception("E-posta gönderimi başarısız: %s", e)


def build_password_reset_email(
    *, to: str, reset_url: str, full_name: str | None = None
) -> EmailMessageData:
    """Şifre sıfırlama e-postasını Türkçe şablonla üretir."""
    greeting = f"Merhaba {full_name}," if full_name else "Merhaba,"
    text = (
        f"{greeting}\n\n"
        "Neurex QA hesabınız için şifre sıfırlama talebi aldık. "
        "Şifrenizi sıfırlamak için aşağıdaki bağlantıyı kullanabilirsiniz:\n\n"
        f"{reset_url}\n\n"
        "Bu bağlantı 15 dakika sonra geçerliliğini yitirir.\n"
        "Eğer talep sizden değilse bu e-postayı görmezden gelebilirsiniz.\n\n"
        "— Neurex QA"
    )
    html = (
        f"<p>{greeting}</p>"
        "<p>Neurex QA hesabınız için şifre sıfırlama talebi aldık. "
        "Şifrenizi sıfırlamak için aşağıdaki bağlantıyı kullanabilirsiniz:</p>"
        f"<p><a href=\"{reset_url}\" style=\"display:inline-block;padding:10px 20px;background:linear-gradient(to right,#2563eb,#4f46e5,#7c3aed);color:#fff;text-decoration:none;border-radius:10px;font-weight:600;\">Şifreyi Sıfırla</a></p>"
        "<p>Bu bağlantı 15 dakika sonra geçerliliğini yitirir.</p>"
        "<p>Eğer talep sizden değilse bu e-postayı görmezden gelebilirsiniz.</p>"
        "<p>— Neurex QA</p>"
    )
    return EmailMessageData(
        to=to,
        subject="Neurex QA — Şifre sıfırlama",
        body_text=text,
        body_html=html,
    )
