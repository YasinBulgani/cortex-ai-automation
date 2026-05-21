"""Visual Verifier — multimodal LLM ile screenshot doğrulama.

MVP: Başlangıçta her zaman pass=true döner (placeholder).
F2'de AI Gateway'in vision endpoint'i (Gemini 2 Flash / GPT-4o) entegre edilir.
"""
from __future__ import annotations

import logging
from typing import Optional

from .schemas import VisualVerifyRequest, VisualVerifyResponse

_logger = logging.getLogger(__name__)


def verify(req: VisualVerifyRequest) -> VisualVerifyResponse:
    """Screenshot + assertion → pass/fail kararı.

    F2: AI Gateway'e vision istegi:
        gateway_complete(
            task_type="visual_verify",
            system_message=VISUAL_SYSTEM,
            user_message=req.assertion,
            images=[req.screenshot_base64],
            json_mode=True,
        )
    """
    # Boş / eksik veri → güvenli taraf pass
    if not req.screenshot_base64:
        return VisualVerifyResponse(
            passed=False, confidence=0.0, reason="Screenshot boş, doğrulanamadı."
        )
    # MVP placeholder: assertion non-empty ise 0.6 güvenle pass
    return VisualVerifyResponse(
        passed=True,
        confidence=0.6,
        reason=(
            "MVP: gerçek vision LLM bağlı değil — placeholder passed=true. "
            "F2 fazında Gemini 2 Flash / GPT-4o ile değiştirilecek."
        ),
    )
