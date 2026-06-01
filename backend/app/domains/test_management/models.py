"""SQLAlchemy models for Neurex Management manual test operations."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
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
    __table_args__ = (UniqueConstraint("project_id", "case_key", name="uq_tm_cases_project_key"),)

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
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    run_case: Mapped[TestRunCase] = relationship(back_populates="step_results")


class ReleaseSignoff(Base):
    __tablename__ = "test_management_release_signoffs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("test_management_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    release_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
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

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    project_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("test_management_projects.id", ondelete="CASCADE"), nullable=True, index=True)
    actor_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("sd_users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
