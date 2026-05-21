"""Nexus Repo domain models.

NexusProject  → bir repo bağlantısı (URL, kimlik bilgileri, tip)
NexusCrawlJob → repo tarama işi (durum, log)
NexusFile     → taranan dosya kaydı
NexusEndpoint → tespit edilen API endpoint
NexusScenario → LLM tarafından üretilen test senaryosu
NexusCase     → senaryo altındaki tek bir test adımı kümesi
NexusExport   → dışa aktarma kaydı (Gherkin / Postman / Excel)
NexusLLMLog   → LLM çağrı izleri
NexusLabel    → kullanıcı etiketleri
NexusComment  → senaryolara yorum
NexusSetting  → proje başına ayarlar (JSON)
"""

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


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── 1. NexusProject ────────────────────────────────────────────────────────────

class NexusProject(Base):
    __tablename__ = "nexus_projects"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    repo_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    repo_type: Mapped[str] = mapped_column(String(50), default="git", nullable=False)  # git | svn | bitbucket | github
    branch: Mapped[str] = mapped_column(String(200), default="main", nullable=False)
    # Kimlik bilgileri şifreli env var ya da Vault'tan çekilir; DB'de plaintext saklanmaz
    credential_ref: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    llm_provider: Mapped[str] = mapped_column(String(50), default="ollama", nullable=False)  # ollama | openai | anthropic
    llm_model: Mapped[str] = mapped_column(String(100), default="qwen2.5:32b", nullable=False)
    archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    crawl_jobs: Mapped[list[NexusCrawlJob]] = relationship(back_populates="project", cascade="all, delete-orphan")
    scenarios: Mapped[list[NexusScenario]] = relationship(back_populates="project", cascade="all, delete-orphan")
    exports: Mapped[list[NexusExport]] = relationship(back_populates="project", cascade="all, delete-orphan")
    settings: Mapped[list[NexusSetting]] = relationship(back_populates="project", cascade="all, delete-orphan")


# ── 2. NexusCrawlJob ───────────────────────────────────────────────────────────

class NexusCrawlJob(Base):
    __tablename__ = "nexus_crawl_jobs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("nexus_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", nullable=False)  # pending | running | done | failed
    commit_sha: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    files_scanned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    endpoints_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    project: Mapped[NexusProject] = relationship(back_populates="crawl_jobs")
    files: Mapped[list[NexusFile]] = relationship(back_populates="crawl_job", cascade="all, delete-orphan")
    endpoints: Mapped[list[NexusEndpoint]] = relationship(back_populates="crawl_job", cascade="all, delete-orphan")


# ── 3. NexusFile ───────────────────────────────────────────────────────────────

class NexusFile(Base):
    __tablename__ = "nexus_files"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    crawl_job_id: Mapped[str] = mapped_column(ForeignKey("nexus_crawl_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    path: Mapped[str] = mapped_column(String(2000), nullable=False)
    language: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # python | typescript | java | ...
    size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tokens_estimate: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # LLM özeti
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    crawl_job: Mapped[NexusCrawlJob] = relationship(back_populates="files")


# ── 4. NexusEndpoint ──────────────────────────────────────────────────────────

class NexusEndpoint(Base):
    __tablename__ = "nexus_endpoints"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    crawl_job_id: Mapped[str] = mapped_column(ForeignKey("nexus_crawl_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    method: Mapped[str] = mapped_column(String(10), nullable=False)   # GET POST PUT DELETE PATCH
    path: Mapped[str] = mapped_column(String(2000), nullable=False)
    source_file: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    source_line: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    request_schema: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    response_schema: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    auth_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    tags: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    crawl_job: Mapped[NexusCrawlJob] = relationship(back_populates="endpoints")


# ── 5. NexusScenario ──────────────────────────────────────────────────────────

class NexusScenario(Base):
    __tablename__ = "nexus_scenarios"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("nexus_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    type: Mapped[str] = mapped_column(String(30), nullable=False)  # manual | service | automation
    feature_area: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    priority: Mapped[str] = mapped_column(String(20), default="medium", nullable=False)  # low | medium | high | critical
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False)  # draft | review | approved | rejected
    gherkin: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    llm_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    llm_prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    llm_completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    project: Mapped[NexusProject] = relationship(back_populates="scenarios")
    cases: Mapped[list[NexusCase]] = relationship(back_populates="scenario", cascade="all, delete-orphan")
    labels: Mapped[list[NexusLabel]] = relationship(back_populates="scenario", cascade="all, delete-orphan")
    comments: Mapped[list[NexusComment]] = relationship(back_populates="scenario", cascade="all, delete-orphan")


# ── 6. NexusCase ──────────────────────────────────────────────────────────────

class NexusCase(Base):
    __tablename__ = "nexus_cases"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    scenario_id: Mapped[str] = mapped_column(ForeignKey("nexus_scenarios.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    preconditions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    steps: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)  # [{step, expected, type: given|when|then}]
    expected_result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    test_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    scenario: Mapped[NexusScenario] = relationship(back_populates="cases")


# ── 7. NexusExport ────────────────────────────────────────────────────────────

class NexusExport(Base):
    __tablename__ = "nexus_exports"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("nexus_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    format: Mapped[str] = mapped_column(String(30), nullable=False)  # gherkin | postman | excel | jira
    file_path: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True)
    scenario_ids: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)  # null = tümü
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    created_by: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    project: Mapped[NexusProject] = relationship(back_populates="exports")


# ── 8. NexusLLMLog ────────────────────────────────────────────────────────────

class NexusLLMLog(Base):
    __tablename__ = "nexus_llm_logs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    project_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    operation: Mapped[str] = mapped_column(String(100), nullable=False)  # crawl_summary | scenario_gen | endpoint_parse
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


# ── 9. NexusLabel ─────────────────────────────────────────────────────────────

class NexusLabel(Base):
    __tablename__ = "nexus_labels"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    scenario_id: Mapped[str] = mapped_column(ForeignKey("nexus_scenarios.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[str] = mapped_column(String(20), default="#6366f1", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    scenario: Mapped[NexusScenario] = relationship(back_populates="labels")


# ── 10. NexusComment ─────────────────────────────────────────────────────────

class NexusComment(Base):
    __tablename__ = "nexus_comments"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    scenario_id: Mapped[str] = mapped_column(ForeignKey("nexus_scenarios.id", ondelete="CASCADE"), nullable=False, index=True)
    author: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    scenario: Mapped[NexusScenario] = relationship(back_populates="comments")


# ── 11. NexusSetting ─────────────────────────────────────────────────────────

class NexusSetting(Base):
    __tablename__ = "nexus_settings"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    project_id: Mapped[str] = mapped_column(ForeignKey("nexus_projects.id", ondelete="CASCADE"), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(200), nullable=False)
    value: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    project: Mapped[NexusProject] = relationship(back_populates="settings")
