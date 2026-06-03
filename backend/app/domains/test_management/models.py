"""SQLAlchemy models for Neurex Management manual test operations."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infra.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"


class TestManagementProject(Base):
    __tablename__ = "test_management_projects"
    __table_args__ = (UniqueConstraint("tenant_id", "key", name="uq_test_management_projects_tenant_key"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String(36), default=DEFAULT_TENANT_ID, server_default=DEFAULT_TENANT_ID, nullable=False, index=True)
    tspm_project_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("tspm_projects.id", ondelete="SET NULL"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    key: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default="")
    status: Mapped[str] = mapped_column(String(32), default="active", server_default="active", nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("sd_users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    suites: Mapped[list["TestSuite"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    cases: Mapped[list["TestCase"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    plans: Mapped[list["TestPlan"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class TestSuite(Base):
    __tablename__ = "test_management_suites"
    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_tm_suites_project_name"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("test_management_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default="")
    order_index: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", server_default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    project: Mapped[TestManagementProject] = relationship(back_populates="suites")
    folders: Mapped[list["TestFolder"]] = relationship(back_populates="suite", cascade="all, delete-orphan")
    cases: Mapped[list["TestCase"]] = relationship(back_populates="suite")


class TestFolder(Base):
    __tablename__ = "test_management_folders"
    __table_args__ = (UniqueConstraint("suite_id", "path", name="uq_tm_folders_suite_path"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    suite_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("test_management_suites.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("test_management_folders.id", ondelete="CASCADE"), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    path: Mapped[str] = mapped_column(String(1000), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    suite: Mapped[TestSuite] = relationship(back_populates="folders")
    cases: Mapped[list["TestCase"]] = relationship(back_populates="folder")


class TestCase(Base):
    __tablename__ = "test_management_cases"
    __table_args__ = (
        UniqueConstraint("project_id", "case_key", name="uq_tm_cases_project_key"),
        Index("ix_tm_cases_project_status", "project_id", "status"),
        Index("ix_tm_cases_project_archived", "project_id", "archived"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("test_management_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    suite_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("test_management_suites.id", ondelete="SET NULL"), nullable=True, index=True)
    folder_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("test_management_folders.id", ondelete="SET NULL"), nullable=True, index=True)
    case_key: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    objective: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default="")
    preconditions: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default="")
    test_data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}", nullable=False)
    priority: Mapped[str] = mapped_column(String(32), default="medium", server_default="medium", nullable=False)
    severity: Mapped[str] = mapped_column(String(32), default="major", server_default="major", nullable=False)
    type: Mapped[str] = mapped_column(String(64), default="functional", server_default="functional", nullable=False)
    automation_status: Mapped[str] = mapped_column(String(32), default="manual", server_default="manual", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", server_default="draft", nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), default="manual", server_default="manual", nullable=False)
    source_ref: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    owner_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("sd_users.id", ondelete="SET NULL"), nullable=True)
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list, server_default="[]", nullable=False)
    custom_fields: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}", nullable=False)
    current_version: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    last_run_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_failed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_run_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True)
    archived: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("sd_users.id", ondelete="SET NULL"), nullable=True)
    updated_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("sd_users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    project: Mapped[TestManagementProject] = relationship(back_populates="cases")
    suite: Mapped[Optional[TestSuite]] = relationship(back_populates="cases")
    folder: Mapped[Optional[TestFolder]] = relationship(back_populates="cases")
    steps: Mapped[list["TestCaseStep"]] = relationship(back_populates="case", cascade="all, delete-orphan", order_by="TestCaseStep.step_no")
    versions: Mapped[list["TestCaseVersion"]] = relationship(back_populates="case", cascade="all, delete-orphan")


class TestCaseStep(Base):
    __tablename__ = "test_management_case_steps"
    __table_args__ = (UniqueConstraint("case_id", "step_no", name="uq_tm_case_steps_case_step"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("test_management_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    step_no: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    expected_result: Mapped[str] = mapped_column(Text, nullable=False)
    test_data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}", nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)

    case: Mapped[TestCase] = relationship(back_populates="steps")


class TestCaseVersion(Base):
    __tablename__ = "test_management_case_versions"
    __table_args__ = (UniqueConstraint("case_id", "version_no", name="uq_tm_case_versions_case_version"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    case_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("test_management_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    change_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    changed_fields: Mapped[list[str]] = mapped_column(JSONB, default=list, server_default="[]", nullable=False)
    snapshot_size_bytes: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("sd_users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    case: Mapped[TestCase] = relationship(back_populates="versions")


class TestPlan(Base):
    __tablename__ = "test_management_plans"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("test_management_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    plan_type: Mapped[str] = mapped_column(String(32), default="regression", server_default="regression", nullable=False)
    release_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft", server_default="draft", nullable=False)
    scope_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("sd_users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    project: Mapped[TestManagementProject] = relationship(back_populates="plans")
    cycles: Mapped[list["TestCycle"]] = relationship(back_populates="plan", cascade="all, delete-orphan")


class RegressionSet(Base):
    __tablename__ = "test_management_regression_sets"
    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_tm_regression_sets_project_name"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("test_management_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    set_type: Mapped[str] = mapped_column(String(32), default="regression", server_default="regression", nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_filters: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}", nullable=False)
    selection_summary: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}", nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("sd_users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    project: Mapped[TestManagementProject] = relationship()
    cases: Mapped[list["RegressionSetCase"]] = relationship(back_populates="regression_set", cascade="all, delete-orphan")


class RegressionSetCase(Base):
    __tablename__ = "test_management_regression_set_cases"
    __table_args__ = (UniqueConstraint("regression_set_id", "case_id", name="uq_tm_regression_set_cases_set_case"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    regression_set_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("test_management_regression_sets.id", ondelete="CASCADE"), nullable=False, index=True)
    case_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("test_management_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    case_version_no: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    case_key_snapshot: Mapped[str] = mapped_column(String(64), nullable=False, server_default="")
    title_snapshot: Mapped[str] = mapped_column(String(500), nullable=False, server_default="")
    priority_snapshot: Mapped[str] = mapped_column(String(32), nullable=False, server_default="")
    severity_snapshot: Mapped[str] = mapped_column(String(32), nullable=False, server_default="")
    type_snapshot: Mapped[str] = mapped_column(String(64), nullable=False, server_default="")
    order_index: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    risk_score: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    include_mode: Mapped[str] = mapped_column(String(32), default="suggested", server_default="suggested", nullable=False)

    regression_set: Mapped[RegressionSet] = relationship(back_populates="cases")
    case: Mapped[TestCase] = relationship()


class TestCycle(Base):
    __tablename__ = "test_management_cycles"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    plan_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("test_management_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("test_management_projects.id", ondelete="CASCADE"), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    environment: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    build_version: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="planned", server_default="planned", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    plan: Mapped[TestPlan] = relationship(back_populates="cycles")
    runs: Mapped[list["TestRun"]] = relationship(back_populates="cycle", cascade="all, delete-orphan")


class TestRun(Base):
    __tablename__ = "test_management_runs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    cycle_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("test_management_cycles.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="not_started", server_default="not_started", nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), default="manual", server_default="manual", nullable=False)
    source_ref: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True)
    scope_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}", nullable=False)
    environment: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    cycle: Mapped[TestCycle] = relationship(back_populates="runs")
    run_cases: Mapped[list["TestRunCase"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class TestRunCase(Base):
    __tablename__ = "test_management_run_cases"
    __table_args__ = (UniqueConstraint("run_id", "case_id", name="uq_tm_run_cases_run_case"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("test_management_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    case_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("test_management_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    case_version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    case_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}", nullable=False)
    assigned_to: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("sd_users.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="not_run", server_default="not_run", nullable=False)
    actual_result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    execution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    run: Mapped[TestRun] = relationship(back_populates="run_cases")
    case: Mapped[TestCase] = relationship()
    step_results: Mapped[list["TestRunStepResult"]] = relationship(back_populates="run_case", cascade="all, delete-orphan")


class TestRunStepResult(Base):
    __tablename__ = "test_management_run_step_results"
    __table_args__ = (UniqueConstraint("run_case_id", "step_no", name="uq_tm_run_step_results_case_step"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    run_case_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("test_management_run_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    step_no: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="not_run", server_default="not_run", nullable=False)
    actual_result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    run_case: Mapped[TestRunCase] = relationship(back_populates="step_results")


class ReleaseSignoff(Base):
    __tablename__ = "test_management_release_signoffs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("test_management_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    release_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    role: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="signed", server_default="signed", nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    report_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}", nullable=False)
    signed_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("sd_users.id", ondelete="SET NULL"), nullable=True)
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ExecutionEvidence(Base):
    __tablename__ = "test_management_execution_evidence"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    run_case_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("test_management_run_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    step_result_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("test_management_run_step_results.id", ondelete="SET NULL"), nullable=True)
    artifact_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("sd_artifacts.id", ondelete="SET NULL"), nullable=True)
    file_name: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(32), default="other", server_default="other", nullable=False)
    storage_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    uploaded_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("sd_users.id", ondelete="SET NULL"), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Requirement(Base):
    __tablename__ = "test_management_requirements"
    __table_args__ = (UniqueConstraint("project_id", "external_source", "external_key", name="uq_tm_requirements_project_source_key"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("test_management_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    external_source: Mapped[str] = mapped_column(String(32), default="internal", server_default="internal", nullable=False)
    external_key: Mapped[str] = mapped_column(String(200), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(String(32), default="medium", server_default="medium", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", server_default="active", nullable=False)
    owner_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("sd_users.id", ondelete="SET NULL"), nullable=True)
    url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    source_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    version_no: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    acceptance_criteria: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, server_default="[]", nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list, server_default="[]", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    links: Mapped[list["RequirementLink"]] = relationship(back_populates="requirement")


class RequirementLink(Base):
    __tablename__ = "test_management_requirement_links"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("test_management_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    requirement_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("test_management_requirements.id", ondelete="SET NULL"), nullable=True, index=True)
    case_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("test_management_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    external_source: Mapped[str] = mapped_column(String(32), default="internal", server_default="internal", nullable=False)
    external_key: Mapped[str] = mapped_column(String(200), nullable=False)
    title_snapshot: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    source_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    coverage_status: Mapped[str] = mapped_column(String(32), default="covered", server_default="covered", nullable=False)

    requirement: Mapped[Optional[Requirement]] = relationship(back_populates="links")


class DefectLink(Base):
    __tablename__ = "test_management_defect_links"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    run_case_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("test_management_run_cases.id", ondelete="CASCADE"), nullable=False, index=True)
    step_result_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("test_management_run_step_results.id", ondelete="SET NULL"), nullable=True)
    external_source: Mapped[str] = mapped_column(String(32), default="internal", server_default="internal", nullable=False)
    external_key: Mapped[str] = mapped_column(String(200), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(100), default="open", server_default="open", nullable=False)
    severity: Mapped[str] = mapped_column(String(32), default="major", server_default="major", nullable=False)
    priority: Mapped[str] = mapped_column(String(32), default="P2", server_default="P2", nullable=False)
    assignee_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("sd_users.id", ondelete="SET NULL"), nullable=True)
    root_cause: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    retest_status: Mapped[str] = mapped_column(String(32), default="not_ready", server_default="not_ready", nullable=False)
    url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class MgmtComment(Base):
    """Polymorphic threaded comment for management entities (case/defect/plan/run/requirement)."""

    __tablename__ = "mgmt_comments"
    __table_args__ = (
        Index("ix_mgmt_comments_entity", "entity_type", "entity_id"),
        Index("ix_mgmt_comments_tenant_created", "tenant_id", "created_at"),
        Index("ix_mgmt_comments_parent", "parent_id"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(
        String(36), default=DEFAULT_TENANT_ID, server_default=DEFAULT_TENANT_ID, nullable=False, index=True
    )
    project_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("test_management_projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False)
    author_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), ForeignKey("sd_users.id", ondelete="SET NULL"), nullable=True
    )
    parent_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), ForeignKey("mgmt_comments.id", ondelete="CASCADE"), nullable=True
    )
    body_md: Mapped[str] = mapped_column(Text, nullable=False)
    mentions: Mapped[list[str]] = mapped_column(JSONB, default=list, server_default="[]", nullable=False)
    reactions: Mapped[dict[str, list[str]]] = mapped_column(
        JSONB, default=dict, server_default="{}", nullable=False
    )
    edited_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class MgmtNotification(Base):
    """In-app notification destined for a single user."""

    __tablename__ = "mgmt_notifications"
    __table_args__ = (
        Index("ix_mgmt_notif_user_unread", "user_id", "read_at"),
        Index("ix_mgmt_notif_created", "created_at"),
        Index("ix_mgmt_notif_user_archived", "user_id", "archived_at"),
        Index("ix_mgmt_notif_user_channel", "user_id", "channel"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(
        String(36), default=DEFAULT_TENANT_ID, server_default=DEFAULT_TENANT_ID, nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("sd_users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("test_management_projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    link_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    severity: Mapped[str] = mapped_column(String(16), default="info", server_default="info", nullable=False)
    channel: Mapped[str] = mapped_column(
        String(32), default="in_app", server_default="in_app", nullable=False
    )
    # ↑ delivery channel: in_app | email | push | slack | teams
    source_trace: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}", nullable=False)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class MgmtDesignTechniqueRun(Base):
    """M-1/M-2/M-9: AI-driven test design technique runs (BVA, EQ, DT, ...).

    Captures the spec (input fields), the generated case drafts, and the
    LLM trace id so promotions back to ``TestCase`` are auditable.
    """

    __tablename__ = "mgmt_design_technique_runs"
    __table_args__ = (
        Index("ix_mgmt_design_runs_tenant_tech", "tenant_id", "technique"),
        Index("ix_mgmt_design_runs_req", "requirement_id"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(
        String(36), default=DEFAULT_TENANT_ID, server_default=DEFAULT_TENANT_ID, nullable=False, index=True
    )
    project_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("test_management_projects.id", ondelete="CASCADE"),
        nullable=True,
    )
    requirement_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("test_management_requirements.id", ondelete="SET NULL"),
        nullable=True,
    )
    technique: Mapped[str] = mapped_column(String(16), nullable=False)
    # technique: BVA | EQ | DT | STD | PAIRWISE | CEG
    input_spec: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}", nullable=False)
    generated_cases: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, default=list, server_default="[]", nullable=False
    )
    llm_trace_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    source: Mapped[str] = mapped_column(
        String(16), default="manual", server_default="manual", nullable=False
    )  # llm | manual | fallback
    created_by: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), ForeignKey("sd_users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    fields: Mapped[list["MgmtDesignInputField"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    partitions: Mapped[list["MgmtDesignPartition"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class MgmtDesignInputField(Base):
    """A single input field spec attached to a design run."""

    __tablename__ = "mgmt_design_input_fields"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("mgmt_design_technique_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    data_type: Mapped[str] = mapped_column(String(32), nullable=False)
    # data_type: int | float | string | date | bool | enum
    min_value: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    max_value: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    allowed_set: Mapped[Optional[list[Any]]] = mapped_column(JSONB, nullable=True)
    nullable: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)

    run: Mapped[MgmtDesignTechniqueRun] = relationship(back_populates="fields")
    partitions: Mapped[list["MgmtDesignPartition"]] = relationship(
        back_populates="field", cascade="all, delete-orphan"
    )


class MgmtDesignPartition(Base):
    """A single equivalence-partition derived for a field (M-2)."""

    __tablename__ = "mgmt_design_partitions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("mgmt_design_technique_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    field_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("mgmt_design_input_fields.id", ondelete="CASCADE"),
        nullable=False,
    )
    partition_label: Mapped[str] = mapped_column(String(128), nullable=False)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    sample_value: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)

    run: Mapped[MgmtDesignTechniqueRun] = relationship(back_populates="partitions")
    field: Mapped[MgmtDesignInputField] = relationship(back_populates="partitions")


class MgmtCaseParamSet(Base):
    """M-9: parameter schema attached to a TestCase for data-driven expansion."""

    __tablename__ = "mgmt_case_param_sets"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(
        String(36), default=DEFAULT_TENANT_ID, server_default=DEFAULT_TENANT_ID, nullable=False, index=True
    )
    case_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("test_management_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    schema_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default="{}", nullable=False
    )  # {fields:[{name,type,required}]}
    created_by: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), ForeignKey("sd_users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    rows: Mapped[list["MgmtCaseDataRow"]] = relationship(
        back_populates="param_set", cascade="all, delete-orphan"
    )


class MgmtCaseDataRow(Base):
    """A single row of values for a `MgmtCaseParamSet`."""

    __tablename__ = "mgmt_case_data_rows"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    param_set_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("mgmt_case_param_sets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    values: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    expected: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default="{}", nullable=False
    )
    source_type: Mapped[str] = mapped_column(
        String(16), default="manual", server_default="manual", nullable=False
    )  # manual | csv | llm
    category: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    # category: boundary | typical | invalid
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    param_set: Mapped[MgmtCaseParamSet] = relationship(back_populates="rows")


class TestImportJob(Base):
    __tablename__ = "test_management_import_jobs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("test_management_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="preview", server_default="preview", nullable=False)
    mapping: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}", nullable=False)
    totals: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}", nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("sd_users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    rows: Mapped[list["TestImportJobRow"]] = relationship(back_populates="job", cascade="all, delete-orphan")


class TestImportJobRow(Base):
    __tablename__ = "test_management_import_job_rows"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    job_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("test_management_import_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    row_no: Mapped[int] = mapped_column(Integer, nullable=False)
    parsed_data: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}", nullable=False)
    validation_errors: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, server_default="[]", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ready", server_default="ready", nullable=False)
    conflict_key: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    job: Mapped[TestImportJob] = relationship(back_populates="rows")


class TestManagementAuditEvent(Base):
    __tablename__ = "test_management_audit_events"
    __table_args__ = (
        Index("ix_tm_audit_entity", "entity_type", "entity_id"),
        Index("ix_tm_audit_project_created", "project_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    project_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("test_management_projects.id", ondelete="CASCADE"), nullable=True, index=True)
    actor_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("sd_users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
