"""
Nexus QA — Faz 4: AI Regresyon Set Önerisi
AI Gateway (Groq/Gemini/Ollama/g4f) üzerinden senaryo gruplama.
OpenAI key yoksa AI Gateway kullanır; o da yoksa akıllı dummy gruplama.
"""
from __future__ import annotations

import json
import logging
import math
import random
import re
from typing import Any

logger = logging.getLogger(__name__)

# ── Sistem Prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
Sen bir kıdemli QA mühendisisin. Sana bir projedeki test senaryolarının listesi verilecek.
Bu senaryoları analiz ederek anlamlı regresyon test setleri öner.

Kurallar:
1. Senaryoları özellik alanına, iş akışına veya risk seviyesine göre grupla.
2. Her set için açıklayıcı bir ad ve kısa açıklama yaz.
3. Bir senaryo birden fazla sette yer alabilir (örneğin hem "Kritik Akışlar" hem "Login Modülü").
4. En az 2, en fazla 7 set öner.
5. Her sette en az 1 senaryo olmalı.
6. Setleri öncelik/önem sırasına göre sırala.
7. Set adları Türkçe ve açıklayıcı olmalı.

MUTLAKA aşağıdaki JSON formatında yanıt ver, başka bir şey yazma:
{
  "sets": [
    {
      "name": "Set adı",
      "description": "Setin kısa açıklaması ve neden bu senaryolar bir arada",
      "scenario_ids": ["id1", "id2"],
      "priority": "critical | high | medium | low"
    }
  ]
}"""

# ── Dummy / Fallback ──────────────────────────────────────────────────────────

_DUMMY_SET_TEMPLATES = [
    {"name": "Kritik İş Akışları — Smoke Test", "description": "Sistemin temel işlevselliğini doğrulayan en kritik uçtan uca akışlar. Her deploy sonrası mutlaka koşulmalıdır.", "priority": "critical", "ratio": 0.4},
    {"name": "Kullanıcı Kimlik Doğrulama ve Yetkilendirme", "description": "Login, logout, şifre sıfırlama, oturum yönetimi ve rol bazlı erişim kontrol senaryoları.", "priority": "critical", "ratio": 0.25},
    {"name": "Veri Girişi ve Validasyon Kuralları", "description": "Form alanları, zorunlu alan kontrolleri, sınır değer analizleri ve hata mesajı doğrulamaları.", "priority": "high", "ratio": 0.3},
    {"name": "Raporlama ve Dashboard", "description": "Dashboard istatistikleri, rapor üretimi, filtreleme ve dışa aktarma senaryoları.", "priority": "medium", "ratio": 0.2},
    {"name": "Negatif Senaryolar ve Hata Yönetimi", "description": "Geçersiz girdi, timeout, bağlantı kopması gibi olumsuz durumlarda sistemin doğru davranışını test eden senaryolar.", "priority": "high", "ratio": 0.3},
    {"name": "Entegrasyon ve API Testleri", "description": "Dış servis entegrasyonları, API uç noktaları ve veri senkronizasyon senaryoları.", "priority": "medium", "ratio": 0.25},
]


def _build_dummy_sets(scenarios: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deterministic dummy grouping when AI is unavailable."""
    ids = [s["id"] for s in scenarios]
    n = len(ids)
    num_sets = min(len(_DUMMY_SET_TEMPLATES), max(2, math.ceil(n / 2)))
    templates = _DUMMY_SET_TEMPLATES[:num_sets]
    rng = random.Random(42)
    result = []
    for tpl in templates:
        count = max(1, round(n * tpl["ratio"]))
        chosen = rng.sample(ids, min(count, n))
        result.append({
            "name": tpl["name"],
            "description": tpl["description"],
            "scenario_ids": chosen,
            "priority": tpl["priority"],
        })
    return result


# ── AI Gateway Call ────────────────────────────────────────────────────────────

def _suggest_via_gateway(
    scenario_text: str,
    extra_instructions: str,
) -> list[dict[str, Any]]:
    """Call AI Gateway for regression set suggestions."""
    try:
        from app.domains.ai.gateway_client import gateway_complete
        user_content = scenario_text
        if extra_instructions:
            user_content += f"\n\nEk Talimatlar:\n{extra_instructions}"

        raw = gateway_complete(
            task_type="suggest_regression",
            user_message=user_content,
            system_message=SYSTEM_PROMPT,
            temperature=0.4,
            max_tokens=3000,
        )

        # Strip markdown code fences if present
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE).strip()

        # Parse JSON
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            # Try to find JSON object in response
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if match:
                parsed = json.loads(match.group())
            else:
                raise ValueError("AI yanıtı JSON formatında değil")

        sets = parsed.get("sets", [])
        if not isinstance(sets, list) or not sets:
            raise ValueError("AI yanıtında geçerli 'sets' listesi bulunamadı")

        return sets

    except Exception as e:
        logger.warning(f"AI Gateway regression suggest başarısız: {e}")
        raise


# ── Main Entry ────────────────────────────────────────────────────────────────

def suggest_regression_sets(
    scenarios: list[dict[str, Any]],
    extra_instructions: str = "",
) -> list[dict[str, Any]]:
    """
    Senaryo listesini analiz ederek regresyon setleri öner.
    Öncelik sırası:
      1. AI Gateway (Groq → Gemini → Ollama → g4f)
      2. Akıllı dummy gruplama (fallback)
    """
    if not scenarios:
        return []

    scenario_text = "\n".join(
        f"- ID: {s['id']} | Başlık: {s['title']} | Durum: {s.get('status', '')} | "
        f"Etiketler: {', '.join(s.get('tags') or [])} | "
        f"Açıklama: {(s.get('description') or '')[:100]}"
        for s in scenarios
    )
    user_content = f"Projedeki senaryolar ({len(scenarios)} adet):\n\n{scenario_text}"

    # Try AI Gateway first
    try:
        from app.domains.ai.gateway_client import gateway_is_available
        if gateway_is_available():
            sets = _suggest_via_gateway(user_content, extra_instructions)
            valid_ids = {s["id"] for s in scenarios}
            for s in sets:
                s["scenario_ids"] = [sid for sid in s.get("scenario_ids", []) if sid in valid_ids]
            logger.info(f"AI Gateway regresyon önerisi: {len(sets)} set")
            return sets
        else:
            logger.info("AI Gateway erişilemiyor, OpenAI/dummy'ye geçiliyor")
    except Exception as e:
        logger.warning(f"AI Gateway hatası: {e}")

    # Final fallback: smart dummy
    logger.info("Dummy regresyon seti kullanılıyor")
    return _build_dummy_sets(scenarios)
