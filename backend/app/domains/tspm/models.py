"""TSPM domain models: projects, scenarios, executions, flows, regression, approvals, imports,
requirements, versions, schedules, test-data, execution-metrics, integrations, api-testing."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infra.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ═══════════════════════════════════════════════════════════════════════
# Core entities
# ═══════════════════════════════════════════════════════════════════════

class TspmProject(Base):
    __tablename__ = "tspm_projects"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default="")
    archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    base_url: Mapped[str] = mapped_column(String(500), default="", nullable=False, server_default="")
    primary_product_id: Mapped[str] = mapped_column(String(64), default="one", nullable=False, server_default="one")
    product_tags: Mapped[list[str]] = mapped_column(JSONB, default=list, nullable=False, server_default="[]")
    default_entry_key: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    # Ana sayfa "Son Açılan Proje" kartı için — /projects/{id}/touch ile güncellenir.
    last_opened_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    scenarios: Mapped[list[TspmScenario]] = relationship(back_populates="project", cascade="all, delete-orphan")
    executions: Mapped[list[TspmExecution]] = relationship(back_populates="project", cascade="all, delete-orphan")
    flows: Mapped[list[TspmFlow]] = relationship(back_populates="project", cascade="all, delete-orphan")
    regression_sets: Mapped[list[TspmRegressionSet]] = relationship(back_populates="project", cascade="all, delete-orphan")
    approvals: Mapped[list[TspmApproval]] = relationship(back_populates="project", cascade="all, delete-orphan")
    imports: Mapped[list[TspmImport]] = relationship(back_populates="project", cascade="all, delete-orphan")
    requirements: Mapped[list[TspmRequirement]] = relationship(back_populates="project", cascade="all, delete-orphan")
    schedules: Mapped[list[TspmSchedule]] = relationship(back_populates="project", cascade="all, delete-orphan")
    test_data_sets: Mapped[list[TspmTestDataSet]] = relationship(back_populates="project", cascade="all, delete-orphan")
    members: Mapped[list[TspmProjectMember]] = relationship(back_populates="project", cascade="all, delete-orphan")
    n8n_workflows: Mapped[list[TspmN8nWorkflow]] = relationship(back_populates="project", cascade="all, delete-orphan")
    automation_artifacts: Mapped[list["TspmAutomationArtifact"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
    autopilot_runs: Mapped[list["TspmAutopilotRun"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
    step_phrases: Mapped[list["TspmStepPhrase"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )
    excel_uploads: Mapped[list["TspmExcelUpload"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
    )


class TspmScenario(Base):
    __tablename__ = "tspm_scenarios"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tspm_projects.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default="")
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    current_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    steps: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(JSONB, nullable=True)
    tags: Mapped[Optional[list[str]]] = mapped_column(JSONB, nullable=True, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    # LLM-as-Judge kalite sinyali (scenario_quality_llm_0001 migration)
    quality_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    quality_issues: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(JSONB, nullable=True)
    quality_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    quality_scored_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    # nomic-embed-text 768 boyutlu vektör; pgvector yerine JSONB olarak.
    title_embedding: Mapped[Optional[list[float]]] = mapped_column(JSONB, nullable=True)

    project: Mapped[TspmProject] = relationship(back_populates="scenarios")
    versions: Mapped[list[TspmScenarioVersion]] = relationship(back_populates="scenario", cascade="all, delete-orphan")
    data_bindings: Mapped[list[TspmScenarioDataBinding]] = relationship(back_populates="scenario", cascade="all, delete-orphan")


# ═══════════════════════════════════════════════════════════════════════
# Executions
# ═══════════════════════════════════════════════════════════════════════

class TspmExecution(Base):
    __tablename__ = "tspm_executions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tspm_projects.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(300), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="running", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    # Mobil koşum alanları (nullable — masaüstü koşumlarında boş)
    platform: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    device_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    app_upload_id: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    # Engine erişilemediğinde `_simulate_run` deterministik sonuç üretir; bu
    # bayrak UI/rapor için "sonuç gerçek Playwright koşumu değil" işareti
    # taşır. SSE `summary` event'i geçicidir; execution DB'den tekrar okunduğunda
    # da simulation/real ayrımı kaybolmamalı (bkz. report/summary, executions
    # listesi). Geçmişe dönük kayıtlar default False kalır.
    simulated: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False
    )

    project: Mapped[TspmProject] = relationship(back_populates="executions")
    results: Mapped[list[TspmExecutionResult]] = relationship(back_populates="execution", cascade="all, delete-orphan")


class TspmExecutionResult(Base):
    __tablename__ = "tspm_execution_results"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    execution_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tspm_executions.id", ondelete="CASCADE"), nullable=False)
    scenario_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tspm_scenarios.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    execution: Mapped[TspmExecution] = relationship(back_populates="results")
    scenario: Mapped[TspmScenario] = relationship()


class TspmExecutionMetrics(Base):
    __tablename__ = "tspm_execution_metrics"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tspm_projects.id", ondelete="CASCADE"), nullable=False)
    execution_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tspm_executions.id", ondelete="CASCADE"), nullable=False)
    total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    passed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    skipped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pass_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class TspmAutopilotRun(Base):
    __tablename__ = "tspm_autopilot_runs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tspm_projects.id", ondelete="CASCADE"), nullable=False)
    trigger: Mapped[str] = mapped_column(String(64), default="manual", nullable=False)
    mode: Mapped[str] = mapped_column(String(32), default="autonomous", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="running", nullable=False)
    risk_level: Mapped[str] = mapped_column(String(32), default="low", nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    snapshot: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True, default=dict)
    recommendations: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(JSONB, nullable=True, default=list)
    actions: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(JSONB, nullable=True, default=list)
    action_results: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(JSONB, nullable=True, default=list)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped[TspmProject] = relationship(back_populates="autopilot_runs")


# ═══════════════════════════════════════════════════════════════════════
# Flows
# ═══════════════════════════════════════════════════════════════════════

class TspmFlow(Base):
    __tablename__ = "tspm_flows"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tspm_projects.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default="")
    nodes: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(JSONB, nullable=True, default=list)
    edges: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(JSONB, nullable=True, default=list)
    # Template metadata (added 2026-05-24 — migration: 20260524_0001_tspm_flow_template_fields)
    template_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    agent_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    tags: Mapped[Optional[list[str]]] = mapped_column(JSONB, nullable=True, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    project: Mapped[TspmProject] = relationship(back_populates="flows")


# ═══════════════════════════════════════════════════════════════════════
# Regression Sets
# ═══════════════════════════════════════════════════════════════════════

class TspmRegressionSet(Base):
    __tablename__ = "tspm_regression_sets"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tspm_projects.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default="")
    scenario_ids: Mapped[Optional[list[str]]] = mapped_column(JSONB, nullable=True, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    project: Mapped[TspmProject] = relationship(back_populates="regression_sets")


# ═══════════════════════════════════════════════════════════════════════
# Approvals
# ═══════════════════════════════════════════════════════════════════════

class TspmApproval(Base):
    __tablename__ = "tspm_approvals"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tspm_projects.id", ondelete="CASCADE"), nullable=False)
    scenario_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("tspm_scenarios.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    source_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    draft_payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    source_batch_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("tspm_ai_batches.id", ondelete="SET NULL"), nullable=True)
    source_test_case_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("tspm_test_cases.id", ondelete="SET NULL"), nullable=True)
    decision_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decision_trace: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True, default=dict)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    project: Mapped[TspmProject] = relationship(back_populates="approvals")


# ═══════════════════════════════════════════════════════════════════════
# Imports
# ═══════════════════════════════════════════════════════════════════════

class TspmImport(Base):
    __tablename__ = "tspm_imports"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tspm_projects.id", ondelete="CASCADE"), nullable=False)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="processing", nullable=False)
    scenario_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    raw_payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    project: Mapped[TspmProject] = relationship(back_populates="imports")


# ═══════════════════════════════════════════════════════════════════════
# Requirements & Coverage (Feature 4)
# ═══════════════════════════════════════════════════════════════════════

class TspmRequirement(Base):
    __tablename__ = "tspm_requirements"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tspm_projects.id", ondelete="CASCADE"), nullable=False)
    external_id: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default="")
    priority: Mapped[str] = mapped_column(String(32), default="medium", nullable=False)
    source: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    project: Mapped[TspmProject] = relationship(back_populates="requirements")
    scenario_links: Mapped[list[TspmScenarioRequirement]] = relationship(back_populates="requirement", cascade="all, delete-orphan")


class TspmScenarioRequirement(Base):
    __tablename__ = "tspm_scenario_requirements"

    scenario_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tspm_scenarios.id", ondelete="CASCADE"), primary_key=True)
    requirement_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tspm_requirements.id", ondelete="CASCADE"), primary_key=True)

    requirement: Mapped[TspmRequirement] = relationship(back_populates="scenario_links")


# ═══════════════════════════════════════════════════════════════════════
# Scenario Versions (Feature 8)
# ═══════════════════════════════════════════════════════════════════════

class TspmScenarioVersion(Base):
    __tablename__ = "tspm_scenario_versions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    scenario_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tspm_scenarios.id", ondelete="CASCADE"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    steps: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    changed_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    scenario: Mapped[TspmScenario] = relationship(back_populates="versions")


# ═══════════════════════════════════════════════════════════════════════
# Schedules (Feature 6)
# ═══════════════════════════════════════════════════════════════════════

class TspmSchedule(Base):
    __tablename__ = "tspm_schedules"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tspm_projects.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    cron_expression: Mapped[str] = mapped_column(String(100), nullable=False)
    regression_set_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("tspm_regression_sets.id", ondelete="SET NULL"), nullable=True)
    scenario_ids: Mapped[Optional[list[str]]] = mapped_column(JSONB, nullable=True, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    # Mobil koşum alanları (nullable — masaüstü schedule'larında boş)
    platform: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    device_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    project: Mapped[TspmProject] = relationship(back_populates="schedules")


# ═══════════════════════════════════════════════════════════════════════
# Test Data Sets & Bindings (Feature 10)
# ═══════════════════════════════════════════════════════════════════════

class TspmTestDataSet(Base):
    __tablename__ = "tspm_test_data_sets"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tspm_projects.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default="")
    columns: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(JSONB, nullable=True, default=list)
    rows: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(JSONB, nullable=True, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    project: Mapped[TspmProject] = relationship(back_populates="test_data_sets")


class TspmScenarioDataBinding(Base):
    __tablename__ = "tspm_scenario_data_bindings"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    scenario_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tspm_scenarios.id", ondelete="CASCADE"), nullable=False)
    data_set_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tspm_test_data_sets.id", ondelete="CASCADE"), nullable=False)
    parameter_mapping: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True, default=dict)

    scenario: Mapped[TspmScenario] = relationship(back_populates="data_bindings")


# ═══════════════════════════════════════════════════════════════════════
# Project Members (RBAC Feature 1)
# ═══════════════════════════════════════════════════════════════════════

class TspmProjectMember(Base):
    __tablename__ = "tspm_project_members"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tspm_projects.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("sd_users.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="viewer", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    project: Mapped[TspmProject] = relationship(back_populates="members")


# ═══════════════════════════════════════════════════════════════════════
# Integrations (Feature 7)
# ═══════════════════════════════════════════════════════════════════════

class TspmIntegration(Base):
    __tablename__ = "tspm_integrations"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tspm_projects.id", ondelete="CASCADE"), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    config: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


# ═══════════════════════════════════════════════════════════════════════
# API Testing (Feature 9)
# ═══════════════════════════════════════════════════════════════════════

class TspmApiCollection(Base):
    __tablename__ = "tspm_api_collections"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tspm_projects.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default="")
    base_url: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    headers: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    requests: Mapped[list[TspmApiRequest]] = relationship(back_populates="collection", cascade="all, delete-orphan")


class TspmApiRequest(Base):
    __tablename__ = "tspm_api_requests"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    collection_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tspm_api_collections.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    method: Mapped[str] = mapped_column(String(16), default="GET", nullable=False)
    path: Mapped[str] = mapped_column(String(1000), default="/", nullable=False)
    headers: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True, default=dict)
    body: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    assertions: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(JSONB, nullable=True, default=list)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    collection: Mapped[TspmApiCollection] = relationship(back_populates="requests")


class TspmApiTestRun(Base):
    __tablename__ = "tspm_api_test_runs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    collection_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tspm_api_collections.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="running", nullable=False)
    results: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(JSONB, nullable=True, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


# ═══════════════════════════════════════════════════════════════════════
# N8N Workflow Links
# ═══════════════════════════════════════════════════════════════════════

class TspmN8nWorkflow(Base):
    """Tracks an n8n workflow linked to a TestwrightAI project."""
    __tablename__ = "tspm_n8n_workflows"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tspm_projects.id", ondelete="CASCADE"), nullable=False)
    n8n_workflow_id: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default="")
    trigger_on: Mapped[str] = mapped_column(String(64), default="manual", nullable=False)
    entity_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_triggered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    webhook_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    config: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    project: Mapped[TspmProject] = relationship(back_populates="n8n_workflows")
    executions: Mapped[list[TspmN8nExecution]] = relationship(back_populates="workflow_link", cascade="all, delete-orphan")


class TspmN8nExecution(Base):
    """Log of individual n8n workflow execution results."""
    __tablename__ = "tspm_n8n_executions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    workflow_link_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tspm_n8n_workflows.id", ondelete="CASCADE"), nullable=False)
    n8n_execution_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="running", nullable=False)
    input_data: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    output_data: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    workflow_link: Mapped[TspmN8nWorkflow] = relationship(back_populates="executions")


# ═══════════════════════════════════════════════════════════════════════
# AI Test Case Generation — Faz 3
# ═══════════════════════════════════════════════════════════════════════

class TspmAiBatch(Base):
    """Tracks one AI bulk generation run (document → test cases)."""
    __tablename__ = "tspm_ai_batches"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tspm_projects.id", ondelete="CASCADE"), nullable=False)
    # Source info
    source_type: Mapped[str] = mapped_column(String(32), default="document", nullable=False)  # document | text | db_schema
    source_name: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    source_text_preview: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # first 500 chars
    analysis_artifact_kind: Mapped[str] = mapped_column(String(64), default="document_analysis", nullable=False)
    source_checksum: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    normalized_source_excerpt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extracted_requirements_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    candidate_scenarios_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    trace_links: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True, default=dict)
    # AI metadata
    ai_provider: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    ai_model: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    extra_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Status & counts
    status: Mapped[str] = mapped_column(String(32), default="generating", nullable=False)  # generating | ready | partial_error | error
    total_generated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    approved_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rejected_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped[TspmProject] = relationship()
    test_cases: Mapped[list["TspmTestCase"]] = relationship(back_populates="batch", cascade="all, delete-orphan")


class TspmTestCase(Base):
    """AI-generated test case pending review/approval."""
    __tablename__ = "tspm_test_cases"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tspm_projects.id", ondelete="CASCADE"), nullable=False)
    batch_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("tspm_ai_batches.id", ondelete="SET NULL"), nullable=True)
    # Core fields
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default="")
    module_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    feature_area: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    test_type: Mapped[str] = mapped_column(String(64), default="functional", nullable=False)  # functional | regression | smoke | edge_case | negative
    priority: Mapped[str] = mapped_column(String(32), default="medium", nullable=False)  # critical | high | medium | low
    risk_level: Mapped[str] = mapped_column(String(32), default="medium", nullable=False)  # high | medium | low
    # Steps
    preconditions: Mapped[Optional[list[str]]] = mapped_column(JSONB, nullable=True, default=list)
    steps: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(JSONB, nullable=True, default=list)
    expected_result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[list[str]]] = mapped_column(JSONB, nullable=True, default=list)
    # Review status
    review_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)  # pending | approved | rejected | edited
    reviewer_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # If approved → linked scenario
    scenario_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("tspm_scenarios.id", ondelete="SET NULL"), nullable=True)
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    batch: Mapped[Optional["TspmAiBatch"]] = relationship(back_populates="test_cases")


class TspmAutomationArtifact(Base):
    """Persisted automation outputs generated from approved test cases."""
    __tablename__ = "tspm_automation_artifacts"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("tspm_projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    batch_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("tspm_ai_batches.id", ondelete="SET NULL"),
        nullable=True,
    )
    artifact_type: Mapped[str] = mapped_column(String(32), nullable=False)  # gherkin | java | playwright
    target: Mapped[str] = mapped_column(String(32), default="shared", nullable=False)  # shared | playwright | maviyaka
    provenance: Mapped[str] = mapped_column(String(32), default="real", nullable=False)  # real | simulated | fallback | stub
    validation_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)  # pending | validated | failed | not_applicable
    generated_by: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    feature_name: Mapped[str] = mapped_column(String(300), nullable=False)
    filename: Mapped[str] = mapped_column(String(300), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    source_test_case_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    project: Mapped[TspmProject] = relationship(back_populates="automation_artifacts")
    batch: Mapped[Optional["TspmAiBatch"]] = relationship()


# ═══════════════════════════════════════════════════════════════════════
# Smart Step Builder (Feature: parametreli adım + AI öneri sistemi)
# ═══════════════════════════════════════════════════════════════════════

class TspmStepPhrase(Base):
    """AI öğrenen BDD cümlecik kütüphanesi — proje bazlı."""
    __tablename__ = "tspm_step_phrases"

    id:         Mapped[str]           = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    project_id: Mapped[str]           = mapped_column(UUID(as_uuid=False), ForeignKey("tspm_projects.id", ondelete="CASCADE"), nullable=False)
    text:       Mapped[str]           = mapped_column(String(500), nullable=False)        # "kullanıcı [url] adresine gider"
    category:   Mapped[str]           = mapped_column(String(16),  nullable=False)        # given | when | then | action
    use_count:  Mapped[int]           = mapped_column(Integer, default=0, nullable=False) # AI öğrenme skoru
    source:     Mapped[str]           = mapped_column(String(32),  nullable=False, default="seed")  # seed | ai_generated | user_defined
    created_at: Mapped[datetime]      = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=True)

    project: Mapped[TspmProject] = relationship(back_populates="step_phrases")


class TspmExcelUpload(Base):
    """Parametre kaynağı olarak yüklenen Excel dosyaları."""
    __tablename__ = "tspm_excel_uploads"

    id:          Mapped[str]           = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    project_id:  Mapped[str]           = mapped_column(UUID(as_uuid=False), ForeignKey("tspm_projects.id", ondelete="CASCADE"), nullable=False)
    filename:    Mapped[str]           = mapped_column(String(255), nullable=False)   # orijinal dosya adı
    stored_path: Mapped[str]           = mapped_column(String(512), nullable=False)   # disk yolu
    columns:     Mapped[Optional[Any]] = mapped_column(JSONB, nullable=True, default=list)  # [{"key": "A", "label": "isim"}, ...]
    row_count:   Mapped[int]           = mapped_column(Integer, default=0, nullable=False)
    file_size:   Mapped[int]           = mapped_column(Integer, default=0, nullable=False)   # byte
    created_at:  Mapped[datetime]      = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    project:    Mapped[TspmProject]             = relationship(back_populates="excel_uploads")
    parameters: Mapped[list["TspmStepParameter"]] = relationship(back_populates="excel_upload", cascade="all, delete-orphan")


class TspmStepParameter(Base):
    """Adım içindeki [parametre] kelimelerinin veri kaynağı tanımları."""
    __tablename__ = "tspm_step_parameters"

    id:               Mapped[str]           = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    # Hangi adıma ait — engine (SQLite) veya backend adım ID'si
    step_id:          Mapped[str]           = mapped_column(String(100), nullable=False)
    step_type:        Mapped[str]           = mapped_column(String(32),  nullable=False)  # manual_step | scenario_step
    project_id:       Mapped[str]           = mapped_column(UUID(as_uuid=False), ForeignKey("tspm_projects.id", ondelete="CASCADE"), nullable=False)
    word:             Mapped[str]           = mapped_column(String(200), nullable=False)  # orijinal kelime "yasin"
    position:         Mapped[int]           = mapped_column(Integer, default=0, nullable=False)  # cümle içi karakter pozisyonu
    # Kaynak tipi: random | excel | db | static
    source_type:      Mapped[str]           = mapped_column(String(16),  nullable=False, default="static")
    # random → random_type dolu
    random_type:      Mapped[Optional[str]] = mapped_column(String(32),  nullable=True)   # name | email | phone | number | uuid | date
    # excel → excel_upload_id + excel_column dolu
    excel_upload_id:  Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("tspm_excel_uploads.id", ondelete="SET NULL"), nullable=True)
    excel_column:     Mapped[Optional[str]] = mapped_column(String(100), nullable=True)   # sütun adı
    excel_row_index:  Mapped[int]           = mapped_column(Integer, default=0, nullable=False)  # sequential satır takibi
    # db → test_data_set_id + test_data_field dolu
    test_data_set_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), ForeignKey("tspm_test_data_sets.id", ondelete="SET NULL"), nullable=True)
    test_data_field:  Mapped[Optional[str]] = mapped_column(String(200), nullable=True)   # alan adı
    created_at:       Mapped[datetime]      = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    project:      Mapped[TspmProject]             = relationship()
    excel_upload: Mapped[Optional[TspmExcelUpload]] = relationship(back_populates="parameters")


# ═══════════════════════════════════════════════════════════════════════
# AI Chat Sessions & Messages
# ═══════════════════════════════════════════════════════════════════════

class AiChatSession(Base):
    __tablename__ = "ai_chat_sessions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("tspm_projects.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("sd_users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), default="Yeni Sohbet", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    messages: Mapped[list["AiChatMessage"]] = relationship(back_populates="session", cascade="all, delete-orphan", order_by="AiChatMessage.created_at")


class AiChatMessage(Base):
    __tablename__ = "ai_chat_messages"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("ai_chat_sessions.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # "user" | "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    session: Mapped[AiChatSession] = relationship(back_populates="messages")
