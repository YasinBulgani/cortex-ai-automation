"""
Öğrenme modülü için Pydantic şemaları.

Bu modül, sentetik banka verileri platformunun öğrenme ve iyileştirme
işlevleri için istek ve yanıt şemalarını tanımlar.
"""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# GERI BİLDİRİM (FEEDBACK) ŞEMALARI
# ============================================================================


class FeedbackCreate(BaseModel):
    """
    Geri bildirim oluşturma isteği şeması.

    Kullanıcılar veri kalitesi, veri türü veya üretim işi hakkında
    detaylı geri bildirim sağlayabilirler.
    """

    dataset_id: Optional[int] = Field(
        default=None,
        description="İlgili veri seti kimliği (opsiyonel)"
    )
    generation_job_id: Optional[int] = Field(
        default=None,
        description="İlgili üretim işi kimliği (opsiyonel)"
    )
    rating: int = Field(
        ge=1,
        le=5,
        description="Kalite puanı (1-5 yıldız)"
    )
    feedback_type: str = Field(
        default="quality",
        description="Geri bildirim türü: quality, data_type, generation, other"
    )
    positive_aspects: list[str] = Field(
        default_factory=list,
        description="Olumlu yönleri listeleyin"
    )
    negative_aspects: list[str] = Field(
        default_factory=list,
        description="Olumsuz yönleri listeleyin"
    )
    comment: Optional[str] = Field(
        default=None,
        description="Detaylı açıklama veya yorum"
    )


class FeedbackResponse(BaseModel):
    """
    Geri bildirim yanıt şeması.

    Veritabanından alınan tam geri bildirim kaydını temsil eder.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Geri bildirim kayıt kimliği")
    dataset_id: Optional[int] = Field(description="İlgili veri seti kimliği")
    generation_job_id: Optional[int] = Field(description="İlgili üretim işi kimliği")
    rating: int = Field(description="Kalite puanı (1-5)")
    feedback_type: str = Field(description="Geri bildirim türü")
    positive_aspects: list = Field(description="Olumlu yönler")
    negative_aspects: list = Field(description="Olumsuz yönler")
    comment: Optional[str] = Field(description="Detaylı yorum")
    created_at: datetime = Field(description="Oluşturulma tarihi ve saati")


class FeedbackListResponse(BaseModel):
    """
    Geri bildirim listesi yanıt şeması.

    Sayfalanmış geri bildirim kayıtlarını ve özet istatistikleri içerir.
    """

    items: list[FeedbackResponse] = Field(
        description="Geri bildirim kayıtları listesi"
    )
    total: int = Field(
        description="Toplam geri bildirim sayısı"
    )
    average_rating: float = Field(
        description="Ortalama kalite puanı"
    )


# ============================================================================
# İÇGÖRÜ (INSIGHT) ŞEMALARI
# ============================================================================


class InsightResponse(BaseModel):
    """
    Detaylı içgörü yanıt şeması.

    Geri bildirimlerden ve ölçümlerden türetilen detaylı analiz
    ve istatistikleri sağlar.
    """

    total_feedbacks: int = Field(
        description="Toplam geri bildirim sayısı"
    )
    average_rating: float = Field(
        description="Ortalama kalite puanı"
    )
    rating_distribution: dict[str, int] = Field(
        description="Puan dağılımı (1-5 yıldız için sayılar)"
    )
    top_positive_aspects: list[dict] = Field(
        description="En sık belirtilen olumlu yönler (aspect, count, percentage)"
    )
    top_negative_aspects: list[dict] = Field(
        description="En sık belirtilen olumsuz yönler (aspect, count, percentage)"
    )
    quality_trend: list[dict] = Field(
        description="Zaman içinde kalite eğilimi (timestamp, average_rating)"
    )
    best_scenarios: list[dict] = Field(
        description="En başarılı senaryolar (scenario_type, success_count, avg_rating)"
    )
    worst_scenarios: list[dict] = Field(
        description="En başarısız senaryolar (scenario_type, failure_count, avg_rating)"
    )


class RecommendationResponse(BaseModel):
    """
    Öneriler yanıt şeması.

    Geri bildirim ve desenlere dayanan iyileştirme önerileri sağlar.
    """

    recommendations: list[dict] = Field(
        description="Öneriler listesi (action, priority, reason, expected_impact)"
    )
    based_on_patterns: int = Field(
        description="Kaç desene dayandığı"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Önerilerin güven düzeyi (0-1)"
    )


# ============================================================================
# OPTİMİZASYON ŞEMALARI
# ============================================================================


class OptimizeRequest(BaseModel):
    """
    Optimizasyon isteği şeması.

    Sistemin farklı yönlerinin otomatik olarak optimize edilmesini ister.
    """

    target: str = Field(
        description="Optimizasyon hedefi: batch_size, parallelism, cache, rules, all"
    )
    aggressive: bool = Field(
        default=False,
        description="Agresif optimizasyon (daha radikal değişiklikler)"
    )


class OptimizeResponse(BaseModel):
    """
    Optimizasyon yanıt şeması.

    Uygulanan optimizasyonların detaylarını ve sonuçlarını içerir.
    """

    optimizations_applied: list[dict] = Field(
        description="Uygulanan optimizasyonlar (name, value, reason)"
    )
    metrics_before: dict = Field(
        description="Optimizasyon öncesi metrikler"
    )
    metrics_after: dict = Field(
        description="Optimizasyon sonrası metrikler"
    )
    improvement_summary: str = Field(
        description="İyileştirmenin özet açıklaması"
    )


# ============================================================================
# METRİKLER ŞEMALARI
# ============================================================================


class MetricsResponse(BaseModel):
    """
    Performans ve kalite metrikleri yanıt şeması.

    Sistem performansı ve veri kalitesi hakkında kapsamlı metrikleri sağlar.
    """

    total_generations: int = Field(
        description="Toplam veri üretim işi sayısı"
    )
    average_quality_score: float = Field(
        description="Ortalama kalite puanı"
    )
    average_generation_time_ms: float = Field(
        description="Ortalama üretim süresi (milisaniye)"
    )
    average_memory_usage_mb: float = Field(
        description="Ortalama bellek kullanımı (megabayt)"
    )
    quality_dimensions: dict = Field(
        description="Kalite boyutları ve puanları"
    )
    performance_trend: list[dict] = Field(
        description="Zaman içinde performans eğilimi (timestamp, metrics)"
    )


# ============================================================================
# DESEN (PATTERN) ŞEMALARI
# ============================================================================


class PatternResponse(BaseModel):
    """
    Öğrenilen desen yanıt şeması.

    Sistemin öğrendiği veri üretim desenleri hakkında bilgi içerir.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(
        description="Desen kayıt kimliği"
    )
    pattern_type: str = Field(
        description="Desen türü (behavioral, data_quality, performance, anomaly)"
    )
    pattern_key: str = Field(
        description="Desen tanımlayıcı anahtarı"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Desenin güven düzeyi (0-1)"
    )
    usage_count: int = Field(
        description="Desenin kaç kez kullanıldığı"
    )
    success_rate: float = Field(
        ge=0.0,
        le=1.0,
        description="Desenin başarı oranı (0-1)"
    )
    is_active: bool = Field(
        description="Desenin aktif olup olmadığı"
    )
    pattern_data: dict = Field(
        description="Desenin detaylı verileri"
    )
    created_at: datetime = Field(
        description="Desenin öğrenildiği tarih ve saat"
    )


class PatternListResponse(BaseModel):
    """
    Desen listesi yanıt şeması.

    Tüm öğrenilen desenlerin sayfalanmış listesini sağlar.
    """

    items: list[PatternResponse] = Field(
        description="Desen kayıtları listesi"
    )
    total: int = Field(
        description="Toplam desen sayısı"
    )
    active_count: int = Field(
        description="Aktif desen sayısı"
    )


# ============================================================================
# SIFIRLAMAYIP (RESET) ŞEMALARI
# ============================================================================


class LearningResetRequest(BaseModel):
    """
    Öğrenme verilerini sıfırlama isteği şeması.

    Geri bildirim, desenler ve metrikleri seçimliye sıfırlayabilir.
    Bu işlem geri alınamaz, dikkat edilmelidir.
    """

    confirm: bool = Field(
        description="Sıfırlama onayı (güvenlik için gerekli)"
    )
    reset_feedbacks: bool = Field(
        default=True,
        description="Geri bildirimleri sıfırla"
    )
    reset_patterns: bool = Field(
        default=True,
        description="Öğrenilen desenleri sıfırla"
    )
    reset_metrics: bool = Field(
        default=False,
        description="Metrikleri sıfırla"
    )


class LearningResetResponse(BaseModel):
    """
    Öğrenme verilerini sıfırlama yanıt şeması.

    Sıfırlama işleminin sonuçlarını ve etkilenen kayıtları gösterir.
    """

    status: str = Field(
        description="İşlem durumu (success, partial, failed)"
    )
    deleted_feedbacks: int = Field(
        description="Silinen geri bildirim sayısı"
    )
    deleted_patterns: int = Field(
        description="Silinen desen sayısı"
    )
    deleted_metrics: int = Field(
        description="Silinen metrik kaydı sayısı"
    )
    message: str = Field(
        description="Işlem hakkında detaylı mesaj"
    )
