"""
Web Push Notification Service — VAPID tabanlı tarayıcı push bildirimleri.

Gereksinim: pip install pywebpush
"""
from __future__ import annotations

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class WebPushService:
    """VAPID tabanlı Web Push bildirimleri."""

    def __init__(self, *, private_key: str, public_key: str, claims_email: str):
        self.private_key = private_key
        self.public_key = public_key
        self.claims_email = claims_email
        self._enabled = bool(private_key and public_key)

    def send(
        self,
        *,
        subscription_info: dict,
        title: str,
        body: str,
        icon: str = "/favicon.ico",
        badge: str = "/badge.png",
        url: str = "/",
        tag: Optional[str] = None,
    ) -> bool:
        """Tek bir cihaza push bildirimi gönder."""
        if not self._enabled:
            logger.debug("[push] VAPID key'ler tanımlı değil — atlandı")
            return False
        try:
            from pywebpush import WebPushException, webpush  # type: ignore
            payload = json.dumps({
                "title": title,
                "body": body,
                "icon": icon,
                "badge": badge,
                "data": {"url": url},
                "tag": tag or title,
            })
            webpush(
                subscription_info=subscription_info,
                data=payload,
                vapid_private_key=self.private_key,
                vapid_claims={"sub": f"mailto:{self.claims_email}"},
            )
            logger.info("[push] bildirim gönderildi: %s", title)
            return True
        except ImportError:
            logger.warning("[push] pywebpush kurulu değil: pip install pywebpush")
            return False
        except Exception as exc:  # noqa: BLE001
            logger.warning("[push] gönderilemedi: %s", exc)
            return False

    def send_bulk(
        self,
        *,
        subscriptions: list[dict],
        title: str,
        body: str,
        **kwargs,
    ) -> tuple[int, int]:
        """Birden fazla cihaza gönderir. (başarılı, başarısız) döner."""
        ok = failed = 0
        for sub in subscriptions:
            if self.send(subscription_info=sub, title=title, body=body, **kwargs):
                ok += 1
            else:
                failed += 1
        return ok, failed


def get_web_push_service() -> WebPushService:
    """FastAPI dependency."""
    from app.config import settings
    return WebPushService(
        private_key=settings.vapid_private_key,
        public_key=settings.vapid_public_key,
        claims_email=settings.vapid_claims_email,
    )
