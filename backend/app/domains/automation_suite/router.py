"""Otomasyon Süiti HTTP API'si."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.deps import get_current_user
from app.domains.automation_suite import mobile as mobile_service
from app.domains.automation_suite import service as suite_service
from app.domains.automation_suite.mobile import (
    MobileGenerateRequest,
    MobileGenerateResponse,
)
from app.domains.automation_suite.schemas import (
    SuiteCatalogSuggestRequest,
    SuiteCatalogSuggestResponse,
    SuiteGenerateRequest,
    SuiteGenerateResponse,
    SuiteHealthResponse,
    SuiteRunRequest,
    SuiteRunResponse,
    SuiteRunStatus,
)
from app.infra.models import User

router = APIRouter(prefix="/automation-suite", tags=["automation-suite"])

CurrentUser = Annotated[User, Depends(get_current_user)]


@router.post(
    "/generate",
    response_model=SuiteGenerateResponse,
    status_code=status.HTTP_200_OK,
)
async def generate(
    body: SuiteGenerateRequest,
    _: CurrentUser,
) -> SuiteGenerateResponse:
    """Manuel testten Gherkin + otomasyon kodu üret.

    Engine'in `/api/pipeline/manual-to-automation` endpoint'ini çağırır,
    sonucu DSL kataloğuyla eşleştirir (bilinen/bilinmeyen cümlecik raporu
    ekler) ve `auto_run=true` ise koşumu arka planda tetikler.
    """
    try:
        return await suite_service.generate_from_manual_test(body)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/run",
    response_model=SuiteRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def run_suite(
    body: SuiteRunRequest,
    _: CurrentUser,
) -> SuiteRunResponse:
    """Mevcut bir feature dosyasını engine üzerinden koştur."""
    try:
        return await suite_service.start_run(body)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/runs/{run_id}", response_model=SuiteRunStatus)
def get_run(
    run_id: str,
    _: CurrentUser,
) -> SuiteRunStatus:
    """Koşum durumu (queued / running / passed / failed / error)."""
    rec = suite_service.get_run_status(run_id)
    if rec is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Koşum bulunamadı: {run_id}",
        )
    return rec


@router.post("/catalog/suggest", response_model=SuiteCatalogSuggestResponse)
def suggest_catalog(
    body: SuiteCatalogSuggestRequest,
    _: CurrentUser,
) -> SuiteCatalogSuggestResponse:
    """Serbest metin → DSL cümlecik önerisi.

    Wizard/manual-to-automation sayfası autocomplete için kullanır.
    """
    return suite_service.suggest_from_description(body.description, limit=body.limit)


@router.get("/health", response_model=SuiteHealthResponse)
async def health(_: CurrentUser) -> SuiteHealthResponse:
    """Backend + Engine + DSL sağlık özeti."""
    return await suite_service.health_snapshot()


@router.post("/mobile/generate", response_model=MobileGenerateResponse)
def mobile_generate(
    body: MobileGenerateRequest,
    _: CurrentUser,
) -> MobileGenerateResponse:
    """Doğal dil + cihaz bağlamı → mobil DSL cümlecikleriyle Gherkin.

    Visium Farm sayfasının "AI Mobil Senaryo Üretici" kartı bu endpoint'i
    çağırır. Katalogdaki `mobile.*` aksiyonları allowed listesine eklenir,
    Ollama sadece bu cümlecikleri kullanarak Gherkin üretir.
    """
    try:
        return mobile_service.generate_mobile_scenario(body)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
