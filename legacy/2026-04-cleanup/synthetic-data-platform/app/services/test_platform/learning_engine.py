"""
LearningEngine — Flaky Test Tespiti ve Otomasyon Optimizasyonu

Geçmiş çalışma verilerini analiz ederek:
  - Flaky test'leri tespit eder
  - Başarısızlık pattern'lerini öğrenir
  - Locator ve timing önerisi sunar
  - Test suite'ini optimize eder
"""
from __future__ import annotations
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class FlakyTest:
    test_id: str
    flakiness_score: float       # 0.0 = stabil, 1.0 = tamamen flaky
    fail_rate: float
    avg_duration: float
    root_cause_guess: str
    suggested_fix: str


@dataclass
class LearningInsight:
    insight_type: str            # flaky / slow / pattern / optimization
    affected_tests: List[str]
    description: str
    action: str
    priority: str                # high / medium / low


@dataclass
class OptimizationReport:
    generated_at: str
    total_runs_analyzed: int
    flaky_tests: List[FlakyTest]
    insights: List[LearningInsight]
    suite_health_score: float    # 0.0 - 1.0
    recommended_actions: List[str]


class LearningEngine:
    """
    Geçmiş test çalışmalarından öğrenerek test kalitesini artırır.

    Hafıza: In-memory sözlük (production'da Redis/PostgreSQL kullanılır).
    """

    def __init__(self):
        # test_id -> list of run records
        self._history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    def record_run(self, execution_summary) -> None:
        """Test çalışma sonucunu hafızaya kaydeder."""
        results = getattr(execution_summary, "results", [])
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        for r in results:
            tc_id = getattr(r, "test_case_id", "UNKNOWN")
            self._history[tc_id].append({
                "status": str(getattr(r, "status", "unknown")),
                "duration": getattr(r, "duration_seconds", 0.0),
                "error": getattr(r, "error_message", ""),
                "timestamp": ts,
            })

    def analyze(self, min_runs: int = 3) -> OptimizationReport:
        """
        Kayıtlı geçmişi analiz eder ve optimizasyon raporu üretir.

        Args:
            min_runs: Analiz için minimum çalışma sayısı

        Returns:
            OptimizationReport
        """
        flaky_tests = []
        insights = []
        total_runs = sum(len(v) for v in self._history.values())

        for tc_id, runs in self._history.items():
            if len(runs) < min_runs:
                continue

            statuses = [r["status"] for r in runs]
            durations = [r["duration"] for r in runs]
            fail_count = sum(1 for s in statuses if "fail" in s.lower() or "error" in s.lower())
            fail_rate = fail_count / len(runs)
            avg_dur = sum(durations) / len(durations)

            # Flaky: bazen geçiyor bazen başarısız
            pass_count = len(runs) - fail_count
            is_flaky = 0 < fail_count < len(runs) and pass_count > 0
            flakiness = fail_rate if is_flaky else 0.0

            if flakiness > 0.2:
                root_cause = self._guess_root_cause(runs)
                fix = self._suggest_fix(root_cause)
                flaky_tests.append(FlakyTest(
                    test_id=tc_id,
                    flakiness_score=round(flakiness, 2),
                    fail_rate=round(fail_rate, 2),
                    avg_duration=round(avg_dur, 2),
                    root_cause_guess=root_cause,
                    suggested_fix=fix,
                ))

            # Yavaş test uyarısı (>10 saniye)
            if avg_dur > 10:
                insights.append(LearningInsight(
                    insight_type="slow",
                    affected_tests=[tc_id],
                    description=f"{tc_id} ortalama {avg_dur:.1f}s — SLA'yi aşıyor.",
                    action="Timeout ayarını gözden geçirin veya paralel çalıştırın.",
                    priority="medium",
                ))

        # Genel sağlık skoru
        all_runs_count = total_runs or 1
        total_fails = sum(
            sum(1 for r in runs if "fail" in r["status"].lower())
            for runs in self._history.values()
        )
        health = max(0.0, 1.0 - (total_fails / all_runs_count) - len(flaky_tests) * 0.05)

        if flaky_tests:
            insights.append(LearningInsight(
                insight_type="flaky",
                affected_tests=[f.test_id for f in flaky_tests],
                description=f"{len(flaky_tests)} flaky test tespit edildi.",
                action="Flaky testleri karantinaya alın, kök neden analizi yapın.",
                priority="high",
            ))

        actions = self._build_actions(flaky_tests, health)

        return OptimizationReport(
            generated_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
            total_runs_analyzed=total_runs,
            flaky_tests=flaky_tests,
            insights=insights,
            suite_health_score=round(health, 2),
            recommended_actions=actions,
        )

    def _guess_root_cause(self, runs: list) -> str:
        errors = [r.get("error", "") for r in runs if r.get("error")]
        if any("timeout" in e.lower() for e in errors):
            return "timing — element yüklenmeden önce etkileşim"
        if any("stale" in e.lower() for e in errors):
            return "stale element — DOM değişikliği"
        if any("network" in e.lower() or "connection" in e.lower() for e in errors):
            return "ağ kararsızlığı"
        return "belirsiz — daha fazla çalışma verisi gerekiyor"

    def _suggest_fix(self, root_cause: str) -> str:
        fixes = {
            "timing": "page.wait_for_selector() veya retry mekanizması ekleyin.",
            "stale element": "Element'i her kullanımdan önce yeniden bulun.",
            "ağ kararsızlığı": "Retry decorator ekleyin, mock server kullanmayı düşünün.",
        }
        for key, fix in fixes.items():
            if key in root_cause:
                return fix
        return "Testi izole test ortamında tekrar çalıştırın ve logları inceleyin."

    def _build_actions(self, flaky: list, health: float) -> List[str]:
        actions = []
        if flaky:
            actions.append(f"{len(flaky)} flaky test karantinaya alınmalı.")
        if health < 0.7:
            actions.append("Suite sağlığı kritik seviyede — CI/CD pipeline'ı durdurmayı değerlendirin.")
        if health > 0.9:
            actions.append("Suite sağlığı mükemmel. Kapsam artırımı planlanabilir.")
        actions.append("Haftalık flaky test review toplantısı düzenleyin.")
        return actions
