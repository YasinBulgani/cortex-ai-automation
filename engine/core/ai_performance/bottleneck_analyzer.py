"""
BottleneckAnalyzer — Performans test sonuçlarını AI ile analiz ederek darboğaz tespiti yapar.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Bottleneck:
    component: str       # api, database, network, frontend, auth
    metric: str
    value: float
    expected: float
    severity: str        # critical, warning, info
    description: str
    recommendation: str


class BottleneckAnalyzer:
    """Performans darboğaz analiz motoru."""

    def analyze(self, results: dict) -> list[Bottleneck]:
        """k6/JMeter sonuçlarından darboğaz tespiti."""
        bottlenecks = []

        http_duration = results.get("http_req_duration", {})
        if isinstance(http_duration, dict):
            p95 = http_duration.get("p(95)", 0)
            if p95 > 2000:
                bottlenecks.append(Bottleneck(
                    component="api",
                    metric="http_req_duration_p95",
                    value=p95,
                    expected=500,
                    severity="critical",
                    description=f"API p95 response time {p95}ms (hedef: <500ms)",
                    recommendation="API endpoint optimizasyonu, DB query index, caching",
                ))
            elif p95 > 500:
                bottlenecks.append(Bottleneck(
                    component="api",
                    metric="http_req_duration_p95",
                    value=p95,
                    expected=500,
                    severity="warning",
                    description=f"API p95 response time {p95}ms (hedef: <500ms)",
                    recommendation="Slow query analizi, connection pooling kontrolü",
                ))

        error_rate = results.get("http_req_failed", {})
        if isinstance(error_rate, dict):
            rate = error_rate.get("rate", 0)
            if rate > 0.05:
                bottlenecks.append(Bottleneck(
                    component="api",
                    metric="error_rate",
                    value=rate,
                    expected=0.01,
                    severity="critical",
                    description=f"Error rate %{rate*100:.1f} (hedef: <%1)",
                    recommendation="Hata loglarını incele, rate limiting kontrol et",
                ))

        vus_max = results.get("vus_max", 0)
        if vus_max and isinstance(http_duration, dict):
            p95 = http_duration.get("p(95)", 0)
            if vus_max > 100 and p95 > 1000:
                bottlenecks.append(Bottleneck(
                    component="database",
                    metric="concurrent_load",
                    value=vus_max,
                    expected=500,
                    severity="warning",
                    description=f"{vus_max} VU'da {p95}ms response — olası DB darboğazı",
                    recommendation="Connection pool boyutunu artır, read replica ekle",
                ))

        return bottlenecks

    def analyze_with_ai(self, results: dict) -> list[Bottleneck]:
        """LLM ile derin performans analizi."""
        from core.llm_bridge import call_llm

        prompt = (
            "Bu performans test sonuçlarını analiz et:\n\n"
            f"{json.dumps(results, indent=2)}\n\n"
            "Darboğazları tespit et. JSON array döndür:\n"
            '[{"component":"...", "metric":"...", "value":0, "expected":0, '
            '"severity":"...", "description":"...", "recommendation":"..."}]'
        )

        try:
            raw = call_llm(
                [
                    {"role": "system", "content": "Kıdemli performans mühendisisın."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )
            if "```" in raw:
                lines = raw.split("\n")
                raw = "\n".join(ln for ln in lines if not ln.strip().startswith("```"))
            items = json.loads(raw)
            return [
                Bottleneck(
                    component=item.get("component", "unknown"),
                    metric=item.get("metric", ""),
                    value=item.get("value", 0),
                    expected=item.get("expected", 0),
                    severity=item.get("severity", "info"),
                    description=item.get("description", ""),
                    recommendation=item.get("recommendation", ""),
                )
                for item in items
            ]
        except Exception as e:
            logger.error("AI bottleneck analysis failed: %s", e)
            return self.analyze(results)
