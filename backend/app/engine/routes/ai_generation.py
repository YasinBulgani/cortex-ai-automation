"""
AI Test/BDD üretim route'ları — Flask engine'den port edilmiş.

ÖNCE (Flask):
  /engine/routes/ai_generation_routes.py — Blueprint, port 5001

SONRA (FastAPI):
  /backend/app/engine/routes/ai_generation.py — APIRouter, port 8000 (consolidated)

Endpoint'ler:
  POST /api/ai/generate-test   — Doğal dil → test kodu
  POST /api/ai/generate-bdd    — Doğal dil → Gherkin feature
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["engine", "ai-generation"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class GenerateTestRequest(BaseModel):
    requirement: str = Field(..., min_length=1, description="Doğal dil gereksinim metni")
    framework: str = Field("pytest-bdd", description="Hedef test framework'ü")
    model: Optional[str] = Field(None, description="Kullanılacak LLM modeli (opsiyonel)")
    page_objects: Optional[list[str]] = Field(None, description="Mevcut page object isimleri")


class GenerateTestResponse(BaseModel):
    framework: str
    code: str
    file_path: str
    validation_passed: bool
    validation_errors: list[str]


class GenerateBDDRequest(BaseModel):
    requirement: str = Field(..., min_length=1, description="Doğal dil gereksinim metni")
    model: Optional[str] = Field(None, description="Kullanılacak LLM modeli (opsiyonel)")


class GenerateBDDResponse(BaseModel):
    feature_content: str
    step_definitions: str
    matched_existing_steps: list[str]
    new_steps_needed: list[str]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_gateway():
    """LLM gateway örneğini döndürür."""
    try:
        from services import get_llm_gateway  # type: ignore[import]
        return get_llm_gateway()
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"LLM gateway servisine erişilemiyor: {exc}",
        )


def _check_feature(name: str) -> None:
    """Feature flag kontrolü; devre dışıysa 503 fırlatır."""
    try:
        from services import is_feature_enabled  # type: ignore[import]
        if not is_feature_enabled(name):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"'{name}' özelliği ai_config.yaml'da devre dışı",
            )
    except ImportError:
        logger.warning(
            "Opsiyonel bağımlılık 'services.is_feature_enabled' yüklenemedi, "
            "feature flag kontrolü atlanıyor (ai_generation)."
        )


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.post("/generate-test", response_model=GenerateTestResponse)
def generate_test(body: GenerateTestRequest) -> GenerateTestResponse:
    """Doğal dil gereksinimden test kodu üretir."""
    _check_feature("test_generation")
    gw = _get_gateway()
    if not gw.available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM API anahtarı yapılandırılmamış",
        )

    try:
        from services.ai_test_generator import AITestGenerator  # type: ignore[import]
        generator = AITestGenerator(gateway=gw, model=body.model)
        result = generator.generate_from_requirement(
            requirement=body.requirement,
            framework=body.framework,
            page_objects=body.page_objects,
        )
        return GenerateTestResponse(
            framework=result.framework,
            code=result.code,
            file_path=result.file_path,
            validation_passed=result.validation_passed,
            validation_errors=result.validation_errors,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Test üretimi başarısız: {exc}",
        )


@router.post("/generate-bdd", response_model=GenerateBDDResponse)
def generate_bdd(body: GenerateBDDRequest) -> GenerateBDDResponse:
    """Doğal dil gereksinimden BDD Gherkin senaryosu üretir."""
    _check_feature("bdd_generation")
    gw = _get_gateway()
    if not gw.available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM API anahtarı yapılandırılmamış",
        )

    try:
        from services.bdd_generator import BDDGenerator  # type: ignore[import]
        generator = BDDGenerator(gateway=gw, model=body.model)
        result = generator.generate(body.requirement)
        return GenerateBDDResponse(
            feature_content=result.feature_content,
            step_definitions=result.step_definitions,
            matched_existing_steps=result.matched_existing_steps,
            new_steps_needed=result.new_steps_needed,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"BDD üretimi başarısız: {exc}",
        )
