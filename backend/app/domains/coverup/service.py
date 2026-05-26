"""Application service layer for CoverUp workflows."""

from __future__ import annotations

from datetime import datetime, timezone
import uuid

from .coverage_parser import CoverageParser
from .gap_detector import GapDetector
from .repository import CoverageReportRepository
from .schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    CoverageGapTarget,
    CoverageReport,
    CoverageSummary,
    CoverageUploadRequest,
    FileCoverage,
    GenerateTestRequest,
    GenerateTestResponse,
    GeneratedTest,
    TrendResponse,
)
from .test_generator import CoverUpTestGenerator


def create_report(
    repository: CoverageReportRepository,
    body: CoverageUploadRequest,
) -> CoverageReport:
    """Parse and persist a coverage upload."""
    try:
        parsed = CoverageParser.parse(body.format, body.report_data)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc

    files = [FileCoverage(**item) for item in parsed.get("files", [])]
    if not files:
        raise ValueError(f"Rapor parse edilemedi veya bos. Format: {body.format}")

    report = CoverageReport(
        report_id=str(uuid.uuid4())[:12],
        project_id=body.project_id,
        project_name=body.project_name,
        commit_sha=body.commit_sha,
        branch=body.branch,
        format=body.format,
        created_at=datetime.now(timezone.utc).isoformat(),
        summary=CoverageSummary(**parsed["summary"]),
        files=files,
    )
    return repository.save_report(report)


def get_report_or_404(
    repository: CoverageReportRepository,
    report_id: str,
    *,
    allowed_project_ids: set[str] | None = None,
) -> CoverageReport:
    report = repository.get_report(report_id, allowed_project_ids=allowed_project_ids)
    if report is None:
        raise KeyError(f"Rapor bulunamadi: {report_id}")
    return report


def analyze_report(
    report: CoverageReport,
    body: AnalyzeRequest,
    *,
    banking_only: bool = False,
) -> AnalyzeResponse:
    """Analyze a persisted report and return prioritized gaps."""
    report_payload = report.model_dump()
    targets_raw = GapDetector.detect_gaps(
        report_payload,
        focus_paths=body.focus_paths or None,
        min_risk=body.min_risk_score,
        max_targets=body.max_targets * 3 if banking_only else body.max_targets,
    )
    banking_paths = GapDetector.identify_banking_critical_paths(report_payload["files"])

    if banking_only:
        filtered: list[dict] = []
        for target in targets_raw:
            if target["file_path"] not in banking_paths:
                continue
            risk_factors = list(target.get("risk_factors", []))
            if "banking_critical_path" not in risk_factors:
                risk_factors.append("banking_critical_path")
            target = {
                **target,
                "risk_score": round(min(target["risk_score"] + 0.2, 1.0), 4),
                "risk_factors": risk_factors,
            }
            if target["risk_score"] >= body.min_risk_score:
                filtered.append(target)
        targets_raw = filtered

    targets_raw = sorted(
        targets_raw,
        key=lambda item: item["risk_score"],
        reverse=True,
    )[: body.max_targets]
    targets = [CoverageGapTarget(**item) for item in targets_raw]

    high = sum(1 for target in targets if target.risk_score >= 0.7)
    medium = sum(1 for target in targets if 0.4 <= target.risk_score < 0.7)
    low = sum(1 for target in targets if target.risk_score < 0.4)

    return AnalyzeResponse(
        report_id=report.report_id,
        targets=targets,
        summary=report.summary,
        high_risk_count=high,
        medium_risk_count=medium,
        low_risk_count=low,
        banking_critical_paths=banking_paths,
    )


def generate_tests(
    repository: CoverageReportRepository,
    report: CoverageReport,
    body: GenerateTestRequest,
) -> GenerateTestResponse:
    """Run the AI test generator and persist generated test metadata."""
    targets = body.targets
    if not targets:
        targets = analyze_report(
            report,
            AnalyzeRequest(
                report_id=report.report_id,
                min_risk_score=0.5,
                max_targets=body.max_tests,
            ),
        ).targets

    if not targets:
        return GenerateTestResponse(
            tests=[],
            total_generated=0,
            estimated_total_gain=0.0,
        )

    try:
        generator = CoverUpTestGenerator()
        agent_result = generator.safe_run(
            {
                "targets": [target.model_dump() for target in targets[: body.max_tests]],
                "framework": body.framework,
                "language": body.language,
                "banking_context": body.banking_context,
            }
        )
        if not agent_result.success:
            raise RuntimeError(f"Test uretimi basarisiz: {agent_result.error}")

        generated = [
            GeneratedTest(
                target_file=item.get("target_file", ""),
                target_function=item.get("target_function"),
                test_file_path=item.get("test_file_path", ""),
                test_code=item.get("test_code", ""),
                test_framework=item.get("test_framework", body.framework),
                estimated_coverage_gain=item.get("estimated_coverage_gain", 0.0),
                lines_targeted=item.get("lines_targeted", []),
            )
            for item in agent_result.data.get("tests", [])
        ]
        repository.save_generated_tests(report.report_id, generated)

        return GenerateTestResponse(
            tests=generated,
            total_generated=len(generated),
            estimated_total_gain=agent_result.data.get("estimated_total_gain", 0.0),
        )
    except (ValueError, KeyError, RuntimeError):
        raise
    except Exception as exc:
        raise RuntimeError(f"Test uretimi sirasinda hata: {str(exc)[:200]}") from exc


def build_trend_response(points) -> TrendResponse:
    """Build a summarized trend response from repository points."""
    if not points:
        return TrendResponse(
            points=[],
            direction="stable",
            current_line_rate=0.0,
        )

    current_rate = points[-1].line_rate
    delta = 0.0
    direction = "stable"
    if len(points) >= 2:
        delta = round(points[-1].line_rate - points[0].line_rate, 4)
        if delta > 0.02:
            direction = "improving"
        elif delta < -0.02:
            direction = "degrading"

    return TrendResponse(
        points=points,
        direction=direction,
        current_line_rate=current_rate,
        delta_7d=delta,
        delta_30d=delta,
    )
