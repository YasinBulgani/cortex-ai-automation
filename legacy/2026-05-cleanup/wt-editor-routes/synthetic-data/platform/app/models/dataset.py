"""
Veritabanı ORM modelleri — SQLAlchemy 2.0.

Bankacılık sentetik veri üretim platformunun ana veri modellerini içerir:
  - Dataset: Yüklenen veri setleri
  - ColumnProfile: Kolon profil ve istatistikleri
  - InferredRule: Otomatik çıkarılan iş kuralları
  - TableRelationship: Tablolar arası ilişkiler
  - GenerationJob: Sentetik veri üretim görevleri
"""

import enum
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.database import Base


# ═══════════════════════════════════════════════════════════════════════
# Enum Tanımları — Bankacılık domainine uygun durum ve tip sınıfları
# ═══════════════════════════════════════════════════════════════════════


class DatasetStatus(str, enum.Enum):
    """Veri seti işleme durumu."""

    UPLOADED = "uploaded"          # Yüklendi, analiz bekliyor
    ANALYZING = "analyzing"        # Şema analizi devam ediyor
    ANALYZED = "analyzed"          # Analiz tamamlandı
    GENERATING = "generating"      # Sentetik veri üretiliyor
    COMPLETED = "completed"        # İşlem tamamlandı
    FAILED = "failed"              # Hata oluştu


class RuleType(str, enum.Enum):
    """Otomatik çıkarılan kural türleri."""

    RANGE = "range"                # Değer aralığı (ör. bakiye 0-1M TL)
    ENUM = "enum"                  # Sabit değer kümesi (ör. hesap_tipi)
    REGEX = "regex"                # Düzenli ifade deseni (ör. IBAN formatı)
    DISTRIBUTION = "distribution"  # İstatistiksel dağılım (ör. normal, log-normal)
    DEPENDENCY = "dependency"      # Kolonlar arası bağımlılık


class PIILevel(str, enum.Enum):
    """Kişisel veri hassasiyet seviyesi."""

    NONE = "none"                  # PII içermiyor
    LOW = "low"                    # Düşük hassasiyet (ör. şehir)
    MEDIUM = "medium"              # Orta hassasiyet (ör. doğum tarihi)
    HIGH = "high"                  # Yüksek hassasiyet (ör. TC kimlik no)
    CRITICAL = "critical"          # Kritik hassasiyet (ör. kredi kartı no)


class RelationshipType(str, enum.Enum):
    """Tablolar arası ilişki türleri."""

    FOREIGN_KEY = "foreign_key"    # Doğrudan yabancı anahtar
    LOGICAL = "logical"            # Mantıksal ilişki (isim benzerliği vb.)
    INFERRED = "inferred"          # AI tarafından çıkarılan ilişki


class Cardinality(str, enum.Enum):
    """İlişki kardinalite türleri."""

    ONE_TO_ONE = "1:1"
    ONE_TO_MANY = "1:N"
    MANY_TO_ONE = "N:1"
    MANY_TO_MANY = "N:N"


class GenerationStatus(str, enum.Enum):
    """Sentetik veri üretim görev durumu."""

    PENDING = "pending"            # Kuyrukta bekliyor
    RUNNING = "running"            # Üretim devam ediyor
    COMPLETED = "completed"        # Başarıyla tamamlandı
    FAILED = "failed"              # Hata ile sonlandı
    CANCELLED = "cancelled"        # Kullanıcı tarafından iptal edildi


class FileType(str, enum.Enum):
    """Desteklenen dosya formatları."""

    CSV = "csv"
    SQL = "sql"
    DDL = "ddl"
    XLSX = "xlsx"
    JSON = "json"


# ═══════════════════════════════════════════════════════════════════════
# ORM Modelleri
# ═══════════════════════════════════════════════════════════════════════


class Dataset(Base):
    """
    Yüklenen veri seti modeli.

    Kullanıcının yüklediği banka veritabanı şemasını veya veri dosyasını
    temsil eder. Her veri setine ait kolon profilleri, kurallar ve
    ilişkiler ayrı tablolarda saklanır.
    """

    __tablename__ = "datasets"

    # Birincil anahtar
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Temel bilgiler
    name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Veri seti adı"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Veri seti açıklaması"
    )

    # Dosya bilgileri
    file_path: Mapped[Optional[str]] = mapped_column(
        String(1024), nullable=True, comment="Yüklenen dosyanın sunucu yolu"
    )
    file_type: Mapped[Optional[FileType]] = mapped_column(
        Enum(FileType), nullable=True, comment="Dosya formatı"
    )
    row_count: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="Veri setindeki satır sayısı"
    )

    # Durum ve zaman damgaları
    status: Mapped[DatasetStatus] = mapped_column(
        Enum(DatasetStatus),
        nullable=False,
        default=DatasetStatus.UPLOADED,
        server_default="uploaded",
        comment="Veri seti işleme durumu",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Oluşturulma zamanı",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="Son güncellenme zamanı",
    )

    # ── İlişkiler (Relationships) ────────────────────────────────────
    column_profiles: Mapped[list["ColumnProfile"]] = relationship(
        "ColumnProfile",
        back_populates="dataset",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    inferred_rules: Mapped[list["InferredRule"]] = relationship(
        "InferredRule",
        back_populates="dataset",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    generation_jobs: Mapped[list["GenerationJob"]] = relationship(
        "GenerationJob",
        back_populates="dataset",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    # Kaynak olduğu ilişkiler
    source_relationships: Mapped[list["TableRelationship"]] = relationship(
        "TableRelationship",
        foreign_keys="[TableRelationship.source_dataset_id]",
        back_populates="source_dataset",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    # Hedef olduğu ilişkiler
    target_relationships: Mapped[list["TableRelationship"]] = relationship(
        "TableRelationship",
        foreign_keys="[TableRelationship.target_dataset_id]",
        back_populates="target_dataset",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Dataset(id={self.id}, name='{self.name}', status='{self.status}')>"


class ColumnProfile(Base):
    """
    Kolon profil ve istatistik modeli.

    Bir veri setindeki her kolon için tip bilgisi, istatistikler,
    PII tespiti ve örnek değerleri saklar.
    """

    __tablename__ = "column_profiles"

    # Birincil anahtar
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Veri seti ilişkisi
    dataset_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Ait olduğu veri seti",
    )

    # Kolon temel bilgileri
    name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Kolon adı"
    )
    data_type: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="SQL veri tipi (VARCHAR, INTEGER vb.)"
    )
    semantic_type: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Semantik tip (email, iban, tc_kimlik, currency vb.)",
    )

    # PII (Kişisel Bilgi) tespiti
    is_pii: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, comment="PII içeriyor mu?"
    )
    pii_level: Mapped[Optional[PIILevel]] = mapped_column(
        Enum(PIILevel),
        nullable=True,
        default=PIILevel.NONE,
        comment="PII hassasiyet seviyesi",
    )

    # İstatistiksel profil bilgileri
    null_ratio: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="NULL değer oranı (0.0 — 1.0)"
    )
    distinct_ratio: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="Benzersiz değer oranı (0.0 — 1.0)"
    )
    min_value: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="Minimum değer (string olarak)"
    )
    max_value: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="Maksimum değer (string olarak)"
    )
    mean_value: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True, comment="Ortalama değer (sayısal kolonlar için)"
    )
    pattern: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Tespit edilen regex deseni (ör. IBAN, telefon formatı)",
    )

    # JSON alanlar — esnek ve genişletilebilir veri saklama
    sample_values: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment="Örnek değerler listesi (JSON)",
    )
    statistics: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment="Detaylı istatistikler (standart sapma, medyan, çeyrekler vb.)",
    )

    # ── İlişki ───────────────────────────────────────────────────────
    dataset: Mapped["Dataset"] = relationship(
        "Dataset", back_populates="column_profiles"
    )

    def __repr__(self) -> str:
        return (
            f"<ColumnProfile(id={self.id}, name='{self.name}', "
            f"type='{self.data_type}', semantic='{self.semantic_type}')>"
        )


class InferredRule(Base):
    """
    Otomatik çıkarılan iş kuralı modeli.

    Şema analizi sırasında veriden otomatik olarak çıkarılan kuralları saklar.
    Örneğin: bakiye aralıkları, IBAN formatı, hesap tipi enum değerleri vb.
    """

    __tablename__ = "inferred_rules"

    # Birincil anahtar
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Veri seti ilişkisi
    dataset_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Ait olduğu veri seti",
    )

    # Kural bilgileri
    column_name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Kuralın uygulandığı kolon adı"
    )
    rule_type: Mapped[RuleType] = mapped_column(
        Enum(RuleType), nullable=False, comment="Kural türü"
    )
    rule_definition: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        comment="Kural tanımı (JSON — parametreler, sınırlar, desen vb.)",
    )

    # Güven skoru ve durum
    confidence_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        comment="Kuralın güven skoru (0.0 — 1.0)",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Kural aktif mi? (Kullanıcı devre dışı bırakabilir)",
    )

    # ── İlişki ───────────────────────────────────────────────────────
    dataset: Mapped["Dataset"] = relationship(
        "Dataset", back_populates="inferred_rules"
    )

    def __repr__(self) -> str:
        return (
            f"<InferredRule(id={self.id}, column='{self.column_name}', "
            f"type='{self.rule_type}', confidence={self.confidence_score:.2f})>"
        )


class TableRelationship(Base):
    """
    Tablolar arası ilişki modeli.

    İki veri seti (tablo) arasındaki yabancı anahtar veya mantıksal
    ilişkileri saklar. İlişki yönü: source → target.
    """

    __tablename__ = "table_relationships"

    # Birincil anahtar
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Kaynak tablo bilgileri
    source_dataset_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Kaynak veri seti (ilişkinin başladığı tablo)",
    )
    source_column: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Kaynak kolon adı"
    )

    # Hedef tablo bilgileri
    target_dataset_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Hedef veri seti (ilişkinin gittiği tablo)",
    )
    target_column: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Hedef kolon adı"
    )

    # İlişki özellikleri
    relationship_type: Mapped[RelationshipType] = mapped_column(
        Enum(RelationshipType), nullable=False, comment="İlişki türü"
    )
    cardinality: Mapped[Optional[Cardinality]] = mapped_column(
        Enum(Cardinality), nullable=True, comment="Kardinalite (1:1, 1:N, N:N)"
    )
    confidence_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        default=0.0,
        comment="İlişki güven skoru (0.0 — 1.0)",
    )

    # ── İlişkiler ────────────────────────────────────────────────────
    source_dataset: Mapped["Dataset"] = relationship(
        "Dataset",
        foreign_keys=[source_dataset_id],
        back_populates="source_relationships",
    )
    target_dataset: Mapped["Dataset"] = relationship(
        "Dataset",
        foreign_keys=[target_dataset_id],
        back_populates="target_relationships",
    )

    def __repr__(self) -> str:
        return (
            f"<TableRelationship(id={self.id}, "
            f"source={self.source_dataset_id}.{self.source_column} → "
            f"target={self.target_dataset_id}.{self.target_column}, "
            f"type='{self.relationship_type}')>"
        )


class GenerationJob(Base):
    """
    Sentetik veri üretim görevi modeli.

    Bir veri seti için başlatılan her üretim işlemini takip eder.
    Senaryo adı, satır sayısı, parametreler ve üretim durumu saklanır.
    """

    __tablename__ = "generation_jobs"

    # Birincil anahtar
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Veri seti ilişkisi
    dataset_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Üretimin yapıldığı veri seti",
    )

    # Üretim parametreleri
    scenario_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Senaryo adı (ör. fraud_detection, credit_application)",
    )
    row_count: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="Üretilecek satır sayısı"
    )
    parameters: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
        comment="Üretim parametreleri (JSON — özelleştirmeler, filtreler vb.)",
    )

    # Durum bilgileri
    status: Mapped[GenerationStatus] = mapped_column(
        Enum(GenerationStatus),
        nullable=False,
        default=GenerationStatus.PENDING,
        server_default="pending",
        comment="Üretim görev durumu",
    )
    output_path: Mapped[Optional[str]] = mapped_column(
        String(1024),
        nullable=True,
        comment="Üretilen dosyanın sunucu yolu",
    )

    # Zaman damgaları
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Görev oluşturulma zamanı",
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Görev tamamlanma zamanı",
    )

    # ── İlişki ───────────────────────────────────────────────────────
    dataset: Mapped["Dataset"] = relationship(
        "Dataset", back_populates="generation_jobs"
    )

    def __repr__(self) -> str:
        return (
            f"<GenerationJob(id={self.id}, dataset_id={self.dataset_id}, "
            f"scenario='{self.scenario_name}', status='{self.status}')>"
        )
