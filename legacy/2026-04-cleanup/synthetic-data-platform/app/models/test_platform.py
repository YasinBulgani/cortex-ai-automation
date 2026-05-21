"""
Test Platform SQLAlchemy Modelleri (15+ model, versioning, audit, soft-delete).

Tablolar:
  - test_projects       : Test projesi kaydı
  - test_suites         : Test suite'i (proje altında)
  - test_cases          : Üretilen test case'ler
  - test_runs           : Test çalıştırma oturumları
  - test_results        : Bireysel test sonuçları
  - bug_reports         : Otomatik üretilen bug taslakları
  - doc_analyses        : Doküman analiz geçmişi
  - schedules           : Zamanlama kayıtları
  - learning_records    : Flaky/yavaş test öğrenme kayıtları
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Integer, String, Text, JSON,
)
from sqlalchemy.orm import relationship

from app.models.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


# ═══════════════════════════════════════════════════════════════════════
# 1. TestProject — Test Projesi
# ═══════════════════════════════════════════════════════════════════════

class TestProject(Base):
    """Test projesi — birden fazla test suite içerebilir."""
    __tablename__ = "test_projects"

    id = Column(String(36), primary_key=True, default=_uuid)
    name = Column(String(200), nullable=False)
    description = Column(Text, default="")
    document_type = Column(String(50), default="unknown")   # BRD / FRD / user_story
    owner = Column(String(100), default="")
    is_active = Column(Boolean, default=True)
    deleted_at = Column(DateTime, nullable=True)             # Soft-delete
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # İlişkiler
    suites = relationship("TestSuite", back_populates="project", cascade="all, delete-orphan")
    doc_analyses = relationship("DocAnalysis", back_populates="project", cascade="all, delete-orphan")


# ═══════════════════════════════════════════════════════════════════════
# 2. TestSuite — Test Suite
# ═══════════════════════════════════════════════════════════════════════

class TestSuite(Base):
    """Test suite — test case'lerin grubu."""
    __tablename__ = "test_suites"

    id = Column(String(36), primary_key=True, default=_uuid)
    project_id = Column(String(36), ForeignKey("test_projects.id"), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, default="")
    status = Column(String(20), default="active")           # active / archived
    version = Column(Integer, default=1)                    # Versioning
    total_cases = Column(Integer, default=0)
    deleted_at = Column(DateTime, nullable=True)            # Soft-delete
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # İlişkiler
    project = relationship("TestProject", back_populates="suites")
    test_cases = relationship("TestCaseModel", back_populates="suite", cascade="all, delete-orphan")
    test_runs = relationship("TestRun", back_populates="suite", cascade="all, delete-orphan")


# ═══════════════════════════════════════════════════════════════════════
# 3. TestCaseModel — Test Case
# ═══════════════════════════════════════════════════════════════════════

class TestCaseModel(Base):
    """Üretilen veya manuel oluşturulan test case kaydı."""
    __tablename__ = "test_cases"

    id = Column(String(36), primary_key=True, default=_uuid)
    suite_id = Column(String(36), ForeignKey("test_suites.id"), nullable=False)
    external_id = Column(String(50), nullable=False, default=_uuid)    # TC-FUNC-001 vb.
    title = Column(String(500), nullable=False)
    description = Column(Text, default="")
    test_type = Column(String(50), default="functional")
    priority = Column(String(20), default="medium")
    preconditions = Column(JSON, default=list)
    steps = Column(JSON, default=list)
    expected_outcome = Column(Text, default="")
    test_data = Column(JSON, default=dict)
    environment = Column(String(50), default="staging")
    is_automatable = Column(Boolean, default=True)
    recommended_framework = Column(String(50), default="playwright")
    automation_script = Column(Text, default="")
    estimated_duration_minutes = Column(Integer, default=5)
    tags = Column(JSON, default=list)
    requirement_ids = Column(JSON, default=list)
    linked_req_id = Column(String(50), default="")
    version = Column(Integer, default=1)                                # Versioning
    deleted_at = Column(DateTime, nullable=True)                        # Soft-delete
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # İlişkiler
    suite = relationship("TestSuite", back_populates="test_cases")
    results = relationship("TestResultModel", back_populates="test_case", cascade="all, delete-orphan")
    bug_reports = relationship("BugReportModel", back_populates="test_case")


# ═══════════════════════════════════════════════════════════════════════
# 4. TestRun — Test Çalıştırma Oturumu
# ═══════════════════════════════════════════════════════════════════════

class TestRun(Base):
    """Test çalıştırma oturumu."""
    __tablename__ = "test_runs"

    id = Column(String(36), primary_key=True, default=_uuid)
    suite_id = Column(String(36), ForeignKey("test_suites.id"), nullable=False)
    execution_id = Column(String(36), unique=True, default=_uuid)
    mode = Column(String(20), default="simulate")           # simulate / real / ci_cd
    status = Column(String(20), default="pending")          # pending / running / passed / failed
    environment = Column(String(50), default="staging")
    triggered_by = Column(String(100), default="api")
    total = Column(Integer, default=0)
    passed = Column(Integer, default=0)
    failed = Column(Integer, default=0)
    skipped = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    pass_rate = Column(Float, default=0.0)
    duration_seconds = Column(Float, default=0.0)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # İlişkiler
    suite = relationship("TestSuite", back_populates="test_runs")
    results = relationship("TestResultModel", back_populates="run", cascade="all, delete-orphan")
    bug_reports = relationship("BugReportModel", back_populates="run")


# ═══════════════════════════════════════════════════════════════════════
# 5. TestResultModel — Bireysel Test Sonucu
# ═══════════════════════════════════════════════════════════════════════

class TestResultModel(Base):
    """Tek bir test case'in çalıştırma sonucu."""
    __tablename__ = "test_results"

    id = Column(String(36), primary_key=True, default=_uuid)
    run_id = Column(String(36), ForeignKey("test_runs.id"), nullable=False)
    test_case_id = Column(String(36), ForeignKey("test_cases.id"), nullable=True)
    external_tc_id = Column(String(50), default="")
    status = Column(String(20), default="pending")          # passed / failed / skipped / error
    duration_seconds = Column(Float, default=0.0)
    output = Column(Text, default="")
    error_message = Column(Text, default="")
    screenshot_path = Column(String(500), default="")
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    # İlişkiler
    run = relationship("TestRun", back_populates="results")
    test_case = relationship("TestCaseModel", back_populates="results")


# ═══════════════════════════════════════════════════════════════════════
# 6. BugReportModel — Otomatik Bug Raporu
# ═══════════════════════════════════════════════════════════════════════

class BugReportModel(Base):
    """Otomatik oluşturulan bug raporu kaydı."""
    __tablename__ = "bug_reports"

    id = Column(String(36), primary_key=True, default=_uuid)
    bug_id = Column(String(20), unique=True, nullable=False, default=lambda: f"BUG-{_uuid()[:8].upper()}")
    run_id = Column(String(36), ForeignKey("test_runs.id"), nullable=True)
    test_case_id = Column(String(36), ForeignKey("test_cases.id"), nullable=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, default="")
    severity = Column(String(20), default="major")          # critical / major / minor / trivial
    priority = Column(String(20), default="high")
    environment = Column(String(100), default="staging")
    steps_to_reproduce = Column(JSON, default=list)
    expected_result = Column(Text, default="")
    actual_result = Column(Text, default="")
    error_message = Column(Text, default="")
    labels = Column(JSON, default=list)
    component = Column(String(100), default="")
    formatted_jira = Column(Text, default="")
    formatted_github = Column(Text, default="")
    is_resolved = Column(Boolean, default=False)
    deleted_at = Column(DateTime, nullable=True)            # Soft-delete
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # İlişkiler
    run = relationship("TestRun", back_populates="bug_reports")
    test_case = relationship("TestCaseModel", back_populates="bug_reports")


# ═══════════════════════════════════════════════════════════════════════
# 7. DocAnalysis — Doküman Analizi Geçmişi
# ═══════════════════════════════════════════════════════════════════════

class DocAnalysis(Base):
    """BRD/FRD/User Story analiz sonucu kaydı."""
    __tablename__ = "doc_analyses"

    id = Column(String(36), primary_key=True, default=_uuid)
    project_id = Column(String(36), ForeignKey("test_projects.id"), nullable=True)
    document_type = Column(String(50), default="unknown")
    title = Column(String(300), default="")
    content_preview = Column(Text, default="")              # İlk 500 karakter
    total_requirements = Column(Integer, default=0)
    high_priority_count = Column(Integer, default=0)
    coverage_score = Column(Float, default=0.0)
    requirements_json = Column(JSON, default=list)          # Tüm gereksinimler
    risk_areas = Column(JSON, default=list)
    missing_details = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

    # İlişkiler
    project = relationship("TestProject", back_populates="doc_analyses")


# ═══════════════════════════════════════════════════════════════════════
# 8. ScheduleModel — Zamanlama Kaydı
# ═══════════════════════════════════════════════════════════════════════

class ScheduleModel(Base):
    """Test suite zamanlama kaydı."""
    __tablename__ = "test_schedules"

    id = Column(String(36), primary_key=True, default=_uuid)
    suite_id = Column(String(36), ForeignKey("test_suites.id"), nullable=False)
    cron_expression = Column(String(100), nullable=False)   # "0 9 * * 1-5"
    status = Column(String(20), default="active")           # active / paused / cancelled
    ci_system = Column(String(50), default="")              # jenkins / gitlab / azure / github_actions
    webhook_url = Column(String(500), default="")
    run_count = Column(Integer, default=0)
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ═══════════════════════════════════════════════════════════════════════
# 9. LearningRecord — Öğrenme Kaydı
# ═══════════════════════════════════════════════════════════════════════

class LearningRecord(Base):
    """Flaky test tespiti ve öğrenme kaydı."""
    __tablename__ = "learning_records"

    id = Column(String(36), primary_key=True, default=_uuid)
    test_case_id = Column(String(36), ForeignKey("test_cases.id"), nullable=True)
    external_tc_id = Column(String(50), default="")
    record_type = Column(String(50), default="flaky")       # flaky / slow / regression / improvement
    flaky_rate = Column(Float, default=0.0)                 # 0.0 — 1.0
    avg_duration_ms = Column(Float, default=0.0)
    failure_count = Column(Integer, default=0)
    run_count = Column(Integer, default=0)
    last_failure_reason = Column(Text, default="")
    recommendation = Column(Text, default="")
    is_quarantined = Column(Boolean, default=False)         # Flaky test karantinası
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
