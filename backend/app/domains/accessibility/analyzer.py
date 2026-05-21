"""Accessibility violation → Türkçe remediation üreten analyzer.

Mimari karar:
    * AI Gateway zaten mevcut (vLLM/Groq/Gemini/Ollama fallback zinciri).
    * Yeni provider eklemiyoruz — ``gateway_complete(task_type=...)`` çağrısıyla
      bütün fallback mantığı ücretsiz geliyor.
    * Structured output: LLM JSON array dönmeli. ``json_mode=True`` ile
      gateway buna zorlanır; parse başarısız olursa graceful fallback.
    * ``max_violations`` ile kesilmeli — tüm sayfalar taranırken 100+
      violation yaratabilir, context window + maliyet riski.

Feature flag:
    ``AI_ACCESSIBILITY_ENABLED`` — default False. Kapalıyken analyzer
    çağrıları no-op yanıt döner (empty remediations + error=None), frontend
    gösterecek şey bulamadığında sessizce atlar.

Test stratejisi:
    * ``gateway_complete`` monkeypatch'le mock'lanır
    * Gerçek HTTP çağrısı yok
    * Hata yolları: gateway exception, JSON parse fail, eksik alan
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from typing import Any, List, Optional

from app.domains.accessibility.schemas import (
    A11yRemediation,
    A11yViolation,
    AnalyzeA11yRequest,
    AnalyzeA11yResponse,
)

logger = logging.getLogger(__name__)


_SYSTEM_PROMPT = """Sen kıdemli bir erişilebilirlik (a11y) uzmanısın. WCAG 2.1/2.2 kriterlerini bilir, Türkçe teknik yazarsın.

Verilen her WCAG violation için:
1. Kısa ve net Türkçe başlık (ör: "Düşük kontrast: okunabilirlik riski")
2. Açıklama — kime etki eder, nasıl ve ne zaman (ekran okuyucu, klavye-only, düşük görüş, renk körlüğü gibi)
3. Somut düzeltme adımları — öncelik sırasıyla (HTML/ARIA/CSS)
4. Mümkünse öncesi/sonrası kod örneği
5. İlgili WCAG kriteri (ör: "1.4.3 Contrast (Minimum)")

Çıktı KATI JSON array, başka metin YOK. Her eleman şu şekilde:
[
  {
    "violation_id": "string",
    "turkish_title": "string",
    "turkish_explanation": "string",
    "remediation": "string",
    "code_example": "string veya null",
    "wcag_reference": "string veya null"
  }
]

Kurallar:
- Türkçe kullan (başlık, açıklama, düzeltme).
- Kod örneklerini tek kod bloğu olarak ver, markdown fence kullanma.
- Emin olmadığın alanlarda null kullan, uydurma.
- Violation kimliği (violation_id) girdideki ile BİREBİR aynı olmalı.
"""


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _parse_json_array(raw: str) -> Optional[list]:
    """LLM yanıtından JSON array parse et — markdown fence ve fazla metne dayanıklı."""
    text = (raw or "").strip()
    if not text:
        return None
    fence = re.match(r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, list) else None
    except json.JSONDecodeError:
        pass
    # Son çare: ilk '[' ve son ']' arasını al
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end > start:
        try:
            parsed = json.loads(text[start : end + 1])
            return parsed if isinstance(parsed, list) else None
        except json.JSONDecodeError:
            return None
    return None


def _compact_violation(v: A11yViolation) -> dict:
    """Violation'ı LLM'e göndermek için sıkıştır — nodes[0] yeterli, HTML kırp."""
    node = v.nodes[0] if v.nodes else None
    node_html = None
    if node and node.html:
        # LLM context window için HTML'i 500 karakterle kırp
        node_html = node.html if len(node.html) <= 500 else node.html[:500] + "…"
    return {
        "id": v.id,
        "impact": v.impact.value if v.impact else None,
        "help": v.help,
        "description": v.description,
        "tags": v.tags or [],
        "wcag_help_url": v.help_url,
        "node_html": node_html,
        "node_target": node.target if node else None,
        "failure_summary": node.failure_summary if node else None,
    }


class AccessibilityAnalyzer:
    """Thread-safe AI-destekli a11y analyzer.

    Tek bir singleton yeterli — gateway_complete zaten stateless.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._total_calls = 0
        self._last_error: str | None = None

    # ── Public ────────────────────────────────────────────────────────────

    def is_enabled(self) -> bool:
        """Feature flag açık mı?"""
        return _env_bool("AI_ACCESSIBILITY_ENABLED", default=False)

    def info(self) -> dict:
        with self._lock:
            return {
                "enabled": self.is_enabled(),
                "total_calls": self._total_calls,
                "last_error": self._last_error,
            }

    def analyze(self, request: AnalyzeA11yRequest) -> AnalyzeA11yResponse:
        """Violations listesini gateway'e gönder, remediation listesi dön.

        Davranış matrisi:
            * Flag kapalı → ok=True, empty remediations, error=None (sessiz no-op)
            * Violations boş → ok=True, empty remediations
            * Gateway erişilemez → ok=False, error=insan-okur mesaj, empty list
            * LLM yanıtı parse edilemedi → ok=False, error, empty list
            * Başarılı → ok=True, remediations dolu, latency_ms
        """
        if not self.is_enabled():
            return AnalyzeA11yResponse(
                ok=True, remediations=[], skipped_count=0, error=None
            )

        if not request.violations:
            return AnalyzeA11yResponse(ok=True, remediations=[])

        trimmed = request.violations[: request.max_violations]
        skipped = max(0, len(request.violations) - len(trimmed))

        t0 = time.monotonic()
        try:
            # Import içeriden — unit test'ler modülü mock'layabilsin
            from app.domains.ai.gateway_client import gateway_complete

            user_message = json.dumps(
                {
                    "url": request.url,
                    "violations": [_compact_violation(v) for v in trimmed],
                },
                ensure_ascii=False,
            )
            raw = gateway_complete(
                task_type="accessibility_analysis",
                user_message=user_message,
                system_message=_SYSTEM_PROMPT,
                temperature=0.2,
                max_tokens=3500,
                json_mode=True,
            )
        except RuntimeError as exc:
            msg = f"AI Gateway erişilemedi: {exc}"
            with self._lock:
                self._last_error = msg
            logger.warning("a11y analyzer: %s", msg)
            return AnalyzeA11yResponse(
                ok=False, remediations=[], skipped_count=skipped, error=msg
            )
        except Exception as exc:  # pragma: no cover - defansif
            msg = f"Beklenmeyen hata: {exc}"
            with self._lock:
                self._last_error = msg
            logger.exception("a11y analyzer: beklenmeyen hata")
            return AnalyzeA11yResponse(
                ok=False, remediations=[], skipped_count=skipped, error=msg
            )

        parsed = _parse_json_array(raw)
        if parsed is None:
            msg = "LLM yanıtı JSON array olarak parse edilemedi"
            with self._lock:
                self._last_error = msg
            logger.warning(
                "a11y analyzer: parse fail — raw first 200 chars: %r",
                (raw or "")[:200],
            )
            return AnalyzeA11yResponse(
                ok=False, remediations=[], skipped_count=skipped, error=msg
            )

        remediations: list[A11yRemediation] = []
        # Kullanıcı sadece istediği violation'lara ait sonuç aldığından emin ol
        requested_ids = {v.id for v in trimmed}
        for item in parsed:
            if not isinstance(item, dict):
                continue
            try:
                rem = A11yRemediation.model_validate(item)
            except Exception as exc:  # noqa: BLE001 - defansif
                logger.debug("a11y analyzer: schema dışı item atlandı: %s", exc)
                continue
            if rem.violation_id not in requested_ids:
                # Model uydurduysa kabul etmeyiz
                logger.debug(
                    "a11y analyzer: bilinmeyen violation_id '%s' atlandı",
                    rem.violation_id,
                )
                continue
            remediations.append(rem)

        elapsed_ms = int((time.monotonic() - t0) * 1000)
        with self._lock:
            self._total_calls += 1
            self._last_error = None

        return AnalyzeA11yResponse(
            ok=True,
            remediations=remediations,
            skipped_count=skipped,
            error=None,
            latency_ms=elapsed_ms,
        )


accessibility_analyzer = AccessibilityAnalyzer()
