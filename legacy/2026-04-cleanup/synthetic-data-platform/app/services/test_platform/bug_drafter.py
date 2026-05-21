"""
BugDrafter — Otomatik Bug Taslağı Oluşturma

Başarısız test sonuçlarından JIRA / GitHub Issues / Azure DevOps
formatında bug raporları üretir.
"""
from __future__ import annotations
import uuid
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class BugSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class BugTracker(str, Enum):
    JIRA = "jira"
    GITHUB = "github"
    AZURE = "azure"
    GENERIC = "generic"


@dataclass
class BugReport:
    bug_id: str
    title: str
    severity: BugSeverity
    environment: str
    steps_to_reproduce: List[str]
    actual_result: str
    expected_result: str
    labels: List[str]
    formatted_output: Dict[str, str]   # tracker -> metin
    created_at: str


class BugDrafter:
    """
    Başarısız test sonuçlarından bug taslağı üretir.
    JIRA, GitHub Issues ve Azure DevOps formatlarını destekler.
    """

    def draft_from_result(
        self,
        test_result,
        environment: str = "staging",
        tracker: BugTracker = BugTracker.GENERIC,
    ) -> BugReport:
        """
        Tek test sonucundan bug raporu oluşturur.

        Args:
            test_result: TestResult nesnesi
            environment: Test ortamı adı
            tracker: Hedef bug tracker

        Returns:
            BugReport
        """
        tc_id = getattr(test_result, "test_case_id", "TC-UNKNOWN")
        error = getattr(test_result, "error_message", "") or "Bilinmeyen hata"
        output = getattr(test_result, "output", "")
        duration = getattr(test_result, "duration_seconds", 0)

        severity = self._infer_severity(error, tc_id)
        title = f"[{severity.value.upper()}] {tc_id}: {error[:80]}"

        steps = [
            f"Test ortamı: {environment}",
            f"Test case: {tc_id}",
            "Testi çalıştır",
            "Sonucu gözlemle",
        ]

        formatted = {
            BugTracker.JIRA.value: self._jira_format(title, error, output, steps, severity),
            BugTracker.GITHUB.value: self._github_format(title, error, output, steps, severity),
            BugTracker.AZURE.value: self._azure_format(title, error, output, steps, severity),
            BugTracker.GENERIC.value: self._generic_format(title, error, steps),
        }

        return BugReport(
            bug_id=f"BUG-{str(uuid.uuid4())[:6].upper()}",
            title=title,
            severity=severity,
            environment=environment,
            steps_to_reproduce=steps,
            actual_result=error[:200],
            expected_result="Test başarıyla tamamlanmalıydı.",
            labels=["automated-test", "regression", severity.value],
            formatted_output=formatted,
            created_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        )

    def draft_bulk(self, failed_results: list, environment: str = "staging") -> List[BugReport]:
        """Birden fazla başarısız test için toplu bug raporu üretir."""
        return [self.draft_from_result(r, environment) for r in failed_results]

    def _infer_severity(self, error: str, tc_id: str) -> BugSeverity:
        error_lower = error.lower()
        if any(k in error_lower for k in ["crash", "null pointer", "500", "database", "security"]):
            return BugSeverity.CRITICAL
        if any(k in error_lower for k in ["assertion", "not found", "timeout", "auth"]):
            return BugSeverity.HIGH
        if "smoke" in tc_id.lower() or "critical" in tc_id.lower():
            return BugSeverity.CRITICAL
        return BugSeverity.MEDIUM

    def _jira_format(self, title, error, output, steps, severity) -> str:
        return f"""**Özet:** {title}

**Şiddet:** {severity.value}
**Tür:** Hata
**Etiketler:** automated-test, regression

**Yeniden Üretim Adımları:**
{chr(10).join(f'# {s}' for s in steps)}

**Gerçekleşen Sonuç:**
{error}

**Beklenen Sonuç:**
Test başarıyla tamamlanmalıydı.

**Test Çıktısı:**
{{code}}
{output[:500]}
{{code}}
"""

    def _github_format(self, title, error, output, steps, severity) -> str:
        return f"""## {title}

**Şiddet:** `{severity.value}`

### Yeniden Üretim Adımları
{chr(10).join(f'{i+1}. {s}' for i, s in enumerate(steps))}

### Gerçekleşen Sonuç
```
{error}
```

### Beklenen Sonuç
Test başarıyla tamamlanmalıydı.

**Etiketler:** bug, {severity.value}
"""

    def _azure_format(self, title, error, output, steps, severity) -> str:
        return f"""Title: {title}
Severity: {severity.value}
Type: Bug

Repro Steps:
{chr(10).join(f'- {s}' for s in steps)}

System Info:
Actual: {error}
Expected: Test passed

Additional Info:
{output[:200]}
"""

    def _generic_format(self, title, error, steps) -> str:
        return f"BUG: {title}\nAdımlar: {'; '.join(steps)}\nHata: {error}"
