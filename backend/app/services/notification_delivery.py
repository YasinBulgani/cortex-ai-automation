"""
Neurex — Bildirim Delivery Servisi
Slack, Microsoft Teams ve Web Push kanallarına bildirim gönderir.
"""
from __future__ import annotations
import logging
from typing import Optional
import httpx

logger = logging.getLogger(__name__)


def send_slack_notification(
    *,
    webhook_url: str,
    title: str,
    message: str,
    color: str = "#0d99ff",
    fields: Optional[list[dict]] = None,
) -> bool:
    """Slack Incoming Webhook ile bildirim gönderir. True=başarılı."""
    if not webhook_url:
        logger.debug("[delivery.slack] webhook_url boş — atlandı")
        return False
    payload = {
        "attachments": [
            {
                "color": color,
                "title": title,
                "text": message,
                "fields": fields or [],
                "footer": "Neurex QA Platform",
                "footer_icon": "https://neurex.app/favicon.ico",
            }
        ]
    }
    try:
        resp = httpx.post(webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
        logger.info("[delivery.slack] bildirim gönderildi: %s", title)
        return True
    except Exception as exc:
        logger.warning("[delivery.slack] gönderilemedi: %s", exc)
        return False


def send_teams_notification(
    *,
    webhook_url: str,
    title: str,
    message: str,
    theme_color: str = "0d99ff",
    facts: Optional[list[dict]] = None,
) -> bool:
    """MS Teams Incoming Webhook ile bildirim gönderir. True=başarılı."""
    if not webhook_url:
        logger.debug("[delivery.teams] webhook_url boş — atlandı")
        return False
    payload = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": theme_color,
        "summary": title,
        "sections": [
            {
                "activityTitle": f"**{title}**",
                "activityText": message,
                "facts": facts or [],
            }
        ],
    }
    try:
        resp = httpx.post(webhook_url, json=payload, timeout=10)
        resp.raise_for_status()
        logger.info("[delivery.teams] bildirim gönderildi: %s", title)
        return True
    except Exception as exc:
        logger.warning("[delivery.teams] gönderilemedi: %s", exc)
        return False


def send_notification(
    *,
    channel: str,
    title: str,
    message: str,
    slack_webhook_url: str = "",
    teams_webhook_url: str = "",
) -> bool:
    """Kanala göre doğru delivery fonksiyonunu çağırır."""
    if channel == "slack":
        return send_slack_notification(
            webhook_url=slack_webhook_url, title=title, message=message
        )
    if channel == "teams":
        return send_teams_notification(
            webhook_url=teams_webhook_url, title=title, message=message
        )
    logger.warning("[delivery] bilinmeyen kanal: %r", channel)
    return False
