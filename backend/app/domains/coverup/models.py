"""SQLAlchemy models for persistent CoverUp storage."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infra.models import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CoverageReportRecord(Base):
    __tablename__ = "coverage_reports"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(64), default="", nullable=False, index=True)
    project_name: Mapped[str] = mapped_column(String(256), default="", nullable=False)
    commit_sha: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    branch: Mapped[str] = mapped_column(String(128), default="main", nullable=False)
    format: Mapped[str] = mapped_column(String(32), nullable=False)

    total_files: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_lines: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    covered_lines: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    missed_lines: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    line_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    branch_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    function_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_functions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    covered_functions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    files_json: Mapped[list[dict]] = mapped_column(JSONB, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    file_details: Mapped[list["CoverageFileDetailRecord"]] = relationship(
        back_populates="report",
        cascade="all, delete-orphan",
    )


class CoverageFileDetailRecord(Base):
    __tablename__ = "coverage_file_details"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("coverage_reports.id", ondelete="CASCADE"),
        nullable=False,
    )
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    total_lines: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    covered_lines: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    missed_lines: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    line_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    branch_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_functions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    covered_functions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    missed_line_numbers: Mapped[list[int]] = mapped_column(
        ARRAY(Integer), default=list, nullable=False
    )
    uncovered_functions: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, nullable=False
    )
    complexity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    report: Mapped[CoverageReportRecord] = relationship(back_populates="file_details")


class CoverupGeneratedTestRecord(Base):
    __tablename__ = "coverup_generated_tests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    report_id: Mapped[str] = mapped_column(String(64), nullable=False)
    target_file: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    target_function: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    test_file_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    test_framework: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    estimated_gain: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    lines_targeted: Mapped[list[int]] = mapped_column(
        ARRAY(Integer), default=list, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
