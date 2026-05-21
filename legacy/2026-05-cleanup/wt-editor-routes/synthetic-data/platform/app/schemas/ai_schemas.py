"""
AI Schemaları Modülü

Bu modül, AI/ML endpoint'leri için Pydantic v2 schemaları tanımlar.

Başlıca Sınıflar:
    - GANEvaluationRequest/Result
    - AnomalyDetectionRequest/Report
    - TunerConfig/Result
    - NLPAnalysisRequest/Result
    - ModelStatus
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, List, Optional, Any
from enum import Enum


class MethodType(str, Enum):
    """Optimizasyon yöntemi enum'ı."""
    BAYESIAN = "bayesian"
    GRID = "grid"


class DistributionType(str, Enum):
    """Dağılım türü enum'ı."""
    GAUSSIAN = "gaussian"
    UNIFORM = "uniform"
    LOGNORMAL = "lognormal"


# ============================================================================
# GAN Discriminator Schemaları
# ============================================================================

class GANEvaluationRequest(BaseModel):
    """
    GAN değerlendirme isteği schemaması.

    Parametreler:
        synthetic_data: Değerlendirmek için sentez veri (örnek sayısı x özellik sayısı)
        real_data: Gerçek veri (isteğe bağlı, karşılaştırma için)
        evaluate_quality: Kalite metriği hesaplanacak mı
    """
    synthetic_data: List[List[float]] = Field(
        ...,
        description="Değerlendirmek için sentez veri",
        examples=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    )
    real_data: Optional[List[List[float]]] = Field(
        None,
        description="Gerçek veri (isteğe bağlı, karşılaştırma için)"
    )
    evaluate_quality: bool = Field(
        True,
        description="Kalite metriklerini hesapla"
    )

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "synthetic_data": [[0.1, 0.2], [0.3, 0.4]],
            "real_data": [[0.15, 0.25], [0.35, 0.45]],
            "evaluate_quality": True
        }
    })


class FeatureImportanceItem(BaseModel):
    """Özellik önem puanı."""
    feature_name: str = Field(..., description="Özellik adı")
    importance_score: float = Field(..., description="Önem puanı (0-1)")


class DiscriminatorMetrics(BaseModel):
    """Discriminator metrikleri."""
    accuracy: float = Field(..., description="Doğruluk (0-1)")
    precision: float = Field(..., description="Kesinlik (0-1)")
    recall: float = Field(..., description="Geri çağırma (0-1)")
    f1_score: float = Field(..., description="F1 puanı (0-1)")
    auc_roc: float = Field(..., description="AUC-ROC puanı (0-1)")


class GANEvaluationResult(BaseModel):
    """
    GAN değerlendirme sonucu schemaması.

    Parametreler:
        quality_score: Genel kalite puanı (0-1)
        metrics: Discriminator metrikleri
        feature_importance: Özellik önem puanları
        is_synthetic: Veri sentez olarak sınıflandırıldı mı
        timestamp: İşlem zaman damgası
    """
    quality_score: float = Field(
        ...,
        description="Genel veri kalitesi puanı (0-1, 1 en iyi)",
        ge=0.0,
        le=1.0
    )
    metrics: DiscriminatorMetrics = Field(..., description="Discriminator metrikleri")
    feature_importance: List[FeatureImportanceItem] = Field(
        ...,
        description="Özellik önem puanları"
    )
    is_synthetic: float = Field(
        ...,
        description="Sentetik veri olma olasılığı (0-1)",
        ge=0.0,
        le=1.0
    )
    timestamp: str = Field(..., description="ISO 8601 zaman damgası")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "quality_score": 0.85,
            "metrics": {
                "accuracy": 0.92,
                "precision": 0.88,
                "recall": 0.90,
                "f1_score": 0.89,
                "auc_roc": 0.95
            },
            "feature_importance": [
                {"feature_name": "feature_0", "importance_score": 0.35},
                {"feature_name": "feature_1", "importance_score": 0.25}
            ],
            "is_synthetic": 0.15,
            "timestamp": "2026-03-29T10:30:00Z"
        }
    })


# ============================================================================
# Anomaly Detection Schemaları
# ============================================================================

class AnomalyDetectionRequest(BaseModel):
    """
    Anomali tespiti isteği schemaması.

    Parametreler:
        data: Anomali tespiti yapılacak veri
        detection_methods: Kullanılacak yöntemler (z_score, pattern, isolation_forest)
        contamination: Beklenen anomali oranı
        feature_names: Özellik adları (isteğe bağlı)
    """
    data: List[List[float]] = Field(
        ...,
        description="Anomali tespiti yapılacak veri",
        examples=[[0.1, 0.2], [0.3, 0.4], [10.0, 20.0]]
    )
    detection_methods: List[str] = Field(
        ["z_score", "pattern", "isolation_forest"],
        description="Kullanılacak anomali tespiti yöntemleri"
    )
    contamination: float = Field(
        0.05,
        description="Beklenen anomali oranı (0-1)",
        ge=0.0,
        le=1.0
    )
    feature_names: Optional[List[str]] = Field(
        None,
        description="Özellik adları"
    )

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "data": [[0.1, 0.2], [0.3, 0.4], [10.0, 20.0]],
            "detection_methods": ["z_score", "isolation_forest"],
            "contamination": 0.05,
            "feature_names": ["feature_0", "feature_1"]
        }
    })


class AnomalyInfo(BaseModel):
    """Anomali bilgisi."""
    index: int = Field(..., description="Veri indeksi")
    anomaly_score: float = Field(..., description="Anomali puanı (0-1)")
    severity: str = Field(..., description="Şiddet seviyesi (low, medium, high)")
    detected_by: List[str] = Field(..., description="Tespit yöntemi")


class AnomalyReport(BaseModel):
    """
    Anomali raporu schemaması.

    Parametreler:
        total_samples: Toplam örnek sayısı
        anomaly_count: Tespit edilen anomali sayısı
        anomaly_percentage: Anomali yüzdesi
        severity_distribution: Şiddet dağılımı
        top_anomalies: En yüksek puanlı anomaliler
        detected_patterns: Tespit edilen desenler
        recommendations: Öneriler
        timestamp: Zaman damgası
    """
    total_samples: int = Field(..., description="Toplam örnek sayısı")
    anomaly_count: int = Field(..., description="Tespit edilen anomali sayısı")
    anomaly_percentage: float = Field(
        ...,
        description="Anomali yüzdesi (0-100)",
        ge=0.0,
        le=100.0
    )
    severity_distribution: Dict[str, int] = Field(
        ...,
        description="Şiddet seviyesi dağılımı (low, medium, high)"
    )
    top_anomalies: List[AnomalyInfo] = Field(
        ...,
        description="En yüksek puanlı anomaliler"
    )
    detected_patterns: List[str] = Field(
        ...,
        description="Tespit edilen anomali desenler"
    )
    recommendations: List[str] = Field(
        ...,
        description="Öneriler"
    )
    timestamp: str = Field(..., description="ISO 8601 zaman damgası")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "total_samples": 1000,
            "anomaly_count": 45,
            "anomaly_percentage": 4.5,
            "severity_distribution": {"low": 30, "medium": 12, "high": 3},
            "top_anomalies": [
                {"index": 156, "anomaly_score": 0.92, "severity": "high", "detected_by": ["z_score", "isolation_forest"]}
            ],
            "detected_patterns": ["Z-score anomali (3 örnek)"],
            "recommendations": ["Yüksek şiddetli anomaliler veri kalitesi sorununu gösterebilir"],
            "timestamp": "2026-03-29T10:30:00Z"
        }
    })


# ============================================================================
# Auto Tuner Schemaları
# ============================================================================

class TunerConfig(BaseModel):
    """
    Tuner konfigürasyonu schemaması.

    Parametreler:
        synthetic_data: Sentez veri
        real_data: Gerçek veri
        optimization_method: Optimizasyon yöntemi (bayesian, grid)
        max_iterations: Maksimum iterasyon sayısı
        distribution_type: Dağılım türü
    """
    synthetic_data: List[List[float]] = Field(
        ...,
        description="Sentez veri"
    )
    real_data: Optional[List[List[float]]] = Field(
        None,
        description="Gerçek veri (karşılaştırma için)"
    )
    optimization_method: MethodType = Field(
        MethodType.BAYESIAN,
        description="Optimizasyon yöntemi"
    )
    max_iterations: int = Field(
        20,
        description="Maksimum iterasyon sayısı",
        ge=5,
        le=100
    )
    distribution_type: DistributionType = Field(
        DistributionType.GAUSSIAN,
        description="Dağılım türü"
    )

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "synthetic_data": [[0.1, 0.2], [0.3, 0.4]],
            "real_data": [[0.15, 0.25], [0.35, 0.45]],
            "optimization_method": "bayesian",
            "max_iterations": 20,
            "distribution_type": "gaussian"
        }
    })


class QualityMetrics(BaseModel):
    """Kalite metrikleri."""
    mean_difference: float = Field(..., description="Ortalama farkı")
    std_difference: float = Field(..., description="Standart sapma farkı")
    correlation_difference: float = Field(..., description="Korelasyon farkı")
    ks_distance: float = Field(..., description="Kolmogorov-Smirnov mesafesi")
    overall_score: float = Field(..., description="Genel kalite puanı (0-1)")


class TunerResult(BaseModel):
    """
    Tuner sonucu schemaması.

    Parametreler:
        best_parameters: En iyi parametreler
        best_quality_score: En iyi kalite puanı
        quality_metrics: Kalite metrikleri
        iterations_completed: Tamamlanan iterasyon sayısı
        optimization_time_seconds: Optimizasyon süresi
        timestamp: Zaman damgası
    """
    best_parameters: Dict[str, float] = Field(
        ...,
        description="En iyi parametreler"
    )
    best_quality_score: float = Field(
        ...,
        description="En iyi kalite puanı (0-1)",
        ge=0.0,
        le=1.0
    )
    quality_metrics: QualityMetrics = Field(
        ...,
        description="Kalite metrikleri"
    )
    iterations_completed: int = Field(
        ...,
        description="Tamamlanan iterasyon sayısı"
    )
    optimization_time_seconds: float = Field(
        ...,
        description="Optimizasyon süresi (saniye)"
    )
    timestamp: str = Field(..., description="ISO 8601 zaman damgası")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "best_parameters": {
                "learning_rate": 0.005,
                "batch_size": 64,
                "noise_scale": 0.05
            },
            "best_quality_score": 0.87,
            "quality_metrics": {
                "mean_difference": 0.05,
                "std_difference": 0.08,
                "correlation_difference": 0.02,
                "ks_distance": 0.1,
                "overall_score": 0.87
            },
            "iterations_completed": 20,
            "optimization_time_seconds": 45.3,
            "timestamp": "2026-03-29T10:30:00Z"
        }
    })


# ============================================================================
# NLP Schemaları
# ============================================================================

class NLPAnalysisRequest(BaseModel):
    """
    NLP analiz isteği schemaması.

    Parametreler:
        text: Analiz edilecek metin
        include_tokenization: Tokenizasyon yapılsın mı
        include_entity_extraction: Varlık çıkarma yapılsın mı
        include_sentiment: Duygu analizi yapılsın mı
        include_grammar: Dilbilgisi kontrolü yapılsın mı
    """
    text: str = Field(
        ...,
        description="Analiz edilecek metin",
        min_length=1,
        max_length=10000,
        examples=["Bu harika bir metin örneğidir."]
    )
    include_tokenization: bool = Field(True, description="Tokenizasyon yapılsın mı")
    include_entity_extraction: bool = Field(True, description="Varlık çıkarma yapılsın mı")
    include_sentiment: bool = Field(True, description="Duygu analizi yapılsın mı")
    include_grammar: bool = Field(True, description="Dilbilgisi kontrolü yapılsın mı")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "text": "Merhaba, bu bir test metnidir. Lütfen analiz edin.",
            "include_tokenization": True,
            "include_entity_extraction": True,
            "include_sentiment": True,
            "include_grammar": True
        }
    })


class TokenizationInfo(BaseModel):
    """Tokenizasyon bilgisi."""
    tokens: List[str] = Field(..., description="Token listesi")
    token_count: int = Field(..., description="Token sayısı")
    unique_tokens: int = Field(..., description="Benzersiz token sayısı")


class EntityInfo(BaseModel):
    """Varlık bilgisi."""
    text: str = Field(..., description="Varlık metni")
    entity_type: str = Field(..., description="Varlık türü")
    start_position: int = Field(..., description="Başlangıç pozisyonu")
    end_position: int = Field(..., description="Bitiş pozisyonu")


class SentimentInfo(BaseModel):
    """Duygu analizi bilgisi."""
    score: float = Field(
        ...,
        description="Duygu puanı (-1 to 1, -1 negatif, 1 pozitif)",
        ge=-1.0,
        le=1.0
    )
    label: str = Field(..., description="Duygu etiketi (positive, negative, neutral)")
    confidence: float = Field(
        ...,
        description="Güven puanı (0-1)",
        ge=0.0,
        le=1.0
    )
    positive_words: List[str] = Field(..., description="Tespit edilen pozitif sözcükler")
    negative_words: List[str] = Field(..., description="Tespit edilen negatif sözcükler")


class GrammarInfo(BaseModel):
    """Dilbilgisi kontrolü bilgisi."""
    is_valid: bool = Field(..., description="Dilbilgisi geçerli mi")
    issues: List[str] = Field(..., description="Bulunaulan sorunlar")
    warnings: List[str] = Field(..., description="Uyarılar")
    score: float = Field(
        ...,
        description="Dilbilgisi puanı (0-1)",
        ge=0.0,
        le=1.0
    )


class NLPAnalysisResult(BaseModel):
    """
    NLP analiz sonucu schemaması.

    Parametreler:
        detected_language: Tespit edilen dil
        text_length: Metin uzunluğu
        tokenization: Tokenizasyon sonucu
        entities: Çıkarılmış varlıklar
        sentiment: Duygu analizi sonucu
        grammar: Dilbilgisi kontrolü sonucu
        timestamp: Zaman damgası
    """
    detected_language: str = Field(..., description="Tespit edilen dil kodu")
    text_length: int = Field(..., description="Metin uzunluğu (karakter)")
    tokenization: Optional[TokenizationInfo] = Field(None, description="Tokenizasyon bilgisi")
    entities: Optional[List[EntityInfo]] = Field(None, description="Çıkarılmış varlıklar")
    sentiment: Optional[SentimentInfo] = Field(None, description="Duygu analizi sonucu")
    grammar: Optional[GrammarInfo] = Field(None, description="Dilbilgisi kontrolü sonucu")
    timestamp: str = Field(..., description="ISO 8601 zaman damgası")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "detected_language": "tr",
            "text_length": 45,
            "tokenization": {
                "tokens": ["bu", "bir", "test"],
                "token_count": 3,
                "unique_tokens": 3
            },
            "entities": [
                {"text": "2026-03-29", "entity_type": "DATE", "start_position": 10, "end_position": 20}
            ],
            "sentiment": {
                "score": 0.5,
                "label": "neutral",
                "confidence": 0.3,
                "positive_words": [],
                "negative_words": []
            },
            "grammar": {
                "is_valid": True,
                "issues": [],
                "warnings": [],
                "score": 0.95
            },
            "timestamp": "2026-03-29T10:30:00Z"
        }
    })


# ============================================================================
# Model Status Schemaları
# ============================================================================

class ModelInfo(BaseModel):
    """Model bilgisi."""
    name: str = Field(..., description="Model adı")
    version: str = Field(..., description="Model versiyonu")
    status: str = Field(..., description="Model durumu (ready, training, error)")
    last_updated: str = Field(..., description="Son güncelleme zamanı")


class ModelStatus(BaseModel):
    """
    Model durumu schemaması.

    Parametreler:
        models: Model bilgileri
        system_health: Sistem sağlığı
        last_evaluation: Son değerlendirme zamanı
        api_version: API versiyonu
    """
    models: Dict[str, ModelInfo] = Field(
        ...,
        description="Mevcut modeller"
    )
    system_health: float = Field(
        ...,
        description="Sistem sağlığı puanı (0-1)",
        ge=0.0,
        le=1.0
    )
    last_evaluation: str = Field(..., description="Son değerlendirme zamanı")
    api_version: str = Field(..., description="API versiyonu")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "models": {
                "gan_discriminator": {
                    "name": "GAN Discriminator",
                    "version": "1.0.0",
                    "status": "ready",
                    "last_updated": "2026-03-29T09:00:00Z"
                },
                "anomaly_detector": {
                    "name": "Anomaly Detector",
                    "version": "1.0.0",
                    "status": "ready",
                    "last_updated": "2026-03-29T09:00:00Z"
                }
            },
            "system_health": 0.98,
            "last_evaluation": "2026-03-29T10:30:00Z",
            "api_version": "1.0.0"
        }
    })


# ============================================================================
# Dashboard Schemaları
# ============================================================================

class DashboardMetric(BaseModel):
    """Dashboard metriği."""
    name: str = Field(..., description="Metrik adı")
    value: float = Field(..., description="Metrik değeri")
    unit: str = Field(..., description="Birim")
    trend: str = Field(..., description="Trend (up, down, stable)")


class AISystemDashboard(BaseModel):
    """
    AI Sistem Dashboard'u.

    Parametreler:
        metrics: Önemli metrikler
        recent_operations: Son işlemler
        warnings: Sistem uyarıları
        timestamp: Zaman damgası
    """
    metrics: List[DashboardMetric] = Field(..., description="Önemli metrikler")
    recent_operations: int = Field(..., description="Son 24 saatteki işlem sayısı")
    warnings: List[str] = Field(..., description="Aktif uyarılar")
    timestamp: str = Field(..., description="ISO 8601 zaman damgası")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "metrics": [
                {"name": "Model Accuracy", "value": 0.92, "unit": "%", "trend": "up"},
                {"name": "Anomalies Detected", "value": 45, "unit": "count", "trend": "stable"}
            ],
            "recent_operations": 256,
            "warnings": [],
            "timestamp": "2026-03-29T10:30:00Z"
        }
    })
