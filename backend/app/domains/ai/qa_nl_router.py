"""QA orchestration and NL test-generation endpoints."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.domains.ai.router_shared import (
    CurrentUser,
    DB,
    check_llm_access,
    raise_structured_internal_error,
    record_llm_usage_safe,
    require_project_access,
)

logger = logging.getLogger(__name__)

router = APIRouter()


class QAPlanRequest(BaseModel):
    goal: str = Field(..., min_length=3, description="QA hedefi — ornegin 'Transfer endpoint kapsamini artir'")
    context: Optional[Dict] = Field(default=None, description="Ek baglam bilgisi")


class QAPlanStep(BaseModel):
    step_id: int
    action: str
    description: str
    target: Optional[str] = None
    params: Dict = Field(default_factory=dict)
    depends_on: List[int] = Field(default_factory=list)
    estimated_duration_ms: int = 5000


class QAPlanResponse(BaseModel):
    plan_id: str
    goal: str
    steps: List[Dict]
    estimated_total_duration_ms: int
    coverage_before: float = 0.0
    expected_coverage_after: float = 0.0


class QACycleResponse(BaseModel):
    plan_id: str
    goal_achieved: bool = False
    coverage_before: float = 0.0
    coverage_after: float = 0.0
    coverage_delta: float = 0.0
    tests_generated: int = 0
    tests_executed: int = 0
    tests_passed: int = 0
    failures_healed: int = 0
    flaky_detected: int = 0
    assertions_added: int = 0
    quality_score: float = 0.0
    next_recommendations: List[str] = Field(default_factory=list)


class QAExploreRequest(BaseModel):
    spec_id: Optional[str] = Field(default=None, description="Belirli bir spec ile sinirla")


class NLTestRequest(BaseModel):
    text: str = Field(..., min_length=3, description="Dogal dil test aciklamasi")
    output_format: str = Field(
        default="api_test",
        description="Cikti formati: api_test, bdd, pytest, playwright",
    )
    context: Optional[Dict] = Field(default=None, description="Ek baglam bilgisi")


class ParsedIntent(BaseModel):
    test_type: str = "positive"
    method: Optional[str] = None
    path_hint: Optional[str] = None
    expected_status: Optional[int] = None
    conditions: List[str] = Field(default_factory=list)
    entities: Dict[str, str] = Field(default_factory=dict)


class MatchedEndpoint(BaseModel):
    endpoint_id: str
    method: str
    path: str
    confidence: float


class GeneratedOutput(BaseModel):
    test_cases: List[Dict] = Field(default_factory=list)
    code: Optional[str] = None
    gherkin: Optional[str] = None


class ValidationResult(BaseModel):
    syntax_valid: bool = True
    warnings: List[str] = Field(default_factory=list)


class NLTestResponse(BaseModel):
    input_text: str
    parsed_intent: Dict
    matched_endpoints: List[Dict]
    output_format: str
    generated: Dict
    validation: Dict
    model_used: str
    duration_ms: float


class BatchNLRequest(BaseModel):
    texts: List[str] = Field(..., min_items=1, description="Dogal dil test aciklamalari listesi")
    output_format: str = Field(default="api_test")


class BatchNLResponse(BaseModel):
    results: List[Dict]
    summary: Dict


class EndpointSuggestion(BaseModel):
    text: str
    test_type: str
    priority: str


class SuggestFromEndpointResponse(BaseModel):
    endpoint_id: str
    endpoint: str
    suggestions: List[Dict]


class ValidateCodeRequest(BaseModel):
    code: str = Field(..., min_length=1, description="Dogrulanacak kod")
    language: str = Field(..., description="python veya typescript")


@router.post("/qa/plan")
def qa_create_plan(
    body: QAPlanRequest,
    db: DB,
    user: CurrentUser,
    project_id: str = "",
):
    if not project_id:
        raise HTTPException(400, "project_id query parametresi gerekli")
    require_project_access(db, user, project_id)

    try:
        from app.domains.ai.qa_orchestrator import QAOrchestrator

        orchestrator = QAOrchestrator(db=db, project_id=project_id, user_id=str(user.id))
        plan = orchestrator.plan(goal=body.goal, context=body.context)
        return plan
    except Exception as exc:
        logger.exception("QA plan olusturma hatasi")
        raise_structured_internal_error("ai_qa_plan_failed", "QA plan hatasi", exc)


@router.post("/qa/execute/{plan_id}")
def qa_execute_plan(
    plan_id: str,
    db: DB,
    user: CurrentUser,
    project_id: str = "",
):
    if not project_id:
        raise HTTPException(400, "project_id query parametresi gerekli")
    require_project_access(db, user, project_id)

    try:
        from app.domains.ai.qa_orchestrator import QAOrchestrator

        orchestrator = QAOrchestrator(db=db, project_id=project_id, user_id=str(user.id))
        result = orchestrator.act(plan_id=plan_id)
        if "error" in result:
            raise HTTPException(404, result["error"])
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("QA plan yurutme hatasi")
        raise_structured_internal_error("ai_qa_execute_failed", "QA execute hatasi", exc)


@router.post("/qa/verify/{plan_id}")
def qa_verify_plan(
    plan_id: str,
    db: DB,
    user: CurrentUser,
    project_id: str = "",
):
    if not project_id:
        raise HTTPException(400, "project_id query parametresi gerekli")
    require_project_access(db, user, project_id)

    try:
        from app.domains.ai.qa_orchestrator import QAOrchestrator

        orchestrator = QAOrchestrator(db=db, project_id=project_id, user_id=str(user.id))
        result = orchestrator.verify(plan_id=plan_id)
        if "error" in result:
            raise HTTPException(404, result["error"])
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("QA dogrulama hatasi")
        raise_structured_internal_error("ai_qa_verify_failed", "QA verify hatasi", exc)


@router.post("/qa/full-cycle")
def qa_full_cycle(
    body: QAPlanRequest,
    db: DB,
    user: CurrentUser,
    project_id: str = "",
):
    if not project_id:
        raise HTTPException(400, "project_id query parametresi gerekli")
    require_project_access(db, user, project_id)

    try:
        from app.domains.ai.qa_orchestrator import QAOrchestrator

        orchestrator = QAOrchestrator(db=db, project_id=project_id, user_id=str(user.id))
        result = orchestrator.run_full_cycle(goal=body.goal, context=body.context)
        return result
    except Exception as exc:
        logger.exception("QA full-cycle hatasi")
        raise_structured_internal_error("ai_qa_full_cycle_failed", "QA full-cycle hatasi", exc)


@router.post("/qa/explore")
def qa_explore(
    body: QAExploreRequest,
    db: DB,
    user: CurrentUser,
    project_id: str = "",
):
    if not project_id:
        raise HTTPException(400, "project_id query parametresi gerekli")
    require_project_access(db, user, project_id)

    try:
        from app.domains.ai.qa_orchestrator import QAOrchestrator

        orchestrator = QAOrchestrator(db=db, project_id=project_id, user_id=str(user.id))
        result = orchestrator.explore(spec_id=body.spec_id)
        return result
    except Exception as exc:
        logger.exception("QA explore hatasi")
        raise_structured_internal_error("ai_qa_explore_failed", "QA explore hatasi", exc)


@router.get("/qa/status/{plan_id}")
def qa_plan_status(
    plan_id: str,
    user: CurrentUser,
    db: DB,
    project_id: str = "",
):
    try:
        require_project_access(db, user, project_id)
        from app.deps import _user_permissions
        from app.domains.ai.qa_orchestrator import get_plan_status_scoped

        perms = _user_permissions(user)
        result = get_plan_status_scoped(
            plan_id,
            project_id=project_id,
            user_id=str(user.id),
            is_admin="admin.*" in perms,
        )
        if "error" in result:
            raise HTTPException(404, result["error"])
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("QA status retrieval failed for plan %s", plan_id)
        raise_structured_internal_error("ai_qa_status_failed", "QA status hatasi", exc)


@router.post("/nl-test/generate", response_model=NLTestResponse)
def nl_test_generate(
    body: NLTestRequest,
    db: DB,
    user: CurrentUser,
    project_id: str = "",
):
    if not project_id:
        raise HTTPException(400, "project_id query parametresi gerekli")
    require_project_access(db, user, project_id)

    valid_formats = ("api_test", "bdd", "pytest", "playwright")
    if body.output_format not in valid_formats:
        raise HTTPException(400, "Gecersiz output_format. Izin verilen: %s" % ", ".join(valid_formats))
    check_llm_access(str(user.id))

    try:
        from app.domains.ai.nl_test_generator import NLTestGenerator

        generator = NLTestGenerator(db=db, project_id=project_id)
        result = generator.generate_from_text(
            text=body.text,
            output_format=body.output_format,
            context=body.context,
        )
        record_llm_usage_safe(str(user.id), body.text, body.context, result)
        return result
    except Exception as exc:
        logger.exception("NL test generation hatasi")
        raise_structured_internal_error("ai_nl_test_generate_failed", "NL test uretim hatasi", exc)


@router.post("/nl-test/batch", response_model=BatchNLResponse)
def nl_test_batch(
    body: BatchNLRequest,
    db: DB,
    user: CurrentUser,
    project_id: str = "",
):
    if not project_id:
        raise HTTPException(400, "project_id query parametresi gerekli")
    require_project_access(db, user, project_id)

    if len(body.texts) > 50:
        raise HTTPException(400, "Tek seferde en fazla 50 metin gonderilebilir")
    check_llm_access(str(user.id))

    try:
        from app.domains.ai.nl_test_generator import NLTestGenerator

        generator = NLTestGenerator(db=db, project_id=project_id)
        result = generator.batch_generate(
            texts=body.texts,
            output_format=body.output_format,
        )
        record_llm_usage_safe(str(user.id), body.texts, result)
        return result
    except Exception as exc:
        logger.exception("NL batch generation hatasi")
        raise_structured_internal_error("ai_nl_test_batch_failed", "NL batch uretim hatasi", exc)


@router.post("/nl-test/suggest/{endpoint_id}", response_model=SuggestFromEndpointResponse)
def nl_test_suggest(
    endpoint_id: str,
    db: DB,
    user: CurrentUser,
    project_id: str = "",
    count: int = 5,
):
    if not project_id:
        raise HTTPException(400, "project_id query parametresi gerekli")
    require_project_access(db, user, project_id)

    count = min(max(count, 1), 20)
    check_llm_access(str(user.id))

    try:
        from app.domains.ai.nl_test_generator import NLTestGenerator

        generator = NLTestGenerator(db=db, project_id=project_id)
        result = generator.suggest_from_endpoint(
            endpoint_id=endpoint_id,
            count=count,
        )
        record_llm_usage_safe(str(user.id), endpoint_id, result)
        return result
    except Exception as exc:
        logger.exception("NL test suggest hatasi")
        raise_structured_internal_error("ai_nl_test_suggest_failed", "NL suggest hatasi", exc)


@router.post("/nl-test/validate")
def nl_test_validate(
    body: ValidateCodeRequest,
    user: CurrentUser,
):
    _ = user
    valid_languages = ("python", "typescript")
    if body.language not in valid_languages:
        raise HTTPException(400, "Gecersiz language. Izin verilen: %s" % ", ".join(valid_languages))

    try:
        from app.domains.ai.nl_test_generator import NLTestGenerator
        from app.infra.database import SessionLocal

        with SessionLocal() as db:
            generator = NLTestGenerator(db=db, project_id="")
            result = generator.validate_code(body.code, body.language)
        return result
    except Exception as exc:
        logger.exception("NL test validate hatasi")
        raise_structured_internal_error("ai_validate_code_failed", "Kod dogrulama hatasi", exc)
