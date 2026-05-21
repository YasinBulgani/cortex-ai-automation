"""
QA Engine API Yolları (Routes) Modülü

Bu modül FastAPI kullanarak QA Engine'in REST API uç noktalarını tanımlar.
URL analizi, test planı oluşturma, otomasyon script'leri üretimi, test çalıştırma,
monkey testing, performans analizi, rapor yönetimi ve proje scaffolding için
endpoints sağlar.

Tüm yorum ve docstring'ler Türkçe'dir.
"""

import logging
import io
import json
from typing import Any, Dict, List, Optional
from datetime import datetime

from fastapi import (
    APIRouter,
    HTTPException,
    BackgroundTasks,
    status,
)

from app.schemas.qa_schemas import (
    TestPlanRequest,
    TestPlanResponse,
    MonkeyTestConfig,
    MonkeyTestResult,
    ProjectConfig,
    QAReport,
    AutomationRequest,
    AutomationResponse,
    RunTestsRequest,
    RunTestsResponse,
    PerformanceMetrics,
    QAStatusResponse,
    EnvironmentConfig,
)
from app.services.qa_engine import QAEngine
from app.services.project_scaffolder import ProjectScaffolder

# Logging konfigürasyonu
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# APIRouter oluştur
router = APIRouter(
    prefix="/api/qa",
    tags=["QA Engine"],
    responses={
        404: {"description": "Kaynak bulunamadı"},
        500: {"description": "Sunucu hatası"},
    }
)

# Module seviyesi QAEngine instance
qa_engine = QAEngine()


# ============================
# URL ANALİZİ ENDPOİNTLERİ
# ============================

@router.post(
    "/analyze",
    response_model=QAStatusResponse,
    summary="URL Analizi",
    description="Verilen URL'yi analiz eder ve sayfa yapısını döndürür",
)
async def analyze_url(request: TestPlanRequest) -> QAStatusResponse:
    """
    Verilen URL'yi analiz et ve sayfa yapısını, formları, linkleri ve
    teknolojileri tespit et.

    Args:
        request: TestPlanRequest nesnesi (url, app_name, vs.)

    Returns:
        QAStatusResponse: Analiz sonuçlarını içeren yanıt
    """
    try:
        logger.info(f"URL analizi başlatılıyor: {request.url}")
        analysis = await qa_engine.analyze(request.url)

        if 'error' in analysis:
            logger.error(f"Analiz hatası: {analysis.get('error')}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"URL analizi başarısız: {analysis.get('error')}"
            )

        logger.info(f"URL analizi tamamlandı: {request.url}")
        return QAStatusResponse(
            status="success",
            message="URL analizi başarıyla tamamlandı",
            data=analysis
        )

    except Exception as e:
        logger.error(f"URL analizi hatası: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"URL analizi sırasında hata oluştu: {str(e)}"
        )


# ============================
# TEST PLANI ENDPOİNTLERİ
# ============================

@router.post(
    "/test-plan",
    response_model=QAStatusResponse,
    summary="Test Planı Oluştur",
    description="Verilen URL ve test türlerine göre test planı oluşturur",
)
async def generate_test_plan(request: TestPlanRequest) -> QAStatusResponse:
    """
    URL'yi analiz edip test planı oluştur.

    Args:
        request: TestPlanRequest nesnesi (url, test_types, vs.)

    Returns:
        QAStatusResponse: Oluşturulan test planını içeren yanıt
    """
    try:
        logger.info(f"Test planı oluşturulüyor: {request.url}")
        plan = await qa_engine.generate_plan(request.url, request.test_types)

        if 'error' in plan:
            logger.error(f"Test planı hatası: {plan.get('error')}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Test planı oluşturulamadı: {plan.get('error')}"
            )

        logger.info(f"Test planı oluşturuldu: {plan.get('plan_id')}")
        return QAStatusResponse(
            status="success",
            message="Test planı başarıyla oluşturuldu",
            data=plan
        )

    except Exception as e:
        logger.error(f"Test planı oluşturma hatası: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Test planı oluşturma sırasında hata oluştu: {str(e)}"
        )


# ============================
# OTOMASYON SCRİPTİ ENDPOİNTLERİ
# ============================

@router.post(
    "/generate-automation",
    response_model=QAStatusResponse,
    summary="Otomasyon Scripti Üret",
    description="Test planından otomatik olarak test scripti üretir",
)
async def generate_automation(request: AutomationRequest) -> QAStatusResponse:
    """
    Test planından otomasyon scriptleri üret (Playwright, Selenium, vs.).

    Args:
        request: AutomationRequest nesnesi (test_plan_id, framework, language, vs.)

    Returns:
        QAStatusResponse: Üretilen scriptleri içeren yanıt
    """
    try:
        logger.info(f"Otomasyon scripti üretiliyor: {request.test_plan_id}")
        automation = await qa_engine.generate_automation(request.test_plan_id)

        if 'error' in automation:
            logger.error(f"Otomasyon üretimi hatası: {automation.get('error')}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Otomasyon üretimi başarısız: {automation.get('error')}"
            )

        logger.info(f"Otomasyon scripti üretildi: {request.test_plan_id}")
        return QAStatusResponse(
            status="success",
            message="Otomasyon scripti başarıyla üretildi",
            data=automation
        )

    except Exception as e:
        logger.error(f"Otomasyon üretimi hatası: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Otomasyon üretimi sırasında hata oluştu: {str(e)}"
        )


# ============================
# TEST ÇALIŞTIRMA ENDPOİNTLERİ
# ============================

@router.post(
    "/run-tests",
    response_model=QAStatusResponse,
    summary="Testleri Çalıştır",
    description="Mevcut bir test planını belirtilen ortamda çalıştırır",
)
async def run_tests(
    request: RunTestsRequest,
    background_tasks: BackgroundTasks
) -> QAStatusResponse:
    """
    Test planını belirtilen ortamda arka planda çalıştır.

    Args:
        request: RunTestsRequest nesnesi (test_plan_id, environment, vs.)
        background_tasks: Arka plan görevleri için BackgroundTasks nesnesi

    Returns:
        QAStatusResponse: Yürütme kimliği ve başlangıç bilgisini içeren yanıt
    """
    try:
        logger.info(
            f"Test çalıştırılıyor: {request.test_plan_id} "
            f"ortamında: {request.environment}"
        )

        execution_id = f"exec_{datetime.now().timestamp()}"

        # Arka planda test çalıştır
        async def run_tests_background():
            """Arka planda test çalıştırma işlemi."""
            try:
                result = await qa_engine.run_tests(
                    request.test_plan_id,
                    request.environment
                )
                logger.info(f"Testler tamamlandı: {execution_id}")
            except Exception as e:
                logger.error(f"Arka plan test hatası: {str(e)}")

        background_tasks.add_task(run_tests_background)

        logger.info(f"Test çalıştırması başlatıldı: {execution_id}")
        return QAStatusResponse(
            status="success",
            message="Testler çalıştırılmaya başladı",
            data={
                "execution_id": execution_id,
                "status": "running",
                "test_plan_id": request.test_plan_id,
                "environment": request.environment
            }
        )

    except Exception as e:
        logger.error(f"Test çalıştırma hatası: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Test çalıştırma sırasında hata oluştu: {str(e)}"
        )


# ============================
# MONKEY TEST ENDPOİNTLERİ
# ============================

@router.post(
    "/monkey-test",
    response_model=QAStatusResponse,
    summary="Monkey Test Başlat",
    description="Rastgele ve otomatik test (monkey test) çalıştırır",
)
async def run_monkey_test(request: MonkeyTestConfig) -> QAStatusResponse:
    """
    URL'de monkey test (rastgele/otomatik test) çalıştır.

    Monkey testing, uygulamaya rastgele girdiler göndererek stabilite
    ve dayanıklılığını test eder.

    Args:
        request: MonkeyTestConfig nesnesi (url, duration_seconds, max_actions, vs.)

    Returns:
        QAStatusResponse: Monkey test sonuçlarını içeren yanıt
    """
    try:
        logger.info(f"Monkey test başlatılıyor: {request.url}")
        config_dict = request.model_dump()
        result = await qa_engine.run_monkey_test(request.url, config_dict)

        if 'error' in result:
            logger.error(f"Monkey test hatası: {result.get('error')}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Monkey test başarısız: {result.get('error')}"
            )

        logger.info(f"Monkey test tamamlandı: {request.url}")
        return QAStatusResponse(
            status="success",
            message="Monkey test başarıyla tamamlandı",
            data=result
        )

    except Exception as e:
        logger.error(f"Monkey test hatası: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Monkey test sırasında hata oluştu: {str(e)}"
        )


# ============================
# RAPOR ENDPOİNTLERİ
# ============================

@router.get(
    "/reports",
    response_model=QAStatusResponse,
    summary="Rapor Listesi",
    description="Tüm oluşturulan raporların listesini döndürür",
)
async def list_reports() -> QAStatusResponse:
    """
    Tüm oluşturulan raporların listesini getir.

    Returns:
        QAStatusResponse: Rapor listesini içeren yanıt
    """
    try:
        logger.info("Rapor listesi alınıyor")
        reports = list(qa_engine._reports.keys())

        return QAStatusResponse(
            status="success",
            message=f"{len(reports)} rapor bulundu",
            data={
                "reports": reports,
                "total": len(reports)
            }
        )

    except Exception as e:
        logger.error(f"Rapor listesi hatası: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rapor listesi alınırken hata oluştu: {str(e)}"
        )


@router.get(
    "/reports/{report_id}",
    response_model=QAStatusResponse,
    summary="Rapor Detayı",
    description="Belirtilen rapor ID'sine göre detaylı rapor bilgisini döndürür",
)
async def get_report(report_id: str) -> QAStatusResponse:
    """
    Belirtilen ID'ye sahip raporu getir.

    Args:
        report_id: Rapor ID'si

    Returns:
        QAStatusResponse: Rapor detaylarını içeren yanıt

    Raises:
        HTTPException: Rapor bulunamadığında 404 hatası
    """
    try:
        logger.info(f"Rapor alınıyor: {report_id}")
        report = qa_engine.get_report(report_id)

        if report is None:
            logger.warning(f"Rapor bulunamadı: {report_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rapor bulunamadı: {report_id}"
            )

        logger.info(f"Rapor getirildi: {report_id}")
        return QAStatusResponse(
            status="success",
            message="Rapor başarıyla alındı",
            data={
                "report_id": report_id,
                "report": report if isinstance(report, dict) else str(report)
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Rapor alma hatası: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Rapor alınırken hata oluştu: {str(e)}"
        )


# ============================
# PROJE SCAFFOLDING ENDPOİNTLERİ
# ============================

@router.post(
    "/new-project",
    response_model=QAStatusResponse,
    summary="Yeni Test Projesi Oluştur",
    description="Sıfırdan yeni bir test otomasyon projesi oluşturur ve ZIP dosyası sağlar",
)
async def create_new_project(request: ProjectConfig) -> QAStatusResponse:
    """
    Sıfırdan yeni bir test otomasyon projesi iskele (scaffold) oluştur.

    Proje yapısı, test dosyaları, sayfa nesneleri, konfigürasyon ve
    fixture'ları otomatik olarak oluşturur.

    Args:
        request: ProjectConfig nesnesi (project_name, base_url, browser, vs.)

    Returns:
        QAStatusResponse: Proje bilgilerini ve indirme linkini içeren yanıt
    """
    try:
        logger.info(f"Yeni proje oluşturulüyor: {request.project_name}")

        # ProjectScaffolder oluştur
        config_dict = request.model_dump()
        scaffolder = ProjectScaffolder(config_dict)

        # Proje yapısını oluştur
        scaffold_result = scaffolder.scaffold()
        logger.info(f"Proje scaffolding tamamlandı: {request.project_name}")

        # Proje arsivi oluştur (ZIP)
        archive_data = scaffolder.create_project_archive()
        archive_id = f"archive_{datetime.now().timestamp()}"

        logger.info(f"Proje arşivi oluşturuldu: {archive_id}")

        return QAStatusResponse(
            status="success",
            message=f"Proje '{request.project_name}' başarıyla oluşturuldu",
            data={
                "project_name": request.project_name,
                "project_path": str(scaffold_result.get('project_path')),
                "files_created": scaffold_result.get('files_created', []),
                "total_files": len(scaffold_result.get('files_created', [])),
                "archive_id": archive_id,
                "download_link": f"/api/qa/project-download/{archive_id}",
                "base_url": request.base_url,
                "browser": request.browser,
                "headless": request.headless
            }
        )

    except Exception as e:
        logger.error(f"Proje oluşturma hatası: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Proje oluşturma sırasında hata oluştu: {str(e)}"
        )


# ============================
# ORTAM YÖNETİMİ ENDPOİNTLERİ
# ============================

@router.get(
    "/environments",
    response_model=QAStatusResponse,
    summary="Ortam Listesi",
    description="Tanımlı test ortamlarının (dev, staging, prod) listesini döndürür",
)
async def list_environments() -> QAStatusResponse:
    """
    Tüm tanımlı test ortamlarını listele.

    Returns:
        QAStatusResponse: Ortam listesini içeren yanıt
    """
    try:
        logger.info("Ortam listesi alınıyor")
        environments = qa_engine.environment_manager.list_environments()

        return QAStatusResponse(
            status="success",
            message=f"{len(environments)} ortam bulundu",
            data={
                "environments": environments,
                "total": len(environments)
            }
        )

    except Exception as e:
        logger.error(f"Ortam listesi hatası: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ortam listesi alınırken hata oluştu: {str(e)}"
        )


@router.post(
    "/environments",
    response_model=QAStatusResponse,
    summary="Ortam Ekle",
    description="Yeni bir test ortamı (dev, staging, prod) ekler",
)
async def add_environment(request: EnvironmentConfig) -> QAStatusResponse:
    """
    Yeni bir test ortamı ekle.

    Args:
        request: EnvironmentConfig nesnesi (name, base_url, api_url, vs.)

    Returns:
        QAStatusResponse: Ortam ekleme sonucunu içeren yanıt
    """
    try:
        logger.info(f"Ortam ekleniyor: {request.name}")
        config_dict = request.model_dump()

        success = qa_engine.environment_manager.add_environment(
            request.name,
            config_dict
        )

        if not success:
            logger.warning(f"Ortam eklenemedi: {request.name}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ortam eklenemedi: {request.name}"
            )

        logger.info(f"Ortam eklendi: {request.name}")
        return QAStatusResponse(
            status="success",
            message=f"Ortam '{request.name}' başarıyla eklendi",
            data={
                "environment_name": request.name,
                "base_url": request.base_url,
                "api_url": request.api_url
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ortam ekleme hatası: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ortam eklerken hata oluştu: {str(e)}"
        )


@router.delete(
    "/environments/{name}",
    response_model=QAStatusResponse,
    summary="Ortam Sil",
    description="Tanımlı bir test ortamını siler",
)
async def delete_environment(name: str) -> QAStatusResponse:
    """
    Belirtilen ada sahip ortamı sil.

    Args:
        name: Silinecek ortamın adı (dev, staging, prod, vs.)

    Returns:
        QAStatusResponse: Ortam silme sonucunu içeren yanıt
    """
    try:
        logger.info(f"Ortam siliniyor: {name}")

        success = qa_engine.environment_manager.remove_environment(name)

        if not success:
            logger.warning(f"Ortam silinemedi: {name}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ortam bulunamadı: {name}"
            )

        logger.info(f"Ortam silindi: {name}")
        return QAStatusResponse(
            status="success",
            message=f"Ortam '{name}' başarıyla silindi",
            data={"deleted_environment": name}
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ortam silme hatası: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ortam silinirken hata oluştu: {str(e)}"
        )


# ============================
# PERFORMANS ANALİZİ ENDPOİNTLERİ
# ============================

@router.post(
    "/performance",
    response_model=QAStatusResponse,
    summary="Performans Analizi",
    description="Verilen URL için detaylı performans analizi yapır",
)
async def analyze_performance(request: TestPlanRequest) -> QAStatusResponse:
    """
    URL'nin performansını analiz et (sayfa yükleme süresi, Core Web Vitals, vs.).

    Args:
        request: TestPlanRequest nesnesi (url alanı)

    Returns:
        QAStatusResponse: Performans metrikleri içeren yanıt
    """
    try:
        logger.info(f"Performans analizi başlatılıyor: {request.url}")
        performance = await qa_engine.performance_analyzer.analyze_performance(
            request.url
        )

        if 'error' in performance:
            logger.error(f"Performans analizi hatası: {performance.get('error')}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Performans analizi başarısız: {performance.get('error')}"
            )

        logger.info(f"Performans analizi tamamlandı: {request.url}")
        return QAStatusResponse(
            status="success",
            message="Performans analizi başarıyla tamamlandı",
            data=performance
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Performans analizi hatası: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Performans analizi sırasında hata oluştu: {str(e)}"
        )


# ============================
# TAM PIPELINE ENDPOİNTLERİ
# ============================

@router.post(
    "/full-pipeline",
    response_model=QAStatusResponse,
    summary="Tam QA Pipeline",
    description="Tüm QA adımlarını (analiz, plan, otomasyon, test, vs.) bir kez çalıştırır",
)
async def run_full_pipeline(request: TestPlanRequest) -> QAStatusResponse:
    """
    Tam QA pipeline'ını çalıştır (9 adım):
    1. URL analizi
    2. Test planı üretimi
    3. Otomasyon script'leri
    4. Test çalıştırma
    5. Monkey testing
    6. Rapor üretimi
    7. Ortam yönetimi
    8. Performans analizi
    9. CI/CD şablonu

    Args:
        request: TestPlanRequest nesnesi (url, test_types, environment, vs.)

    Returns:
        QAStatusResponse: Tam pipeline sonuçlarını içeren yanıt
    """
    try:
        logger.info(f"Tam pipeline başlatılıyor: {request.url}")

        result = await qa_engine.run_full_pipeline(
            request.url,
            request.test_types,
            request.environment
        )

        if 'error' in result:
            logger.error(f"Pipeline hatası: {result.get('error')}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Pipeline başarısız: {result.get('error')}"
            )

        logger.info(f"Tam pipeline tamamlandı: {result.get('pipeline_id')}")
        return QAStatusResponse(
            status="success",
            message="Tam QA pipeline başarıyla tamamlandı",
            data=result
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Pipeline hatası: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline çalıştırma sırasında hata oluştu: {str(e)}"
        )


# ============================
# CI/CD ŞABLONLARı ENDPOİNTLERİ
# ============================

@router.get(
    "/cicd-template/{provider}",
    response_model=QAStatusResponse,
    summary="CI/CD Şablonu",
    description="Belirtilen CI/CD sağlayıcısı (GitHub Actions, Jenkins) için yapılandırma şablonu döndürür",
)
async def get_cicd_template(provider: str) -> QAStatusResponse:
    """
    Belirtilen CI/CD sağlayıcısı için yapılandırma şablonu getir.

    Args:
        provider: CI/CD sağlayıcısı ("github_actions" veya "jenkins")

    Returns:
        QAStatusResponse: CI/CD şablonu içeriğini içeren yanıt
    """
    try:
        logger.info(f"CI/CD şablonu alınıyor: {provider}")

        # Sağlayıcı adını doğrula
        valid_providers = ["github_actions", "jenkins"]
        if provider not in valid_providers:
            logger.warning(f"Geçersiz CI/CD sağlayıcısı: {provider}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Geçersiz sağlayıcı: {provider}. "
                       f"Desteklenenler: {', '.join(valid_providers)}"
            )

        template = qa_engine.generate_cicd_template(provider)

        if not template:
            logger.warning(f"Şablon oluşturulamadı: {provider}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Şablon oluşturulamadı: {provider}"
            )

        logger.info(f"CI/CD şablonu getirildi: {provider}")
        return QAStatusResponse(
            status="success",
            message=f"{provider} için CI/CD şablonu başarıyla alındı",
            data={
                "provider": provider,
                "template": template,
                "template_type": "yaml" if provider == "github_actions" else "groovy"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"CI/CD şablonu hatası: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"CI/CD şablonu alınırken hata oluştu: {str(e)}"
        )


# ============================
# SAĞ ŎLUK KONTROLÜ (HEALTH CHECK)
# ============================

@router.get(
    "/health",
    response_model=QAStatusResponse,
    summary="Sağlık Kontrolü",
    description="QA Engine'in çalışır durumda olup olmadığını kontrol eder",
)
async def health_check() -> QAStatusResponse:
    """
    QA Engine'in sağlık durumunu kontrol et.

    Returns:
        QAStatusResponse: Sağlık durumunu bildiren yanıt
    """
    try:
        logger.info("Sağlık kontrolü yapılıyor")

        # Temel kontroller
        qa_engine_ok = qa_engine is not None
        env_manager_ok = qa_engine.environment_manager is not None

        return QAStatusResponse(
            status="success" if (qa_engine_ok and env_manager_ok) else "error",
            message="QA Engine sağlıklı" if (qa_engine_ok and env_manager_ok)
                   else "QA Engine sorunlu",
            data={
                "timestamp": datetime.now().isoformat(),
                "qa_engine": "ok" if qa_engine_ok else "error",
                "environment_manager": "ok" if env_manager_ok else "error",
                "version": "1.0.0"
            }
        )

    except Exception as e:
        logger.error(f"Sağlık kontrolü hatası: {str(e)}")
        return QAStatusResponse(
            status="error",
            message="Sağlık kontrolü başarısız",
            data={"error": str(e)}
        )
