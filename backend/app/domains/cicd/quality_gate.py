"""Quality Gate — deployment öncesi geç/kal mekanizması.

Kullanım:
  gate = QualityGate(name="Production Gate")
  gate.add_check(PassRateCheck(min_pct=80))
  gate.add_check(MaxFailuresCheck(max_count=5))
  gate.add_check(DurationCheck(max_seconds=600))
  result = gate.evaluate(execution_summary)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CheckResult:
    name: str
    passed: bool
    value: Any
    threshold: Any
    message: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "passed": self.passed,
            "value": self.value,
            "threshold": self.threshold,
            "message": self.message,
        }


class BaseCheck(ABC):
    name: str = "check"

    @abstractmethod
    def run(self, summary: dict) -> CheckResult:
        """Alt sınıflar bu metodu override etmek zorundadır."""


class PassRateCheck(BaseCheck):
    """Geçme oranı minimum eşiği aşmalı."""
    name = "Geçme Oranı"

    def __init__(self, min_pct: float = 80.0):
        self.min_pct = min_pct

    def run(self, summary: dict) -> CheckResult:
        total = summary.get("total", 0)
        passed = summary.get("passed", 0)
        pct = round(passed / total * 100, 1) if total else 0.0
        ok = pct >= self.min_pct
        return CheckResult(
            name=self.name,
            passed=ok,
            value=f"{pct}%",
            threshold=f"{self.min_pct}%",
            message="" if ok else f"Geçme oranı {pct}% — minimum {self.min_pct}% bekleniyor",
        )


class MaxFailuresCheck(BaseCheck):
    """Başarısız test sayısı limiti aşmamalı."""
    name = "Maksimum Başarısız Test"

    def __init__(self, max_count: int = 5):
        self.max_count = max_count

    def run(self, summary: dict) -> CheckResult:
        failed = summary.get("failed", 0)
        ok = failed <= self.max_count
        return CheckResult(
            name=self.name,
            passed=ok,
            value=failed,
            threshold=self.max_count,
            message="" if ok else f"{failed} test başarısız — maksimum {self.max_count} izin veriliyor",
        )


class DurationCheck(BaseCheck):
    """Toplam koşu süresi limiti aşmamalı."""
    name = "Koşu Süresi"

    def __init__(self, max_seconds: float = 600.0):
        self.max_seconds = max_seconds

    def run(self, summary: dict) -> CheckResult:
        duration = summary.get("duration_s", 0.0)
        ok = duration <= self.max_seconds
        return CheckResult(
            name=self.name,
            passed=ok,
            value=f"{duration:.0f}s",
            threshold=f"{self.max_seconds:.0f}s",
            message="" if ok else f"Koşu süresi {duration:.0f}s — maksimum {self.max_seconds:.0f}s",
        )


class NoNewFlakiesCheck(BaseCheck):
    """Yeni flaky test eklenmemeli."""
    name = "Yeni Flaky Test"

    def __init__(self, max_new: int = 0):
        self.max_new = max_new

    def run(self, summary: dict) -> CheckResult:
        new_flaky = summary.get("new_flaky_count", 0)
        ok = new_flaky <= self.max_new
        return CheckResult(
            name=self.name,
            passed=ok,
            value=new_flaky,
            threshold=self.max_new,
            message="" if ok else f"{new_flaky} yeni flaky test tespit edildi",
        )


class CoverageCheck(BaseCheck):
    """Kod kapsam yüzdesi eşiği aşmalı."""
    name = "Kod Kapsamı"

    def __init__(self, min_pct: float = 70.0):
        self.min_pct = min_pct

    def run(self, summary: dict) -> CheckResult:
        coverage = summary.get("coverage_pct", None)
        if coverage is None:
            return CheckResult(name=self.name, passed=True, value="N/A", threshold=f"{self.min_pct}%",
                               message="Kapsam verisi yok, kontrol atlandı")
        ok = float(coverage) >= self.min_pct
        return CheckResult(
            name=self.name,
            passed=ok,
            value=f"{coverage}%",
            threshold=f"{self.min_pct}%",
            message="" if ok else f"Kapsam {coverage}% — minimum {self.min_pct}% bekleniyor",
        )


@dataclass
class GateResult:
    gate_name: str
    result: str          # "passed" | "failed"
    checks: list[CheckResult] = field(default_factory=list)
    blocking_messages: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "gate_name": self.gate_name,
            "result": self.result,
            "passed": self.result == "passed",
            "checks": [c.to_dict() for c in self.checks],
            "blocking_messages": self.blocking_messages,
        }


class QualityGate:
    def __init__(self, name: str = "Default Gate"):
        self.name = name
        self._checks: list[BaseCheck] = []

    def add_check(self, check: BaseCheck) -> "QualityGate":
        self._checks.append(check)
        return self

    def evaluate(self, summary: dict) -> GateResult:
        results = [c.run(summary) for c in self._checks]
        failed_checks = [r for r in results if not r.passed]
        overall = "passed" if not failed_checks else "failed"
        return GateResult(
            gate_name=self.name,
            result=overall,
            checks=results,
            blocking_messages=[r.message for r in failed_checks if r.message],
        )


# ── Factory — config'den gate oluştur ────────────────────────────────────────

def build_gate_from_config(config: dict) -> QualityGate:
    """API body veya DB config'inden QualityGate nesnesi oluşturur.

    config örneği:
      {
        "name": "Production Gate",
        "min_pass_rate": 85,
        "max_failures": 3,
        "max_duration_s": 300,
        "max_new_flakies": 0,
        "min_coverage_pct": 75
      }
    """
    gate = QualityGate(name=config.get("name", "Default Gate"))

    if "min_pass_rate" in config:
        gate.add_check(PassRateCheck(min_pct=float(config["min_pass_rate"])))
    if "max_failures" in config:
        gate.add_check(MaxFailuresCheck(max_count=int(config["max_failures"])))
    if "max_duration_s" in config:
        gate.add_check(DurationCheck(max_seconds=float(config["max_duration_s"])))
    if "max_new_flakies" in config:
        gate.add_check(NoNewFlakiesCheck(max_new=int(config["max_new_flakies"])))
    if "min_coverage_pct" in config:
        gate.add_check(CoverageCheck(min_pct=float(config["min_coverage_pct"])))

    return gate
