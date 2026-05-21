"""
bgts_runner.py — TestwrightAI E2E Test Runner (engine/runner.py wrapper'ı)

Mevcut runner.py'yi DEĞİŞTİRMEDEN, TestwrightAI'a özgü test koşum senaryolarını
yönetir: smoke, regression, API, paralel, retry ve rapor üretimi.

Not: Dosya adı (bgts_runner.py) geriye uyumluluk ve CI pipeline'lara etki etmemek
için korunmuştur. Komut satırı adı sonraki refactor fazında değiştirilecektir.

Kullanım:
  python bgts_runner.py --smoke
  python bgts_runner.py --regression --parallel 4
  python bgts_runner.py --feature login
  python bgts_runner.py --all --retry 2 --report
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from config.settings import settings
from config.test_config import test_config

console = Console()

ALLURE_RESULTS = Path(test_config.ALLURE_RESULTS_DIR)
ALLURE_REPORT = settings.ALLURE_REPORT_DIR

FEATURE_MARKER_MAP = {
    "login": "login",
    "projects": "projects",
    "scenarios": "scenarios",
    "approvals": "approvals",
    "executions": "executions",
    "analytics": "analytics",
    "flows": "flows",
    "requirements": "requirements",
    "coverage": "coverage",
    "schedules": "schedules",
    "test_data": "test_data",
    "integrations": "integrations",
    "api_tests": "api_tests",
    "members": "members",
    "dashboard": "dashboard",
}


@dataclass
class TestResult:
    """Tek bir test koşusunun özet sonucu."""
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    duration_seconds: float = 0.0
    return_code: int = 0
    failures: list[dict] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    marker: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return round(self.passed / self.total * 100, 2)

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "errors": self.errors,
            "duration_seconds": self.duration_seconds,
            "success_rate": self.success_rate,
            "return_code": self.return_code,
            "failures": self.failures,
            "timestamp": self.timestamp,
            "marker": self.marker,
        }


class TestwrightAIRunner:
    """TestwrightAI projesine özgü test çalıştırıcısı."""

    def __init__(
        self,
        progress_callback: Optional[Callable[[str, float], None]] = None,
    ):
        self.progress_callback = progress_callback
        self._last_result: Optional[TestResult] = None

    def _notify(self, message: str, pct: float = 0.0) -> None:
        if self.progress_callback:
            self.progress_callback(message, pct)

    def _build_pytest_cmd(
        self,
        markers: str | None = None,
        test_path: str = "tests/",
        extra_args: list[str] | None = None,
        parallel_workers: int = 0,
        junit_xml: str | None = None,
    ) -> list[str]:
        cmd = [
            sys.executable, "-m", "pytest",
            test_path,
            f"--alluredir={ALLURE_RESULTS}",
            "--tb=short",
            "-v",
            "--color=yes",
            "--import-mode=importlib",
        ]
        if markers:
            cmd += ["-m", markers]
        if parallel_workers > 1:
            cmd += ["-n", str(parallel_workers), "--dist=loadfile"]
        if junit_xml:
            cmd += [f"--junitxml={junit_xml}"]
        if extra_args:
            cmd += extra_args
        return cmd

    def _run(
        self,
        markers: str | None = None,
        test_path: str = "tests/",
        extra_args: list[str] | None = None,
        parallel_workers: int = 0,
        label: str = "test",
    ) -> TestResult:
        ALLURE_RESULTS.mkdir(parents=True, exist_ok=True)

        junit_path = ROOT / "reports" / f"testwright-ai-{label}-{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
        junit_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = self._build_pytest_cmd(
            markers=markers,
            test_path=test_path,
            extra_args=extra_args,
            parallel_workers=parallel_workers,
            junit_xml=str(junit_path),
        )

        self._notify(f"{label} testleri başlıyor...", 0.0)
        start = time.time()

        proc = subprocess.run(cmd, cwd=str(ROOT))

        elapsed = time.time() - start
        self._notify(f"{label} testleri tamamlandı.", 100.0)

        result = TestResult(
            return_code=proc.returncode,
            duration_seconds=round(elapsed, 2),
            marker=markers or "all",
        )

        if junit_path.exists():
            self._parse_junit(junit_path, result)

        self._last_result = result
        return result

    def _parse_junit(self, xml_path: Path, result: TestResult) -> None:
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            if root.tag == "testsuites":
                suites = root.findall("testsuite")
            else:
                suites = [root]

            for suite in suites:
                result.total += int(suite.get("tests", 0))
                result.failures += self._extract_failures(suite)
                result.errors += int(suite.get("errors", 0))
                result.skipped += int(suite.get("skipped", 0))

            result.failed = len(result.failures)
            result.passed = result.total - result.failed - result.skipped - result.errors
            if result.passed < 0:
                result.passed = 0
        except Exception:
            pass

    @staticmethod
    def _extract_failures(suite_elem: ET.Element) -> list[dict]:
        failures = []
        for tc in suite_elem.iter("testcase"):
            fail_el = tc.find("failure")
            err_el = tc.find("error")
            el = fail_el or err_el
            if el is not None:
                failures.append({
                    "test": tc.get("classname", "") + "::" + tc.get("name", ""),
                    "message": el.get("message", ""),
                    "type": el.get("type", ""),
                    "text": (el.text or "")[:500],
                })
        return failures

    # ── Kamu API'leri ─────────────────────────────────────────

    def run_smoke(self) -> TestResult:
        console.print(Panel("[bold green]TestwrightAI Smoke Testleri[/bold green]", border_style="green"))
        return self._run(markers="smoke", label="smoke")

    def run_regression(self) -> TestResult:
        console.print(Panel("[bold blue]TestwrightAI Regresyon Testleri[/bold blue]", border_style="blue"))
        return self._run(markers="regression", label="regression")

    def run_by_feature(self, feature_name: str) -> TestResult:
        marker = FEATURE_MARKER_MAP.get(feature_name, feature_name)
        console.print(Panel(f"[bold cyan]TestwrightAI Feature: {feature_name}[/bold cyan]", border_style="cyan"))
        return self._run(markers=marker, label=f"feature-{feature_name}")

    def run_api_tests(self) -> TestResult:
        console.print(Panel("[bold magenta]TestwrightAI API Testleri[/bold magenta]", border_style="magenta"))
        return self._run(markers="api", label="api")

    def run_all(self) -> TestResult:
        console.print(Panel("[bold yellow]TestwrightAI Tüm Testler[/bold yellow]", border_style="yellow"))
        return self._run(markers=None, label="all")

    def run_parallel(self, workers: int = 4) -> TestResult:
        console.print(Panel(f"[bold cyan]TestwrightAI Paralel ({workers} worker)[/bold cyan]", border_style="cyan"))
        return self._run(markers=None, parallel_workers=workers, label="parallel")

    def run_with_retry(self, max_retries: int = 2, markers: str | None = None) -> TestResult:
        console.print(Panel(
            f"[bold yellow]TestwrightAI Retry ({max_retries} deneme)[/bold yellow]",
            border_style="yellow",
        ))
        best_result: TestResult | None = None

        for attempt in range(1, max_retries + 1):
            console.print(f"\n[dim]Deneme {attempt}/{max_retries}[/dim]")
            result = self._run(markers=markers, label=f"retry-{attempt}")
            best_result = result

            if result.return_code == 0:
                console.print(f"[green]Tüm testler {attempt}. denemede geçti.[/green]")
                break

            if attempt < max_retries:
                extra = ["--lf"]
                console.print("[yellow]Başarısız testler yeniden denenecek...[/yellow]")
                result = self._run(
                    markers=markers,
                    extra_args=extra,
                    label=f"retry-{attempt}-rerun",
                )
                best_result = result
                if result.return_code == 0:
                    break

        return best_result  # type: ignore[return-value]

    def generate_report(self) -> bool:
        """Allure HTML raporu üretir (mevcut runner.py'deki generate_allure_report'u kullanır)."""
        from runner import generate_allure_report, check_allure_installed

        if not check_allure_installed():
            console.print("[yellow]Allure CLI bulunamadı — rapor üretilemiyor.[/yellow]")
            return False

        console.print("[bold]Allure raporu üretiliyor...[/bold]")
        ok = generate_allure_report()
        if ok:
            console.print(f"[green]Rapor hazır:[/green] {ALLURE_REPORT}")
        else:
            console.print("[red]Allure raporu üretilemedi.[/red]")
        return ok

    def get_last_results(self) -> TestResult | None:
        return self._last_result


def _print_summary(result: TestResult) -> None:
    table = Table(title="TestwrightAI Test Sonuçları", show_header=True, header_style="bold cyan")
    table.add_column("Metrik", style="dim")
    table.add_column("Değer", justify="right")
    table.add_row("Toplam", str(result.total))
    table.add_row("Başarılı", f"[green]{result.passed}[/green]")
    table.add_row("Başarısız", f"[red]{result.failed}[/red]")
    table.add_row("Atlanan", f"[yellow]{result.skipped}[/yellow]")
    table.add_row("Hata", f"[red]{result.errors}[/red]")
    table.add_row("Başarı Oranı", f"{result.success_rate}%")
    table.add_row("Süre", f"{result.duration_seconds}s")
    console.print(table)

    if result.failures:
        console.print("\n[bold red]Başarısız Testler:[/bold red]")
        for f in result.failures[:10]:
            console.print(f"  [red]✗[/red] {f['test']}")
            if f.get("message"):
                console.print(f"    [dim]{f['message'][:120]}[/dim]")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="TestwrightAI E2E Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Örnekler:\n"
            "  python bgts_runner.py --smoke\n"
            "  python bgts_runner.py --regression --parallel 4\n"
            "  python bgts_runner.py --feature login --retry 2\n"
            "  python bgts_runner.py --all --report\n"
        ),
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--smoke", action="store_true", help="Smoke testlerini çalıştır")
    group.add_argument("--regression", action="store_true", help="Regresyon testlerini çalıştır")
    group.add_argument("--api", action="store_true", help="API testlerini çalıştır")
    group.add_argument("--all", action="store_true", help="Tüm testleri çalıştır")
    group.add_argument("--feature", type=str, metavar="NAME", help="Belirli feature'ı çalıştır")

    parser.add_argument("--parallel", type=int, default=0, metavar="N", help="Paralel worker sayısı (pytest-xdist)")
    parser.add_argument("--retry", type=int, default=0, metavar="N", help="Başarısız testleri N kez yeniden dene")
    parser.add_argument("--report", action="store_true", help="Allure raporu üret")
    parser.add_argument("--json-output", type=str, metavar="PATH", help="Sonuçları JSON dosyasına yaz")

    args = parser.parse_args()

    console.print(Panel.fit(
        "[bold cyan]TestwrightAI E2E Test Runner[/bold cyan]\n"
        f"[dim]{datetime.now().strftime('%d.%m.%Y %H:%M:%S')}[/dim]\n"
        f"[white]BASE_URL:[/white] {test_config.BASE_URL}\n"
        f"[white]Tarayıcı:[/white] {test_config.BROWSER} ({'headless' if test_config.HEADLESS else 'headed'})",
        border_style="cyan",
    ))

    runner = TestwrightAIRunner()

    if args.retry > 0:
        markers = None
        if args.smoke:
            markers = "smoke"
        elif args.regression:
            markers = "regression"
        elif args.api:
            markers = "api"
        elif args.feature:
            markers = FEATURE_MARKER_MAP.get(args.feature, args.feature)
        result = runner.run_with_retry(max_retries=args.retry, markers=markers)
    elif args.parallel > 0:
        result = runner.run_parallel(workers=args.parallel)
    elif args.smoke:
        result = runner.run_smoke()
    elif args.regression:
        result = runner.run_regression()
    elif args.api:
        result = runner.run_api_tests()
    elif args.feature:
        result = runner.run_by_feature(args.feature)
    else:
        result = runner.run_all()

    _print_summary(result)

    if args.report:
        runner.generate_report()

    if args.json_output:
        out = Path(args.json_output)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
        console.print(f"[green]JSON çıktı:[/green] {out}")

    sys.exit(result.return_code)


if __name__ == "__main__":
    main()
