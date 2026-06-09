"""Shared security helpers for internal AI Gateway routes."""
from __future__ import annotations

import hmac
import logging
import os
from datetime import datetime, timedelta, timezone as _tz

from fastapi import HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)


def require_internal_key(x_internal_key: str) -> None:
    """Require the backend-to-gateway shared secret for internal AI routes.

    S-HIGH-7: Key TTL enforcement — warn if key exceeds TTL in production.
    """
    if not settings.INTERNAL_KEY:
        logger.error("INTERNAL_KEY ayari eksik, AI Gateway internal route'lari kullanilamaz.")
        raise HTTPException(status_code=503, detail="Internal servis anahtari ayarlanamadi")
    if not x_internal_key:
        raise HTTPException(status_code=401, detail="X-Internal-Key header'i zorunludur")
    if not hmac.compare_digest(x_internal_key, settings.INTERNAL_KEY):
        raise HTTPException(status_code=403, detail="Gecersiz internal key")

    # Check key age in production
    if settings.is_production_like:
        key_rotated_at_str = os.environ.get("GATEWAY_INTERNAL_KEY_ROTATED_AT", "")
        if key_rotated_at_str:
            try:
                key_rotated_at = datetime.fromisoformat(key_rotated_at_str)
                now = datetime.now(_tz.utc)
                key_age_days = (now - key_rotated_at).days
                ttl_days = settings.INTERNAL_KEY_TTL_DAYS
                if key_age_days > ttl_days:
                    logger.warning(
                        f"GÜVENLİK: AI Gateway internal key {key_age_days} gün önce "
                        f"rotasyona uğradı (TTL: {ttl_days} gün). Anahtarı yenileyin."
                    )
            except Exception:
                pass
