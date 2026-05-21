"""
ClassificationEngine — Manuel vs Otomasyon Karar Motoru

Her test case için otomasyon uygunluğunu skorlar ve
en uygun framework'ü (Playwright, Selenium, Appium, RestAssured) önerir.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class AutomationFramework(str, Enum):
    PLAYWRIGHT = "playwright"
    SELENIUM = "selenium"
    APPIUM = "appium"
    REQUESTS = "requests"  # API testleri için
    MANUAL = "manual"


@dataclass
class ClassificationResult:
    test_case_id: str
    is_automatable: bool
    confidence_score: float       # 0.0 - 1.0
    recommended_framework: AutomationFramework
    reasoning: str
    automation_roi: str           # high / medium / low
    manual_effort_hours: float
    automation_effort_hours: float


class ClassificationEngine:
    """
    Test case'leri analiz ederek otomasyon kararı verir.

    Kriterler:
      - Tekrar sıklığı (yüksek → otomasyon)
      - Stabilite (flaky UI → manuel tercih)
      - Test tipi (API → her zaman otomasyon)
      - Veri bağımlılığı
    """

    # Otomasyon skoru artıran/azaltan anahtar kelimeler
    _PRO_AUTOMATION = {"regression", "api", "smoke", "performance", "security", "boundary", "database"}
    _PRO_MANUAL = {"exploratory", "usability", "ux", "accessibility", "visual", "user experience"}
    _FRAMEWORK_MAP = {
        "api": AutomationFramework.REQUESTS,
        "mobile": AutomationFramework.APPIUM,
        "ui": AutomationFramework.PLAYWRIGHT,
        "performance": AutomationFramework.PLAYWRIGHT,
        "security": AutomationFramework.REQUESTS,
    }

    def classify(self, test_case) -> ClassificationResult:
        """Tek test case'i sınıflandır."""
        tc_id = getattr(test_case, "id", "TC-UNKNOWN")
        tags = {t.lower() for t in getattr(test_case, "tags", [])}
        test_type = str(getattr(test_case, "test_type", "")).lower()
        title = str(getattr(test_case, "title", "")).lower()

        # Skor hesapla
        score = 0.5
        if test_type in self._PRO_AUTOMATION or any(t in self._PRO_AUTOMATION for t in tags):
            score += 0.35
        if test_type in self._PRO_MANUAL or any(t in self._PRO_MANUAL for t in tags):
            score -= 0.40

        # Ek sinyaller
        if "manual" in title or "exploratory" in title:
            score -= 0.3
        if "api" in title or "endpoint" in title:
            score += 0.3

        score = max(0.0, min(1.0, score))
        is_auto = score >= 0.55

        # Framework seç
        framework = AutomationFramework.MANUAL
        if is_auto:
            for keyword, fw in self._FRAMEWORK_MAP.items():
                if keyword in test_type or keyword in title:
                    framework = fw
                    break
            if framework == AutomationFramework.MANUAL:
                framework = AutomationFramework.PLAYWRIGHT

        # ROI hesapla (manuel saat / otomasyon saat)
        manual_h = 0.25 if test_type in {"smoke", "sanity"} else 0.5
        auto_h = 2.0 if not is_auto else (0.5 if framework == AutomationFramework.REQUESTS else 1.5)
        roi = "high" if (manual_h * 50) > auto_h else ("medium" if (manual_h * 20) > auto_h else "low")

        return ClassificationResult(
            test_case_id=tc_id,
            is_automatable=is_auto,
            confidence_score=round(score, 2),
            recommended_framework=framework,
            reasoning=self._build_reasoning(score, test_type, is_auto, framework),
            automation_roi=roi,
            manual_effort_hours=manual_h,
            automation_effort_hours=auto_h,
        )

    def classify_suite(self, test_cases: list) -> List[ClassificationResult]:
        """Test suite'i toplu sınıflandır."""
        return [self.classify(tc) for tc in test_cases]

    def _build_reasoning(self, score: float, test_type: str, is_auto: bool, fw: AutomationFramework) -> str:
        if is_auto:
            return (f"Otomasyon skoru {score:.0%} — '{test_type}' tipi tekrarlanabilir. "
                    f"Önerilen framework: {fw.value}.")
        return (f"Otomasyon skoru {score:.0%} — keşifsel/kullanılabilirlik testi manuel yapılmalı.")

    def classify_as_dict(self, test_case) -> dict:
        """
        Tek test case'i sınıflandır ve sonucu dict olarak döndür.

        Args:
            test_case: dict veya TestCase nesnesi.

        Returns:
            Dict with keys:
              - automation_suitable (bool)
              - recommended_tool (str)
              - estimated_effort (str)
              - reason (str)
        """
        if isinstance(test_case, dict):
            # dict girdisini geçici nesneye çevir
            class _TC:
                pass
            tc = _TC()
            tc.id = test_case.get("id", "TC-UNKNOWN")
            tc.tags = test_case.get("tags", [])
            tc.test_type = test_case.get("category", test_case.get("test_type", "functional"))
            tc.title = test_case.get("title", "")
            result = self.classify(tc)
        else:
            result = self.classify(test_case)

        # Map effort
        effort_map = {"high": "high", "medium": "medium", "low": "low"}
        if result.automation_effort_hours <= 1.0:
            effort = "low"
        elif result.automation_effort_hours <= 4.0:
            effort = "medium"
        else:
            effort = "high"

        return {
            "automation_suitable": result.is_automatable,
            "recommended_tool": result.recommended_framework.value,
            "estimated_effort": effort,
            "reason": result.reasoning,
        }
