"""Lightweight i18n helper.

Usage:
    from app.core.i18n import t, get_locale

    msg = t("auth.invalid_credentials", locale="en")
    # or: msg = t("auth.invalid_credentials")   # uses contextvar locale

To set locale per-request, add the middleware:
    app.add_middleware(LocaleMiddleware)
"""

from __future__ import annotations

import contextvars
import logging
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from .catalog import CATALOGS, DEFAULT_LOCALE, SUPPORTED_LOCALES

logger = logging.getLogger(__name__)

_locale_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "i18n_locale", default=DEFAULT_LOCALE
)


def get_locale() -> str:
    return _locale_var.get()


def set_locale(locale: str) -> None:
    if locale in SUPPORTED_LOCALES:
        _locale_var.set(locale)


def t(key: str, locale: Optional[str] = None, **fmt) -> str:
    """Translate `key`. Falls back: requested locale -> default -> raw key."""
    loc = locale or get_locale()
    catalog = CATALOGS.get(loc) or CATALOGS.get(DEFAULT_LOCALE, {})
    msg = catalog.get(key)
    if msg is None and loc != DEFAULT_LOCALE:
        msg = CATALOGS.get(DEFAULT_LOCALE, {}).get(key)
    if msg is None:
        return key  # graceful degradation
    if fmt:
        try:
            return msg.format(**fmt)
        except Exception:
            logger.debug("i18n format failed key=%s", key)
            return msg
    return msg


def parse_accept_language(header: str) -> str:
    """Pick the first supported locale from an Accept-Language header."""
    if not header:
        return DEFAULT_LOCALE
    parts = [p.strip().split(";")[0].lower() for p in header.split(",")]
    for p in parts:
        # match exact ("tr", "en") or language prefix ("tr-tr" -> "tr")
        short = p.split("-")[0]
        if short in SUPPORTED_LOCALES:
            return short
    return DEFAULT_LOCALE


class LocaleMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Priority: ?lang= > X-Locale header > Accept-Language > default
        locale = (
            request.query_params.get("lang")
            or request.headers.get("x-locale")
            or parse_accept_language(request.headers.get("accept-language", ""))
        )
        token = _locale_var.set(locale if locale in SUPPORTED_LOCALES else DEFAULT_LOCALE)
        try:
            response = await call_next(request)
        finally:
            _locale_var.reset(token)
        response.headers["Content-Language"] = get_locale()
        return response
