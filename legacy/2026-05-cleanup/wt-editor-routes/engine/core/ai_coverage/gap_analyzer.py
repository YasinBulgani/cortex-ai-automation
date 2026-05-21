"""
CoverageGapAnalyzer — Test kapsama boşluklarını tespit eder.

Analiz boyutları:
  - Endpoint coverage: Test edilmemiş API endpoint'leri
  - Page coverage: Test edilmemiş UI sayfaları
  - Scenario coverage: Eksik edge case / negatif senaryolar
  - Data coverage: Test edilmemiş veri sınıfları (boundary, null, max)
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class CoverageGap:
    area: str           # api, ui, data, scenario
    target: str         # endpoint path, page name, vb.
    description: str
    severity: str       # critical, high, medium, low
    suggested_test: str = ""


@dataclass
class CoverageReport:
    total_targets: int = 0
    covered_targets: int = 0
    gaps: list[CoverageGap] = field(default_factory=list)

    @property
    def coverage_pct(self) -> float:
        if self.total_targets == 0:
            return 0.0
        return round((self.covered_targets / self.total_targets) * 100, 1)

    def to_dict(self) -> dict:
        return {
            "total_targets": self.total_targets,
            "covered_targets": self.covered_targets,
            "coverage_pct": self.coverage_pct,
            "gap_count": len(self.gaps),
            "gaps_by_severity": {
                sev: sum(1 for g in self.gaps if g.severity == sev)
                for sev in ["critical", "high", "medium", "low"]
            },
            "gaps": [
                {
                    "area": g.area,
                    "target": g.target,
                    "description": g.description,
                    "severity": g.severity,
                    "suggested_test": g.suggested_test,
                }
                for g in self.gaps
            ],
        }


class CoverageGapAnalyzer:
    """Test kapsama boşluk analiz motoru."""

    def analyze_api_coverage(
        self,
        openapi_spec: dict,
        existing_tests: list[str],
    ) -> CoverageReport:
        """OpenAPI spec ile mevcut testleri karşılaştırarak API coverage analizi."""
        report = CoverageReport()
        paths = openapi_spec.get("paths", {})

        all_endpoints = []
        for path, methods in paths.items():
            for method in methods:
                if method.upper() in ("GET", "POST", "PUT", "DELETE", "PATCH"):
                    all_endpoints.append(f"{method.upper()} {path}")

        report.total_targets = len(all_endpoints)
        tests_text = " ".join(existing_tests)

        for ep in all_endpoints:
            method, path = ep.split(" ", 1)
            path_parts = path.strip("/").replace("/", "_").replace("{", "").replace("}", "")
            if _is_covered(path, tests_text) or _is_covered(path_parts, tests_text):
                report.covered_targets += 1
            else:
                severity = "high" if method in ("POST", "DELETE") else "medium"
                report.gaps.append(CoverageGap(
                    area="api",
                    target=ep,
                    description=f"API endpoint {ep} için test bulunamadı",
                    severity=severity,
                    suggested_test=f"test_{method.lower()}_{path_parts}",
                ))

        return report

    def analyze_ui_coverage(
        self,
        pages: list[dict],
        existing_tests: list[str],
    ) -> CoverageReport:
        """UI sayfalarının test kapsamını analiz et."""
        report = CoverageReport(total_targets=len(pages))
        tests_text = " ".join(existing_tests)

        for page in pages:
            name = page.get("name", "")
            path = page.get("path", "")
            if _is_covered(name, tests_text) or _is_covered(path, tests_text):
                report.covered_targets += 1
            else:
                report.gaps.append(CoverageGap(
                    area="ui",
                    target=f"{name} ({path})",
                    description=f"UI sayfası '{name}' için E2E test bulunamadı",
                    severity="high" if page.get("critical", False) else "medium",
                ))

        return report

    def analyze_with_ai(
        self,
        test_files_content: str,
        application_context: str,
    ) -> list[CoverageGap]:
        """LLM ile derin kapsama analizi yap."""
        from core.llm_bridge import call_llm

        prompt = (
            "Mevcut test dosyalarını analiz et ve eksik kapsama alanlarını bul.\n\n"
            f"TEST DOSYALARI:\n{test_files_content[:6000]}\n\n"
            f"UYGULAMA BİLGİSİ:\n{application_context[:3000]}\n\n"
            "Eksik test senaryolarını JSON array olarak döndür:\n"
            '[{"area":"...", "target":"...", "description":"...", "severity":"...", '
            '"suggested_test":"..."}]'
        )

        try:
            raw = call_llm(
                [
                    {"role": "system", "content": "Sen kıdemli bir test analiz uzmanısın."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
            )
            raw = _clean_json(raw)
            items = json.loads(raw)
            return [
                CoverageGap(
                    area=item.get("area", "unknown"),
                    target=item.get("target", ""),
                    description=item.get("description", ""),
                    severity=item.get("severity", "medium"),
                    suggested_test=item.get("suggested_test", ""),
                )
                for item in items
            ]
        except Exception as e:
            logger.error("AI coverage analysis failed: %s", e)
            return []


def _is_covered(target: str, tests_text: str) -> bool:
    """Hedefin test metinlerinde geçip geçmediğini kontrol et."""
    target_clean = target.lower().strip("/").replace("-", "_").replace("/", "_")
    return target_clean in tests_text.lower()


def _clean_json(raw: str) -> str:
    if "```" in raw:
        lines = raw.split("\n")
        return "\n".join(ln for ln in lines if not ln.strip().startswith("```"))
    return raw
