"""Message catalog. Add keys here; new locales = new dict."""

from __future__ import annotations

DEFAULT_LOCALE = "tr"
SUPPORTED_LOCALES = {"tr", "en"}


TR = {
    # auth
    "auth.invalid_credentials": "E-posta veya sifre hatali",
    "auth.account_inactive": "Hesap pasif",
    "auth.token_required": "Kimlik dogrulama gerekli",
    "auth.token_invalid": "Gecersiz veya suresi dolmus token",
    "auth.rate_limited": "Cok fazla giris denemesi. {minutes} dakika bekleyin.",
    "auth.no_permission": "Bu islem icin yetkiniz yok: {perm}",
    "auth.password_too_short": "Sifre en az 8 karakter olmali",

    # invitations
    "invite.invalid": "Davet gecersiz, kullanilmis veya suresi dolmus",
    "invite.email_subject": "{org} davetiniz",
    "invite.sent": "Davet gonderildi",

    # generic
    "generic.not_found": "Bulunamadi",
    "generic.forbidden": "Yetkisiz erisim",
    "generic.bad_request": "Hatali istek",
    "generic.server_error": "Sunucu hatasi",
    "generic.ok": "Basarili",

    # billing
    "billing.plan_limit_exceeded": "Plan limiti asildi: {feature}",
    "billing.subscription_required": "Bu ozellik icin abonelik gerekli",
}


EN = {
    # auth
    "auth.invalid_credentials": "Invalid email or password",
    "auth.account_inactive": "Account is inactive",
    "auth.token_required": "Authentication required",
    "auth.token_invalid": "Invalid or expired token",
    "auth.rate_limited": "Too many login attempts. Wait {minutes} minutes.",
    "auth.no_permission": "You don't have permission for: {perm}",
    "auth.password_too_short": "Password must be at least 8 characters",

    # invitations
    "invite.invalid": "Invitation is invalid, used, or expired",
    "invite.email_subject": "Your {org} invitation",
    "invite.sent": "Invitation sent",

    # generic
    "generic.not_found": "Not found",
    "generic.forbidden": "Forbidden",
    "generic.bad_request": "Bad request",
    "generic.server_error": "Internal server error",
    "generic.ok": "OK",

    # billing
    "billing.plan_limit_exceeded": "Plan limit exceeded: {feature}",
    "billing.subscription_required": "Subscription required for this feature",
}


CATALOGS = {
    "tr": TR,
    "en": EN,
}
