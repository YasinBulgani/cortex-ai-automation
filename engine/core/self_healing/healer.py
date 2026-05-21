"""
SelfHealingEngine — 6 Kategorili Otonom Test Tamir Sistemi.

Kategoriler:
  1. Selector healing   — kırılan locator'ları tamir
  2. Timing healing     — timeout/wait sorunlarını çöz
  3. Runtime error      — exception handling
  4. Test data healing  — bozuk/eksik veri düzeltme
  5. Visual assertion   — görsel assertion adaptasyonu
  6. Flow change        — iş akışı değişikliğine adaptasyon
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from config.settings import settings

logger = logging.getLogger(__name__)


class HealingCategory(Enum):
    SELECTOR = "selector"
    TIMING = "timing"
    RUNTIME = "runtime"
    TEST_DATA = "test_data"
    VISUAL = "visual"
    FLOW_CHANGE = "flow_change"


@dataclass
class HealingResult:
    category: HealingCategory
    original_error: str
    fix_applied: str
    confidence: float
    auto_applied: bool
    duration_ms: int = 0


@dataclass
class HealingRecord:
    test_id: str
    timestamp: float
    result: HealingResult
    success: bool


class SelfHealingEngine:
    """Ana self-healing orkestratörü. Failure sınıflandırma + kategori-spesifik tamir."""

    HISTORY_FILE = "healing_history.json"

    def __init__(self):
        from core.self_healing.classifier import FailureClassifier
        from core.self_healing.locator_recovery import LocatorRecovery
        from config.ai_config_loader import get_self_healing_config

        cfg = get_self_healing_config()
        self.CONFIDENCE_THRESHOLD = cfg.get("confidence_threshold", 0.85)
        self._auto_apply = cfg.get("auto_apply", True)
        self._max_retry = cfg.get("max_retry", 3)

        self.classifier = FailureClassifier()
        self.locator_recovery = LocatorRecovery()
        self._history: list[dict] = []
        self._history_path = settings.REPORTS_DIR / self.HISTORY_FILE

    def diagnose_and_heal(
        self,
        test_id: str,
        error_message: str,
        page_content: str = "",
        dom_snapshot: str = "",
        console_logs: list[str] | None = None,
    ) -> Optional[HealingResult]:
        """
        Başarısız bir testi analiz edip otomatik düzeltme dener.

        Returns:
            HealingResult (başarılı ise) veya None
        """
        start = time.time()

        category = self.classifier.classify(error_message, console_logs or [])
        logger.info("Failure classified as: %s for test %s", category.value, test_id)

        fix = self._apply_category_fix(
            category, error_message, page_content, dom_snapshot
        )

        duration_ms = int((time.time() - start) * 1000)

        if not fix:
            return None

        result = HealingResult(
            category=category,
            original_error=error_message,
            fix_applied=fix["fix_code"],
            confidence=fix["confidence"],
            auto_applied=fix["confidence"] >= self.CONFIDENCE_THRESHOLD,
            duration_ms=duration_ms,
        )

        self._record(test_id, result, success=result.auto_applied)
        return result

    def _apply_category_fix(
        self,
        category: HealingCategory,
        error: str,
        page_content: str,
        dom_snapshot: str,
    ) -> Optional[dict]:
        if category == HealingCategory.SELECTOR:
            return self._heal_selector(error, page_content, dom_snapshot)
        elif category == HealingCategory.TIMING:
            return self._heal_timing(error)
        elif category == HealingCategory.RUNTIME:
            return self._heal_runtime(error)
        elif category == HealingCategory.TEST_DATA:
            return self._heal_test_data(error)
        elif category == HealingCategory.VISUAL:
            return self._heal_visual(error)
        elif category == HealingCategory.FLOW_CHANGE:
            return self._heal_flow_change(error, page_content)
        return None

    def _heal_selector(self, error: str, page_content: str, dom: str) -> Optional[dict]:
        """Kırılan locator için alternatif bul."""
        suggestion = self.locator_recovery.recover(error, page_content, dom)
        if suggestion and suggestion.get("fix_code"):
            return suggestion
        return None

    def _heal_timing(self, error: str) -> dict:
        """Timeout sorunları için wait stratejisi öner."""
        if "timeout" in error.lower():
            wait_ms = 10000
            if "navigation" in error.lower():
                wait_ms = 30000
            return {
                "fix_code": f"await page.waitForTimeout({wait_ms})",
                "confidence": 0.90,
                "fix_type": "timing_increase",
            }
        return {"fix_code": "await page.waitForLoadState('networkidle')", "confidence": 0.75}

    def _heal_runtime(self, error: str) -> dict:
        """Runtime hataları için genel düzeltme."""
        if "net::ERR_" in error:
            return {
                "fix_code": "retry_with_backoff(page, action, max_retries=3)",
                "confidence": 0.70,
            }
        return {"fix_code": "try_catch_and_retry()", "confidence": 0.50}

    def _heal_test_data(self, error: str) -> dict:
        """Test verisi sorunları için düzeltme."""
        if "not found" in error.lower() or "null" in error.lower():
            return {
                "fix_code": "regenerate_test_data(scenario_id)",
                "confidence": 0.80,
            }
        return {"fix_code": "refresh_test_fixtures()", "confidence": 0.60}

    def _heal_visual(self, error: str) -> dict:
        """Görsel assertion sorunları için düzeltme."""
        return {
            "fix_code": "update_visual_baseline(screenshot_path)",
            "confidence": 0.65,
        }

    def _heal_flow_change(self, error: str, page_content: str) -> dict:
        """İş akışı değişikliklerine adaptasyon."""
        return {
            "fix_code": "ai_analyze_flow_change(page, expected_flow)",
            "confidence": 0.55,
        }

    def _record(self, test_id: str, result: HealingResult, success: bool) -> None:
        record = {
            "test_id": test_id,
            "timestamp": time.time(),
            "category": result.category.value,
            "confidence": result.confidence,
            "auto_applied": result.auto_applied,
            "success": success,
            "fix_applied": result.fix_applied,
            "duration_ms": result.duration_ms,
        }
        self._history.append(record)
        self._persist_history()

    def _persist_history(self) -> None:
        try:
            self._history_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._history_path, "w", encoding="utf-8") as f:
                json.dump(self._history, f, indent=2, ensure_ascii=False)
        except OSError:
            logger.warning("Healing history persist failed")

    def get_stats(self) -> dict:
        """Healing istatistiklerini döndür."""
        total = len(self._history)
        if total == 0:
            return {"total": 0}
        auto = sum(1 for h in self._history if h.get("auto_applied"))
        success = sum(1 for h in self._history if h.get("success"))
        by_cat = {}
        for h in self._history:
            cat = h.get("category", "unknown")
            by_cat[cat] = by_cat.get(cat, 0) + 1
        return {
            "total": total,
            "auto_applied": auto,
            "success": success,
            "success_rate": round(success / total, 2) if total else 0,
            "by_category": by_cat,
        }
