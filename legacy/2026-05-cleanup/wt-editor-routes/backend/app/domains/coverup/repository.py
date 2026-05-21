"""Persistence layer for CoverUp coverage reports."""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .models import (
    CoverageFileDetailRecord,
    CoverageReportRecord,
    CoverupGeneratedTestRecord,
)
from .schemas import (
    CoverageReport,
    CoverageReportListItem,
    FileCoverage,
    GeneratedTest,
    TrendPoint,
)


class CoverageReportRepository:
    """Database-backed repository for CoverUp reports."""

    def __init__(self, db: Session):
        self.db = db

    def save_report(self, report: CoverageReport) -> CoverageReport:
        summary = report.summary
        files_payload = [file_coverage.model_dump() for file_coverage in report.files]
        record = self.db.get(CoverageReportRecord, report.report_id)

        if record is None:
            record = CoverageReportRecord(id=report.report_id)
            self.db.add(record)

        record.project_id = report.project_id
        record.project_name = report.project_name
        record.commit_sha = report.commit_sha
        record.branch = report.branch
        record.format = report.format
        record.total_files = summary.total_files
        record.total_lines = summary.total_lines
        record.covered_lines = summary.covered_lines
        record.missed_lines = summary.missed_lines
        record.line_rate = summary.line_rate
        record.branch_rate = summary.branch_rate
        record.function_rate = summary.function_rate
        record.total_functions = summary.total_functions
        record.covered_functions = summary.covered_functions
        record.files_json = files_payload

        self.db.execute(
            delete(CoverageFileDetailRecord).where(
                CoverageFileDetailRecord.report_id == report.report_id
            )
        )

        for file_coverage in report.files:
            self.db.add(
                CoverageFileDetailRecord(
                    report_id=report.report_id,
                    file_path=file_coverage.file_path,
                    total_lines=file_coverage.total_lines,
                    covered_lines=file_coverage.covered_lines,
                    missed_lines=file_coverage.missed_lines,
                    line_rate=file_coverage.line_rate,
                    branch_rate=file_coverage.branch_rate,
                    total_functions=file_coverage.total_functions,
                    covered_functions=file_coverage.covered_functions,
                    missed_line_numbers=file_coverage.missed_line_numbers,
                    uncovered_functions=file_coverage.uncovered_functions,
                    complexity=file_coverage.complexity,
                )
            )

        self.db.commit()
        return self.get_report(report.report_id) or report

    def get_report(
        self,
        report_id: str,
        *,
        allowed_project_ids: set[str] | None = None,
    ) -> CoverageReport | None:
        record = self.db.get(CoverageReportRecord, report_id)
        if record is None:
            return None
        if allowed_project_ids is not None and record.project_id not in allowed_project_ids:
            return None
        return self._to_schema(record)

    def list_reports(self, *, project_ids: set[str] | None = None) -> list[CoverageReportListItem]:
        query = select(CoverageReportRecord).order_by(CoverageReportRecord.created_at.desc())
        if project_ids is not None:
            if not project_ids:
                return []
            query = query.where(CoverageReportRecord.project_id.in_(project_ids))
        rows = self.db.scalars(query).all()
        return [
            CoverageReportListItem(
                report_id=row.id,
                project_id=row.project_id,
                project_name=row.project_name,
                commit_sha=row.commit_sha,
                branch=row.branch,
                format=row.format,
                created_at=self._iso(row.created_at),
                line_rate=row.line_rate,
                branch_rate=row.branch_rate,
                total_files=row.total_files,
            )
            for row in rows
        ]

    def list_trend_points(self, *, project_ids: set[str] | None = None) -> list[TrendPoint]:
        query = select(CoverageReportRecord).order_by(CoverageReportRecord.created_at.asc())
        if project_ids is not None:
            if not project_ids:
                return []
            query = query.where(CoverageReportRecord.project_id.in_(project_ids))
        rows = self.db.scalars(query).all()
        return [
            TrendPoint(
                report_id=row.id,
                project_id=row.project_id,
                commit_sha=row.commit_sha,
                branch=row.branch,
                created_at=self._iso(row.created_at),
                line_rate=row.line_rate,
                branch_rate=row.branch_rate,
                function_rate=row.function_rate,
                total_lines=row.total_lines,
                covered_lines=row.covered_lines,
            )
            for row in rows
        ]

    def save_generated_tests(
        self,
        report_id: str,
        generated_tests: list[GeneratedTest],
    ) -> None:
        for generated in generated_tests:
            self.db.add(
                CoverupGeneratedTestRecord(
                    report_id=report_id,
                    target_file=generated.target_file,
                    target_function=generated.target_function,
                    test_file_path=generated.test_file_path,
                    test_framework=generated.test_framework,
                    estimated_gain=generated.estimated_coverage_gain,
                    lines_targeted=generated.lines_targeted,
                )
            )
        self.db.commit()

    @staticmethod
    def _iso(value) -> str:
        return value.isoformat() if value is not None else ""

    def _to_schema(self, record: CoverageReportRecord) -> CoverageReport:
        return CoverageReport(
            report_id=record.id,
            project_id=record.project_id,
            project_name=record.project_name,
            commit_sha=record.commit_sha,
            branch=record.branch,
            format=record.format,
            created_at=self._iso(record.created_at),
            summary={
                "total_files": record.total_files,
                "total_lines": record.total_lines,
                "covered_lines": record.covered_lines,
                "missed_lines": record.missed_lines,
                "line_rate": record.line_rate,
                "branch_rate": record.branch_rate,
                "function_rate": record.function_rate,
                "total_functions": record.total_functions,
                "covered_functions": record.covered_functions,
            },
            files=[FileCoverage(**payload) for payload in (record.files_json or [])],
        )
