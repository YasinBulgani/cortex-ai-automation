"""Template registry — id → (subject, html, text).

Templates use ``str.format_map(SafeDict)`` for substitution. Missing keys
render as ``{key}`` rather than raising — this keeps an unexpected payload
from crashing the send loop. Inputs are HTML-escaped before substitution
to avoid injection via user-controlled fields like display names.
"""
from __future__ import annotations

import html
from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class Template:
    id: str
    subject: str
    html: str
    text: str


class _SafeDict(dict):
    def __missing__(self, key: str) -> str:  # type: ignore[override]
        return "{" + key + "}"


_BASE_STYLE = (
    "font-family:-apple-system,Segoe UI,Roboto,sans-serif;"
    "max-width:560px;margin:0 auto;padding:32px;color:#0f172a;"
)
_HEADER_STYLE = (
    "background:linear-gradient(135deg,#6366f1,#3b82f6);"
    "color:#fff;padding:24px 32px;border-radius:12px 12px 0 0;"
    "font-size:20px;font-weight:600;"
)
_BODY_STYLE = (
    "background:#fff;border:1px solid #e2e8f0;border-top:none;"
    "padding:32px;border-radius:0 0 12px 12px;line-height:1.6;"
)
_BTN_STYLE = (
    "display:inline-block;background:#6366f1;color:#fff;"
    "padding:12px 24px;text-decoration:none;border-radius:8px;"
    "font-weight:600;margin-top:16px;"
)


def _wrap_html(title: str, body_html: str) -> str:
    return (
        f'<div style="{_BASE_STYLE}">'
        f'<div style="{_HEADER_STYLE}">{title}</div>'
        f'<div style="{_BODY_STYLE}">{body_html}</div>'
        "</div>"
    )


# ── Templates ───────────────────────────────────────────────────────────────


TEMPLATES: dict[str, Template] = {
    "welcome": Template(
        id="welcome",
        subject="Neurex QA'ya hoş geldiniz, {full_name}!",
        html=_wrap_html(
            "Hoş geldiniz",
            (
                "<p>Merhaba <strong>{full_name}</strong>,</p>"
                "<p>Neurex QA'ya katıldığınız için teşekkürler. Test "
                "süreçlerinizi otomatikleştirmeye hemen başlayabilirsiniz.</p>"
                "<p>İlk projenizi oluşturmak için panelinize gidin:</p>"
                f'<a href="{{dashboard_url}}" style="{_BTN_STYLE}">Panele Git</a>'
                "<p style='margin-top:24px;color:#64748b;font-size:13px;'>"
                "Sorularınız için <a href='mailto:support@neurexqa.com'>"
                "support@neurexqa.com</a> adresine yazabilirsiniz.</p>"
            ),
        ),
        text=(
            "Merhaba {full_name},\n\n"
            "Neurex QA'ya katıldığınız için teşekkürler.\n"
            "Panel: {dashboard_url}\n\n"
            "Destek: support@neurexqa.com"
        ),
    ),
    "plan_changed": Template(
        id="plan_changed",
        subject="Planınız {plan_label} olarak güncellendi",
        html=_wrap_html(
            "Plan değişikliği",
            (
                "<p>Merhaba,</p>"
                "<p>Hesabınızın planı <strong>{plan_label}</strong> "
                "olarak güncellendi.</p>"
                "<p>Aylık ücret: <strong>${monthly_price}</strong></p>"
                "<p>Yeni dönem başlangıcı: {period_start}</p>"
                f'<a href="{{billing_url}}" style="{_BTN_STYLE}">'
                "Faturalama Detayları</a>"
                "<p style='margin-top:24px;color:#64748b;font-size:13px;'>"
                "Yanlış bir değişiklik mi? Faturalama panelinden geri "
                "alabilir veya destek ekibimize yazabilirsiniz.</p>"
            ),
        ),
        text=(
            "Planınız {plan_label} olarak güncellendi.\n"
            "Aylık ücret: ${monthly_price}\n"
            "Dönem başlangıcı: {period_start}\n\n"
            "Faturalama: {billing_url}"
        ),
    ),
    "payment_failed": Template(
        id="payment_failed",
        subject="⚠️ Ödeme başarısız oldu",
        html=_wrap_html(
            "Ödeme başarısız",
            (
                "<p>Merhaba,</p>"
                "<p>Son fatura ödemeniz başarısız oldu. Hesabınızın "
                "servis erişimi <strong>{grace_days} gün</strong> içinde "
                "kısıtlanabilir.</p>"
                "<p>Lütfen ödeme yönteminizi güncelleyin:</p>"
                f'<a href="{{billing_url}}" style="{_BTN_STYLE}">'
                "Ödeme Yöntemini Güncelle</a>"
                "<p style='margin-top:24px;color:#64748b;font-size:13px;'>"
                "Yardım için <a href='mailto:billing@neurexqa.com'>"
                "billing@neurexqa.com</a> ekibine ulaşabilirsiniz.</p>"
            ),
        ),
        text=(
            "Son fatura ödemeniz başarısız oldu.\n"
            "Grace period: {grace_days} gün.\n\n"
            "Ödeme yönteminizi güncelleyin: {billing_url}\n"
            "Destek: billing@neurexqa.com"
        ),
    ),
    "password_reset": Template(
        id="password_reset",
        subject="Parola sıfırlama bağlantısı",
        html=_wrap_html(
            "Parola sıfırlama",
            (
                "<p>Merhaba,</p>"
                "<p>Parola sıfırlama isteği aldık. Bağlantı "
                "<strong>{ttl_minutes} dakika</strong> içinde geçerli.</p>"
                f'<a href="{{reset_url}}" style="{_BTN_STYLE}">'
                "Parolayı Sıfırla</a>"
                "<p style='margin-top:24px;color:#64748b;font-size:13px;'>"
                "Bu isteği siz yapmadıysanız, bu e-postayı silebilirsiniz.</p>"
            ),
        ),
        text=(
            "Parola sıfırlama isteğiniz alındı.\n"
            "Bağlantı {ttl_minutes} dakika içinde geçerli.\n\n"
            "Sıfırla: {reset_url}"
        ),
    ),
    "subscription_canceled": Template(
        id="subscription_canceled",
        subject="Aboneliğiniz iptal edildi",
        html=_wrap_html(
            "Abonelik iptal",
            (
                "<p>Merhaba,</p>"
                "<p>Aboneliğiniz iptal edildi. Mevcut dönem "
                "sonuna kadar (<strong>{period_end}</strong>) servisi "
                "kullanmaya devam edebilirsiniz.</p>"
                "<p>Tekrar düşünmek isterseniz, faturalama panelinden "
                "aboneliği yeniden aktive edebilirsiniz.</p>"
                f'<a href="{{billing_url}}" style="{_BTN_STYLE}">'
                "Aboneliği Yeniden Aktive Et</a>"
            ),
        ),
        text=(
            "Aboneliğiniz iptal edildi.\n"
            "Servis erişimi {period_end} tarihine kadar açık.\n\n"
            "Yeniden aktive: {billing_url}"
        ),
    ),
}


def render(template_id: str, ctx: Mapping[str, object]) -> tuple[str, str, str]:
    """Return (subject, html, text). Inputs are HTML-escaped before substitution."""
    if template_id not in TEMPLATES:
        raise KeyError(f"Bilinmeyen template: {template_id}")
    tpl = TEMPLATES[template_id]
    escaped = _SafeDict(
        {k: html.escape(str(v)) if v is not None else "" for k, v in ctx.items()}
    )
    raw = _SafeDict({k: str(v) if v is not None else "" for k, v in ctx.items()})
    return (
        tpl.subject.format_map(raw),
        tpl.html.format_map(escaped),
        tpl.text.format_map(raw),
    )
