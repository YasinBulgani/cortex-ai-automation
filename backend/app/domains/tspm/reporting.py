"""
TestwrightAI TSPM Reporting Service

Test execution raporlama, coverage hesaplama, traceability zinciri ve
root-cause analiz servisi.

Üretilen rapor formatları: HTML, JSON, Markdown
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════

class ReportFormat(str, Enum):
    HTML = "html"
    JSON = "json"
    MARKDOWN = "md"


class TestStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BROKEN = "broken"


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RootCauseCategory(str, Enum):
    PRODUCT_BUG = "PRODUCT_BUG"
    TEST_ISSUE = "TEST_ISSUE"
    ENVIRONMENT = "ENVIRONMENT"
    AUTOMATION_DEBT = "AUTOMATION_DEBT"
    UNKNOWN = "UNKNOWN"


class CoverageStatus(str, Enum):
    FULLY_COVERED = "fully_covered"
    PARTIALLY_COVERED = "partially_covered"
    NOT_COVERED = "not_covered"


class TrendDirection(str, Enum):
    IMPROVING = "improving"
    STABLE = "stable"
    DECLINING = "declining"


# ═══════════════════════════════════════════════════════════════════════
# Data Models
# ═══════════════════════════════════════════════════════════════════════

class StepResult(BaseModel):
    order: int = 0
    action: str = ""
    status: TestStatus = TestStatus.PASSED
    duration_ms: int = 0
    detail: str = ""
    error: str = ""
    screenshot: Optional[str] = None


class ErrorInfo(BaseModel):
    type: str = ""
    message: str = ""
    stack_trace: str = ""
    screenshot: Optional[str] = None
    trace_file: Optional[str] = None


class RootCause(BaseModel):
    category: RootCauseCategory = RootCauseCategory.UNKNOWN
    subcategory: str = ""
    description: str = ""
    action: str = ""
    assignee: str = ""
    affected_requirements: list[str] = Field(default_factory=list)


class TestResult(BaseModel):
    test_id: str = ""
    scenario_id: Optional[str] = None
    title: str = ""
    status: TestStatus = TestStatus.PASSED
    duration_ms: int = 0
    severity: Severity = Severity.MEDIUM
    module: str = ""
    tags: list[str] = Field(default_factory=list)
    requirement_ids: list[str] = Field(default_factory=list)
    steps: list[StepResult] = Field(default_factory=list)
    error: Optional[ErrorInfo] = None
    root_cause: Optional[RootCause] = None


class SeverityBreakdown(BaseModel):
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0


class ReportSummary(BaseModel):
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    broken: int = 0
    pass_rate: float = 0.0
    severity_breakdown: dict[str, SeverityBreakdown] = Field(default_factory=dict)


class EnvironmentInfo(BaseModel):
    browser: str = "chromium"
    base_url: str = ""
    os: str = ""
    node_version: str = ""
    python_version: str = ""
    ci: bool = False


class TimingInfo(BaseModel):
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: Optional[datetime] = None
    duration_seconds: float = 0.0


class CoverageInfo(BaseModel):
    requirements_covered: int = 0
    requirements_total: int = 0
    coverage_percent: float = 0.0
    modules: list[dict[str, Any]] = Field(default_factory=list)


class TrendPoint(BaseModel):
    run_id: str = ""
    date: str = ""
    total: int = 0
    passed: int = 0
    pass_rate: float = 0.0


class TrendInfo(BaseModel):
    previous_pass_rate: float = 0.0
    delta: float = 0.0
    direction: TrendDirection = TrendDirection.STABLE
    history: list[TrendPoint] = Field(default_factory=list)


class TraceabilityEntry(BaseModel):
    requirement_id: str
    requirement_external_id: str = ""
    requirement_title: str = ""
    priority: str = "medium"
    test_cases: list[dict[str, Any]] = Field(default_factory=list)
    automation_files: list[str] = Field(default_factory=list)
    execution_statuses: list[str] = Field(default_factory=list)
    overall_status: CoverageStatus = CoverageStatus.NOT_COVERED


class ExecutionReport(BaseModel):
    report_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    execution_id: str = ""
    project_id: str = ""
    title: str = ""
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    environment: EnvironmentInfo = Field(default_factory=EnvironmentInfo)
    timing: TimingInfo = Field(default_factory=TimingInfo)
    summary: ReportSummary = Field(default_factory=ReportSummary)
    results: list[TestResult] = Field(default_factory=list)
    coverage: CoverageInfo = Field(default_factory=CoverageInfo)
    trends: TrendInfo = Field(default_factory=TrendInfo)
    traceability: list[TraceabilityEntry] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════
# Report Builder
# ═══════════════════════════════════════════════════════════════════════

class ReportBuilder:
    """Test execution sonuçlarından rapor nesnesi oluşturur."""

    def __init__(self, project_id: str, execution_id: str, title: str = ""):
        self._report = ExecutionReport(
            project_id=project_id,
            execution_id=execution_id,
            title=title or f"Execution Report {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')}",
        )
        self._results: list[TestResult] = []

    def set_environment(self, **kwargs: Any) -> ReportBuilder:
        self._report.environment = EnvironmentInfo(**kwargs)
        return self

    def set_timing(self, started_at: datetime, finished_at: datetime) -> ReportBuilder:
        delta = (finished_at - started_at).total_seconds()
        self._report.timing = TimingInfo(
            started_at=started_at,
            finished_at=finished_at,
            duration_seconds=delta,
        )
        return self

    def add_result(self, result: TestResult) -> ReportBuilder:
        self._results.append(result)
        return self

    def add_results(self, results: list[TestResult]) -> ReportBuilder:
        self._results.extend(results)
        return self

    def set_coverage(self, covered: int, total: int, modules: list[dict] | None = None) -> ReportBuilder:
        pct = round(covered / total * 100, 1) if total > 0 else 0.0
        self._report.coverage = CoverageInfo(
            requirements_covered=covered,
            requirements_total=total,
            coverage_percent=pct,
            modules=modules or [],
        )
        return self

    def set_trend(self, history: list[TrendPoint]) -> ReportBuilder:
        if len(history) >= 2:
            current_rate = history[-1].pass_rate
            prev_rate = history[-2].pass_rate
            delta = round(current_rate - prev_rate, 1)
            if delta > 1:
                direction = TrendDirection.IMPROVING
            elif delta < -1:
                direction = TrendDirection.DECLINING
            else:
                direction = TrendDirection.STABLE
            self._report.trends = TrendInfo(
                previous_pass_rate=prev_rate,
                delta=delta,
                direction=direction,
                history=history,
            )
        return self

    def set_traceability(self, entries: list[TraceabilityEntry]) -> ReportBuilder:
        self._report.traceability = entries
        return self

    def build(self) -> ExecutionReport:
        self._report.results = self._results
        self._report.summary = self._compute_summary()
        return self._report

    def _compute_summary(self) -> ReportSummary:
        total = len(self._results)
        passed = sum(1 for r in self._results if r.status == TestStatus.PASSED)
        failed = sum(1 for r in self._results if r.status == TestStatus.FAILED)
        skipped = sum(1 for r in self._results if r.status == TestStatus.SKIPPED)
        broken = sum(1 for r in self._results if r.status == TestStatus.BROKEN)
        rate = round(passed / total * 100, 1) if total > 0 else 0.0

        severity_map: dict[str, SeverityBreakdown] = {}
        for sev in Severity:
            subset = [r for r in self._results if r.severity == sev]
            severity_map[sev.value] = SeverityBreakdown(
                total=len(subset),
                passed=sum(1 for r in subset if r.status == TestStatus.PASSED),
                failed=sum(1 for r in subset if r.status == TestStatus.FAILED),
                skipped=sum(1 for r in subset if r.status == TestStatus.SKIPPED),
            )

        return ReportSummary(
            total=total, passed=passed, failed=failed,
            skipped=skipped, broken=broken, pass_rate=rate,
            severity_breakdown=severity_map,
        )


# ═══════════════════════════════════════════════════════════════════════
# Coverage Calculator
# ═══════════════════════════════════════════════════════════════════════

class CoverageCalculator:
    """Requirement-Scenario-Execution üçlüsünden coverage hesaplar."""

    @staticmethod
    def calculate(
        requirements: list[dict[str, Any]],
        scenario_links: list[dict[str, Any]],
        execution_results: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Args:
            requirements: [{id, external_id, title, priority}]
            scenario_links: [{requirement_id, scenario_id}]
            execution_results: [{scenario_id, status}]
        """
        req_scenarios: dict[str, list[str]] = {}
        for link in scenario_links:
            rid = link["requirement_id"]
            req_scenarios.setdefault(rid, []).append(link["scenario_id"])

        scenario_status: dict[str, str] = {}
        for er in execution_results:
            scenario_status[er["scenario_id"]] = er["status"]

        matrix_rows: list[dict[str, Any]] = []
        covered_count = 0
        automated_count = 0
        passed_count = 0

        for req in requirements:
            rid = req["id"]
            linked = req_scenarios.get(rid, [])
            has_tests = len(linked) > 0
            statuses = [scenario_status.get(sid, "not_run") for sid in linked]
            all_passed = has_tests and all(s == "passed" for s in statuses)
            any_failed = any(s == "failed" for s in statuses)

            if has_tests:
                covered_count += 1
                if len(linked) > 0:
                    automated_count += 1
                if all_passed:
                    passed_count += 1

            if not has_tests:
                status = "not_covered"
            elif any_failed:
                status = "at_risk"
            elif all_passed:
                status = "covered"
            else:
                status = "partially_covered"

            matrix_rows.append({
                "requirement_id": rid,
                "external_id": req.get("external_id", ""),
                "title": req.get("title", ""),
                "priority": req.get("priority", "medium"),
                "scenario_count": len(linked),
                "scenario_ids": linked,
                "statuses": statuses,
                "status": status,
            })

        total = len(requirements)
        return {
            "total_requirements": total,
            "covered_count": covered_count,
            "coverage_percent": round(covered_count / total * 100, 1) if total else 0.0,
            "automated_count": automated_count,
            "passed_count": passed_count,
            "at_risk_count": sum(1 for r in matrix_rows if r["status"] == "at_risk"),
            "gaps": [r for r in matrix_rows if r["status"] == "not_covered"],
            "matrix": matrix_rows,
        }


# ═══════════════════════════════════════════════════════════════════════
# Traceability Engine
# ═══════════════════════════════════════════════════════════════════════

class TraceabilityEngine:
    """Requirement → Test Case → Automation → Execution zinciri."""

    @staticmethod
    def build_chain(
        requirements: list[dict[str, Any]],
        scenarios: list[dict[str, Any]],
        scenario_req_links: list[dict[str, Any]],
        automation_mappings: list[dict[str, Any]],
        execution_results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Args:
            requirements: [{id, external_id, title, priority}]
            scenarios: [{id, title, status}]
            scenario_req_links: [{scenario_id, requirement_id}]
            automation_mappings: [{scenario_id, file_path, test_name, framework}]
            execution_results: [{scenario_id, execution_id, status, duration_ms}]
        """
        scenario_map = {s["id"]: s for s in scenarios}
        auto_by_scenario: dict[str, list[dict]] = {}
        for am in automation_mappings:
            auto_by_scenario.setdefault(am["scenario_id"], []).append(am)

        exec_by_scenario: dict[str, list[dict]] = {}
        for er in execution_results:
            exec_by_scenario.setdefault(er["scenario_id"], []).append(er)

        req_to_scenarios: dict[str, list[str]] = {}
        for link in scenario_req_links:
            req_to_scenarios.setdefault(link["requirement_id"], []).append(link["scenario_id"])

        chains: list[dict[str, Any]] = []

        for req in requirements:
            rid = req["id"]
            linked_scenario_ids = req_to_scenarios.get(rid, [])

            test_cases = []
            all_statuses = []

            for sid in linked_scenario_ids:
                sc = scenario_map.get(sid)
                if not sc:
                    continue

                automations = []
                for am in auto_by_scenario.get(sid, []):
                    execs = exec_by_scenario.get(sid, [])
                    automations.append({
                        "file_path": am.get("file_path", ""),
                        "test_name": am.get("test_name", ""),
                        "framework": am.get("framework", "unknown"),
                        "executions": [
                            {
                                "execution_id": e.get("execution_id", ""),
                                "status": e.get("status", "not_run"),
                                "duration_ms": e.get("duration_ms", 0),
                            }
                            for e in execs
                        ],
                    })

                latest_status = "not_run"
                execs = exec_by_scenario.get(sid, [])
                if execs:
                    latest_status = execs[-1].get("status", "not_run")
                all_statuses.append(latest_status)

                test_cases.append({
                    "scenario_id": sid,
                    "title": sc.get("title", ""),
                    "status": sc.get("status", "draft"),
                    "automations": automations,
                    "latest_execution_status": latest_status,
                })

            if not test_cases:
                coverage = CoverageStatus.NOT_COVERED
            elif all(s == "passed" for s in all_statuses):
                coverage = CoverageStatus.FULLY_COVERED
            else:
                coverage = CoverageStatus.PARTIALLY_COVERED

            chains.append({
                "requirement": {
                    "id": rid,
                    "external_id": req.get("external_id", ""),
                    "title": req.get("title", ""),
                    "priority": req.get("priority", "medium"),
                },
                "test_cases": test_cases,
                "coverage_status": coverage.value,
                "automation_count": sum(len(tc["automations"]) for tc in test_cases),
                "execution_statuses": all_statuses,
            })

        return chains

    @staticmethod
    def impact_analysis(
        changed_requirement_id: str,
        chains: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Bir gereksinim değiştiğinde etkilenen testleri döndürür."""
        for chain in chains:
            if chain["requirement"]["id"] == changed_requirement_id:
                affected_tests = []
                affected_files = set()
                for tc in chain["test_cases"]:
                    affected_tests.append({
                        "scenario_id": tc["scenario_id"],
                        "title": tc["title"],
                    })
                    for auto in tc["automations"]:
                        affected_files.add(auto["file_path"])

                return {
                    "requirement": chain["requirement"],
                    "affected_test_count": len(affected_tests),
                    "affected_tests": affected_tests,
                    "affected_files": sorted(affected_files),
                    "risk_level": "high" if chain["requirement"]["priority"] in ("critical", "high") else "medium",
                }

        return {"requirement_id": changed_requirement_id, "affected_test_count": 0}


# ═══════════════════════════════════════════════════════════════════════
# Root Cause Analyzer
# ═══════════════════════════════════════════════════════════════════════

class RootCauseAnalyzer:
    """Başarısız testleri kök neden kategorilerine sınıflandırır."""

    _ERROR_PATTERNS: list[tuple[str, RootCauseCategory, str]] = [
        ("TimeoutError", RootCauseCategory.TEST_ISSUE, "timing"),
        ("net::ERR_CONNECTION_REFUSED", RootCauseCategory.ENVIRONMENT, "infra_down"),
        ("ECONNREFUSED", RootCauseCategory.ENVIRONMENT, "infra_down"),
        ("locator.click", RootCauseCategory.TEST_ISSUE, "stale_locator"),
        ("locator.fill", RootCauseCategory.TEST_ISSUE, "stale_locator"),
        ("Element not found", RootCauseCategory.TEST_ISSUE, "stale_locator"),
        ("Element not visible", RootCauseCategory.TEST_ISSUE, "stale_locator"),
        ("not.toBeVisible", RootCauseCategory.TEST_ISSUE, "wrong_assertion"),
        ("expect(received)", RootCauseCategory.PRODUCT_BUG, "functional"),
        ("AssertionError", RootCauseCategory.PRODUCT_BUG, "functional"),
        ("500 Internal Server", RootCauseCategory.PRODUCT_BUG, "functional"),
        ("404 Not Found", RootCauseCategory.PRODUCT_BUG, "functional"),
        ("OOM", RootCauseCategory.ENVIRONMENT, "resource"),
        ("Out of Memory", RootCauseCategory.ENVIRONMENT, "resource"),
        ("ENOMEM", RootCauseCategory.ENVIRONMENT, "resource"),
        ("database", RootCauseCategory.ENVIRONMENT, "infra_down"),
        ("redis", RootCauseCategory.ENVIRONMENT, "infra_down"),
        ("permission denied", RootCauseCategory.ENVIRONMENT, "config"),
    ]

    @classmethod
    def classify(cls, error_message: str, error_type: str = "") -> RootCause:
        combined = f"{error_type} {error_message}".lower()

        for pattern, category, subcategory in cls._ERROR_PATTERNS:
            if pattern.lower() in combined:
                return RootCause(
                    category=category,
                    subcategory=subcategory,
                    description=cls._generate_description(category, subcategory, error_message),
                )

        return RootCause(
            category=RootCauseCategory.UNKNOWN,
            subcategory="unclassified",
            description=f"Sınıflandırılamayan hata: {error_message[:200]}",
        )

    @classmethod
    def analyze_failed_results(cls, results: list[TestResult]) -> list[dict[str, Any]]:
        rca_entries = []
        for r in results:
            if r.status != TestStatus.FAILED:
                continue
            error_msg = r.error.message if r.error else ""
            error_type = r.error.type if r.error else ""
            rc = cls.classify(error_msg, error_type)
            rc.affected_requirements = r.requirement_ids

            rca_entries.append({
                "test_id": r.test_id,
                "title": r.title,
                "module": r.module,
                "severity": r.severity.value,
                "error_message": error_msg,
                "root_cause": rc.model_dump(),
            })

        return rca_entries

    @classmethod
    def distribution(cls, rca_entries: list[dict]) -> dict[str, int]:
        dist: dict[str, int] = {}
        for entry in rca_entries:
            cat = entry.get("root_cause", {}).get("category", "UNKNOWN")
            dist[cat] = dist.get(cat, 0) + 1
        return dist

    @staticmethod
    def _generate_description(category: RootCauseCategory, subcategory: str, error: str) -> str:
        descriptions = {
            ("PRODUCT_BUG", "functional"): "Uygulama beklenen davranışı sağlamıyor",
            ("TEST_ISSUE", "timing"): "Test bekleme süresi yetersiz veya zamanlama sorunu",
            ("TEST_ISSUE", "stale_locator"): "Selector/locator güncelliğini yitirmiş veya element bulunamıyor",
            ("TEST_ISSUE", "wrong_assertion"): "Test doğrulama kriteri hatalı veya güncel değil",
            ("ENVIRONMENT", "infra_down"): "Servis veya altyapı bileşeni erişilemez durumda",
            ("ENVIRONMENT", "resource"): "Yetersiz sistem kaynağı (bellek, CPU, disk)",
            ("ENVIRONMENT", "config"): "Ortam yapılandırma sorunu",
        }
        key = (category.value, subcategory)
        base = descriptions.get(key, "Analiz gerekiyor")
        return f"{base}. Hata: {error[:150]}"


# ═══════════════════════════════════════════════════════════════════════
# Report Renderer
# ═══════════════════════════════════════════════════════════════════════

class ReportRenderer:
    """ExecutionReport'u farklı formatlarda render eder."""

    TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "reports" / "templates"

    @classmethod
    def to_json(cls, report: ExecutionReport) -> str:
        return report.model_dump_json(indent=2)

    @classmethod
    def to_markdown(cls, report: ExecutionReport) -> str:
        s = report.summary
        lines = [
            f"# Test Execution Özeti",
            "",
            f"**Proje:** {report.project_id}",
            f"**Çalıştırma:** {report.title}",
            f"**Tarih:** {report.generated_at.strftime('%d.%m.%Y %H:%M')}",
            f"**Ortam:** {report.environment.browser} / {report.environment.base_url}",
            "",
            "---",
            "",
            "## Sonuçlar",
            "",
            "| Metrik | Değer |",
            "|--------|-------|",
            f"| Toplam | {s.total} |",
            f"| Başarılı | {s.passed} ({s.pass_rate}%) |",
            f"| Başarısız | {s.failed} |",
            f"| Atlanan | {s.skipped} |",
            f"| Süre | {report.timing.duration_seconds:.0f}s |",
            "",
        ]

        failed = [r for r in report.results if r.status == TestStatus.FAILED]
        if failed:
            lines.extend([
                "## Başarısız Testler",
                "",
                "| # | Test | Modül | Kök Neden | Hata |",
                "|---|------|-------|-----------|------|",
            ])
            for i, f in enumerate(failed, 1):
                rc_cat = f.root_cause.category.value if f.root_cause else "UNKNOWN"
                err_msg = (f.error.message[:60] + "...") if f.error and f.error.message else "-"
                lines.append(f"| {i} | {f.title} | {f.module} | {rc_cat} | {err_msg} |")
            lines.append("")

        if report.coverage.requirements_total > 0:
            lines.extend([
                "## Kapsam",
                "",
                f"- Gereksinim kapsama: {report.coverage.coverage_percent}%"
                f" ({report.coverage.requirements_covered}/{report.coverage.requirements_total})",
                "",
            ])

        if report.trends.history:
            lines.extend([
                "## Trend",
                "",
                f"- Önceki oran: {report.trends.previous_pass_rate}%",
                f"- Delta: {report.trends.delta:+.1f}%",
                f"- Yön: {report.trends.direction.value}",
                "",
            ])

        lines.extend([
            "---",
            "*Otomatik üretildi — TestwrightAI Raporlama Motoru*",
        ])

        return "\n".join(lines)

    @classmethod
    def to_html(cls, report: ExecutionReport) -> str:
        s = report.summary
        rate_class = "good" if s.pass_rate >= 85 else ("warn" if s.pass_rate >= 70 else "bad")

        result_cards = []
        for r in report.results:
            status_cls = r.status.value
            status_label = {
                "passed": "BAŞARILI", "failed": "BAŞARISIZ",
                "skipped": "ATLANDI", "broken": "KIRIK",
            }.get(r.status.value, r.status.value.upper())

            steps_html = ""
            for step in r.steps:
                cls_name = "pass" if step.status == TestStatus.PASSED else "fail"
                icon = "✓" if step.status == TestStatus.PASSED else "✗"
                text = step.detail or step.error or step.action
                steps_html += (
                    f'<div class="step {cls_name}">'
                    f'<span class="step-icon">{icon}</span>'
                    f'<span class="step-text">{text}</span></div>\n'
                )

            tags_html = "".join(f'<span class="tag">{t}</span>' for t in r.tags)

            result_cards.append(
                f'<div class="card">'
                f'<div class="card-header">'
                f'<span class="badge {status_cls}">{status_label}</span>'
                f'<h3>{r.title}</h3>'
                f'<span class="duration">{r.duration_ms}ms</span></div>'
                f'<div class="steps">{steps_html}</div>'
                f'<div class="card-meta">{tags_html}'
                f'<span>Modül: {r.module}</span></div></div>'
            )

        rca_cards = []
        for r in report.results:
            if r.status != TestStatus.FAILED or not r.root_cause:
                continue
            rca_cards.append(
                f'<div class="rca-card">'
                f'<h4>{r.title}</h4>'
                f'<div class="detail"><strong>Kategori:</strong> '
                f'{r.root_cause.category.value} &gt; {r.root_cause.subcategory}</div>'
                f'<div class="detail"><strong>Açıklama:</strong> '
                f'{r.root_cause.description}</div>'
                f'<div class="detail"><strong>Aksiyon:</strong> '
                f'{r.root_cause.action or "Belirlenmedi"}</div></div>'
            )

        try:
            template_path = cls.TEMPLATE_DIR / "execution_report.html"
            template = template_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            template = "<html><body><h1>{{ title }}</h1><pre>{{ json_data }}</pre></body></html>"

        replacements = {
            "{{ title }}": report.title,
            "{{ date }}": report.generated_at.strftime("%d.%m.%Y %H:%M"),
            "{{ environment }}": f"{report.environment.browser} / {report.environment.base_url}",
            "{{ duration }}": f"{report.timing.duration_seconds:.0f}s",
            "{{ total }}": str(s.total),
            "{{ passed }}": str(s.passed),
            "{{ failed }}": str(s.failed),
            "{{ skipped }}": str(s.skipped),
            "{{ pass_rate }}": str(s.pass_rate),
            "{{ rate_class }}": rate_class,
            "{{ project_name }}": report.project_id,
            "<!-- {{ result_cards }} -->": "\n".join(result_cards),
            "<!-- {{ rca_cards }} -->": "\n".join(rca_cards) if rca_cards else '<p style="color: var(--green); padding: 16px;">Tüm testler başarılı!</p>',
        }

        html = template
        for key, value in replacements.items():
            html = html.replace(key, value)

        return html


# ═══════════════════════════════════════════════════════════════════════
# Quality Scorecard
# ═══════════════════════════════════════════════════════════════════════

class QualityScorecard:
    """Proje kalite puanını hesaplar."""

    WEIGHTS = {
        "pass_rate": 0.30,
        "critical_pass_rate": 0.25,
        "coverage": 0.20,
        "automation_rate": 0.15,
        "flaky_penalty": 0.10,
    }

    THRESHOLDS = {
        "pass_rate": {"green": 85, "yellow": 75},
        "critical_pass_rate": {"green": 95, "yellow": 90},
        "coverage": {"green": 90, "yellow": 70},
        "automation_rate": {"green": 70, "yellow": 40},
        "flaky_rate": {"green": 5, "yellow": 10},
    }

    @classmethod
    def calculate(
        cls,
        pass_rate: float,
        critical_pass_rate: float,
        requirement_coverage: float,
        automation_rate: float,
        flaky_rate: float = 0.0,
    ) -> dict[str, Any]:
        scores = {
            "pass_rate": min(pass_rate / 100, 1.0),
            "critical_pass_rate": min(critical_pass_rate / 100, 1.0),
            "coverage": min(requirement_coverage / 100, 1.0),
            "automation_rate": min(automation_rate / 100, 1.0),
            "flaky_penalty": max(1.0 - (flaky_rate / 20), 0.0),
        }

        weighted_score = sum(
            scores[k] * cls.WEIGHTS[k] for k in cls.WEIGHTS
        )
        overall = round(weighted_score * 100, 1)

        if overall >= 85:
            health = "healthy"
        elif overall >= 70:
            health = "at_risk"
        else:
            health = "critical"

        def status(metric: str, value: float) -> str:
            t = cls.THRESHOLDS.get(metric, {"green": 85, "yellow": 70})
            if value >= t["green"]:
                return "green"
            elif value >= t["yellow"]:
                return "yellow"
            return "red"

        return {
            "overall_score": overall,
            "health": health,
            "dimensions": {
                "pass_rate": {"value": pass_rate, "weight": cls.WEIGHTS["pass_rate"], "status": status("pass_rate", pass_rate)},
                "critical_pass_rate": {"value": critical_pass_rate, "weight": cls.WEIGHTS["critical_pass_rate"], "status": status("critical_pass_rate", critical_pass_rate)},
                "requirement_coverage": {"value": requirement_coverage, "weight": cls.WEIGHTS["coverage"], "status": status("coverage", requirement_coverage)},
                "automation_rate": {"value": automation_rate, "weight": cls.WEIGHTS["automation_rate"], "status": status("automation_rate", automation_rate)},
                "flaky_rate": {"value": flaky_rate, "weight": cls.WEIGHTS["flaky_penalty"], "status": status("flaky_rate", 100 - flaky_rate)},
            },
        }


# ═══════════════════════════════════════════════════════════════════════
# Convenience: generate_report()
# ═══════════════════════════════════════════════════════════════════════

def generate_report(
    report: ExecutionReport,
    output_dir: str | Path,
    formats: list[ReportFormat] | None = None,
) -> dict[str, str]:
    """Raporu belirtilen formatlarda dosyaya yazar."""
    formats = formats or [ReportFormat.HTML, ReportFormat.JSON, ReportFormat.MARKDOWN]
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    ts = report.generated_at.strftime("%Y%m%d_%H%M%S")
    base_name = f"execution_{report.execution_id[:8]}_{ts}"
    files: dict[str, str] = {}

    for fmt in formats:
        if fmt == ReportFormat.JSON:
            path = output_dir / f"{base_name}.json"
            path.write_text(ReportRenderer.to_json(report), encoding="utf-8")
            files["json"] = str(path)

        elif fmt == ReportFormat.MARKDOWN:
            path = output_dir / f"{base_name}.md"
            path.write_text(ReportRenderer.to_markdown(report), encoding="utf-8")
            files["md"] = str(path)

        elif fmt == ReportFormat.HTML:
            path = output_dir / f"{base_name}.html"
            path.write_text(ReportRenderer.to_html(report), encoding="utf-8")
            files["html"] = str(path)

    return files
