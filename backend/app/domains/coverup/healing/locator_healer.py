"""LLM tabanlı locator healer — kırık selector → 3 aday + confidence.

Tasarım:
    * ``LocatorHealer.propose(event) -> List[HealingProposal]`` tek giriş.
    * Altında: prompt inşası + LLM çağrısı + JSON parse + güvenlik filtresi.
    * LLM provider enjekte edilebilir (``call_llm_fn``). Default ``None`` →
      runtime'da ``usage_service.record_usage`` ile entegre bir çağırıcı
      bağlanır. Testler kolayca mock enjekte eder.
    * LLM JSON parse başarısızsa boş liste döner — orchestrator "öneri yok"
      olarak işler, PR açılmaz. Sessiz fail değil; audit log'a yazılır.

Prompt stratejisi:
    * Türkçe sistem prompt'u (projenin diğer prompt'ları Türkçe),
    * ARIA snapshot'ı doğrudan içerir (playwright_mcp formatında),
    * selector öncelik sırası: data-testid > role > aria-label > text > css.
      Çünkü en stabil locator'lar bu sırada (projenin DSL katalog kararı).

Güvenlik filtresi:
    * ``new_locator`` içinde script/event-handler enjekte edilemez — zaten
      sadece attribute selector, ama extra sigorta.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Callable, List, Optional

from .schemas import FailureEvent, HealingProposal, LocatorKind

logger = logging.getLogger(__name__)

# Tehlikeli pattern'ler — LLM çıktısında bunlar varsa öneri reddedilir.
# (LLM prompt'a sadık olsa bile adversarial dom_snapshot ile yönlendirilebilir.)
_FORBIDDEN = re.compile(
    r"(?i)(javascript:|onerror\s*=|onload\s*=|<script|eval\s*\()"
)


_SYSTEM_PROMPT = """\
Sen kıdemli bir QA otomasyon mühendisisin. Görevin kırık bir Playwright
locator'ı için stabil alternatifler üretmek.

## Kurallar
- Playwright lokatör önceliği: data-testid > role > aria-label > text > css
- Her öneriye 0.0-1.0 arası bir `confidence` ver (0.8+ yüksek, 0.5-0.79 orta, <0.5 düşük)
- Aynı elemana işaret ettiğinden emin ol — snapshot'ı dikkatlice oku
- xpath sadece başka seçenek yoksa; stabil değil
- `rationale` kısa (1 cümle): neden bu öneri daha iyi

## Çıktı ZORUNLU JSON formatı
{
  "proposals": [
    {"new_locator": "...", "new_locator_kind": "css|role|text|test-id|xpath", "confidence": 0.0-1.0, "rationale": "..."}
  ]
}

Maks 3 öneri döndür. Başka metin yazma.
"""


_LocatorKinds = {"css", "role", "text", "test-id", "xpath", "other"}


LlmCallable = Callable[[str, str], str]
"""(system_prompt, user_prompt) -> raw_response_text."""


class LocatorHealer:
    def __init__(self, *, call_llm: Optional[LlmCallable] = None) -> None:
        self._call_llm = call_llm

    def bind_llm(self, call_llm: LlmCallable) -> None:
        self._call_llm = call_llm

    # ── Public ────────────────────────────────────────────────────────────

    def propose(self, event: FailureEvent) -> List[HealingProposal]:
        if self._call_llm is None:
            logger.warning("LocatorHealer: LLM bağlı değil, boş öneri döndü")
            return []

        if not event.dom_snapshot.strip():
            # ARIA snapshot yoksa LLM körlemesine selector üretir — güvenilmez
            logger.info(
                "LocatorHealer: run=%s dom_snapshot boş, öneri yok",
                event.run_id,
            )
            return []

        user_prompt = self._build_user_prompt(event)
        try:
            raw = self._call_llm(_SYSTEM_PROMPT, user_prompt)
        except Exception as exc:
            logger.warning("LocatorHealer: LLM çağrısı hata (%s)", exc)
            return []

        return self._parse_and_filter(raw)

    # ── Internal ──────────────────────────────────────────────────────────

    @staticmethod
    def _build_user_prompt(event: FailureEvent) -> str:
        return (
            f"## Kırık Locator\n"
            f"Dosya: `{event.test_file_path}`"
            + (f" (satır {event.line_number})\n" if event.line_number else "\n")
            + f"Eski locator ({event.locator_kind}): `{event.locator}`\n"
            + (f"Test adı: {event.test_name}\n" if event.test_name else "")
            + "\n## Hata\n"
            + (event.error_message[:1500] if event.error_message else "(yok)")
            + "\n\n## ARIA / DOM snapshot (kırık element civarı)\n```\n"
            + event.dom_snapshot[:4000]
            + "\n```\n"
            + (f"\nHedef URL: {event.page_url}\n" if event.page_url else "")
        )

    @staticmethod
    def _parse_and_filter(raw: str) -> List[HealingProposal]:
        if not raw or not raw.strip():
            return []

        text = raw.strip()
        # Bazı provider'lar ```json ... ``` sarar
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.DOTALL)

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            logger.warning(
                "LocatorHealer: JSON parse başarısız (%s). Ham çıktı: %s",
                exc,
                text[:200],
            )
            return []

        if not isinstance(data, dict):
            return []
        raw_props = data.get("proposals") or []
        if not isinstance(raw_props, list):
            return []

        out: List[HealingProposal] = []
        for item in raw_props:
            if not isinstance(item, dict):
                continue
            new_loc = str(item.get("new_locator", "")).strip()
            if not new_loc:
                continue
            if _FORBIDDEN.search(new_loc):
                logger.warning(
                    "LocatorHealer: güvensiz pattern reddedildi: %r", new_loc
                )
                continue
            kind_raw = str(item.get("new_locator_kind") or "css").strip().lower()
            kind: LocatorKind = (
                kind_raw  # type: ignore[assignment]
                if kind_raw in _LocatorKinds
                else "other"
            )
            try:
                conf = float(item.get("confidence", 0.0))
            except (TypeError, ValueError):
                conf = 0.0
            conf = max(0.0, min(1.0, conf))
            rationale = str(item.get("rationale") or "")[:500]
            try:
                out.append(
                    HealingProposal(
                        new_locator=new_loc,
                        new_locator_kind=kind,
                        confidence=conf,
                        rationale=rationale,
                    )
                )
            except ValueError as exc:
                logger.debug("LocatorHealer: proposal reddedildi: %s", exc)
                continue

        # Confidence'a göre azalan sırada — orchestrator ilk elemanı seçer
        out.sort(key=lambda p: p.confidence, reverse=True)
        return out[:3]


# Proses ömrü boyunca paylaşılan singleton (LLM'i main.py startup'ta bind eder)
locator_healer = LocatorHealer()
