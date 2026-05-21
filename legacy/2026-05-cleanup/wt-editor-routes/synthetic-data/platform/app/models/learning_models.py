"""
Öz-öğrenme Modülü İçin SQLAlchemy 2.0 Modelleri
Turkish Banking Synthetic Data Generation Platform

Bu modül, yapay veri üretim sisteminin performansını izlemek,
geri bildirim toplamak ve öğrenilen desenleri depolamak için
veritabanı modellerini tanımlar.
"""

from enum import Enum as PyEnum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    Integer,
    JSON,
    String,
    Text,
    func,
    desc,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.database import Base


# ============================================================================
# ENUM TANIMALARI
# ============================================================================


class FeedbackType(str, PyEnum):
    """
    Geri bildirim türleri - kullanıcıdan alınan geri bildirimlerin kategorileri

    Değerler:
    - quality: Veri kalitesi hakkındaki geri bildirim
    - accuracy: Doğruluk ve tutarlılık hakkındaki geri bildirim
    - diversity: Veri çeşitliliği hakkındaki geri bildirim
    - performance: Üretim hızı ve performansı hakkındaki geri bildirim
    - usability: Kullanılabilirlik ve arayüz hakkındaki geri bildirim
    """
    QUALITY = "quality"
    ACCURACY = "accuracy"
    DIVERSITY = "diversity"
    PERFORMANCE = "performance"
    USABILITY = "usability"


class PatternType(str, PyEnum):
    """
    Öğrenilen desenler için kategoriler - sistem tarafından keşfedilen ve
    kaydedilen tekrar kullanılabilir desenler

    Değerler:
    - column_mapping: Sütun eşleştirme desenleri
    - distribution_fit: Dağılım uyum desenleri
    - rule_combination: Kural kombinasyon desenleri
    - scenario_config: Senaryo yapılandırması desenleri
    - domain_specific: Bankacılık alanına özel desenleri
    """
    COLUMN_MAPPING = "column_mapping"
    DISTRIBUTION_FIT = "distribution_fit"
    RULE_COMBINATION = "rule_combination"
    SCENARIO_CONFIG = "scenario_config"
    DOMAIN_SPECIFIC = "domain_specific"


class OptimizationType(str, PyEnum):
    """
    Optimizasyon türleri - sistem performansını artırmak için yapılan
    optimizasyon denemelerinin kategorileri

    Değerler:
    - batch_size: Toplu işlem boyutu optimizasyonu
    - parallelism: Paralel işleme optimizasyonu
    - cache_strategy: Önbellek stratejisi optimizasyonu
    - rule_weights: Kural ağırlık optimizasyonu
    - generation_params: Üretim parametreleri optimizasyonu
    """
    BATCH_SIZE = "batch_size"
    PARALLELISM = "parallelism"
    CACHE_STRATEGY = "cache_strategy"
    RULE_WEIGHTS = "rule_weights"
    GENERATION_PARAMS = "generation_params"


# ============================================================================
# MODEL 1: LearningFeedback - Kullanıcı Geri Bildirimleri
# ============================================================================


class LearningFeedback(Base):
    """
    Kullanıcılardan alınan geri bildirimler tablosu

    Bu tablo, kullanıcıların üretilen veri setleri ve sistem performansı
    hakkında sağladığı derecelendirme ve yorum bilgilerini depolar.
    Geri bildirimler, sistem öğrenmesi ve iyileştirme için kullanılır.

    Tablonun Amacı:
    - Veri kalitesi hakkında gerçek kullanıcı görüşünü yakalamak
    - İyileştirme alanlarını belirlemek
    - Kullanıcı memnuniyetini izlemek
    """

    __tablename__ = "learning_feedbacks"

    # Birincil Anahtar
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Dış Anahtarlar ve İlişkiler
    dataset_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    """Geri bildirim verilen veri setinin ID'si"""

    generation_job_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    """Geri bildirim verilen üretim işinin ID'si"""

    user_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    """Geri bildirimi sağlayan kullanıcının ID'si"""

    # Geri Bildirim Alanları
    rating: Mapped[int] = mapped_column(Integer)
    """1-5 arasında yıldız derecelendirmesi (1: çok kötü, 5: mükemmel)"""

    feedback_type: Mapped[FeedbackType] = mapped_column(Enum(FeedbackType))
    """Geri bildirimin kategorisi (kalite, doğruluk, çeşitlilik, vb.)"""

    positive_aspects: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    """İyi giden alanlar listesi (JSON formatında string listesi)"""

    negative_aspects: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    """Kötü giden alanlar listesi (JSON formatında string listesi)"""

    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    """Kullanıcı tarafından yazılan açık yorum"""

    generation_params: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    """Geri bildirim sırasında kullanılan üretim parametrelerinin snapshot'ı"""

    # Zaman Bilgileri
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now()
    )
    """Geri bildirimin oluşturulma tarihi ve saati"""

    def __repr__(self) -> str:
        return (
            f"<LearningFeedback(id={self.id}, rating={self.rating}, "
            f"type={self.feedback_type}, user={self.user_id})>"
        )


# ============================================================================
# MODEL 2: GenerationMetrics - Üretim Metrikleri
# ============================================================================


class GenerationMetrics(Base):
    """
    Veri üretim işlerinin performans metrikleri tablosu

    Bu tablo, her veri üretim işi sırasında toplanan teknik metrikleri
    ve kalite ölçümlerini depolar. Bu veriler sistem öğrenmesi ve
    performans optimizasyonu için analiz edilir.

    Tablonun Amacı:
    - Üretim performansını ölçmek ve takip etmek
    - Kalite metrikleri toplayarak sistemin başarısını değerlendirmek
    - Zaman içinde trendleri izlemek ve iyileştirmeleri doğrulamak
    """

    __tablename__ = "generation_metrics"

    # Birincil Anahtar
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Dış Anahtarlar
    generation_job_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    """Metriklerin ait olduğu üretim işinin ID'si"""

    dataset_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    """Oluşturulan veri setinin ID'si"""

    # Üretim Bilgileri
    scenario_type: Mapped[str] = mapped_column(String(50))
    """Üretilen senaryo türü (örn: credit_card, bank_account, transaction)"""

    row_count: Mapped[int] = mapped_column(Integer)
    """Üretilen toplam satır sayısı"""

    column_count: Mapped[int] = mapped_column(Integer)
    """Üretilen toplam sütun sayısı"""

    # Performans Metrikleri
    generation_time_ms: Mapped[float] = mapped_column(Float)
    """Üretim işleminin aldığı toplam süre (milisaniye cinsinden)"""

    memory_usage_mb: Mapped[float] = mapped_column(Float)
    """Üretim sırasında kullanılan maksimum bellek (MB cinsinden)"""

    # Kalite Metrikleri (0-100 ölçeğinde)
    quality_score: Mapped[float] = mapped_column(Float)
    """Genel veri kalitesi puanı (0-100)"""

    completeness_score: Mapped[float] = mapped_column(Float)
    """Veri tamlığı puanı - boş alan oranı (0-100)"""

    uniqueness_score: Mapped[float] = mapped_column(Float)
    """Benzersizlik puanı - tekrar eden satırların oranı (0-100)"""

    consistency_score: Mapped[float] = mapped_column(Float)
    """Tutarlılık puanı - veri türü ve format uyumluluğu (0-100)"""

    accuracy_score: Mapped[float] = mapped_column(Float)
    """Doğruluk puanı - kurallara uygunluk (0-100)"""

    # Parametreler ve Kurallar
    parameters: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    """Bu üretim işinde kullanılan parametrelerin snapshot'ı"""

    rule_scores: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    """Her kural için etkinlik/başarı puanları (JSON dict formatında)"""

    # Zaman Bilgileri
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    """Metriklerin kaydedilme tarihi ve saati"""

    def __repr__(self) -> str:
        return (
            f"<GenerationMetrics(id={self.id}, job={self.generation_job_id}, "
            f"rows={self.row_count}, quality={self.quality_score})>"
        )


# ============================================================================
# MODEL 3: LearnedPattern - Öğrenilen Desenleri
# ============================================================================


class LearnedPattern(Base):
    """
    Sistem tarafından öğrenilen ve keşfedilen tekrar kullanılabilir desenleri

    Bu tablo, sistem tarafından başarılı üretim işlerinden çıkarılan
    ve gelecekte tekrar kullanılabilir hale getirilen desenleri depolar.
    Öğrenilen desenleri, sistemi daha hızlı ve daha verimli hale getirir.

    Tablonun Amacı:
    - Başarılı üretim konfigürasyonlarını depolamak
    - Tekrar kullanılabilir desenleri izlemek
    - Desenin başarı oranını ve güvenirliğini takip etmek
    - Sistem öğrenmesini gerçekleştirmek
    """

    __tablename__ = "learned_patterns"

    # Birincil Anahtar
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Desen Bilgileri
    pattern_type: Mapped[PatternType] = mapped_column(Enum(PatternType))
    """Desenin kategorisi (sütun eşleştirme, dağılım, kural, vb.)"""

    pattern_key: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    """Deseni benzersiz olarak tanımlayan anahtar"""

    pattern_data: Mapped[dict] = mapped_column(JSON)
    """Öğrenilen desenin verileri (JSON formatında)"""

    # Güven ve Başarı Metrikleri
    confidence: Mapped[float] = mapped_column(Float)
    """Desenin güvenilirlik skoru (0-1 arasında, 1=çok güvenilir)"""

    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    """Desenin kaç kez kullanıldığı"""

    success_count: Mapped[int] = mapped_column(Integer, default=0)
    """Desenin kaç kez başarıyla kullanıldığı"""

    success_rate: Mapped[float] = mapped_column(Float, default=0.0)
    """Desenin başarı oranı (success_count / usage_count)"""

    # Durum Bilgileri
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    """Desenin aktif olup olmadığı (pasifleştirilmiş desenleri dışlamak için)"""

    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    """Desenin en son kullanılma tarihi ve saati"""

    # Zaman Bilgileri
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    """Desenin keşfedilme ve kaydedilme tarihi"""

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )
    """Desenin en son güncellenme tarihi"""

    def __repr__(self) -> str:
        return (
            f"<LearnedPattern(id={self.id}, key={self.pattern_key}, "
            f"type={self.pattern_type}, success_rate={self.success_rate})>"
        )


# ============================================================================
# MODEL 4: OptimizationHistory - Optimizasyon Geçmişi
# ============================================================================


class OptimizationHistory(Base):
    """
    Sistem performansını optimize etme denemelerinin geçmişi

    Bu tablo, sistem parametrelerinde yapılan değişiklikleri ve
    bu değişikliklerin sonuçlarını depolar. Her optimizasyon denemesi
    kayıt altına alınarak, hangi değişikliklerin etkili olduğu analiz
    edilebilir ve sistematik iyileştirmeler yapılabilir.

    Tablonun Amacı:
    - Optimizasyon denemelerini belgelemek
    - Hangi değişikliklerin faydalı olduğunu belirlemek
    - Sistem öğrenmesi için veriler sağlamak
    - Geriye doğru gidebilmek için audit trail oluşturmak
    """

    __tablename__ = "optimization_history"

    # Birincil Anahtar
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Optimizasyon Bilgileri
    optimization_type: Mapped[OptimizationType] = mapped_column(Enum(OptimizationType))
    """Optimizasyon türü (batch size, parallelism, cache, kural ağırlıkları, vb.)"""

    previous_value: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    """Değişiklikten önce kullanılan değer"""

    new_value: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    """Değişiklikten sonra kullanılan yeni değer"""

    # Etkinlik Metrikleri
    metric_before: Mapped[float] = mapped_column(Float)
    """Değişiklikten önceki metrik değeri (örn: saniye cinsinden süre)"""

    metric_after: Mapped[float] = mapped_column(Float)
    """Değişiklikten sonraki metrik değeri"""

    improvement_pct: Mapped[float] = mapped_column(Float)
    """İyileştirme yüzdesi ((metric_before - metric_after) / metric_before * 100)"""

    # Açıklamalar
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    """Optimizasyon denemesinin nedenini açıklayan metin"""

    # Durum
    applied: Mapped[bool] = mapped_column(Boolean, default=False)
    """Optimizasyon işleminin gerçekten uygulanıp uygulanmadığı"""

    # Zaman Bilgileri
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    """Optimizasyon denemesinin yapılma tarihi ve saati"""

    def __repr__(self) -> str:
        return (
            f"<OptimizationHistory(id={self.id}, type={self.optimization_type}, "
            f"improvement={self.improvement_pct}%, applied={self.applied})>"
        )


# ============================================================================
# YARDIMCı FONKSİYONLAR VE UTILITIES
# ============================================================================


def get_top_patterns_by_success_rate(session, pattern_type: Optional[PatternType] = None, limit: int = 10):
    """
    En yüksek başarı oranına sahip desenleri getirir

    Args:
        session: SQLAlchemy session
        pattern_type: Belirli bir desen türü için filtreleme (isteğe bağlı)
        limit: Döndürülecek maksimum kayıt sayısı

    Returns:
        En yüksek başarı oranına sahip LearnedPattern nesnelerinin listesi
    """
    query = session.query(LearnedPattern).filter(
        LearnedPattern.is_active == True
    )

    if pattern_type:
        query = query.filter(LearnedPattern.pattern_type == pattern_type)

    return query.order_by(desc(LearnedPattern.success_rate)).limit(limit).all()


def calculate_average_quality_metrics(session, dataset_id: int):
    """
    Belirli bir veri seti için ortalama kalite metriklerini hesaplar

    Args:
        session: SQLAlchemy session
        dataset_id: Veri seti ID'si

    Returns:
        Ortalama kalite metrikleri içeren bir sözlük
    """
    from sqlalchemy import func as sql_func

    metrics = session.query(
        sql_func.avg(GenerationMetrics.quality_score).label("avg_quality"),
        sql_func.avg(GenerationMetrics.completeness_score).label("avg_completeness"),
        sql_func.avg(GenerationMetrics.uniqueness_score).label("avg_uniqueness"),
        sql_func.avg(GenerationMetrics.consistency_score).label("avg_consistency"),
        sql_func.avg(GenerationMetrics.accuracy_score).label("avg_accuracy"),
    ).filter(GenerationMetrics.dataset_id == dataset_id).first()

    return {
        "quality": metrics.avg_quality,
        "completeness": metrics.avg_completeness,
        "uniqueness": metrics.avg_uniqueness,
        "consistency": metrics.avg_consistency,
        "accuracy": metrics.avg_accuracy,
    }
