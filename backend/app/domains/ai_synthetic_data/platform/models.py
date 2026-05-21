"""
SQLAlchemy modelleri — sentetik veri platform alt-modülü.

Tablolar `tspm_synthetic_*` prefix'i ile ayrılır (ADR-0003 Faz 3.B).
Platform-v4'teki orijinal isimler (`projects`, `detected_schemas`, vb.)
backend'in mevcut `tspm_*` tablolarıyla çakışmasın diye prefix'lendi.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Boolean, DateTime,
    ForeignKey, JSON,
)
from sqlalchemy.orm import relationship

from app.infra.database import Base


def _new_id() -> str:
    return str(uuid.uuid4())


class SyntheticProject(Base):
    """Sentetik veri projesi — şemaları ve üretim geçmişini gruplar."""
    __tablename__ = "tspm_synthetic_projects"

    id = Column(String(36), primary_key=True, default=_new_id)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    owner_id = Column(String(64), nullable=True, index=True)  # User.id refs (opsiyonel)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    schemas = relationship(
        "SyntheticDetectedSchema",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    generations = relationship(
        "SyntheticGenerationHistory",
        back_populates="project",
        cascade="all, delete-orphan",
    )


class SyntheticDetectedSchema(Base):
    """Analiz edilmiş tablo şeması."""
    __tablename__ = "tspm_synthetic_detected_schemas"

    id = Column(String(36), primary_key=True, default=_new_id)
    project_id = Column(
        String(36),
        ForeignKey("tspm_synthetic_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    table_name = Column(String(255), nullable=False)
    source_type = Column(String(50), default="csv")  # csv | json | dataframe
    source_info = Column(Text, default="")
    row_count = Column(Integer, default=0)
    columns = Column(JSON, nullable=False, default=list)
    relationships_json = Column("relationships", JSON, default=list)
    # ``relationships`` reserved sözcük değil ama kolon adı SQLAlchemy property
    # ile çakışıyor — JSON kolon adı aynı, sınıf attribute adı _json süffixi.
    pii_summary = Column(JSON, default=dict, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("SyntheticProject", back_populates="schemas")
    rules = relationship(
        "SyntheticGenerationRule",
        back_populates="schema",
        cascade="all, delete-orphan",
    )


class SyntheticGenerationRule(Base):
    """Kolon bazlı üretim kuralı."""
    __tablename__ = "tspm_synthetic_generation_rules"

    id = Column(String(36), primary_key=True, default=_new_id)
    schema_id = Column(
        String(36),
        ForeignKey("tspm_synthetic_detected_schemas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    column_name = Column(String(255), nullable=False)
    rule_type = Column(String(50), nullable=False)   # faker | range | enum | sequential | date_range | random_string | nullable | temporal_order
    rule_config = Column(JSON, nullable=False, default=dict)
    is_active = Column(Boolean, default=True)
    learned = Column(Boolean, default=False)         # LearningEngine.apply_suggestions ile geldi mi?
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    schema = relationship("SyntheticDetectedSchema", back_populates="rules")


class SyntheticGenerationHistory(Base):
    """Veri üretim geçmişi — hem analiz hem LearningEngine için."""
    __tablename__ = "tspm_synthetic_generation_history"

    id = Column(String(36), primary_key=True, default=_new_id)
    project_id = Column(
        String(36),
        ForeignKey("tspm_synthetic_projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    schema_ids = Column(JSON, default=list)
    row_count = Column(Integer, default=0)
    scenario = Column(String(100), default="default")
    format = Column(String(20), default="csv")     # csv | json | parquet
    status = Column(String(20), default="pending") # pending | running | success | failed
    result_path = Column(Text, default="")
    generated_data_preview = Column(JSON, default=list)
    duration_ms = Column(Integer, default=0)
    error_message = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("SyntheticProject", back_populates="generations")
