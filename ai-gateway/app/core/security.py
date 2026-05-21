"""Shared security helpers for internal AI Gateway routes."""
from __future__ import annotations

import hmac
import logging

from fastapi import HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)


def require_internal_key(x_internal_key: str) -> None:
    """Require the backend-to-gateway shared secret for internal AI routes."""
    if not settings.INTERNAL_KEY:
        logger.error("INTERNAL_KEY ayari eksik, AI Gateway internal route'lari kullanilamaz.")
        raise HTTPException(status_code=503, detail="Internal servis anahtari ayarlanamadi")
    if not x_internal_key:
        raise HTTPException(status_code=401, detail="X-Internal-Key header'i zorunludur")
    if not hmac.compare_digest(x_internal_key, settings.INTERNAL_KEY):
        raise HTTPException(status_code=403, detail="Gecersiz internal key")
