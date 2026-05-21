"""
FailureClassifier — Test hata mesajlarını 6 self-healing kategorisine sınıflandırır.

Kural tabanlı + LLM fallback ile çalışır.
"""
from __future__ import annotations

import logging
import re

from core.self_healing.healer import HealingCategory

logger = logging.getLogger(__name__)

_SELECTOR_PATTERNS = [
    r"locator",
    r"selector",
    r"element.*not found",
    r"no element",
    r"waiting for selector",
    r"getByRole.*resolved to",
    r"strict mode violation",
]

_TIMING_PATTERNS = [
    r"timeout",
    r"exceeded.*ms",
    r"timed? ?out",
    r"waiting for.*load",
    r"page\.waitFor",
    r"navigation.*timeout",
]

_RUNTIME_PATTERNS = [
    r"net::ERR_",
    r"ERR_CONNECTION",
    r"ERR_NAME_NOT_RESOLVED",
    r"crash",
    r"context.*destroyed",
    r"target.*closed",
    r"protocol error",
]

_TEST_DATA_PATTERNS = [
    r"not found",
    r"null",
    r"undefined",
    r"no.*data",
    r"empty.*result",
    r"fixture.*missing",
    r"seed.*fail",
]

_VISUAL_PATTERNS = [
    r"visual.*mismatch",
    r"screenshot.*differ",
    r"ssim.*below",
    r"pixel.*diff",
    r"baseline.*not found",
    r"image.*comparison.*fail",
]

_FLOW_PATTERNS = [
    r"unexpected.*page",
    r"redirect",
    r"unexpected.*url",
    r"step.*order",
    r"wizard.*step",
    r"navigation.*changed",
]


def _match_patterns(text: str, patterns: list[str]) -> int:
    """Return number of pattern matches."""
    count = 0
    for p in patterns:
        if re.search(p, text, re.IGNORECASE):
            count += 1
    return count


class FailureClassifier:
    """Kural tabanlı hata sınıflandırıcı."""

    def classify(self, error_message: str, console_logs: list[str] | None = None) -> HealingCategory:
        combined = error_message
        if console_logs:
            combined += " " + " ".join(console_logs)

        scores = {
            HealingCategory.SELECTOR: _match_patterns(combined, _SELECTOR_PATTERNS),
            HealingCategory.TIMING: _match_patterns(combined, _TIMING_PATTERNS),
            HealingCategory.RUNTIME: _match_patterns(combined, _RUNTIME_PATTERNS),
            HealingCategory.TEST_DATA: _match_patterns(combined, _TEST_DATA_PATTERNS),
            HealingCategory.VISUAL: _match_patterns(combined, _VISUAL_PATTERNS),
            HealingCategory.FLOW_CHANGE: _match_patterns(combined, _FLOW_PATTERNS),
        }

        best = max(scores, key=scores.get)
        if scores[best] == 0:
            return self._classify_with_llm(combined)

        logger.info("Classified as %s (score=%d)", best.value, scores[best])
        return best

    def _classify_with_llm(self, error_text: str) -> HealingCategory:
        """Kural eşleşmediğinde LLM ile sınıflandır."""
        try:
            from core.llm_bridge import call_llm
            raw = call_llm(
                [
                    {"role": "system", "content": "Test hata sınıflandırıcısın. Verilen hatayı şu kategorilerden birine ata: selector, timing, runtime, test_data, visual, flow_change. Sadece kategori adını döndür."},
                    {"role": "user", "content": error_text[:1000]},
                ],
                temperature=0.1,
                max_tokens=20,
            )
            category_name = raw.strip().lower().replace(" ", "_")
            try:
                return HealingCategory(category_name)
            except ValueError:
                pass
        except Exception as e:
            logger.debug("LLM classification failed: %s", e)
        logger.warning("No pattern matched, LLM inconclusive — defaulting to RUNTIME")
        return HealingCategory.RUNTIME
