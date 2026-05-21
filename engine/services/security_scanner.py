"""
Güvenlik tarama entegrasyonu.

OWASP ZAP CLI üzerinden güvenlik taraması başlatır ve sonuçları parse eder.
Shannon otonom pentester entegrasyonu için alt yapı hazırlar.
"""
from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent

_CWE_INJECTION = {"89", "78", "90", "91"}
_CWE_XSS = {"79", "80"}
_CWE_AUTH = {"287", "306", "862"}


@dataclass
class SecurityFinding:
    severity: str   # "critical" | "high" | "medium" | "low" | "info"
    category: str   # "injection" | "xss" | "auth" | "config" | "info_disclosure"
    title: str
    description: str
    url: str
    evidence: str
    cwe_id: str

    def to_dict(self) -> dict:
        return {
            "severity": self.severity,
            "category": self.category,
            "title": self.title,
            "description": self.description[:300],
            "url": self.url,
            "cwe_id": self.cwe_id,
        }


class SecurityScanner:
    """ZAP tabanlı güvenlik tarama entegrasyonu."""

    def __init__(self, zap_path: str = "zap-cli", target_url: str = "http://127.0.0.1:8000"):
        self.zap_path = zap_path
        self.target_url = target_url

    def quick_scan(self) -> list[SecurityFinding]:
        """Hızlı güvenlik taraması (spider + active scan)."""
        self._run_cmd(["spider", self.target_url], timeout=300)
        self._run_cmd(["active-scan", self.target_url], timeout=600)
        return self._get_alerts()

    def api_scan(self, openapi_spec_url: str) -> list[SecurityFinding]:
        """OpenAPI spec tabanlı API güvenlik taraması."""
        result = self._run_cmd(
            ["openapi", openapi_spec_url, "-t", self.target_url, "-f", "json"],
            timeout=600,
        )
        return self._parse_alerts(result.stdout) if result else []

    def save_report(self, findings: list[SecurityFinding], output: str | Path = "reports/security-findings.json"):
        try:
            out = _REPO_ROOT / output
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps([f.to_dict() for f in findings], indent=2, ensure_ascii=False))
        except OSError as exc:
            logger.warning("Güvenlik raporu yazılamadı: %s", exc)

    # ── internal ────────────────────────────────────────────────────────────

    def _run_cmd(self, args: list[str], timeout: int = 300) -> subprocess.CompletedProcess | None:
        try:
            return subprocess.run(
                [self.zap_path, *args],
                capture_output=True, text=True, timeout=timeout,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return None

    def _get_alerts(self) -> list[SecurityFinding]:
        result = self._run_cmd(["alerts", "-f", "json"])
        if result and result.stdout:
            return self._parse_alerts(result.stdout)
        return []

    @staticmethod
    def _parse_alerts(json_output: str) -> list[SecurityFinding]:
        try:
            alerts = json.loads(json_output)
        except json.JSONDecodeError:
            return []

        findings: list[SecurityFinding] = []
        for alert in alerts if isinstance(alerts, list) else []:
            cwe = str(alert.get("cweid", ""))
            if cwe in _CWE_INJECTION:
                category = "injection"
            elif cwe in _CWE_XSS:
                category = "xss"
            elif cwe in _CWE_AUTH:
                category = "auth"
            else:
                category = "config"

            risk = alert.get("risk", "Informational")
            severity_map = {"Critical": "critical", "High": "high", "Medium": "medium", "Low": "low", "Informational": "info"}
            severity = severity_map.get(risk, "info")

            findings.append(SecurityFinding(
                severity=severity,
                category=category,
                title=alert.get("name", "Bilinmeyen"),
                description=alert.get("description", ""),
                url=alert.get("url", ""),
                evidence=alert.get("evidence", ""),
                cwe_id=cwe,
            ))
        return findings
