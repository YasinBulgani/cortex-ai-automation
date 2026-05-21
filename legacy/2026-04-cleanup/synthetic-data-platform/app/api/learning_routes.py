"""
Kendi Kendine Öğrenme Modülü API Yönlendiriciler

Bu modül, yapay zeka destekli sentetik veri üretim sisteminin öğrenme
ve optimizasyon süreçlerini yönetmek için gerekli API uç noktalarını sağlar.

Temel işlevler:
- Geri bildirim toplama ve işleme
- Patern keşfi ve analizi
- Otomatik parametr optimizasyonu
- Performans metrikleri izleme
- Bilgi tabanı sinkronizasyonu
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
import logging

from app.models.database import get_db
from app.services.self_learning import SelfLearningEngine
from app.schemas.learning_schemas import (
    FeedbackCreate,
    FeedbackResponse,
    FeedbackListResponse,
    InsightResponse,
    RecommendationResponse,
    OptimizeRequest,
    OptimizeResponse,
    MetricsResponse,
    PatternResponse,
    PatternListResponse,
    LearningResetRequest,
    LearningResetResponse,
)

# Günlüğe kayıt kurulumu
logger = logging.getLogger(__name__)

# Router tanımı
learning_router = APIRouter(
    prefix="/api/learning",
    tags=["Self-Learning / Kendi Kendine Öğrenme"],
)

# Modül seviyesi öğrenme motoru örneği
learning_engine = SelfLearningEngine()


# ============================================================================
# 1. Geri Bildirim Yönetimi Uç Noktaları
# ============================================================================


@learning_router.post(
    "/feedback",
    response_model=FeedbackResponse,
    summary="Geri bildirim gönder",
    description="Sentetik veri kalitesi hakkında geri bildirim gönderin. "
    "Bu geri bildirim sistem öğrenmesini iyileştirmek için kullanılır.",
)
async def submit_feedback(
    feedback: FeedbackCreate,
    db: Session = Depends(get_db),
) -> FeedbackResponse:
    """
    Geri bildirim kayıt uç noktası

    Kullanıcılardan üretilen sentetik verilerin kalitesi ve uygunluğu
    hakkında geri bildirim alır. Bu geri bildirimler sistem tarafından
    analiz edilerek gelecekteki veri üretim parametrelerinin
    optimizasyonunda kullanılır.

    Args:
        feedback: Geri bildirim nesnesi (FeedbackCreate şeması)
        db: Veritabanı oturumu

    Returns:
        FeedbackResponse: Oluşturulan geri bildirim nesnesi

    Raises:
        HTTPException 400: Geçersiz geri bildirim verisi
        HTTPException 500: Geri bildirim işleme hatası
    """
    try:
        logger.info(f"Geri bildirim alınıyor: {feedback.dataset_id}")

        # Geri bildirimi topla ve işle
        created_feedback = learning_engine.feedback_collector.collect_feedback(
            feedback_data=feedback.dict(),
            db_session=db,
        )

        logger.info(f"Geri bildirim başarıyla kaydedildi: {created_feedback.id}")
        return created_feedback

    except ValueError as e:
        logger.error(f"Geçersiz geri bildirim: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Geri bildirim işleme hatası: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Geri bildirim işlenirken bir hata oluştu"
        )


@learning_router.get(
    "/feedback",
    response_model=FeedbackListResponse,
    summary="Geri bildirimleri listele",
    description="Kaydedilmiş tüm geri bildirimleri sorgulayın. "
    "Veri seti kimliği ve sayfalama parametreleriyle filtreleyebilirsiniz.",
)
async def list_feedbacks(
    dataset_id: Optional[int] = Query(None, description="Veri seti kimliği"),
    limit: int = Query(50, ge=1, le=500, description="Döndürülecek maksimum kayıt sayısı"),
    offset: int = Query(0, ge=0, description="Başlangıç ofset"),
    db: Session = Depends(get_db),
) -> FeedbackListResponse:
    """
    Geri bildirimleri listele uç noktası

    Veritabanında kayıtlı geri bildirimleri sayfalama desteğiyle listeler.
    İsteğe bağlı olarak belirli bir veri seti kimliğine göre filtreleyebilir,
    sayfalama parametreleriyle sonuç sayını ve başlangıç noktasını kontrol
    edebilirsiniz.

    Args:
        dataset_id: Filtreleme için veri seti kimliği (isteğe bağlı)
        limit: Döndürülecek maksimum kayıt sayısı (1-500)
        offset: Başlangıç ofset (sayfalama)
        db: Veritabanı oturumu

    Returns:
        FeedbackListResponse: Geri bildirimlerin listesi ve toplam sayısı

    Raises:
        HTTPException 500: Veritabanı sorgulama hatası
    """
    try:
        logger.info(f"Geri bildirimler sorgulanıyor: dataset_id={dataset_id}")

        # Filtreleme koşulları oluştur
        query_filters = {}
        if dataset_id is not None:
            query_filters["dataset_id"] = dataset_id

        # Veritabanından geri bildirimleri sorgula
        feedbacks = learning_engine.feedback_collector.query_feedbacks(
            db_session=db,
            filters=query_filters,
            limit=limit,
            offset=offset,
        )

        # Toplam sayı elde et
        total_count = learning_engine.feedback_collector.count_feedbacks(
            db_session=db,
            filters=query_filters,
        )

        return FeedbackListResponse(
            items=feedbacks,
            total=total_count,
            limit=limit,
            offset=offset,
        )

    except Exception as e:
        logger.error(f"Geri bildirim listesi sorgulanırken hata: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Geri bildirimler sorgulanırken bir hata oluştu"
        )


# ============================================================================
# 2. İçgörü ve Öneriler Uç Noktaları
# ============================================================================


@learning_router.get(
    "/insights",
    response_model=InsightResponse,
    summary="Öğrenilen bilgiler",
    description="Sistem tarafından keşfedilen ve öğrenilen içgörüleri alın. "
    "Bu, patern analizi, anomali tespiti ve veri kalitesi bilgilerini içerir.",
)
async def get_insights(
    db: Session = Depends(get_db),
) -> InsightResponse:
    """
    İçgörüleri al uç noktası

    Sistem tarafından gerçekleştirilen analiz sonucunda keşfedilen
    önemli içgörüleri döndürür. Bu içgörüler veri dağılımları,
    tespit edilen paternler, anomaliler ve kalite metriklerini
    içerir.

    Args:
        db: Veritabanı oturumu

    Returns:
        InsightResponse: Keşfedilen içgörülerin listesi

    Raises:
        HTTPException 500: İçgörü analizi hatası
    """
    try:
        logger.info("İçgörüler alınıyor")

        # Öğrenme motorundan içgörüleri al
        insights = learning_engine.get_insights(db_session=db)

        logger.info(f"İçgörü sayısı: {len(insights.insights)}")
        return insights

    except Exception as e:
        logger.error(f"İçgörü alınırken hata: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="İçgörüler alınırken bir hata oluştu"
        )


@learning_router.get(
    "/recommendations",
    response_model=RecommendationResponse,
    summary="Öneriler",
    description="Sistem tarafından üretilen akıllı öneriler. "
    "Senaryo tipine göre filtreleyebilirsiniz.",
)
async def get_recommendations(
    scenario_type: Optional[str] = Query(
        None,
        description="Senaryo tipi (örn: 'kişisel_kredi', 'işletme')"
    ),
    db: Session = Depends(get_db),
) -> RecommendationResponse:
    """
    Önerileri al uç noktası

    Sistem tarafından analiz sonuçlarına dayalı olarak oluşturulan
    öneriler döndürür. Bu öneriler veri üretim kalitesini artırmak,
    parametreleri optimize etmek ve yaygın sorunları çözmek için
    yapılmaktadır.

    Args:
        scenario_type: Belirli senaryo tipi için filtreleme (isteğe bağlı)
        db: Veritabanı oturumu

    Returns:
        RecommendationResponse: Sistem tarafından oluşturulan öneriler

    Raises:
        HTTPException 500: Öneri üretimi hatası
    """
    try:
        logger.info(f"Öneriler alınıyor: scenario_type={scenario_type}")

        # Öğrenme motorundan önerileri al
        recommendations = learning_engine.get_recommendations(
            db_session=db,
            scenario_type=scenario_type,
        )

        logger.info(f"Öneri sayısı: {len(recommendations.recommendations)}")
        return recommendations

    except Exception as e:
        logger.error(f"Öneri alınırken hata: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Öneriler alınırken bir hata oluştu"
        )


# ============================================================================
# 3. Optimizasyon Uç Noktaları
# ============================================================================


@learning_router.post(
    "/optimize",
    response_model=OptimizeResponse,
    summary="Manuel optimizasyon tetikle",
    description="Veri üretim parametrelerinin manuel olarak optimize edilmesini tetikleyin.",
)
async def trigger_optimization(
    request: OptimizeRequest,
    db: Session = Depends(get_db),
) -> OptimizeResponse:
    """
    Optimizasyon tetikleme uç noktası

    Kalite optimizasiyon motorunu manuel olarak tetikler. Bu, veri
    üretim parametrelerinin geri bildirim ve performans metriklerine
    dayalı olarak güncellenmeleri anlamına gelir.

    Args:
        request: Optimizasyon isteği (OptimizeRequest şeması)
        db: Veritabanı oturumu

    Returns:
        OptimizeResponse: Optimizasyon sonuçları ve yeni parametreler

    Raises:
        HTTPException 400: Geçersiz optimizasyon parametreleri
        HTTPException 500: Optimizasyon hatası
    """
    try:
        logger.info(f"Optimizasyon tetikleniyor: {request.optimization_type}")

        # Kalite optimizasiyon motorunu çalıştır
        optimization_result = learning_engine.quality_optimizer.optimize_parameters(
            optimization_type=request.optimization_type,
            target_metrics=request.target_metrics,
            constraints=request.constraints,
            db_session=db,
        )

        logger.info("Optimizasyon tamamlandı")
        return OptimizeResponse(
            success=True,
            optimization_type=request.optimization_type,
            previous_parameters=optimization_result.get("previous_params"),
            optimized_parameters=optimization_result.get("new_params"),
            improvement_percentage=optimization_result.get("improvement"),
            details=optimization_result.get("details"),
        )

    except ValueError as e:
        logger.error(f"Geçersiz optimizasyon parametreleri: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Optimizasyon hatası: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Optimizasyon gerçekleştirilirken bir hata oluştu"
        )


# ============================================================================
# 4. Metrikleri ve Paternleri Yönetme Uç Noktaları
# ============================================================================


@learning_router.get(
    "/metrics",
    response_model=MetricsResponse,
    summary="Öğrenme metrikleri",
    description="Sistem performansı ve öğrenme ilerleme metriklerini alın.",
)
async def get_metrics(
    db: Session = Depends(get_db),
) -> MetricsResponse:
    """
    Metrikleri al uç noktası

    Öğrenme motoru tarafından izlenen performans ve kalite metriklerini
    döndürür. Bu metrikler veri üretim kalitesi, sistem performansı ve
    öğrenme ilerleme durumunu gösterir.

    Args:
        db: Veritabanı oturumu

    Returns:
        MetricsResponse: Toplam performans ve kalite metrikleri

    Raises:
        HTTPException 500: Metrik alma hatası
    """
    try:
        logger.info("Metrikleri alma alınıyor")

        # Performans özeti al
        performance_summary = learning_engine.get_performance_summary(db_session=db)

        # Kalite boyutları özeti al
        quality_summary = learning_engine.get_quality_dimensions_summary(db_session=db)

        return MetricsResponse(
            performance_metrics=performance_summary,
            quality_dimensions=quality_summary,
            timestamp=learning_engine.get_last_update_time(),
        )

    except Exception as e:
        logger.error(f"Metrik alınırken hata: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Metrikleri alınırken bir hata oluştu"
        )


@learning_router.get(
    "/patterns",
    response_model=PatternListResponse,
    summary="Keşfedilen paternler",
    description="Veri analizinden keşfedilen paternleri listeleyin. "
    "Patern tipi ve güven seviyesine göre filtreleyebilirsiniz.",
)
async def list_patterns(
    pattern_type: Optional[str] = Query(
        None,
        description="Patern tipi (örn: 'dağılım', 'korelasyon')"
    ),
    min_confidence: float = Query(
        0.5,
        ge=0.0,
        le=1.0,
        description="Minimum güven seviyesi"
    ),
    limit: int = Query(50, ge=1, le=500, description="Maksimum patern sayısı"),
    db: Session = Depends(get_db),
) -> PatternListResponse:
    """
    Paternleri listele uç noktası

    Sistem tarafından keşfedilen paternleri listeler. Patern tipi
    ve güven seviyesine göre filtreleme yapabilirsiniz.

    Args:
        pattern_type: Patern tipi filtrelemesi (isteğe bağlı)
        min_confidence: Minimum güven seviyesi (0.0-1.0)
        limit: Döndürülecek maksimum patern sayısı
        db: Veritabanı oturumu

    Returns:
        PatternListResponse: Keşfedilen paternlerin listesi

    Raises:
        HTTPException 400: Geçersiz sorgu parametreleri
        HTTPException 500: Patern sorgusu hatası
    """
    try:
        if not (0.0 <= min_confidence <= 1.0):
            raise ValueError("Güven seviyesi 0.0 ile 1.0 arasında olmalıdır")

        logger.info(
            f"Paternler sorgulanıyor: "
            f"type={pattern_type}, confidence={min_confidence}"
        )

        # Paternleri sorgula
        patterns = learning_engine.pattern_detector.query_patterns(
            db_session=db,
            pattern_type=pattern_type,
            min_confidence=min_confidence,
            limit=limit,
        )

        return PatternListResponse(
            patterns=patterns,
            total=len(patterns),
            filters={
                "pattern_type": pattern_type,
                "min_confidence": min_confidence,
            },
        )

    except ValueError as e:
        logger.error(f"Geçersiz sorgu parametreleri: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Patern sorgulanırken hata: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Paternler sorgulanırken bir hata oluştu"
        )


@learning_router.get(
    "/patterns/{pattern_id}",
    response_model=PatternResponse,
    summary="Tek patern detayı",
    description="Belirtilen kimliğin patern detaylarını alın.",
)
async def get_pattern_detail(
    pattern_id: int,
    db: Session = Depends(get_db),
) -> PatternResponse:
    """
    Patern detayları uç noktası

    Belirtilen patern kimliğine ait detaylı bilgileri döndürür.
    Patern tanımı, güven seviyesi, etkiler ve ilgili veriler
    bu detaylara dahil edilir.

    Args:
        pattern_id: Patern kimliği
        db: Veritabanı oturumu

    Returns:
        PatternResponse: Patern detayları

    Raises:
        HTTPException 404: Patern bulunamadı
        HTTPException 500: Patern alma hatası
    """
    try:
        logger.info(f"Patern detayları alınıyor: {pattern_id}")

        # Patern detaylarını al
        pattern = learning_engine.pattern_detector.get_pattern_by_id(
            pattern_id=pattern_id,
            db_session=db,
        )

        if not pattern:
            raise HTTPException(
                status_code=404,
                detail=f"Kimliği {pattern_id} olan patern bulunamadı"
            )

        return pattern

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Patern detayı alınırken hata: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Patern detayları alınırken bir hata oluştu"
        )


# ============================================================================
# 5. Sistem Yönetimi Uç Noktaları
# ============================================================================


@learning_router.post(
    "/reset",
    response_model=LearningResetResponse,
    summary="Öğrenme verisini sıfırla",
    description="Sistem öğrenme verilerini tamamen veya kısmen sıfırlayın.",
)
async def reset_learning(
    request: LearningResetRequest,
    db: Session = Depends(get_db),
) -> LearningResetResponse:
    """
    Öğrenme verisini sıfırla uç noktası

    Sistem tarafından toplamı öğrenme verilerini (geri bildirimler,
    paternler, metrikler vb.) sıfırlar. Sıfırlanacak veri türleri
    istekle belirtilebilir.

    Args:
        request: Sıfırlama isteği (LearningResetRequest şeması)
        db: Veritabanı oturumu

    Returns:
        LearningResetResponse: Sıfırlama işlemi sonuçları

    Raises:
        HTTPException 400: Geçersiz sıfırlama seçeneği
        HTTPException 500: Sıfırlama hatası
    """
    try:
        logger.warning(f"Öğrenme verisi sıfırlanıyor: {request.data_types}")

        # Sıfırlama işlemini gerçekleştir
        reset_result = learning_engine.reset_learning_data(
            data_types=request.data_types,
            cascade=request.cascade,
            db_session=db,
        )

        logger.warning("Öğrenme verisi sıfırlama tamamlandı")
        return LearningResetResponse(
            success=True,
            reset_data_types=request.data_types,
            records_deleted=reset_result.get("deleted_count", 0),
            message=reset_result.get("message", "Sıfırlama başarıyla tamamlandı"),
        )

    except ValueError as e:
        logger.error(f"Geçersiz sıfırlama seçeneği: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Sıfırlama hatası: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Öğrenme verisi sıfırlanırken bir hata oluştu"
        )


@learning_router.post(
    "/sync-knowledge",
    summary="Bilgi tabanı senkronizasyonu",
    description="Sistem öğrenme verilerini merkezi bilgi tabanına senkronize edin.",
)
async def sync_knowledge(
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Bilgi senkronizasyonu uç noktası

    Sistem tarafından öğrenilen verileri merkezi bilgi tabanına
    senkronize eder. Bu işlem, diğer sistemlerin faydalanabilmesi
    için bilgilerin düzenlemesi ve merkezi depoya yazılması anlamına gelir.

    Args:
        db: Veritabanı oturumu

    Returns:
        dict: Senkronizasyon sonuçları (durumu ve sayıları içeren)

    Raises:
        HTTPException 500: Senkronizasyon hatası
    """
    try:
        logger.info("Bilgi tabanı senkronizasyonu başlatılıyor")

        # Bilgi tabanı senkronizasyonunu gerçekleştir
        sync_result = learning_engine.sync_to_knowledge_base(db_session=db)

        logger.info(f"Senkronizasyon tamamlandı: {sync_result}")
        return {
            "status": "success",
            "synced_insights": sync_result.get("insights_count", 0),
            "synced_patterns": sync_result.get("patterns_count", 0),
            "synced_recommendations": sync_result.get("recommendations_count", 0),
            "timestamp": learning_engine.get_last_update_time(),
        }

    except Exception as e:
        logger.error(f"Senkronizasyon hatası: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Bilgi tabanı senkronizasyonu sırasında bir hata oluştu"
        )


# ============================================================================
# 6. Parametre Seçimi ve Metrik Kaydı Uç Noktaları
# ============================================================================


@learning_router.get(
    "/parameters/{scenario_type}",
    summary="Senaryo için önerilen parametreler",
    description="Belirtilen senaryo tipi için sistem tarafından seçilen parametreleri alın.",
)
async def get_scenario_parameters(
    scenario_type: str,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Senaryo parametreleri uç noktası

    Belirtilen senaryo tipi için sistem tarafından seçilen en iyi
    parametreleri döndürür. Bu parametreler öğrenme motoru tarafından
    exploit/explore stratejisine dayalı olarak belirlenir.

    Args:
        scenario_type: Senaryo tipi (örn: 'kişisel_kredi')
        db: Veritabanı oturumu

    Returns:
        dict: Seçilen parametreler ve stratejisi (exploit/explore)

    Raises:
        HTTPException 400: Geçersiz senaryo tipi
        HTTPException 500: Parametre seçimi hatası
    """
    try:
        logger.info(f"Parametreler alınıyor: {scenario_type}")

        # Parametreleri seç
        selected_params = learning_engine.select_parameters(
            scenario_type=scenario_type,
            db_session=db,
        )

        return {
            "scenario_type": scenario_type,
            "parameters": selected_params.get("params"),
            "strategy": selected_params.get("strategy"),  # exploit veya explore
            "confidence": selected_params.get("confidence"),
            "last_updated": selected_params.get("last_updated"),
        }

    except ValueError as e:
        logger.error(f"Geçersiz senaryo tipi: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Parametre seçimi hatası: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Parametreler alınırken bir hata oluştu"
        )


@learning_router.post(
    "/record-metrics",
    summary="Üretim metriklerini kaydet",
    description="Veri üretim işleminden elde edilen metrikleri sisteme kaydedin.",
)
async def record_metrics(
    metrics_data: Dict[str, Any],
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Metrik kaydı uç noktası

    Veri üretim işleminden elde edilen metrikleri sisteme kaydeder.
    Bu metrikler, sistem performansını izlemek ve gelecekteki
    optimizasyon kararlarını almak için kullanılır.

    Args:
        metrics_data: Kayıt edilecek metrik verileri
        db: Veritabanı oturumu

    Returns:
        dict: Kaydedilen metrik kimliği ve durumu

    Raises:
        HTTPException 400: Geçersiz metrik verisi
        HTTPException 500: Metrik kaydı hatası
    """
    try:
        logger.info("Üretim metrikleri kaydediliyor")

        # Metrikleri kaydet
        recorded_metric = learning_engine.record_generation_metrics(
            metrics_data=metrics_data,
            db_session=db,
        )

        logger.info(f"Metrik kaydedildi: {recorded_metric.get('id')}")
        return {
            "status": "success",
            "metric_id": recorded_metric.get("id"),
            "recorded_at": recorded_metric.get("timestamp"),
            "message": "Metrikler başarıyla kaydedildi",
        }

    except ValueError as e:
        logger.error(f"Geçersiz metrik verisi: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Metrik kaydı hatası: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Metrikler kaydedilirken bir hata oluştu"
        )
