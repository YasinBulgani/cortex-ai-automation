"""LLM Stepper — Doğal dil → Appium aksiyon JSON'ı.

3 seviyeli çalışır:
  1. Primary: AI Gateway üzerinden GPT-4o / Gemini.
  2. Fallback: Kural tabanlı Türkçe pattern matcher (offline / dev için).
  3. Grounding: Varsa Appium page source verilir, locator halüsinasyonu azalır.

MVP: Heuristic öncelikli, gateway opsiyonel.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Optional

from .schemas import AppiumAction, Platform, StepGenerationResponse

_logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """Sen bir mobil test adım üretici asistansın.
Türkçe doğal dildeki test senaryosunu Appium aksiyon JSON dizisine çevir.
Kurallar:
- Öncelik sırası: accessibilityId > predicate (iOS) / id (Android) > xpath.
- Her "find" aksiyonunu ya "tap" ya "sendKeys" ya "verifyVisible" izlemeli.
- Belirsizse varsayılan timeout=5000ms.
- YALNIZCA JSON dizisi dön, markdown veya açıklama YAZMA.

Format örneği:
[
  {"action":"launch"},
  {"action":"find","by":"accessibilityId","value":"login_button","timeout":5000},
  {"action":"tap"},
  {"action":"verifyVisible","by":"accessibilityId","value":"home_screen","timeout":8000}
]
"""


_TR_UPPER_MAP = str.maketrans("İIĞÜŞÖÇ", "iığüşöç")


def _tr_lower(s: str) -> str:
    """Türkçe-dayanıklı küçültme. 'İ' → 'i', 'I' → 'ı', vb.

    Python'un default lower()'ı İ'yi 'i̇' (dotted i) yapar; bu pattern match'leri
    kırar. Bu yardımcı önce Türkçe büyük karakterleri manuel eşler, sonra
    standart lower uygular.
    """
    return s.translate(_TR_UPPER_MAP).lower()


def _heuristic_stepper(prompt: str, platform: Platform) -> list[AppiumAction]:
    """Offline / fallback heuristic — Türkçe anahtar kelime tabanlı."""
    p = _tr_lower(prompt)
    steps: list[AppiumAction] = [AppiumAction(action="launch")]

    # Onboarding / dil
    if "onboarding" in p or "tanıtım" in p or "atla" in p:
        steps.extend([
            AppiumAction(action="find", by="accessibilityId", value="onboarding_skip", timeout=5000),
            AppiumAction(action="tap"),
            AppiumAction(action="wait", ms=500),
        ])
    if "türkçe" in p or "dil" in p:
        steps.extend([
            AppiumAction(action="find", by="accessibilityId", value="lang_tr"),
            AppiumAction(action="tap"),
        ])

    # Login akışı
    if "giriş" in p or "login" in p:
        steps.extend([
            AppiumAction(action="find", by="accessibilityId", value="login_button", timeout=5000),
            AppiumAction(action="tap"),
        ])

    if "email" in p or "e-posta" in p or "eposta" in p:
        email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", prompt)
        email = email_match.group(0) if email_match else "test@bgts.ai"
        steps.extend([
            AppiumAction(action="find", by="accessibilityId", value="email_input"),
            AppiumAction(action="sendKeys", text=email),
        ])

    if "şifre" in p or "parola" in p or "password" in p:
        pw_match = re.search(r"['\"]([^'\"]{4,32})['\"]", prompt)
        pw = pw_match.group(1) if pw_match else "Test123!"
        steps.extend([
            AppiumAction(action="find", by="accessibilityId", value="password_input"),
            AppiumAction(action="sendKeys", text=pw),
        ])

    if "devam" in p or "gönder" in p or "submit" in p:
        steps.extend([
            AppiumAction(action="find", by="accessibilityId", value="submit_button"),
            AppiumAction(action="tap"),
        ])

    # Arama + sepet
    if "ara" in p or "search" in p:
        q_match = re.search(r"['\"]([^'\"]+)['\"]", prompt)
        q = q_match.group(1) if q_match else "test"
        steps.extend([
            AppiumAction(action="find", by="accessibilityId", value="search_input"),
            AppiumAction(action="sendKeys", text=q),
        ])

    if "sepet" in p or "cart" in p:
        steps.extend([
            AppiumAction(action="find", by="accessibilityId", value="add_to_cart"),
            AppiumAction(action="tap"),
            AppiumAction(action="verifyVisible", by="accessibilityId", value="cart_badge_1", timeout=3000),
        ])

    # Çıkış
    if "çıkış" in p or "logout" in p:
        steps.extend([
            AppiumAction(action="find", by="accessibilityId", value="profile_tab"),
            AppiumAction(action="tap"),
            AppiumAction(action="find", by="accessibilityId", value="logout_button"),
            AppiumAction(action="tap"),
            AppiumAction(action="find", by="accessibilityId", value="confirm_yes"),
            AppiumAction(action="tap"),
            AppiumAction(action="verifyVisible", by="accessibilityId", value="login_screen", timeout=5000),
        ])

    # Ana sayfa doğrulama
    if "ana sayfa" in p or "anasayfa" in p or "doğrula" in p or "görün" in p:
        steps.append(
            AppiumAction(action="verifyVisible", by="accessibilityId", value="home_screen", timeout=8000)
        )

    # Hiçbir kural eşleşmediyse makul bir fallback
    if len(steps) == 1:
        steps.extend([
            AppiumAction(action="wait", ms=1000),
            AppiumAction(action="verifyVisible", by="accessibilityId", value="app_root", timeout=5000),
        ])

    return steps


def _parse_llm_json(raw: str) -> Optional[list[dict]]:
    """LLM JSON çıktısını parse et — markdown fence, fazla metin ve truncated JSON'a dayanıklı."""
    text = raw.strip()
    # Markdown fence temizle
    fence = re.match(r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    # Array baş/son
    start = text.find("[")
    end = text.rfind("]")
    if start >= 0 and end > start:
        text = text[start : end + 1]
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        _logger.warning("LLM JSON parse başarısız, ilk 200 char: %s", raw[:200])
    return None


def generate_steps(
    prompt: str,
    platform: Platform = "android",
    page_source: Optional[str] = None,
    app_package: Optional[str] = None,
) -> StepGenerationResponse:
    """NL → Appium adımları. Önce AI Gateway, olmazsa heuristic fallback.

    Dönüş her zaman en az 1 adım içerir.
    """
    # 1. AI Gateway dene (sadece modül yüklenebiliyorsa)
    try:
        from app.domains.ai.gateway_client import gateway_complete  # type: ignore

        user_msg = prompt.strip()
        if page_source:
            # Grounding: page_source büyük olabilir, 8KB ile sınırla
            user_msg += f"\n\n### Mevcut Sayfa (Appium page source, kırpılmış):\n{page_source[:8000]}"
        if app_package:
            user_msg += f"\n\n### Uygulama paketi: {app_package}"
        user_msg += f"\n\n### Hedef platform: {platform}"

        raw = gateway_complete(
            task_type="generate_mobile_steps",
            user_message=user_msg,
            system_message=SYSTEM_PROMPT,
            temperature=0.3,
            max_tokens=2000,
            json_mode=True,
        )
        parsed = _parse_llm_json(raw)
        if parsed:
            steps: list[AppiumAction] = []
            for item in parsed:
                try:
                    steps.append(AppiumAction(**item))
                except Exception as e:
                    _logger.warning("Adım geçersiz, atlanıyor: %s (%s)", item, e)
            if steps:
                return StepGenerationResponse(
                    steps=steps, model="ai-gateway", fallback_used=False
                )
    except Exception as e:
        _logger.info("AI Gateway erişilemedi, heuristic fallback: %s", e)

    # 2. Heuristic fallback
    heuristic = _heuristic_stepper(prompt, platform)
    return StepGenerationResponse(
        steps=heuristic, model="heuristic-tr", fallback_used=True
    )
