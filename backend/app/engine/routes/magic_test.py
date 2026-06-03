from __future__ import annotations
"""
Magic Test routes — Flask engine'den FastAPI'ye port edilmiştir.

ÖNCE (Flask):
  /engine/routes/magic_test_routes.py — Blueprint, port 5001

SONRA (FastAPI):
  /backend/app/engine/routes/magic_test.py — APIRouter, port 8000 (consolidated)

AI destekli test senaryosu üretimi, monkey testing ve strateji analizi endpoint'leri.

Not: Bu endpoint'ler AI ve Playwright çağrıları yapar ve yavaş olabilir.
Rate limiting için upstream proxy (nginx/API gateway) seviyesinde konfigürasyon önerilir.
Varsayılan page.goto timeout: 30 sn. AI çağrısı için toplam timeout: 120 sn.
"""

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse, PlainTextResponse
from pydantic import BaseModel, Field, field_validator, AnyHttpUrl

logger = logging.getLogger(__name__)

# AI/Playwright endpoint'leri için toplam istek timeout'u (saniye).
# Playwright page.goto 30 sn + AI işleme için ek pay.
_AI_REQUEST_TIMEOUT_SECONDS = 120

router = APIRouter(prefix="/api/magic", tags=["engine", "magic-test"])

# ─── Module-level singletons (engine-side) ───────────────────────────────────

_test_case_manager = None


def _get_test_case_manager():
    global _test_case_manager
    if _test_case_manager is None:
        from core.test_case_manager import TestCaseManager  # engine-side import
        _test_case_manager = TestCaseManager()
    return _test_case_manager


# ─── Schemas ─────────────────────────────────────────────────────────────────

_VALID_MONKEY_MODES = {"random", "smart", "hybrid"}
_VALID_EXPORT_FORMATS = {"gherkin", "json"}


class GenerateTestCasesBody(BaseModel):
    url: str = Field(..., description="Test edilecek sayfa URL'i (http/https zorunlu)")
    goals: str = Field(default="General testing", description="Test hedefleri")
    count: int = Field(default=5, ge=1, le=50)

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL http:// veya https:// ile başlamalıdır")
        return v.strip()


class MonkeyTestBody(BaseModel):
    url: str = Field(..., description="Monkey test edilecek sayfa URL'i (http/https zorunlu)")
    mode: str = Field(default="smart", description="random | smart | hybrid")
    iterations: int = Field(default=50, ge=1, le=500)
    timeout: int = Field(default=30, ge=5, le=300)

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL http:// veya https:// ile başlamalıdır")
        return v.strip()

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        if v not in _VALID_MONKEY_MODES:
            raise ValueError(f"Geçersiz mode. İzin verilenler: {_VALID_MONKEY_MODES}")
        return v


class AnalyzeStrategyBody(BaseModel):
    url: str = Field(..., description="Analiz edilecek sayfa URL'i (http/https zorunlu)")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL http:// veya https:// ile başlamalıdır")
        return v.strip()


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.post("/generate-test-cases", status_code=status.HTTP_201_CREATED, response_model=dict)
def generate_test_cases(body: GenerateTestCasesBody) -> dict:
    """
    AI açıklamalı test senaryoları üretir.

    Playwright ile sayfayı açar, PageInspector ile analiz eder,
    AI Engine ile senaryolar oluşturur ve TestCaseManager'a kaydeder.

    Uyarı: Bu endpoint Playwright + AI çağrısı yaptığından yavaş olabilir.
    Toplam yanıt süresi 30-120 saniye arasında değişebilir.
    Yüksek yük altında rate limiting için API gateway konfigürasyonu önerilir.
    """
    try:
        from core.ai_engine import get_ai_engine
        from core.page_inspector import PageInspector
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError

        test_case_manager = _get_test_case_manager()

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            try:
                try:
                    page.goto(body.url, wait_until="domcontentloaded", timeout=30000)
                except PWTimeoutError:
                    raise HTTPException(
                        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                        detail="Sayfa yüklenemedi: 30 saniyelik timeout aşıldı",
                    )
                page.wait_for_timeout(2000)

                inspector = PageInspector(page)
                page_summary = inspector.get_summary_text()
                page_type = inspector.detect_page_type()
                form_fields = inspector.get_form_fields_with_validation()

                enriched_goals = (
                    f"{body.goals}\n"
                    f"[Sayfa Tipi: {page_type}]\n"
                    f"[Form Alanları: {len(form_fields)} alan bulundu]"
                )

                ai_engine = get_ai_engine()
                test_cases_data = ai_engine.generate_test_cases_with_explanations(
                    url=body.url,
                    page_context=page_summary,
                    goals=enriched_goals,
                    count=body.count,
                )

                generated_cases = []
                for tc in test_cases_data:
                    test_id = test_case_manager.create_test_case(
                        url=body.url,
                        title=tc.get("title", "Test Senaryosu"),
                        steps=tc.get("steps", []),
                        explanations=tc.get("explanations", []),
                        description=tc.get("description"),
                        risk_level=tc.get("risk_level", "medium"),
                        tags=tc.get("tags", [page_type]),
                    )
                    generated_cases.append({
                        "test_id": test_id,
                        "title": tc.get("title", "Test Senaryosu"),
                        "risk_level": tc.get("risk_level", "medium"),
                        "step_count": len(tc.get("steps", [])),
                    })

                return {
                    "status": "success",
                    "page_type": page_type,
                    "test_cases": generated_cases,
                    "total": len(generated_cases),
                    "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                }
            finally:
                context.close()
                browser.close()

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("generate_test_cases failed: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Test senaryosu üretimi başarısız",
        )


@router.post("/monkey-test", status_code=status.HTTP_200_OK)
def monkey_test(body: MonkeyTestBody) -> StreamingResponse:
    """
    Monkey testing (keşif testi) çalıştırır.

    İlerlemeyi Server-Sent Events (SSE) akışı ile iletir.
    Bağlantı kesilirse browser session otomatik olarak kapatılır.

    mode: random | smart | hybrid
    iterations: Kaç adım atılacağı (1-500)
    timeout: Her adım için maksimum bekleme süresi saniye (5-300)
    """

    def generate_stream():
        try:
            from core.browser import BrowserEngine
            from core.monkey_test_engine import MonkeyTestEngine
            from playwright.sync_api import TimeoutError as PWTimeoutError

            browser_engine = BrowserEngine()
            page = browser_engine.get_page(body.url)

            try:
                try:
                    page.goto(body.url, wait_until="networkidle", timeout=30000)
                except PWTimeoutError:
                    yield f"data: {json.dumps({'error': 'Sayfa yüklenemedi: timeout'})}\n\n"
                    return

                monkey_engine = MonkeyTestEngine()

                for progress in monkey_engine.run_monkey_test_streamed(
                    page=page,
                    url=body.url,
                    mode=body.mode,
                    iterations=body.iterations,
                    timeout=body.timeout,
                ):
                    yield f"data: {json.dumps(progress)}\n\n"

            finally:
                browser_engine.close_page(page)

        except Exception as exc:
            logger.error("monkey_test stream error: %s", type(exc).__name__)
            yield f"data: {json.dumps({'error': 'Monkey test başarısız'})}\n\n"

    return StreamingResponse(generate_stream(), media_type="text/event-stream")


@router.post("/analyze-test-strategy", response_model=dict)
def analyze_test_strategy(body: AnalyzeStrategyBody) -> dict:
    """
    Sayfayı analiz eder ve en uygun test stratejisini önerir.

    Playwright ile sayfayı açar, etkileşimli elementleri ve form alanlarını tespit eder,
    AI Engine ile strateji analizi yapar ve sonucu TestCaseManager'a kaydeder.

    Uyarı: Bu endpoint Playwright + AI çağrısı yaptığından yavaş olabilir.
    Toplam yanıt süresi 30-120 saniye arasında değişebilir.
    """
    try:
        from core.ai_engine import get_ai_engine
        from core.page_inspector import PageInspector
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError

        test_case_manager = _get_test_case_manager()

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            try:
                try:
                    page.goto(body.url, wait_until="domcontentloaded", timeout=30000)
                except PWTimeoutError:
                    raise HTTPException(
                        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                        detail="Sayfa yüklenemedi: 30 saniyelik timeout aşıldı",
                    )
                page.wait_for_timeout(2000)

                inspector = PageInspector(page)
                page_summary = inspector.get_summary_text()
                page_type = inspector.detect_page_type()
                ranked_elements = inspector.get_interactive_elements_ranked()
                form_fields = inspector.get_form_fields_with_validation()

                enriched_context = (
                    f"{page_summary}\n"
                    f"[Tespit Edilen Sayfa Tipi: {page_type}]\n"
                    f"[Önemli Elementler: {len(ranked_elements)} adet]\n"
                    f"[Form Alanları: {len(form_fields)} adet, "
                    f"Zorunlu: {sum(1 for f in form_fields if f.get('required'))}]"
                )

                ai_engine = get_ai_engine()
                analysis = ai_engine.analyze_page_for_test_strategy(
                    url=body.url,
                    page_context=enriched_context,
                )
                analysis["page_type"] = page_type
                analysis["detected_elements_count"] = len(ranked_elements)
                analysis["form_fields_count"] = len(form_fields)

                analysis_id = test_case_manager.record_strategy_analysis(
                    url=body.url,
                    page_type=analysis.get("page_type", page_type),
                    complexity_score=analysis.get("complexity_score", 5.0),
                    critical_elements=analysis.get("critical_elements", []),
                    recommendations=analysis.get("recommendations", []),
                    best_practices=analysis.get("best_practices", []),
                )

                return {
                    "status": "success",
                    "analysis_id": analysis_id,
                    "analysis": analysis,
                    "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                }
            finally:
                context.close()
                browser.close()

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("analyze_test_strategy failed: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Strateji analizi başarısız",
        )


@router.get("/test-cases", response_model=dict)
def list_test_cases(
    url: str | None = Query(default=None, description="URL'ye göre filtrele"),
    limit: int = Query(default=50, ge=1, le=500),
) -> dict:
    """Üretilmiş test senaryolarını listeler. Opsiyonel URL filtresi."""
    try:
        test_case_manager = _get_test_case_manager()
        test_cases = test_case_manager.list_test_cases(url=url, limit=limit)
        return {"status": "success", "test_cases": test_cases, "total": len(test_cases)}
    except Exception as exc:
        logger.error("list_test_cases failed: %s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Test case listesi alınamadı",
        )


@router.get("/test-cases/{test_id}", response_model=dict)
def get_test_case(test_id: str) -> dict:
    """Belirli bir test senaryosunun detaylarını ve çalıştırma geçmişini döner."""
    try:
        test_case_manager = _get_test_case_manager()
        test_case = test_case_manager.get_test_case(test_id)

        if not test_case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Test case bulunamadı"
            )

        execution_history = test_case_manager.get_execution_history(test_id)
        return {
            "status": "success",
            "test_case": test_case,
            "execution_history": execution_history,
            "total_executions": len(execution_history),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("get_test_case failed for id=%s: %s", test_id, type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Test case alınamadı",
        )


@router.get("/test-cases/{test_id}/export")
def export_test_case(
    test_id: str,
    format: str = Query(default="gherkin", description="gherkin | json"),
):
    """
    Test senaryosunu Gherkin veya JSON formatında dışa aktarır.

    format: gherkin — plain text Gherkin (.feature) olarak döner
    format: json    — JSON dict olarak döner
    """
    if format not in _VALID_EXPORT_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Geçersiz format. İzin verilenler: {_VALID_EXPORT_FORMATS}",
        )

    try:
        test_case_manager = _get_test_case_manager()
        test_case = test_case_manager.get_test_case(test_id)

        if not test_case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Test case bulunamadı"
            )

        if format == "gherkin":
            gherkin_content = test_case_manager.export_test_case_to_gherkin(test_id)
            return PlainTextResponse(content=gherkin_content, status_code=200)

        # format == "json"
        return {"status": "success", "test_case": test_case}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("export_test_case failed for id=%s: %s", test_id, type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Test case export başarısız",
        )
