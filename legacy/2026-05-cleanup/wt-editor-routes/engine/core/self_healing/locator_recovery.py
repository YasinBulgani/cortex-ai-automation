"""
LocatorRecovery — Kırılan locator'lar için AI destekli alternatif bulucu.

1. DOM'dan benzer element arama (attribute, text, role matching)
2. Geçmiş locator haritasından fallback
3. LLM ile akıllı öneri (son çare)
"""
from __future__ import annotations

import json
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


def _extract_selector_from_error(error: str) -> Optional[str]:
    """Hata mesajından kırılan selector'ı çıkar."""
    patterns = [
        r'locator\("([^"]+)"\)',
        r'selector\s+"([^"]+)"',
        r'waiting for selector\s+"([^"]+)"',
        r"getByRole\('([^']+)'",
        r'\[data-testid="([^"]+)"\]',
    ]
    for pat in patterns:
        m = re.search(pat, error)
        if m:
            return m.group(1)
    return None


class LocatorRecovery:
    """Locator kurtarma motoru: DOM analizi + LLM fallback."""

    def recover(
        self, error: str, page_content: str = "", dom_snapshot: str = ""
    ) -> Optional[dict]:
        """
        Kırılan locator için alternatif öneri üret.

        Returns:
            {"fix_code": "...", "confidence": 0.0-1.0} veya None
        """
        broken_selector = _extract_selector_from_error(error)
        if not broken_selector:
            return None

        dom = dom_snapshot or page_content

        alt = self._find_by_attributes(broken_selector, dom)
        if alt:
            return alt

        alt = self._find_by_text_similarity(broken_selector, dom)
        if alt:
            return alt

        return self._ask_llm(broken_selector, dom)

    def _find_by_attributes(self, selector: str, dom: str) -> Optional[dict]:
        """data-testid, id, name attribute'larından eşleşme ara."""
        if not dom:
            return None

        if "data-testid" in selector:
            testid = re.search(r'data-testid="([^"]+)"', selector)
            if testid:
                tid = testid.group(1)
                parts = tid.split("-")
                if len(parts) >= 2:
                    for variant in [
                        f'[data-testid="{"-".join(parts[:-1])}"]',
                        f'[data-testid*="{parts[-1]}"]',
                    ]:
                        if variant != selector and _check_dom_contains(dom, variant):
                            return {"fix_code": variant, "confidence": 0.85}

        if selector.startswith("#"):
            element_id = selector[1:]
            for attr in ["name", "data-testid"]:
                pattern = f'{attr}="{element_id}"'
                if pattern in dom:
                    return {
                        "fix_code": f'[{attr}="{element_id}"]',
                        "confidence": 0.80,
                    }

        return None

    def _find_by_text_similarity(self, selector: str, dom: str) -> Optional[dict]:
        """Text içeriğinden eşleşme ara."""
        if not dom:
            return None

        clean = re.sub(r'[\[\]#.\'"=*^$]', " ", selector).strip()
        words = [w for w in clean.split() if len(w) > 2]

        for word in words:
            role_pattern = f'role="button"[^>]*>{word}'
            if re.search(role_pattern, dom, re.IGNORECASE):
                return {
                    "fix_code": f'getByRole("button", {{ name: "{word}" }})',
                    "confidence": 0.70,
                }
            text_pattern = f">{word}<"
            if text_pattern in dom:
                return {
                    "fix_code": f'getByText("{word}")',
                    "confidence": 0.65,
                }

        return None

    def _ask_llm(self, selector: str, dom: str) -> Optional[dict]:
        """LLM ile locator öneri al (son çare)."""
        try:
            from core.llm_bridge import call_llm

            prompt = (
                f"Bu selector kırıldı: {selector}\n\n"
                f"DOM (ilk 3000 karakter):\n{dom[:3000]}\n\n"
                "En kararlı alternatif Playwright selector öner. "
                'Sadece JSON döndür: {{"selector": "...", "confidence": 0.0-1.0}}'
            )
            raw = call_llm(
                [
                    {"role": "system", "content": "Sen Playwright locator uzmanısın."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
            )
            data = json.loads(raw)
            return {
                "fix_code": data.get("selector", ""),
                "confidence": min(data.get("confidence", 0.5), 0.80),
            }
        except Exception as e:
            logger.warning("LLM locator recovery failed: %s", e)
            return None


def _check_dom_contains(dom: str, selector_hint: str) -> bool:
    """DOM'da selector ipucunun var olup olmadığını kontrol et."""
    clean = selector_hint.strip("[]").replace("*=", "=")
    if "=" in clean:
        parts = clean.split("=", 1)
        attr_val = parts[1].strip('"')
        return attr_val in dom
    return selector_hint in dom
