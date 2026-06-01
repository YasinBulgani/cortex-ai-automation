"""Veritabanı modelleri (ERD: kullanıcılar, katalog, kurallar, işler, denetim, artefaktlar)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infra.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


sd_user_roles = Table(
    "sd_user_roles",
    Base.metadata,
    Column(
        "user_id",
        UUID(as_uuid=False),
        ForeignKey("sd_users.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "role_id",
        UUID(as_uuid=False),
        ForeignKey("sd_roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Role(Base):
    __tablename__ = "sd_roles"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    users: Mapped[list["User"]] = relationship(
        "User", secondary=sd_user_roles, back_populates="roles"
    )
    permissions: Mapped[list["RolePermission"]] = relationship(
        back_populates="role", cascade="all, delete-orphan"
    )


class RolePermission(Base):
    __tablename__ = "sd_role_permissions"

    role_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("sd_roles.id", ondelete="CASCADE"), primary_key=True
    )
    permission: Mapped[str] = mapped_column(String(128), primary_key=True)

    role: Mapped[Role] = relationship(back_populates="permissions")


_DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"


class User(Base):
    __tablename__ = "sd_users"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    department: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    tenant_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        default=_DEFAULT_TENANT_ID,
        server_default=_DEFAULT_TENANT_ID,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    # ── MFA / TOTP ───────────────────────────────────────────────
    totp_secret: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default="false")
    mfa_backup_codes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    roles: Mapped[list[Role]] = relationship(
        secondary=sd_user_roles, back_populates="users"
    )


class RefreshToken(Base):
    __tablename__ = "sd_refresh_tokens"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True,
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("sd_users.id", ondelete="CASCADE"), nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False,
    )
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship(backref="refresh_tokens")


class Dataset(Base):
    __tablename__ = "sd_datasets"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), ForeignKey("sd_users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    versions: Mapped[list[DatasetVersion]] = relationship(
        back_populates="dataset", cascade="all, delete-orphan"
    )


class DatasetVersion(Base):
    __tablename__ = "sd_dataset_versions"
    __table_args__ = (
        UniqueConstraint("dataset_id", "version", name="uq_sd_dataset_version"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    dataset_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("sd_datasets.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    dataset: Mapped[Dataset] = relationship(back_populates="versions")
    schema_snapshot: Mapped[Optional["SchemaSnapshot"]] = relationship(
        back_populates="dataset_version", uselist=False, cascade="all, delete-orphan"
    )
    generation_jobs: Mapped[list[GenerationJob]] = relationship(
        back_populates="dataset_version"
    )


class SchemaSnapshot(Base):
    __tablename__ = "sd_schema_snapshots"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    dataset_version_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("sd_dataset_versions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    profile: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    pii_flags: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    dataset_version: Mapped[DatasetVersion] = relationship(
        back_populates="schema_snapshot"
    )


class RuleSet(Base):
    __tablename__ = "sd_rule_sets"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    dataset_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("sd_datasets.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    rules_body: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class GenerationJob(Base):
    __tablename__ = "sd_generation_jobs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    dataset_version_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("sd_dataset_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    rule_set_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), ForeignKey("sd_rule_sets.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False)
    rq_job_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), ForeignKey("sd_users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    dataset_version: Mapped[DatasetVersion] = relationship(
        back_populates="generation_jobs"
    )
    events: Mapped[list[JobEvent]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    artifacts: Mapped[list[Artifact]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class JobEvent(Base):
    __tablename__ = "sd_job_events"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    job_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("sd_generation_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    level: Mapped[str] = mapped_column(String(16), default="info", nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    job: Mapped[GenerationJob] = relationship(back_populates="events")


class AuditEvent(Base):
    __tablename__ = "sd_audit_events"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    ts: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )
    actor_user_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), ForeignKey("sd_users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    ip: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # ── Hash chain (Dalga 0 · BDDK tamper-evident) ────────────────────
    # Migration 20260419_0007_bind_audit_hash_chain ekler.
    tenant_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    seq: Mapped[Optional[int]] = mapped_column(nullable=True)
    prev_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)


class Artifact(Base):
    __tablename__ = "sd_artifacts"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    job_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("sd_generation_jobs.id", ondelete="CASCADE"),
        nullable=False,
    )
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    job: Mapped[GenerationJob] = relationship(back_populates="artifacts")


class AgentV2Run(Base):
    __tablename__ = "sd_agent_v2_runs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True)
    tenant_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True, index=True)
    project_id: Mapped[str] = mapped_column(UUID(as_uuid=False), nullable=False, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True)
    input_source: Mapped[str] = mapped_column(String(32), nullable=False)
    input_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False, index=True)
    workflow_type: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    dry_run: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    intent_graph: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    app_map: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    scenarios: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(JSONB, nullable=True)
    generated_code: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    run_result: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    healing_result: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    review: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    report: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    errors: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    tokens_used: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    llm_calls_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_usd: Mapped[float] = mapped_column(Numeric(10, 6), default=0, nullable=False)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Numeric(10, 3), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    events: Mapped[list["AgentV2RunEvent"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    artifacts: Mapped[list["AgentV2RunArtifact"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    approvals: Mapped[list["AgentV2RunApproval"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )


class AgentV2RunEvent(Base):
    __tablename__ = "sd_agent_v2_run_events"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("sd_agent_v2_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    agent_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    run: Mapped[AgentV2Run] = relationship(back_populates="events")


class AgentV2RunArtifact(Base):
    __tablename__ = "sd_agent_v2_run_artifacts"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("sd_agent_v2_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), default="application/octet-stream", nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    run: Mapped[AgentV2Run] = relationship(back_populates="artifacts")


class AgentV2RunApproval(Base):
    __tablename__ = "sd_agent_v2_run_approvals"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("sd_agent_v2_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_user_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    run: Mapped["AgentV2Run"] = relationship(back_populates="approvals")


class AutomationRun(Base):
    __tablename__ = "sd_automation_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False, index=True)
    trigger: Mapped[str] = mapped_column(String(32), default="manual", nullable=False)
    environment: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    device: Mapped[Optional[str]] = mapped_column(String(160), nullable=True)
    target: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    provenance: Mapped[str] = mapped_column(String(32), default="fallback", nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), ForeignKey("sd_users.id", ondelete="SET NULL"), nullable=True
    )
    retry_of: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    artifacts: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False, default=list)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    next_action: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    run_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class AgentV2DeadLetter(Base):
    __tablename__ = "sd_agent_v2_dead_letters"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    run_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True, index=True)
    queue_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)


# ── DSL Sözlüğü: Düzenleme Önerileri + Audit + Kullanıcı Geri Bildirimi ─────


class DslEditProposal(Base):
    """DSL cümleciği için bir düzenleme önerisi (human veya AI kaynaklı).

    Proposal akışı:
        pending → approved → merged (veya rejected)

    `diff`: `{"op": "create|update|delete|deprecate",
              "before": {...}, "after": {...}, "changed_fields": [...]}`
    Direct-commit modunda proposal create edildiği anda approved + merged olur.
    """

    __tablename__ = "sd_dsl_edit_proposals"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    action_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    proposer_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("sd_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # "human" | "ai"
    proposer_kind: Mapped[str] = mapped_column(
        String(16), nullable=False, default="human"
    )
    # "create" | "update" | "delete" | "deprecate"
    operation: Mapped[str] = mapped_column(String(16), nullable=False)
    # "pending" | "approved" | "rejected" | "merged" | "error"
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending", index=True
    )
    diff: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    ai_reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # Git entegrasyonu
    base_commit_sha: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    branch: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    commit_sha: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    pr_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # İnceleyen admin (approve/reject)
    reviewer_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("sd_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewer_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )


class DslCatalogAudit(Base):
    """DSL kataloğunda gerçekleşen her değişikliğin kalıcı kaydı.

    AuditEvent'in DSL-özel kardeş tablosu — proposal işaretlenip git commit
    başarıyla atıldığında bu tabloya bir satır yazılır. Log'lanan gerçek
    "katalog değişti" olayıdır; rollback/forensics için kullanılır.
    """

    __tablename__ = "sd_dsl_catalog_audit"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    action_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    operation: Mapped[str] = mapped_column(String(16), nullable=False)
    actor_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("sd_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    proposal_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("sd_dsl_edit_proposals.id", ondelete="SET NULL"),
        nullable=True,
    )
    commit_sha: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    pr_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    diff: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )


class DslFeedback(Base):
    """DSL arama sonucu için 👍 / 👎 geri bildirim kaydı.

    Skor rerank'ı için kullanılır: belirli bir `query`'e `action_id` için
    net pozitif geri bildirim varsa o cümleciğin skoruna bonus verilir.
    """

    __tablename__ = "sd_dsl_feedback"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=_uuid
    )
    user_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("sd_users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    query: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    action_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    # "up" | "down" | "ignored"
    vote: Mapped[str] = mapped_column(String(16), nullable=False)
    # "lexical" | "semantic" | "hybrid" | "llm_rerank"
    search_mode: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    raw_score: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )
