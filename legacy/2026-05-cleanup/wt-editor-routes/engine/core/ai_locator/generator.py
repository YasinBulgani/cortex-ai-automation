"""
AILocatorGenerator — DOM analizi + LLM ile en kararlı locator'ları üretir.

Strateji öncelik sırası:
  P0: data-testid
  P1: getByRole + accessible name
  P2: getByLabel
  P3: #id
  P4: aria-label
  P5: getByPlaceholder
  P6: name attribute
  P7: getByText
  P8: CSS class-based (önerilmez)
  P9: XPath (son çare)
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

STABILITY_MAP = {
    "data-testid": 5,
    "role": 5,
    "label": 4,
    "id": 4,
    "aria-label": 4,
    "placeholder": 3,
    "name": 3,
    "text": 2,
    "css": 2,
    "xpath": 1,
}


@dataclass
class LocatorSuggestion:
    strategy: str
    selector: str
    confidence: float
    stability: int
    reason: str


LOCATOR_SYSTEM_PROMPT = """Sen bir Playwright test otomasyon uzmanısın. 
Verilen HTML element ve bağlamından en kararlı locator'ları üret.
Kurallar:
1. data-testid > getByRole > getByLabel > getByText > CSS > XPath
2. CSS class selector'lar Tailwind nedeniyle KULLANILMAZ
3. Her öneri: strategy, selector, confidence (0-1), stability (1-5), reason içermeli
4. JSON array döndür: [{"strategy":"...","selector":"...","confidence":0.9,"stability":5,"reason":"..."}]
Sadece JSON döndür."""


class AILocatorGenerator:
    """Playwright sayfası için AI destekli locator üretici."""

    def generate_for_element(
        self,
        element_description: str,
        page_content: str,
        accessibility_tree: str = "",
    ) -> list[LocatorSuggestion]:
        """Tek bir element için locator önerileri üret."""
        from core.llm_bridge import call_llm

        user_content = (
            f"Element: {element_description}\n\n"
            f"Accessibility Tree:\n{accessibility_tree[:3000]}\n\n"
            f"DOM (özet):\n{page_content[:5000]}"
        )

        try:
            raw = call_llm(
                [
                    {"role": "system", "content": LOCATOR_SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.1,
            )
            raw = _clean_json(raw)
            items = json.loads(raw)
            return [
                LocatorSuggestion(
                    strategy=item.get("strategy", "unknown"),
                    selector=item.get("selector", ""),
                    confidence=item.get("confidence", 0.5),
                    stability=item.get("stability", 1),
                    reason=item.get("reason", ""),
                )
                for item in items
                if item.get("selector")
            ]
        except Exception as e:
            logger.error("AI locator generation failed: %s", e)
            return []

    def generate_page_inventory(
        self, page_content: str, page_name: str = "unknown"
    ) -> list[dict]:
        """Sayfa DOM'undan tüm interaktif elementler için locator envanteri çıkar."""
        from core.llm_bridge import call_llm

        prompt = (
            f"Sayfa: {page_name}\n\n"
            f"DOM:\n{page_content[:8000]}\n\n"
            "Bu sayfadaki TÜM interaktif elementleri (butonlar, inputlar, linkler, "
            "dropdown, checkbox, vb.) listele. Her biri için:\n"
            '- element_name, element_type, suggested_testid, best_selector, stability\n\n'
            "JSON array döndür."
        )

        try:
            raw = call_llm(
                [
                    {"role": "system", "content": "Playwright locator uzmanısın."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
            )
            return json.loads(_clean_json(raw))
        except Exception as e:
            logger.error("Page inventory generation failed: %s", e)
            return []


def _clean_json(raw: str) -> str:
    """LLM çıktısından markdown bloğunu temizle."""
    if "```" in raw:
        lines = raw.split("\n")
        cleaned = [ln for ln in lines if not ln.strip().startswith("```")]
        return "\n".join(cleaned)
    return raw
