"""Self-Healing Locator Service.

Test adımında locator bulunamadığında LLM'e şunları sorar:
  - RETRY: aynı locator, daha uzun timeout
  - REWRITE: yeni locator öner (xpath fallback)
  - UI_CHANGED: uygulama gerçekten değişmiş
  - ENV_ISSUE: ortam sorunu, cihazı restart et

MVP: Deterministik mini bir heuristic (xpath üret, retry öner).
F2 fazında gerçek vision + DOM + LLM mantığı aktive edilir.
"""
from __future__ import annotations

import logging
from typing import Literal, Optional

from pydantic import BaseModel

_logger = logging.getLogger(__name__)

HealDecision = Literal["RETRY", "REWRITE", "UI_CHANGED", "ENV_ISSUE"]


class HealRequest(BaseModel):
    failed_action: dict
    page_source: Optional[str] = None
    screenshot_base64: Optional[str] = None
    retry_count: int = 0


class HealSuggestion(BaseModel):
    decision: HealDecision
    new_action: Optional[dict] = None
    confidence: float
    reason: str


def suggest(req: HealRequest) -> HealSuggestion:
    """Heal kararı öner.

    Karar politikası (MVP):
      - retry_count == 0 → RETRY (timeout 2x)
      - retry_count == 1 → REWRITE (by=accessibilityId ise xpath fallback)
      - retry_count >= 2 → UI_CHANGED (karantinaya al)
    """
    act = dict(req.failed_action)
    by = act.get("by")
    value = act.get("value")

    if req.retry_count == 0:
        new_timeout = int(act.get("timeout") or 5000) * 2
        healed = {**act, "timeout": new_timeout}
        return HealSuggestion(
            decision="RETRY",
            new_action=healed,
            confidence=0.9,
            reason=f"Timeout 2x artırıldı ({new_timeout}ms).",
        )

    if req.retry_count == 1 and by == "accessibilityId" and value:
        xp = f"//*[@content-desc='{value}' or @name='{value}' or @resource-id='{value}']"
        healed = {**act, "by": "xpath", "value": xp}
        return HealSuggestion(
            decision="REWRITE",
            new_action=healed,
            confidence=0.7,
            reason="accessibilityId bulunamadı, xpath fallback uygulandı.",
        )

    return HealSuggestion(
        decision="UI_CHANGED",
        new_action=None,
        confidence=0.5,
        reason=(
            "2 denemede locator bulunamadı — uygulama UI'ı değişmiş olabilir. "
            "Testi quarantine kuyruğuna al, insan incelemesi gerek."
        ),
    )
