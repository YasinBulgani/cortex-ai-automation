"""
ZAPAIAnalyzer — OWASP ZAP sonuçlarını AI ile analiz eder.

Yetenekler:
  - ZAP JSON raporunu parse etme
  - AI ile false positive tespiti
  - OWASP Top 10 eşleme
  - Önceliklendirilmiş güvenlik raporu
  - CI/CD entegrasyonu için SARIF çıktısı
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from core.ai_security.vulnerability_analyzer import SecurityFinding, SecurityReport
from services.prompt_loader import get_engine_prompt

logger = logging.getLogger(__name__)
SECURITY_ANALYZER_PROMPT = get_engine_prompt("security_analyzer")


@dataclass
class ZAPFinding:
    alert: str
    risk: str
    confidence: str
    url: str
    description: str
    solution: str
    cweid: str = ""
    wascid: str = ""
    ai_analysis: str = ""
    false_positive_prob: float = 0.0


class ZAPAIAnalyzer:
    """OWASP ZAP rapor analizörü + AI zenginleştirme."""

    def parse_report(self, report_path: str | Path) -> list[ZAPFinding]:
        """ZAP JSON raporunu parse et."""
        path = Path(report_path)
        if not path.exists():
            logger.error("ZAP report not found: %s", path)
            return []

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        findings = []
        sites = data.get("site", [])
        if isinstance(sites, dict):
            sites = [sites]

        for site in sites:
            for alert in site.get("alerts", []):
                instances = alert.get("instances", [])
                url = instances[0].get("uri", "") if instances else ""
                findings.append(ZAPFinding(
                    alert=alert.get("alert", ""),
                    risk=alert.get("riskdesc", "").split(" ")[0] if alert.get("riskdesc") else "Info",
                    confidence=alert.get("confidence", ""),
                    url=url,
                    description=alert.get("desc", ""),
                    solution=alert.get("solution", ""),
                    cweid=str(alert.get("cweid", "")),
                    wascid=str(alert.get("wascid", "")),
                ))

        return findings

    def analyze_with_ai(self, findings: list[ZAPFinding]) -> list[ZAPFinding]:
        """LLM ile bulguları zenginleştir: false positive tespiti + önceliklendirme."""
        if not findings:
            return findings

        from core.llm_bridge import call_llm

        batch = [
            {
                "alert": f.alert,
                "risk": f.risk,
                "url": f.url,
                "description": f.description[:200],
                "cweid": f.cweid,
            }
            for f in findings[:30]
        ]

        prompt = (
            f"{SECURITY_ANALYZER_PROMPT}\n\n"
            "OWASP ZAP güvenlik bulgularını analiz et:\n\n"
            f"{json.dumps(batch, indent=2, ensure_ascii=False)}\n\n"
            "Her bulgu için:\n"
            "1. Gerçek risk seviyesi (actual_risk)\n"
            "2. False positive olasılığı (0-1)\n"
            "3. Kısa analiz\n"
            "4. OWASP Top 10 2024 kategorisi\n\n"
            "JSON array döndür."
        )

        try:
            raw = call_llm(
                [
                    {"role": "system", "content": SECURITY_ANALYZER_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )
            if "```" in raw:
                lines = raw.split("\n")
                raw = "\n".join(ln for ln in lines if not ln.strip().startswith("```"))
            enriched = json.loads(raw)

            for i, enr in enumerate(enriched):
                if i < len(findings):
                    findings[i].ai_analysis = enr.get("analysis", "")
                    findings[i].false_positive_prob = enr.get("false_positive_probability", 0.0)
        except Exception as e:
            logger.error("AI ZAP analysis failed: %s", e)

        return findings

    def to_security_report(self, findings: list[ZAPFinding], url: str) -> SecurityReport:
        """ZAP bulgularını standart SecurityReport'a dönüştür."""
        report = SecurityReport(target_url=url, scan_type="zap_dast")
        for f in findings:
            risk_map = {"high": "high", "medium": "medium", "low": "low", "informational": "info"}
            report.findings.append(SecurityFinding(
                title=f.alert,
                severity=risk_map.get(f.risk.lower(), "info"),
                category="dast",
                description=f.description,
                recommendation=f.solution,
                owasp_ref=f"CWE-{f.cweid}" if f.cweid else "",
            ))
        return report

    def to_sarif(self, findings: list[ZAPFinding]) -> dict:
        """SARIF format çıktısı üret (CI/CD entegrasyonu için)."""
        results = []
        for f in findings:
            results.append({
                "ruleId": f"ZAP-{f.cweid}" if f.cweid else "ZAP-UNKNOWN",
                "level": {"High": "error", "Medium": "warning", "Low": "note"}.get(f.risk, "none"),
                "message": {"text": f.alert},
                "locations": [{
                    "physicalLocation": {
                        "artifactLocation": {"uri": f.url},
                    }
                }],
            })
        return {
            "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
            "version": "2.1.0",
            "runs": [{
                "tool": {"driver": {"name": "OWASP-ZAP-AI", "version": "1.0"}},
                "results": results,
            }],
        }
