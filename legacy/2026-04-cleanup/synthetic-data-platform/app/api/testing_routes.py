"""
Test Otomasyonu API Rotaları

FastAPI router'ı test otomasyonu, görsel regresyon, erişilebilirlik testi
ve test kaydı/oynatması için API endpoints'lerini sağlar.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, UploadFile, File, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
import logging

from app.schemas.testing_schemas import (
    VisualRegressionRequest,
    VisualRegressionResult,
    AccessibilityCheckRequest,
    AccessibilityReport,
    TestRecording,
    TestSessionSummary,
    TestRunRequest,
    TestRunResult,
    ChangeTypeEnum,
    A11yIssueSeverity,
    ActionTypeEnum,
    AssertionTypeEnum
)
from app.services.visual_regression import VisualRegressionTester, ChangeType
from app.services.accessibility_tester import AccessibilityTester, A11yIssueType
from app.services.test_recorder import TestRecorder, ActionType, AssertionType

logger = logging.getLogger(__name__)

# Router oluştur
router = APIRouter(
    prefix="/api/v1/testing",
    tags=["Test Otomasyonu"],
    responses={
        404: {"description": "Bulunamadı"},
        500: {"description": "Sunucu hatası"}
    }
)

# Singleton hizmetleri başlat
_visual_tester: Optional[VisualRegressionTester] = None
_accessibility_tester: Optional[AccessibilityTester] = None
_test_recorder: Optional[TestRecorder] = None


def get_visual_tester() -> VisualRegressionTester:
    """Görsel regresyon tester'ını alır (lazy initialization)."""
    global _visual_tester
    if _visual_tester is None:
        _visual_tester = VisualRegressionTester(
            baseline_dir="/tmp/baselines",
            current_dir="/tmp/current",
            diff_dir="/tmp/diffs"
        )
    return _visual_tester


def get_accessibility_tester() -> AccessibilityTester:
    """Erişilebilirlik tester'ını alır (lazy initialization)."""
    global _accessibility_tester
    if _accessibility_tester is None:
        _accessibility_tester = AccessibilityTester(min_contrast_ratio=4.5)
    return _accessibility_tester


def get_test_recorder() -> TestRecorder:
    """Test recorder'ını alır (lazy initialization)."""
    global _test_recorder
    if _test_recorder is None:
        _test_recorder = TestRecorder(recordings_dir="/tmp/recordings")
    return _test_recorder


# ==================== Görsel Regresyon Endpoints ====================

@router.post(
    "/visual-regression/run",
    response_model=VisualRegressionResult,
    summary="Görsel Regresyon Testi Çalıştır",
    description="Görsel regresyon testini çalıştırır, temel görüntüyü yakalar veya karşılaştırır."
)
async def run_visual_regression(
    request: VisualRegressionRequest,
    background_tasks: BackgroundTasks
) -> VisualRegressionResult:
    """
    Görsel regresyon testi çalıştırır.

    İki görüntüyü karşılaştırır veya temel görüntüyü yakalar.
    Benzerlik oranını ve değişim bölgelerini raporlar.

    Args:
        request: Görsel regresyon isteği
        background_tasks: Arka plan görevleri

    Returns:
        Görsel regresyon testi sonucu

    Raises:
        HTTPException: İstek geçersiz veya işlem başarısız ise
    """
    try:
        logger.info(f"Görsel regresyon testi başlatıldı - Test: {request.test_name}")

        tester = get_visual_tester()
        test_id = f"vr_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        if request.capture_baseline:
            # Temel görüntüyü yakala
            if not request.image_data:
                raise HTTPException(
                    status_code=400,
                    detail="Temel görüntü yakalamak için image_data gereklidir"
                )

            baseline_path = tester.capture_baseline(request.image_data, request.test_name)
            logger.info(f"Temel görüntü yakalandı: {baseline_path}")

            return VisualRegressionResult(
                test_id=test_id,
                test_name=request.test_name,
                passed=True,
                change_type=ChangeTypeEnum.identical,
                similarity_percentage=100.0,
                changed_pixels_count=0,
                changed_pixels_percentage=0.0,
                regions_affected=[],
                baseline_path=baseline_path,
                current_path=baseline_path,
                timestamp=datetime.utcnow()
            )

        elif request.baseline_path and request.current_path:
            # Görüntüleri karşılaştır
            identical, similarity = tester.compare_screenshots(
                request.baseline_path,
                request.current_path
            )

            # Görsel değişiklikleri tespit et
            change_report = tester.detect_visual_changes(
                request.baseline_path,
                request.current_path
            )

            diff_report_path = None
            if request.generate_diff_report:
                diff_report_path = tester.generate_diff_report(
                    request.baseline_path,
                    request.current_path,
                    f"/tmp/diffs/{request.test_name}_diff.png"
                )

                # JSON raporunu arka planda oluştur
                json_report_path = f"/tmp/diffs/{request.test_name}_report.json"
                background_tasks.add_task(
                    tester.generate_json_report,
                    change_report,
                    json_report_path
                )

            result = VisualRegressionResult(
                test_id=test_id,
                test_name=request.test_name,
                passed=identical or change_report.change_type != ChangeType.CRITICAL,
                change_type=ChangeTypeEnum(change_report.change_type.value),
                similarity_percentage=change_report.similarity_percentage,
                changed_pixels_count=change_report.changed_pixels_count,
                changed_pixels_percentage=change_report.changed_pixels_percentage,
                regions_affected=change_report.regions_affected,
                baseline_path=request.baseline_path,
                current_path=request.current_path,
                diff_report_path=diff_report_path,
                timestamp=datetime.utcnow()
            )

            logger.info(
                f"Görsel regresyon testi tamamlandı - "
                f"Test: {request.test_name}, Sonuç: {result.change_type.value}"
            )
            return result

        else:
            raise HTTPException(
                status_code=400,
                detail="Temel görüntü yakalama (capture_baseline) veya "
                       "karşılaştırma (baseline_path + current_path) gereklidir"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Görsel regresyon testi hatası: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/visual-regression/results",
    response_model=List[VisualRegressionResult],
    summary="Görsel Regresyon Sonuçlarını Listele",
    description="Kaydedilmiş tüm görsel regresyon test sonuçlarını listeler."
)
async def get_visual_regression_results(
    test_name: Optional[str] = Query(None, description="Test adına göre filtrele"),
    limit: int = Query(10, description="Maksimum sonuç sayısı")
) -> List[VisualRegressionResult]:
    """
    Görsel regresyon test sonuçlarını listeler.

    Args:
        test_name: Test adına göre filtreleme (opsiyonel)
        limit: Maksimum sonuç sayısı

    Returns:
        Test sonuçları listesi
    """
    try:
        # TODO: Veritabanından sonuçları sor
        logger.info("Görsel regresyon sonuçları alındı")
        return []

    except Exception as e:
        logger.error(f"Sonuç alma hatası: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Erişilebilirlik Endpoints ====================

@router.post(
    "/accessibility/check",
    response_model=AccessibilityReport,
    summary="Erişilebilirlik Kontrolü Çalıştır",
    description="Sayfa veya bileşen erişilebilirliğini WCAG 2.1 standartlarına göre kontrol eder."
)
async def run_accessibility_check(request: AccessibilityCheckRequest) -> AccessibilityReport:
    """
    Erişilebilirlik kontrolünü çalıştırır.

    WCAG 2.1 standartlarına göre renk kontrastı, ARIA etiketleri,
    klavye navigasyonu ve ekran okuyucu uyumluluğunu kontrol eder.

    Args:
        request: Erişilebilirlik kontrol isteği

    Returns:
        Erişilebilirlik raporu

    Raises:
        HTTPException: İstek geçersiz veya işlem başarısız ise
    """
    try:
        logger.info(f"Erişilebilirlik kontrolü başlatıldı - Test: {request.test_name}")

        tester = get_accessibility_tester()
        tester.passed_checks = 0
        tester.failed_checks = 0
        tester.issues = []

        test_id = f"a11y_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Renk kontrastı kontrolü
        if request.check_contrast:
            for element in request.elements:
                if "foreground_color" in element and "background_color" in element:
                    try:
                        tester.check_color_contrast(
                            element["foreground_color"],
                            element["background_color"],
                            element.get("text_size", 14),
                            element.get("is_bold", False)
                        )
                    except Exception as e:
                        logger.warning(f"Renk kontrastı kontrolü hatası: {e}")

        # ARIA etiketleri doğrulaması
        if request.check_aria_labels:
            tester.validate_aria_labels(request.elements)

        # Klavye navigasyonu kontrolü
        if request.check_keyboard:
            tester.check_keyboard_navigation(request.elements)

        # Ekran okuyucu uyumluluğu kontrolü
        if request.check_screen_reader:
            tester.check_screen_reader_compatibility(request.elements)

        # Raporu oluştur
        report = tester.generate_a11y_report(request.test_name, request.wcag_level)

        # Raporu sözlüğe dönüştür
        report_dict = {
            "test_id": test_id,
            "test_name": request.test_name,
            "test_date": report.test_date,
            "total_checks": report.total_checks,
            "passed_checks": report.passed_checks,
            "failed_checks": report.failed_checks,
            "compliance_percentage": report.compliance_percentage,
            "wcag_level": report.wcag_level,
            "issues": [
                {
                    "issue_type": issue.issue_type.value,
                    "severity": issue.severity,
                    "element_id": issue.element_id,
                    "element_type": issue.element_type,
                    "message": issue.message,
                    "suggestion": issue.suggestion,
                    "location": issue.location
                }
                for issue in report.issues
            ],
            "recommendations": report.recommendations,
            "timestamp": report.timestamp
        }

        logger.info(
            f"Erişilebilirlik kontrolü tamamlandı - "
            f"Test: {request.test_name}, Uyumluluk: {report.compliance_percentage:.2f}%"
        )

        return AccessibilityReport(**report_dict)

    except Exception as e:
        logger.error(f"Erişilebilirlik kontrolü hatası: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/accessibility/report/{test_id}",
    response_model=AccessibilityReport,
    summary="Erişilebilirlik Raporunu Getir",
    description="Belirtilen test ID'sine ait erişilebilirlik raporunu getirir."
)
async def get_accessibility_report(test_id: str) -> AccessibilityReport:
    """
    Kaydedilmiş bir erişilebilirlik raporunu getirir.

    Args:
        test_id: Test tanımlayıcısı

    Returns:
        Erişilebilirlik raporu

    Raises:
        HTTPException: Rapor bulunamazsa
    """
    try:
        logger.info(f"Erişilebilirlik raporu alındı - Test ID: {test_id}")
        # TODO: Veritabanından raporu sor
        raise HTTPException(status_code=404, detail="Rapor bulunamadı")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Rapor alma hatası: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Test Kaydı Endpoints ====================

@router.post(
    "/recorder/start",
    response_model=Dict[str, str],
    summary="Test Kaydını Başlat",
    description="Yeni bir test kaydı oturumunu başlatır."
)
async def start_recording(
    test_name: str = Query(..., description="Test adı"),
    description: str = Query("", description="Test açıklaması"),
    tags: List[str] = Query(None, description="Test etiketleri")
) -> Dict[str, str]:
    """
    Yeni bir test kaydı oturumunu başlatır.

    Args:
        test_name: Test adı
        description: Test açıklaması
        tags: Test etiketleri

    Returns:
        Oturum bilgileri (session_id vb.)

    Raises:
        HTTPException: Kaydı başlatma başarısız ise
    """
    try:
        recorder = get_test_recorder()
        session_id = recorder.start_recording(test_name, description, tags)

        logger.info(f"Test kaydı başlatıldı - Session ID: {session_id}")

        return {
            "session_id": session_id,
            "test_name": test_name,
            "status": "recording"
        }

    except Exception as e:
        logger.error(f"Test kaydı başlatma hatası: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/recorder/stop",
    response_model=TestRecording,
    summary="Test Kaydını Durdur",
    description="Aktif test kaydı oturumunu durdurur ve kaydeder."
)
async def stop_recording() -> TestRecording:
    """
    Aktif test kaydını durdurur.

    Returns:
        Tamamlanan test oturumu

    Raises:
        HTTPException: Oturum yoksa veya durdurma başarısız ise
    """
    try:
        recorder = get_test_recorder()
        session = recorder.stop_recording()

        logger.info(
            f"Test kaydı durduruldu - Session: {session.name}, "
            f"Adımlar: {len(session.steps)}"
        )

        # Oturumu sözlüğe dönüştür
        session_dict = {
            "id": session.id,
            "name": session.name,
            "description": session.description,
            "created_at": session.created_at,
            "started_at": session.started_at,
            "ended_at": session.ended_at,
            "status": session.status,
            "total_duration_ms": session.total_duration_ms,
            "success_rate": session.success_rate,
            "tags": session.tags,
            "steps": [
                {
                    "id": step.id,
                    "timestamp": step.timestamp,
                    "action": step.action.value,
                    "selector": step.selector,
                    "value": step.value,
                    "duration_ms": step.duration_ms,
                    "screenshot_path": step.screenshot_path,
                    "assertion_type": step.assertion_type.value if step.assertion_type else None,
                    "assertion_expected": step.assertion_expected,
                    "assertion_passed": step.assertion_passed,
                    "error_message": step.error_message,
                    "metadata": step.metadata
                }
                for step in session.steps
            ]
        }

        return TestRecording(**session_dict)

    except Exception as e:
        logger.error(f"Test kaydı durdurma hatası: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/recorder/sessions",
    response_model=List[TestSessionSummary],
    summary="Kaydedilen Oturumları Listele",
    description="Tüm kaydedilmiş test oturumlarını listeler."
)
async def list_sessions(
    tag: Optional[str] = Query(None, description="Etiket ile filtreleme"),
    limit: int = Query(20, description="Maksimum sonuç sayısı")
) -> List[TestSessionSummary]:
    """
    Kaydedilmiş tüm test oturumlarını listeler.

    Args:
        tag: Etiket ile filtreleme (opsiyonel)
        limit: Maksimum sonuç sayısı

    Returns:
        Test oturumu özeti listesi
    """
    try:
        recorder = get_test_recorder()
        sessions = recorder.list_recordings()

        # Etikete göre filtrele
        if tag:
            sessions = [s for s in sessions if tag in s.get("tags", [])]

        # Limiti uygula
        sessions = sessions[:limit]

        logger.info(f"Test oturumları listelendi - Toplam: {len(sessions)}")

        return [TestSessionSummary(**session) for session in sessions]

    except Exception as e:
        logger.error(f"Oturumları listeleme hatası: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/recorder/sessions/{session_id}",
    response_model=TestRecording,
    summary="Test Oturumunu Getir",
    description="Belirtilen session ID'sine ait test oturumunu getirir."
)
async def get_session(session_id: str) -> TestRecording:
    """
    Kaydedilmiş bir test oturumunu getirir.

    Args:
        session_id: Oturum tanımlayıcısı

    Returns:
        Test kaydı oturumu

    Raises:
        HTTPException: Oturum bulunamazsa
    """
    try:
        recorder = get_test_recorder()
        session = recorder._load_session(session_id)

        session_dict = {
            "id": session.id,
            "name": session.name,
            "description": session.description,
            "created_at": session.created_at,
            "started_at": session.started_at,
            "ended_at": session.ended_at,
            "status": session.status,
            "total_duration_ms": session.total_duration_ms,
            "success_rate": session.success_rate,
            "tags": session.tags,
            "steps": [
                {
                    "id": step.id,
                    "timestamp": step.timestamp,
                    "action": step.action.value,
                    "selector": step.selector,
                    "value": step.value,
                    "duration_ms": step.duration_ms,
                    "screenshot_path": step.screenshot_path,
                    "assertion_type": step.assertion_type.value if step.assertion_type else None,
                    "assertion_expected": step.assertion_expected,
                    "assertion_passed": step.assertion_passed,
                    "error_message": step.error_message,
                    "metadata": step.metadata
                }
                for step in session.steps
            ]
        }

        logger.info(f"Test oturumu alındı - Session ID: {session_id}")
        return TestRecording(**session_dict)

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Oturum bulunamadı")
    except Exception as e:
        logger.error(f"Oturum alma hatası: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/recorder/export",
    summary="Test Oturumunu Dışa Aktar",
    description="Kaydedilmiş bir test oturumunu JSON formatında dışa aktarır."
)
async def export_session(
    session_id: str = Query(..., description="Oturum tanımlayıcısı"),
    format: str = Query("json", description="Dışa aktarma formatı (json, yaml)")
) -> FileResponse:
    """
    Kaydedilmiş bir test oturumunu dışa aktarır.

    Args:
        session_id: Oturum tanımlayıcısı
        format: Dışa aktarma formatı

    Returns:
        Dışa aktarılan dosya

    Raises:
        HTTPException: Oturum bulunamazsa veya export başarısız ise
    """
    try:
        recorder = get_test_recorder()
        output_path = recorder.export_recording(session_id, format)

        logger.info(f"Test oturumu dışa aktarıldı - Output: {output_path}")

        return FileResponse(
            path=output_path,
            filename=Path(output_path).name,
            media_type="application/json"
        )

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Oturum bulunamadı")
    except Exception as e:
        logger.error(f"Dışa aktarma hatası: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/recorder/import",
    response_model=Dict[str, str],
    summary="Test Oturumunu İçe Aktar",
    description="JSON formatında bir test oturumunu içe aktarır."
)
async def import_session(file: UploadFile = File(...)) -> Dict[str, str]:
    """
    JSON formatında bir test oturumunu içe aktarır.

    Args:
        file: İçe aktarılacak JSON dosyası

    Returns:
        İçe aktarılan oturum bilgileri

    Raises:
        HTTPException: Dosya geçersiz veya import başarısız ise
    """
    try:
        # Dosyayı geçici olarak kaydet
        temp_path = f"/tmp/import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        content = await file.read()

        with open(temp_path, 'wb') as f:
            f.write(content)

        # İçe aktar
        recorder = get_test_recorder()
        session_id = recorder.import_recording(temp_path)

        logger.info(f"Test oturumu içe aktarıldı - Session ID: {session_id}")

        return {
            "session_id": session_id,
            "status": "imported"
        }

    except Exception as e:
        logger.error(f"İçe aktarma hatası: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Health Check ====================

@router.get(
    "/health",
    response_model=Dict[str, str],
    summary="Sağlık Kontrolü",
    description="Test otomasyonu API'sinin sağlık durumunu kontrol eder."
)
async def health_check() -> Dict[str, str]:
    """
    Test otomasyonu API'sinin sağlık durumunu kontrol eder.

    Returns:
        Sağlık durumu bilgileri
    """
    return {
        "status": "healthy",
        "service": "Test Otomasyonu API",
        "timestamp": datetime.utcnow().isoformat()
    }
