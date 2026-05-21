"""
SQLAlchemy modelleri — şema analizi, üretim kuralları ve geçmiş.
SQLite uyumlu (UUID yerine String kullanılıyor).
"""
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean, DateTime,
    ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from app.database import Base


def new_id():
    return str(uuid.uuid4())


class Project(Base):
    """Kullanıcı projesi — şemaları ve üretimleri gruplar."""
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=new_id)
    name = Column(String(255), nullable=False)
    description = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    schemas = relationship("DetectedSchema", back_populates="project", cascade="all, delete-orphan")
    generations = relationship("GenerationHistory", back_populates="project", cascade="all, delete-orphan")


class DetectedSchema(Base):
    """Analiz edilmiş tablo şeması."""
    __tablename__ = "detected_schemas"

    id = Column(String(36), primary_key=True, default=new_id)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    table_name = Column(String(255), nullable=False)
    source_type = Column(String(50), default="csv")
    source_info = Column(Text, default="")
    row_count = Column(Integer, default=0)
    columns = Column(JSON, nullable=False, default=list)
    relationships = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="schemas")
    rules = relationship("GenerationRule", back_populates="schema", cascade="all, delete-orphan")


class GenerationRule(Base):
    """Kolon bazlı üretim kuralları."""
    __tablename__ = "generation_rules"

    id = Column(String(36), primary_key=True, default=new_id)
    schema_id = Column(String(36), ForeignKey("detected_schemas.id"), nullable=False)
    column_name = Column(String(255), nullable=False)
    rule_type = Column(String(50), nullable=False)
    rule_config = Column(JSON, nullable=False, default=dict)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    schema = relationship("DetectedSchema", back_populates="rules")


class GenerationHistory(Base):
    """Veri üretim geçmişi."""
    __tablename__ = "generation_history"

    id = Column(String(36), primary_key=True, default=new_id)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    schema_ids = Column(JSON, default=list)
    row_count = Column(Integer, default=0)
    scenario = Column(String(100), default="default")
    format = Column(String(20), default="csv")
    status = Column(String(20), default="pending")
    result_path = Column(Text, default="")
    generated_data_preview = Column(JSON, default=list)
    duration_ms = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="generations")
