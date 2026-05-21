"""
Pydantic request/response şemaları.

FastAPI endpoint'leri için istek doğrulama ve yanıt serileştirme
şemalarını içerir. Tüm şemalar ORM modelleri ile uyumludur.

Adım 9 güncellemesi — API katmanı için ek şemalar eklendi:
  - UploadResponse, AnalysisRequest/Response (detaylı)
  - GenerateRequest (gelişmiş), ScenarioRequest (gelişmiş)
  - NaturalLanguageRequest/Response
  - ExportResponse, JobResponse, JobListResponse
  - StatsResponse, ErrorResponse, HealthResponse
  - ClassifyResponse, PIIDetectionResponse
  - RelationshipInferRequest/Response
  - RuleInferResponse, ScenarioListResponse
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.dataset import (
    Cardinality,
    DatasetStatus,
    FileType,
    GenerationStatus,
    PIILevel,
    RelationshipType,
    RuleType,
)


# ═══════════════════════════════════════════════════════════════════════
# Dataset Şemaları
# ═══════════════════════════════════════════════════════════════════════


class DatasetCreate(BaseModel):
    """Yeni veri seti oluşturma isteği."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Veri seti adı",
        examples=["musteri_tablosu"],
    )
    description: Optional[str] = Field(
        None,
        max_length=2000,
        description="Veri seti açıklaması",
        examples=["Bireysel bankacılık müşteri verileri"],
    )
    file_type: Optional[FileType] = Field(
        None,
        description="Yüklenen dosya formatı",
    )


class DatasetResponse(BaseModel):
    """Tekil veri seti yanıtı."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None
    file_path: Optional[str] = None
    file_type: Optional[FileType] = None
    row_count: Optional[int] = None
    status: DatasetStatus
    created_at: datetime
    updated_at: datetime


class DatasetDetailResponse(DatasetResponse):
    """
    Detaylı veri seti yanıtı.

    Kolon profilleri ve kurallar dahil.
    """

    column_profiles: list["ColumnProfileResponse"] = []
    inferred_rules: list["RuleResponse"] = []


class DatasetListResponse(BaseModel):
    """Veri seti listesi yanıtı (sayfalandırma destekli)."""

    model_config = ConfigDict(from_attributes=True)

    items: list[DatasetResponse]
    total: int = Field(description="Toplam veri seti sayısı")
    page: int = Field(default=1, description="Mevcut sayfa numarası")
    page_size: int = Field(default=20, description="Sayfa başına öğe sayısı")


# ═══════════════════════════════════════════════════════════════════════
# ColumnProfile Şemaları
# ═══════════════════════════════════════════════════════════════════════


class ColumnProfileResponse(BaseModel):
    """Kolon profil ve istatistik yanıtı."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    dataset_id: int
    name: str
    data_type: str
    semantic_type: Optional[str] = None
    is_pii: bool = False
    pii_level: Optional[PIILevel] = None
    null_ratio: Optional[float] = None
    distinct_ratio: Optional[float] = None
    min_value: Optional[str] = None
    max_value: Optional[str] = None
    mean_value: Optional[float] = None
    pattern: Optional[str] = None
    sample_values: Optional[dict[str, Any]] = None
    statistics: Optional[dict[str, Any]] = None


# ═══════════════════════════════════════════════════════════════════════
# InferredRule Şemaları
# ═══════════════════════════════════════════════════════════════════════


class RuleResponse(BaseModel):
    """Çıkarılan iş kuralı yanıtı."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    dataset_id: int
    column_name: str
    rule_type: RuleType
    rule_definition: dict[str, Any]
    confidence_score: float
    is_active: bool


class RuleListResponse(BaseModel):
    """Kural listesi yanıtı."""

    model_config = ConfigDict(from_attributes=True)

    items: list[RuleResponse]
    total: int = Field(description="Toplam kural sayısı")


# ═══════════════════════════════════════════════════════════════════════
# TableRelationship Şemaları
# ═══════════════════════════════════════════════════════════════════════


class RelationshipResponse(BaseModel):
    """Tablo ilişkisi yanıtı."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    source_dataset_id: int
    target_dataset_id: int
    source_column: str
    target_column: str
    relationship_type: RelationshipType
    cardinality: Optional[Cardinality] = None
    confidence_score: float


# ═══════════════════════════════════════════════════════════════════════
# GenerationJob Şemaları
# ═══════════════════════════════════════════════════════════════════════


class GenerationRequest(BaseModel):
    """Sentetik veri üretim isteği."""

    dataset_id: int = Field(
        ...,
        description="Üretimin yapılacağı veri seti ID'si",
    )
    row_count: int = Field(
        ...,
        gt=0,
        le=100_000,
        description="Üretilecek satır sayısı",
        examples=[1000],
    )
    scenario_name: Optional[str] = Field(
        None,
        max_length=255,
        description="Senaryo adı (ör. fraud_detection, credit_application)",
        examples=["fraud_detection"],
    )
    parameters: Optional[dict[str, Any]] = Field(
        None,
        description="Ek üretim parametreleri (JSON)",
    )


class GenerationResponse(BaseModel):
    """Sentetik veri üretim yanıtı."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    dataset_id: int
    scenario_name: Optional[str] = None
    row_count: int
    parameters: Optional[dict[str, Any]] = None
    status: GenerationStatus
    output_path: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


# ═══════════════════════════════════════════════════════════════════════
# Senaryo ve Analiz Şemaları
# ═══════════════════════════════════════════════════════════════════════


class ScenarioRequest(BaseModel):
    """Senaryo tabanlı üretim isteği."""

    dataset_id: int = Field(
        ...,
        description="Kaynak veri seti ID'si",
    )
    scenario_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Senaryo adı",
        examples=["fraud_detection"],
    )
    row_count: int = Field(
        default=1000,
        gt=0,
        le=100_000,
        description="Üretilecek satır sayısı",
    )
    parameters: Optional[dict[str, Any]] = Field(
        None,
        description="Senaryoya özel parametreler",
    )


class AnalysisResponse(BaseModel):
    """Şema analiz sonucu yanıtı."""

    model_config = ConfigDict(from_attributes=True)

    dataset_id: int
    status: DatasetStatus
    column_count: int = Field(description="Analiz edilen kolon sayısı")
    rule_count: int = Field(description="Çıkarılan kural sayısı")
    relationship_count: int = Field(description="Tespit edilen ilişki sayısı")
    pii_column_count: int = Field(description="PII içeren kolon sayısı")
    columns: list[ColumnProfileResponse] = []
    rules: list[RuleResponse] = []
    relationships: list[RelationshipResponse] = []


# ═══════════════════════════════════════════════════════════════════════
# API Katmanı Ek Şemaları (Adım 9)
# ═══════════════════════════════════════════════════════════════════════


class UploadResponse(BaseModel):
    """Dosya yükleme yanıtı."""

    dataset_id: int = Field(description="Oluşturulan veri seti ID'si")
    name: str = Field(description="Veri seti adı")
    file_type: FileType = Field(description="Dosya formatı")
    file_size: int = Field(description="Dosya boyutu (byte)")
    row_count: Optional[int] = Field(None, description="Tespit edilen satır sayısı")
    message: str = Field(description="İşlem sonuç mesajı")


class ClassifyResponse(BaseModel):
    """Kolon sınıflandırma yanıtı."""

    dataset_id: int
    column_count: int = Field(description="Sınıflandırılan kolon sayısı")
    classifications: list[dict[str, Any]] = Field(
        description="Kolon sınıflandırma sonuçları"
    )
    message: str = Field(default="Kolon sınıflandırma tamamlandı")


class PIIDetectionResponse(BaseModel):
    """PII tespit sonucu yanıtı."""

    dataset_id: int
    total_columns: int = Field(description="Toplam kolon sayısı")
    pii_columns: int = Field(description="PII içeren kolon sayısı")
    risk_score: float = Field(description="Genel PII risk skoru (0-100)")
    detections: list[dict[str, Any]] = Field(
        description="Kolon bazlı PII tespit sonuçları"
    )
    kvkk_summary: Optional[dict[str, Any]] = Field(
        None, description="KVKK kategori dağılımı"
    )
    message: str = Field(default="PII tespiti tamamlandı")


class RuleInferResponse(BaseModel):
    """Kural çıkarım sonucu yanıtı."""

    dataset_id: int
    rule_count: int = Field(description="Çıkarılan kural sayısı")
    rules: list[dict[str, Any]] = Field(description="Çıkarılan kurallar listesi")
    average_confidence: float = Field(description="Ortalama güven skoru")
    type_distribution: dict[str, int] = Field(
        description="Kural tipi dağılımı"
    )
    message: str = Field(default="Kural çıkarımı tamamlandı")


class RelationshipInferRequest(BaseModel):
    """Çoklu dataset ilişki çıkarım isteği."""

    dataset_ids: list[int] = Field(
        ...,
        min_length=2,
        description="İlişki tespiti yapılacak veri seti ID'leri (en az 2)",
        examples=[[1, 2, 3]],
    )


class RelationshipInferResponse(BaseModel):
    """İlişki çıkarım sonucu yanıtı."""

    dataset_ids: list[int] = Field(description="Analiz edilen veri seti ID'leri")
    relationship_count: int = Field(description="Tespit edilen ilişki sayısı")
    relationships: list[dict[str, Any]] = Field(
        description="Tespit edilen ilişkiler"
    )
    generation_order: Optional[list[dict[str, Any]]] = Field(
        None, description="Veri üretim sırası (topological sort)"
    )
    message: str = Field(default="İlişki çıkarımı tamamlandı")


class GenerateDetailRequest(BaseModel):
    """Gelişmiş sentetik veri üretim isteği."""

    row_count: int = Field(
        default=1000,
        gt=0,
        le=100_000,
        description="Üretilecek satır sayısı",
        examples=[1000],
    )
    output_format: str = Field(
        default="csv",
        description="Çıktı formatı (csv, json, sql)",
        examples=["csv"],
    )
    rules_override: Optional[dict[str, Any]] = Field(
        None,
        description="Kural geçersiz kılma parametreleri (opsiyonel)",
    )
    seed: Optional[int] = Field(
        None,
        description="Tekrarlanabilirlik için rastgelelik tohumu",
    )
    preserve_distribution: bool = Field(
        default=True,
        description="Orijinal veri dağılımını koru",
    )


class ScenarioGenerateRequest(BaseModel):
    """Senaryo bazlı üretim isteği (gelişmiş)."""

    scenario_type: str = Field(
        ...,
        description="Senaryo tipi (ör. bireysel, premium, riskli, dormant)",
        examples=["fraud_detection"],
    )
    count: int = Field(
        default=1000,
        gt=0,
        le=100_000,
        description="Üretilecek müşteri sayısı",
    )
    custom_config: Optional[dict[str, Any]] = Field(
        None,
        description="Senaryoya özel konfigürasyon (bakiye aralığı, segment vb.)",
    )
    output_format: str = Field(
        default="csv",
        description="Çıktı formatı (csv, json)",
        examples=["csv"],
    )


class NaturalLanguageRequest(BaseModel):
    """Doğal dil ile sentetik veri üretim isteği."""

    text: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Doğal dil talebi (Türkçe veya İngilizce)",
        examples=[
            "1000 adet premium bankacılık müşterisi üret, bakiyeleri 100K-5M TL arası olsun"
        ],
    )
    output_format: str = Field(
        default="csv",
        description="Çıktı formatı (csv, json)",
        examples=["csv"],
    )


class NaturalLanguageResponse(BaseModel):
    """Doğal dil üretim yanıtı."""

    parsed_request: dict[str, Any] = Field(
        description="Doğal dilden çıkarılan parametreler"
    )
    job_id: int = Field(description="Üretim görev ID'si")
    status: str = Field(description="Görev durumu")
    message: str = Field(description="Sonuç mesajı")


class ExportResponse(BaseModel):
    """Üretilen veri dışa aktarım yanıtı."""

    job_id: int = Field(description="Üretim görev ID'si")
    format: str = Field(description="Dosya formatı (csv, json, sql)")
    file_name: str = Field(description="Dosya adı")
    file_size: int = Field(description="Dosya boyutu (byte)")
    row_count: int = Field(description="Satır sayısı")
    download_url: str = Field(description="İndirme URL'i")
    message: str = Field(default="Dışa aktarım hazır")


class JobResponse(BaseModel):
    """Üretim görevi detay yanıtı."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    dataset_id: int
    scenario_name: Optional[str] = None
    row_count: int
    parameters: Optional[dict[str, Any]] = None
    status: GenerationStatus
    output_path: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class JobListResponse(BaseModel):
    """Üretim görevi listesi yanıtı."""

    items: list[JobResponse]
    total: int = Field(description="Toplam görev sayısı")
    page: int = Field(default=1, description="Mevcut sayfa numarası")
    page_size: int = Field(default=20, description="Sayfa başına öğe sayısı")


class ScenarioInfo(BaseModel):
    """Senaryo bilgisi."""

    name: str = Field(description="Senaryo adı")
    description: str = Field(description="Senaryo açıklaması")
    default_config: dict[str, Any] = Field(
        description="Varsayılan konfigürasyon"
    )


class ScenarioListResponse(BaseModel):
    """Mevcut senaryolar listesi yanıtı."""

    scenarios: list[ScenarioInfo]
    total: int = Field(description="Toplam senaryo sayısı")


class StatsResponse(BaseModel):
    """Platform istatistikleri yanıtı."""

    total_datasets: int = Field(description="Toplam veri seti sayısı")
    total_jobs: int = Field(description="Toplam üretim görevi sayısı")
    total_rows_generated: int = Field(description="Toplam üretilen satır sayısı")
    completed_jobs: int = Field(description="Tamamlanan görev sayısı")
    failed_jobs: int = Field(description="Başarısız görev sayısı")
    active_jobs: int = Field(description="Aktif görev sayısı")
    datasets_by_status: dict[str, int] = Field(
        description="Duruma göre veri seti dağılımı"
    )
    average_generation_time: Optional[float] = Field(
        None, description="Ortalama üretim süresi (saniye)"
    )
    platform_version: str = Field(description="Platform versiyonu")


class HealthResponse(BaseModel):
    """Sağlık kontrolü yanıtı."""

    status: str = Field(description="Servis durumu")
    version: str = Field(description="Uygulama versiyonu")
    database: str = Field(description="Veritabanı bağlantı durumu")
    llm_provider: str = Field(description="LLM sağlayıcı durumu")
    uptime_seconds: Optional[float] = Field(
        None, description="Çalışma süresi (saniye)"
    )


class ErrorResponse(BaseModel):
    """Genel hata yanıtı."""

    error: str = Field(description="Hata kodu")
    message: str = Field(description="Hata mesajı (Türkçe)")
    detail: Optional[str] = Field(None, description="Detaylı hata bilgisi")
    path: Optional[str] = Field(None, description="İstek yolu")
