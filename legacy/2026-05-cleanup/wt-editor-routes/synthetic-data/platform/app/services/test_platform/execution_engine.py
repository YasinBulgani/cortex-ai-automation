"""
ExecutionEngine — Test Çalıştırma Motoru

Test case'leri veya script'leri sıralı/paralel çalıştırır,
sonuçları toplar ve özet rapor üretir.
"""
from __future__ import annotations
import asyncio
import subprocess
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class TestResult:
    test_case_id: str
    status: ExecutionStatus
    duration_seconds: float
    output: str
    error_message: Optional[str] = None
    screenshot_path: Optional[str] = None
    retry_count: int = 0


@dataclass
class ExecutionSummary:
    execution_id: str
    total: int
    passed: int
    failed: int
    skipped: int
    error: int
    pass_rate: float
    total_duration_seconds: float
    results: List[TestResult]
    started_at: str
    finished_at: str


class ExecutionEngine:
    """
    Test script'lerini çalıştırır.

    Desteklenen modlar:
      - Simüle: Gerçek framework kurulu değilse sonuç simüle eder
      - Gerçek: pytest subprocess ile çalıştırır
      - Paralel: asyncio ile eş zamanlı çalıştırır
    """

    def __init__(self, max_workers: int = 4, retry_on_failure: int = 1):
        self.max_workers = max_workers
        self.retry_on_failure = retry_on_failure

    def run_suite(self, test_cases: list, mode: str = "simulate") -> ExecutionSummary:
        """
        Test suite'i çalıştırır.

        Args:
            test_cases: TestCase nesneleri veya script kod stringlari
            mode: 'simulate' | 'real'

        Returns:
            ExecutionSummary
        """
        execution_id = str(uuid.uuid4())[:8]
        start = time.time()
        started_at = time.strftime("%Y-%m-%dT%H:%M:%S")
        results: List[TestResult] = []

        for tc in test_cases:
            tc_id = getattr(tc, "id", str(tc))[:20]
            if mode == "simulate":
                result = self._simulate_run(tc_id)
            else:
                result = self._real_run(tc)
            results.append(result)

        total_duration = time.time() - start
        passed = sum(1 for r in results if r.status == ExecutionStatus.PASSED)
        failed = sum(1 for r in results if r.status == ExecutionStatus.FAILED)
        skipped = sum(1 for r in results if r.status == ExecutionStatus.SKIPPED)
        errors = sum(1 for r in results if r.status == ExecutionStatus.ERROR)
        total = len(results)

        return ExecutionSummary(
            execution_id=execution_id,
            total=total,
            passed=passed,
            failed=failed,
            skipped=skipped,
            error=errors,
            pass_rate=round(passed / total, 4) if total > 0 else 0.0,
            total_duration_seconds=round(total_duration, 2),
            results=results,
            started_at=started_at,
            finished_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        )

    def run_script(self, script_code: str, timeout: int = 60) -> TestResult:
        """Tek bir Python test scriptini subprocess ile çalıştırır."""
        tc_id = "SCRIPT-" + str(uuid.uuid4())[:6]
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write(script_code)
            tmp_path = f.name

        start = time.time()
        try:
            proc = subprocess.run(
                ["python", "-m", "pytest", tmp_path, "-v", "--tb=short"],
                capture_output=True, text=True, timeout=timeout
            )
            duration = time.time() - start
            status = ExecutionStatus.PASSED if proc.returncode == 0 else ExecutionStatus.FAILED
            return TestResult(
                test_case_id=tc_id,
                status=status,
                duration_seconds=round(duration, 2),
                output=proc.stdout[-2000:],
                error_message=proc.stderr[-500:] if proc.returncode != 0 else None,
            )
        except subprocess.TimeoutExpired:
            return TestResult(
                test_case_id=tc_id, status=ExecutionStatus.ERROR,
                duration_seconds=timeout, output="",
                error_message="Zaman aşımı",
            )
        except Exception as e:
            return TestResult(
                test_case_id=tc_id, status=ExecutionStatus.ERROR,
                duration_seconds=0, output="", error_message=str(e),
            )
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def _simulate_run(self, tc_id: str) -> TestResult:
        """Gerçek çalıştırma olmadan simüle edilmiş sonuç üretir."""
        import random
        # %85 başarı oranı simülasyonu
        roll = random.random()
        if roll < 0.85:
            status = ExecutionStatus.PASSED
            output = f"PASSED: {tc_id} — tüm adımlar başarıyla tamamlandı."
            err = None
        elif roll < 0.93:
            status = ExecutionStatus.FAILED
            output = f"FAILED: {tc_id}"
            err = "AssertionError: Beklenen değer alınamadı."
        else:
            status = ExecutionStatus.SKIPPED
            output = f"SKIPPED: {tc_id} — bağımlılık eksik."
            err = None

        return TestResult(
            test_case_id=tc_id,
            status=status,
            duration_seconds=round(random.uniform(0.5, 3.0), 2),
            output=output,
            error_message=err,
        )

    def _real_run(self, tc) -> TestResult:
        """Script kodu varsa gerçek çalıştırma, yoksa simülasyon."""
        code = getattr(tc, "code", None)
        if code:
            return self.run_script(code)
        return self._simulate_run(getattr(tc, "id", "TC"))
