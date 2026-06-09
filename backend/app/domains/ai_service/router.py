"""AI Service Router - LLM-powered features."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from backend.app.deps import (
    get_current_user,
    require_permission,
    get_db,
)
from backend.app.core.logger import get_logger

from .schemas import (
    BDDGenerationRequest,
    BDDGenerationResponse,
    TestImprovementRequest,
    TestImprovementResponse,
    MissingTestSuggestion,
    MissingTestRequest,
    RegressionSelectionRequest,
    RegressionSelectionResponse,
    DefectAnalysisRequest,
    DefectAnalysisResponse,
    ReleaseNotesRequest,
    ReleaseNotesResponse,
    HallucinationValidationRequest,
    HallucinationValidationResponse,
)
from .service import (
    BDDGeneratorService,
    TestImproverService,
    MissingTestSuggesterService,
    RegressionSelectorService,
    RCAService,
    ReleaseNotesGeneratorService,
    HallucinationValidatorService,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/ai-service", tags=["ai_service"])


# MVP Feature 1: Test Scenario Generation
@router.post(
    "/generate-bdd",
    response_model=BDDGenerationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_bdd(
    request: BDDGenerationRequest,
    current_user=Depends(get_current_user),
    _=Depends(require_permission("ai.generate")),
    db=Depends(get_db),
):
    """Generate BDD test cases from user story or requirement."""
    try:
        service = BDDGeneratorService(db=db, current_user=current_user)
        result = await service.generate(
            story=request.story,
            project_id=request.project_id,
            context=request.context,
        )
        return BDDGenerationResponse(
            success=True,
            test_cases=result["test_cases"],
            confidence_score=result["confidence_score"],
            execution_time_ms=result["execution_time_ms"],
        )
    except Exception as e:
        logger.error(f"BDD generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# MVP Feature 2: Test Improvement
@router.post(
    "/improve-test",
    response_model=TestImprovementResponse,
    status_code=status.HTTP_200_OK,
)
async def improve_test(
    request: TestImprovementRequest,
    current_user=Depends(get_current_user),
    _=Depends(require_permission("ai.generate")),
    db=Depends(get_db),
):
    """Suggest improvements for existing test case."""
    try:
        service = TestImproverService(db=db, current_user=current_user)
        result = await service.improve(
            test_case_id=request.test_case_id,
            project_id=request.project_id,
        )
        return TestImprovementResponse(
            success=True,
            suggestions=result["suggestions"],
            quality_score=result["quality_score"],
        )
    except Exception as e:
        logger.error(f"Test improvement failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# MVP Feature 3: Missing Test Suggestions
@router.post(
    "/suggest-missing-tests",
    response_model=list[MissingTestSuggestion],
    status_code=status.HTTP_200_OK,
)
async def suggest_missing_tests(
    request: MissingTestRequest,
    current_user=Depends(get_current_user),
    _=Depends(require_permission("ai.generate")),
    db=Depends(get_db),
):
    """Analyze coverage gaps and suggest missing test cases."""
    try:
        service = MissingTestSuggesterService(db=db, current_user=current_user)
        suggestions = await service.suggest(
            project_id=request.project_id,
            requirement_ids=request.requirement_ids,
            min_confidence=request.min_confidence or 0.7,
        )
        return suggestions
    except Exception as e:
        logger.error(f"Missing test suggestion failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# MVP Feature 4: Regression Suite Selection
@router.post(
    "/select-regression-suite",
    response_model=RegressionSelectionResponse,
    status_code=status.HTTP_200_OK,
)
async def select_regression_suite(
    request: RegressionSelectionRequest,
    current_user=Depends(get_current_user),
    _=Depends(require_permission("ai.generate")),
    db=Depends(get_db),
):
    """Select optimal regression test suite based on code changes."""
    try:
        service = RegressionSelectorService(db=db, current_user=current_user)
        result = await service.select(
            project_id=request.project_id,
            code_changes=request.code_changes,
            max_test_count=request.max_test_count or 50,
        )
        return RegressionSelectionResponse(
            success=True,
            selected_test_ids=result["selected_test_ids"],
            coverage_prediction=result["coverage_prediction"],
            estimated_duration_minutes=result["estimated_duration_minutes"],
        )
    except Exception as e:
        logger.error(f"Regression selection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# MVP Feature 5: Defect RCA Analysis
@router.post(
    "/analyze-defect",
    response_model=DefectAnalysisResponse,
    status_code=status.HTTP_200_OK,
)
async def analyze_defect(
    request: DefectAnalysisRequest,
    current_user=Depends(get_current_user),
    _=Depends(require_permission("defects.read")),
    db=Depends(get_db),
):
    """Analyze defect and suggest root cause."""
    try:
        service = RCAService(db=db, current_user=current_user)
        result = await service.analyze(
            defect_id=request.defect_id,
            error_log=request.error_log,
            reproduction_steps=request.reproduction_steps,
        )
        return DefectAnalysisResponse(
            success=True,
            root_causes=result["root_causes"],
            confidence_score=result["confidence_score"],
            similar_defect_ids=result["similar_defect_ids"],
        )
    except Exception as e:
        logger.error(f"Defect analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# MVP Feature 6: Release Notes Generation
@router.post(
    "/generate-release-notes",
    response_model=ReleaseNotesResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_release_notes(
    request: ReleaseNotesRequest,
    current_user=Depends(get_current_user),
    _=Depends(require_permission("tspm.admin")),
    db=Depends(get_db),
):
    """Generate release notes from test results and defect fixes."""
    try:
        service = ReleaseNotesGeneratorService(db=db, current_user=current_user)
        result = await service.generate(
            project_id=request.project_id,
            version=request.version,
            fixed_defect_ids=request.fixed_defect_ids,
            new_features=request.new_features,
        )
        return ReleaseNotesResponse(
            success=True,
            content=result["content"],
            format=result["format"],  # markdown, html, text
        )
    except Exception as e:
        logger.error(f"Release notes generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# MVP Feature 7: Hallucination Detection
@router.post(
    "/validate-output",
    response_model=HallucinationValidationResponse,
    status_code=status.HTTP_200_OK,
)
async def validate_output(
    request: HallucinationValidationRequest,
    current_user=Depends(get_current_user),
    _=Depends(require_permission("ai.generate")),
    db=Depends(get_db),
):
    """Validate LLM output for hallucinations."""
    try:
        service = HallucinationValidatorService(db=db, current_user=current_user)
        result = await service.validate(
            output_text=request.output_text,
            output_type=request.output_type,  # bdd, code, summary, etc
            source_context=request.source_context,
        )
        return HallucinationValidationResponse(
            is_valid=result["is_valid"],
            confidence_score=result["confidence_score"],
            hallucination_risks=result["hallucination_risks"],
            recommendations=result["recommendations"],
        )
    except Exception as e:
        logger.error(f"Output validation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Health check
@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check(
    current_user=Depends(get_current_user),
):
    """Health check for AI service."""
    return {
        "status": "ok",
        "service": "ai_service",
        "user_id": str(current_user.id),
    }
