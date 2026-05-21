"""
PatternAnalyzer — Test sonuç geçmişinden pattern'ları analiz eder.

Tespit edilen pattern'lar:
  - Flaky testler (tutarsız pass/fail)
  - Kronik fail testler
  - Yavaşlayan testler (performance drift)
  - Korelasyon: Hangi dosya değişiklikleri hangi testleri kırıyor
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class AIInsight:
    type: str           # flaky_pattern, chronic_fail, perf_drift, correlation
    severity: str       # critical, warning, info
    description: str
    suggestion: str
    affected_tests: list[str] = field(default_factory=list)
    confidence: float = 0.0


class PatternAnalyzer:
    """Test sonuç pattern analiz motoru."""

    FLAKY_THRESHOLD = 0.3
    CHRONIC_FAIL_THRESHOLD = 3

    def analyze(self, history: list[dict]) -> list[AIInsight]:
        """Tüm execution history'yi analiz et."""
        insights = []
        insights.extend(self._detect_flaky_tests(history))
        insights.extend(self._detect_chronic_failures(history))
        insights.extend(self._detect_performance_drift(history))
        insights.extend(self._detect_healing_patterns(history))
        insights.extend(self._detect_failure_correlation(history))
        return insights

    def _detect_flaky_tests(self, history: list[dict]) -> list[AIInsight]:
        """Flaky test tespiti: Son N çalıştırmada tutarsız sonuçlar."""
        test_results: dict[str, list[str]] = {}

        for run in history[-20:]:
            for record in run.get("records", []):
                tid = record.get("test_id", "")
                status = record.get("status", "")
                if tid:
                    test_results.setdefault(tid, []).append(status)

        flaky_tests = []
        for tid, statuses in test_results.items():
            if len(statuses) < 3:
                continue
            passes = sum(1 for s in statuses if s in ("pass", "healed"))
            fails = sum(1 for s in statuses if s == "fail")
            total = passes + fails
            if total == 0:
                continue
            flaky_rate = min(passes, fails) / total
            if flaky_rate >= self.FLAKY_THRESHOLD:
                flaky_tests.append(tid)

        if flaky_tests:
            return [AIInsight(
                type="flaky_pattern",
                severity="warning",
                description=f"{len(flaky_tests)} flaky test tespit edildi",
                suggestion="Shared test data, timing veya environment sorunlarını araştırın. "
                           "Flaky testleri quarantine'e alın.",
                affected_tests=flaky_tests,
                confidence=0.85,
            )]
        return []

    def _detect_chronic_failures(self, history: list[dict]) -> list[AIInsight]:
        """Ardışık fail eden testleri tespit et."""
        consecutive_fails: dict[str, int] = {}

        for run in history[-10:]:
            current_fails = set()
            for record in run.get("records", []):
                if record.get("status") == "fail":
                    current_fails.add(record.get("test_id", ""))

            for tid in current_fails:
                consecutive_fails[tid] = consecutive_fails.get(tid, 0) + 1

            for tid in list(consecutive_fails):
                if tid not in current_fails:
                    consecutive_fails[tid] = 0

        chronic = [
            tid for tid, count in consecutive_fails.items()
            if count >= self.CHRONIC_FAIL_THRESHOLD
        ]

        if chronic:
            return [AIInsight(
                type="chronic_fail",
                severity="critical",
                description=f"{len(chronic)} test ardışık olarak fail ediyor",
                suggestion="Bu testler muhtemelen bir bug veya environment sorununa işaret ediyor. "
                           "Root cause analizi yapın.",
                affected_tests=chronic,
                confidence=0.95,
            )]
        return []

    def _detect_performance_drift(self, history: list[dict]) -> list[AIInsight]:
        """Test süresinde yavaşlama tespiti."""
        test_durations: dict[str, list[int]] = {}

        for run in history[-30:]:
            for record in run.get("records", []):
                tid = record.get("test_id", "")
                dur = record.get("duration_ms", 0)
                if tid and dur > 0:
                    test_durations.setdefault(tid, []).append(dur)

        drifting = []
        for tid, durations in test_durations.items():
            if len(durations) < 10:
                continue
            recent = durations[-5:]
            older = durations[:5]
            recent_avg = sum(recent) / len(recent)
            older_avg = sum(older) / len(older)
            if older_avg > 0 and (recent_avg - older_avg) / older_avg > 0.5:
                drifting.append(tid)

        if drifting:
            return [AIInsight(
                type="perf_drift",
                severity="warning",
                description=f"{len(drifting)} testte %50+ süre artışı tespit edildi",
                suggestion="Test environment, uygulamada performans regression veya "
                           "test data hacmi artışını kontrol edin.",
                affected_tests=drifting,
                confidence=0.75,
            )]
        return []

    def _detect_healing_patterns(self, history: list[dict]) -> list[AIInsight]:
        """Self-healing sıklığı ve pattern'ları analiz et."""
        healed_tests: dict[str, int] = {}

        for run in history[-20:]:
            for record in run.get("records", []):
                if record.get("status") == "healed":
                    tid = record.get("test_id", "")
                    healed_tests[tid] = healed_tests.get(tid, 0) + 1

        frequent_heals = [
            tid for tid, count in healed_tests.items() if count >= 3
        ]

        if frequent_heals:
            return [AIInsight(
                type="frequent_healing",
                severity="info",
                description=f"{len(frequent_heals)} test sık sık self-healing gerektiriyor",
                suggestion="Bu testlerin locator'ları ve test data'sı stabilize edilmeli. "
                           "Kalıcı düzeltme yapılmalı.",
                affected_tests=frequent_heals,
                confidence=0.80,
            )]
        return []

    def _detect_failure_correlation(self, history: list[dict]) -> list[AIInsight]:
        """Birlikte fail eden testleri tespit et (co-failure correlation)."""
        from collections import Counter

        pair_counts: Counter = Counter()
        fail_counts: Counter = Counter()

        for run in history[-20:]:
            failed_in_run = [
                r.get("test_id", "") for r in run.get("records", [])
                if r.get("status") == "fail"
            ]
            fail_counts.update(failed_in_run)
            for i, a in enumerate(failed_in_run):
                for b in failed_in_run[i + 1:]:
                    pair = tuple(sorted([a, b]))
                    pair_counts[pair] += 1

        correlated_groups: list[tuple[str, str]] = []
        for (a, b), count in pair_counts.most_common(10):
            min_fails = min(fail_counts[a], fail_counts[b])
            if min_fails >= 3 and count / min_fails >= 0.6:
                correlated_groups.append((a, b))

        if correlated_groups:
            affected = list(set(t for pair in correlated_groups for t in pair))
            return [AIInsight(
                type="failure_correlation",
                severity="info",
                description=f"{len(correlated_groups)} test çifti birlikte fail ediyor (ortak bağımlılık)",
                suggestion="Bu testler muhtemelen aynı bileşene/servise bağımlı. "
                           "Ortak setup veya paylaşılan modülü kontrol edin.",
                affected_tests=affected[:20],
                confidence=0.70,
            )]
        return []
