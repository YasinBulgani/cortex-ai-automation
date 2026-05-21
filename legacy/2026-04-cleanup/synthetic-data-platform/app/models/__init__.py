"""
Veritabanı modelleri paketi.

Tüm SQLAlchemy ORM modelleri ve veritabanı yardımcıları buradan import edilir.
"""

# Veritabanı altyapısı
from app.models.database import Base, SessionLocal, engine, get_db, create_tables

# ORM modelleri
from app.models.dataset import (
    Dataset,
    ColumnProfile,
    InferredRule,
    TableRelationship,
    GenerationJob,
)

# Enum sınıfları
from app.models.dataset import (
    DatasetStatus,
    RuleType,
    PIILevel,
    RelationshipType,
    Cardinality,
    GenerationStatus,
    FileType,
)

__all__ = [
    # Veritabanı altyapısı
    "Base",
    "SessionLocal",
    "engine",
    "get_db",
    "create_tables",
    # ORM modelleri
    "Dataset",
    "ColumnProfile",
    "InferredRule",
    "TableRelationship",
    "GenerationJob",
    # Enum'lar
    "DatasetStatus",
    "RuleType",
    "PIILevel",
    "RelationshipType",
    "Cardinality",
    "GenerationStatus",
    "FileType",
]
