"""
Nexus QA — Faz 7: AI Chat Assistant Service
Proje bağlamında çalışan, tüm Nexus QA fazlarını bilen
konuşmacı AI asistan servisi.

Yetenekler:
  - Serbest chat (QA soruları, test stratejisi, Gherkin/Java/Playwright soruları)
  - Test case öneri (bağlamsal)
  - Senaryo açıklama ve review
  - BDD dönüşüm yardımı
  - Hata debug yardımı
  - Regresyon seti önerileri
"""
from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger("nexusqa.ai_chat")

# ── Redis Session Store ───────────────────────────────────────────────────────
_SESSION_TTL = 7200   # 2 saat
_SESSION_PREFIX = "nexusqa:chat:"
_MAX_HISTORY = 16     # 8 exchange = 16 mesaj


def _get_redis():
    """Redis bağlantısı döndür; yoksa None."""
    try:
        import redis
        url = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")
        return redis.Redis.from_url(url, decode_responses=True, socket_connect_timeout=1)
    except Exception:
        return None


def load_session(session_id: str) -> list[dict[str, str]]:
    """Redis'ten conversation history yükle."""
    r = _get_redis()
    if not r:
        return []
    try:
        raw = r.get(f"{_SESSION_PREFIX}{session_id}")
        if raw:
            return json.loads(raw)
    except Exception as exc:
        logger.debug(f"Session yüklenemedi ({session_id}): {exc}")
    return []


def save_session(session_id: str, history: list[dict[str, str]]) -> None:
    """Conversation history'yi Redis'e kaydet (2 saat TTL)."""
    r = _get_redis()
    if not r:
        return
    try:
        trimmed = history[-_MAX_HISTORY:]
        r.setex(f"{_SESSION_PREFIX}{session_id}", _SESSION_TTL, json.dumps(trimmed))
    except Exception as exc:
        logger.debug(f"Session kaydedilemedi ({session_id}): {exc}")

# ── System Prompt ─────────────────────────────────────────────────────────────

_CHAT_SYSTEM_PROMPT = """\
Sen Nexus QA asistanısın. Kıdemli bir QA mühendisi olarak proje ekibine yardım ediyorsun.

Nexus QA Platformu hakkında bilgin var:
- Faz 1: Doküman analizi ve test case üretimi (AI ile)
- Faz 2-3: Test case bulk review (approve/reject/edit)
- Faz 4: AI regresyon seti önerisi
- Faz 5: Gherkin + Java NexusQA + Playwright TypeScript kod üretimi
- Faz 6: AI debug loop, kök neden analizi, Allure export
- NexusQA: Selenium 4 + Cucumber tabanlı Java framework

Cevap verirken:
1. Her zaman Türkçe konuş
2. Teknik detaylarda kod örnekleri ver (Gherkin, Java, TypeScript)
3. QA best practices'i benimse
4. Kısa ve net cevaplar ver (çok uzun olmasın)
5. Eğer proje bağlamı verilirse onu kullan
6. Proje verisi verilmişse önce o veriye dayan; sayı, durum ve isim uydurma
7. Bağlamda olmayan noktaları varsayım diye açıkça belirt
8. Gerekirse somut sonraki adımı öner

Desteklediğin konular: Test tasarımı, BDD, Playwright, Selenium, CI/CD entegrasyonu,
test otomasyonu, regresyon stratejisi, test kalitesi, Allure raporlama."""


# ── Context Builder ───────────────────────────────────────────────────────────

def _build_project_context(project_context: dict[str, Any]) -> str:
    """Proje bağlamını sistem mesajına eklemek için formatlı metin üretir."""
    if not project_context:
        return ""

    parts = []
    if project_context.get("project_name"):
        parts.append(f"Proje: {project_context['project_name']}")
    if project_context.get("scenario_count") is not None:
        parts.append(f"Toplam senaryo: {project_context['scenario_count']}")
    if project_context.get("pending_test_cases") is not None:
        parts.append(f"Bekleyen test case: {project_context['pending_test_cases']}")
    if project_context.get("last_pass_rate") is not None:
        parts.append(f"Son test başarı oranı: {project_context['last_pass_rate']}%")
    if project_context.get("modules"):
        modules_str = ", ".join(project_context["modules"])
        parts.append(f"Modüller: {modules_str}")
    if project_context.get("failed_tests"):
        failed_str = "; ".join(project_context["failed_tests"][:5])
        parts.append(f"Son başarısız testler: {failed_str}")

    if not parts:
        return ""
    return "\n\nProje Bağlamı:\n" + "\n".join(f"- {p}" for p in parts)


# ── Intent Detection ──────────────────────────────────────────────────────────

def _detect_intent(message: str) -> str:
    """Basit kural tabanlı intent tespiti."""
    msg_lower = message.lower()

    if any(w in msg_lower for w in ["gherkin", "feature", "scenario", "bdd", "cucumber"]):
        return "bdd_help"
    if any(w in msg_lower for w in ["playwright", "typescript", "locator", "selector", "page.click"]):
        return "playwright_help"
    if any(w in msg_lower for w in ["java", "nexusqa", "step definition", "@given", "@when", "@then", "selenium"]):
        return "java_help"
    if any(w in msg_lower for w in ["hata", "başarısız", "fail", "error", "debug", "neden"]):
        return "debug_help"
    if any(w in msg_lower for w in ["test case", "test yaz", "senaryo yaz", "oluştur", "üret"]):
        return "generate_test"
    if any(w in msg_lower for w in ["regresyon", "regression", "set öner", "hangi test"]):
        return "regression_suggest"
    if any(w in msg_lower for w in ["kapsam", "coverage", "oran", "istatistik"]):
        return "stats"

    return "general"


# ── Enriched Prompt Builder ───────────────────────────────────────────────────

def _enrich_prompt_for_intent(
    user_message: str,
    intent: str,
    history: list[dict[str, str]],
) -> str:
    """Intent'e göre kullanıcı mesajını zenginleştir."""
    if intent == "bdd_help":
        return (
            f"{user_message}\n\n"
            f"[Bilgi: Türkçe Gherkin format kullan: 'Olduğu gibi'/'Eğer'/'O zaman'/'Ve'. "
            f"Scenario ve Scenario Outline örnekleri ver.]"
        )
    if intent == "playwright_help":
        return (
            f"{user_message}\n\n"
            f"[Bilgi: @playwright/test kullan. getByRole, getByLabel, getByTestId tercih et. "
            f"TypeScript yazım kurallarına uy.]"
        )
    if intent == "java_help":
        return (
            f"{user_message}\n\n"
            f"[Bilgi: NexusQA framework = Selenium 4 + Cucumber. "
            f"Paket: com.nexusqa.steps. @Given/@When/@Then/@And annotation'ları kullan.]"
        )
    if intent == "debug_help":
        return (
            f"{user_message}\n\n"
            f"[Bilgi: Kök neden kategorileri: PRODUCT_BUG / TEST_ISSUE / ENVIRONMENT / AUTOMATION_DEBT. "
            f"Somut fix adımları öner.]"
        )
    return user_message


# ── Main Chat Function ─────────────────────────────────────────────────────────

def chat_with_ai(
    user_message: str,
    project_id: Optional[str] = None,
    project_context: Optional[dict[str, Any]] = None,
    conversation_history: Optional[list[dict[str, str]]] = None,
    session_id: Optional[str] = None,
    retrieval_context: Optional[str] = None,
) -> dict[str, Any]:
    """
    Kullanıcı mesajını AI Gateway'e gönder, cevap al.

    Args:
        user_message: Kullanıcının sorusu
        project_id: Proje ID (gateway context için)
        project_context: {'project_name', 'scenario_count', 'modules', ...}
        conversation_history: [{'role': 'user'|'assistant', 'content': '...'}]
        session_id: Oturum ID
        retrieval_context: Soruya göre seçilmiş ilgili proje kayıtları

    Returns:
        {
            response: str,
            intent: str,
            ai_provider: str,
            fallback_used: bool,
            session_id: str,
            timestamp: str,
        }
    """
    sid = session_id or _generate_session_id()
    # Geçmiş önce parametre olarak gelenlere bak, yoksa Redis'ten yükle
    if conversation_history is not None:
        history = conversation_history
    else:
        history = load_session(sid)
    context = project_context or {}

    # 1. Intent detection
    intent = _detect_intent(user_message)
    logger.debug(f"Chat intent: {intent}")

    # 2. Enrich prompt
    enriched_message = _enrich_prompt_for_intent(user_message, intent, history)

    # 3. Build full system prompt
    project_ctx_str = _build_project_context(context)
    full_system = _CHAT_SYSTEM_PROMPT + project_ctx_str
    if retrieval_context:
        full_system += (
            "\n\nİlgili Proje Kayıtları:\n"
            f"{retrieval_context[:6000]}"
        )

    # 4. Build conversation context for AI (last 8 exchanges max)
    context_messages = history[-16:]  # 8 exchanges = 16 messages
    if context_messages:
        context_str = "\n".join(
            f"{'Kullanıcı' if m['role'] == 'user' else 'Asistan'}: {m['content']}"
            for m in context_messages
        )
        user_prompt = f"Konuşma geçmişi:\n{context_str}\n\nYeni soru: {enriched_message}"
    else:
        user_prompt = enriched_message

    # 5. Call AI Gateway
    try:
        from app.domains.ai.gateway_client import gateway_complete, gateway_is_available
        if gateway_is_available():
            response = gateway_complete(
                task_type="chat",
                user_message=user_prompt,
                system_message=full_system,
                temperature=0.7,
                max_tokens=2000,
                project_id=project_id,
            )
            # Geçmişi güncelle ve Redis'e kaydet
            history.append({"role": "user", "content": user_message})
            history.append({"role": "assistant", "content": response})
            save_session(sid, history)
            return {
                "response": response,
                "intent": intent,
                "ai_provider": "gateway",
                "fallback_used": False,
                "session_id": sid,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
    except Exception as e:
        logger.warning(f"AI Gateway chat başarısız: {e}")

    # 6. Fallback: canned response
    fallback = _canned_response(user_message, intent)
    return {
        "response": fallback,
        "intent": intent,
        "ai_provider": "fallback",
        "fallback_used": True,
        "session_id": sid,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _generate_session_id() -> str:
    import uuid
    return str(uuid.uuid4())


def get_session_history(session_id: str) -> list[dict[str, str]]:
    """Dış kullanım için — session geçmişini döndür."""
    return load_session(session_id)


def clear_session(session_id: str) -> None:
    """Session'ı Redis'ten sil."""
    r = _get_redis()
    if r:
        try:
            r.delete(f"{_SESSION_PREFIX}{session_id}")
        except Exception:
            pass


def _canned_response(message: str, intent: str) -> str:
    """AI unavailable olduğunda basit kural tabanlı cevaplar."""
    canned: dict[str, str] = {
        "bdd_help": (
            "Gherkin için Türkçe format kullanın:\n\n"
            "```gherkin\n"
            "# language: tr\n"
            "Özellik: Kullanıcı Girişi\n"
            "  Senaryo: Başarılı giriş\n"
            "    Olduğu gibi kullanıcı giriş sayfasındayım\n"
            "    Eğer geçerli bilgileri girerim\n"
            "    O zaman anasayfaya yönlendirilirim\n"
            "```"
        ),
        "playwright_help": (
            "Playwright TypeScript örneği:\n\n"
            "```typescript\n"
            "import { test, expect } from '@playwright/test';\n\n"
            "test('kullanıcı giriş yapabilir', async ({ page }) => {\n"
            "  await page.goto('/login');\n"
            "  await page.getByLabel('Email').fill('user@test.com');\n"
            "  await page.getByLabel('Şifre').fill('password123');\n"
            "  await page.getByRole('button', { name: 'Giriş Yap' }).click();\n"
            "  await expect(page).toHaveURL('/dashboard');\n"
            "});\n"
            "```"
        ),
        "java_help": (
            "NexusQA (Selenium 4 + Cucumber) step definition örneği:\n\n"
            "```java\n"
            "package com.nexusqa.steps;\n\n"
            "@Given(\"kullanıcı giriş sayfasındayım\")\n"
            "public void kullanici_giris_sayfasinda() {\n"
            "    driver.get(BASE_URL + \"/login\");\n"
            "}\n\n"
            "@When(\"geçerli bilgileri girerim\")\n"
            "public void gecerli_bilgileri_girerim() {\n"
            "    driver.findElement(By.id(\"email\")).sendKeys(\"user@test.com\");\n"
            "    driver.findElement(By.id(\"password\")).sendKeys(\"pass\");\n"
            "}\n"
            "```"
        ),
        "debug_help": (
            "Test hata analizi için şu adımları izleyin:\n"
            "1. Hata mesajını kategorize edin: PRODUCT_BUG / TEST_ISSUE / ENVIRONMENT\n"
            "2. Locator sorunları için data-testid kullanın\n"
            "3. Timing sorunları için waitForSelector kullanın\n"
            "4. Allure raporundan screenshot ve trace inceleyin\n"
            "5. AI Debug Raporu sayfasından otomatik analiz alın"
        ),
        "general": (
            "Nexus QA asistanı olarak QA süreçleri, test otomasyonu, "
            "BDD senaryoları ve Playwright/Selenium konularında yardımcı olabilirim. "
            "Şu anda AI Gateway erişilebilir değil, ancak temel sorularınıza yanıt verebilirim."
        ),
    }
    return canned.get(intent, canned["general"])


# ── Quick Actions ─────────────────────────────────────────────────────────────

QUICK_ACTIONS = [
    {
        "id": "explain_bdd",
        "label": "BDD nedir?",
        "message": "BDD (Behavior Driven Development) nedir ve Gherkin nasıl kullanılır?",
        "icon": "📖",
    },
    {
        "id": "playwright_starter",
        "label": "Playwright başlangıç",
        "message": "Playwright TypeScript ile basit bir login testi nasıl yazılır?",
        "icon": "🎭",
    },
    {
        "id": "regression_strategy",
        "label": "Regresyon stratejisi",
        "message": "İyi bir regresyon test seti nasıl oluşturulur?",
        "icon": "🔄",
    },
    {
        "id": "debug_tips",
        "label": "Hata debug ipuçları",
        "message": "Başarısız test senaryolarını debug etmek için en iyi yöntemler nelerdir?",
        "icon": "🔧",
    },
    {
        "id": "allure_tips",
        "label": "Allure kullanımı",
        "message": "Allure raporlarını nasıl etkin kullanabilirim?",
        "icon": "📊",
    },
    {
        "id": "ci_integration",
        "label": "CI/CD entegrasyonu",
        "message": "Test otomasyonunu GitHub Actions'a nasıl entegre ederim?",
        "icon": "🚀",
    },
]
