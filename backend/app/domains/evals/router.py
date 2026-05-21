"""Eval REST API — admin ve CI self-service için.

Endpoints:
    GET  /evals/suites                 → mevcut suite'lerin listesi
    POST /evals/run                    → tüm veya seçili suite'leri koş (sync)
    GET  /evals/adapters               → kayıtlı adapter'lar
    GET  /evals/scorers                → kayıtlı scorer'lar

Uzun koşumlar için async ``jobs/`` domain'ine eklenebilir ama şu anki
ölçekte (~15 case) sync yeterli. Async versiyonu E1.1 Faz 2'de.
"""
from __future__ import annotations

from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.deps import require_permission
from app.infra.models import User

from .adapters import list_adapters
from .loader import load_suites
from .reporting import history_report, history_summary, latest_report, write_reports
from .runner import run_suite
from .schemas import SuiteResult
from .scorers import list_scorers

router = APIRouter(prefix="/evals", tags=["evals"])


_ADMIN_PERM = "admin.evals"


class SuiteListItem(BaseModel):
    name: str
    adapter: str
    case_count: int
    scorers: List[str]
    description: str = ""


class RunRequest(BaseModel):
    suite_names: Optional[List[str]] = Field(
        default=None,
        description="Koşulacak suite isimleri. Boş → hepsi.",
    )
    max_workers: Optional[int] = Field(default=None, ge=1, le=32)


class RunResponse(BaseModel):
    overall_passed: bool
    results: List[SuiteResult]


class LatestEvalResponse(BaseModel):
    latest: dict | None


class EvalHistoryResponse(BaseModel):
    runs: List[dict]


class EvalSummaryResponse(BaseModel):
    summary: dict


@router.get("/suites", response_model=List[SuiteListItem])
def list_suites_endpoint(
    _: Annotated[User, Depends(require_permission(_ADMIN_PERM))],
) -> List[SuiteListItem]:
    suites = load_suites()
    return [
        SuiteListItem(
            name=s.name,
            adapter=s.adapter_name,
            case_count=len(s.cases),
            scorers=list(s.scorers),
            description=s.description,
        )
        for s in suites
    ]


@router.get("/adapters", response_model=List[str])
def list_adapters_endpoint(
    _: Annotated[User, Depends(require_permission(_ADMIN_PERM))],
) -> List[str]:
    return list_adapters()


@router.get("/scorers", response_model=List[str])
def list_scorers_endpoint(
    _: Annotated[User, Depends(require_permission(_ADMIN_PERM))],
) -> List[str]:
    return list_scorers()


@router.get("/latest", response_model=LatestEvalResponse)
def latest_endpoint(
    _: Annotated[User, Depends(require_permission(_ADMIN_PERM))],
) -> LatestEvalResponse:
    return LatestEvalResponse(latest=latest_report())


@router.get("/history", response_model=EvalHistoryResponse)
def history_endpoint(
    _: Annotated[User, Depends(require_permission(_ADMIN_PERM))],
    limit: int = 50,
) -> EvalHistoryResponse:
    return EvalHistoryResponse(runs=history_report(limit=max(1, min(limit, 500))))


@router.get("/summary", response_model=EvalSummaryResponse)
def summary_endpoint(
    _: Annotated[User, Depends(require_permission(_ADMIN_PERM))],
    limit: int = 30,
) -> EvalSummaryResponse:
    return EvalSummaryResponse(summary=history_summary(limit=max(1, min(limit, 500))))


@router.post("/run", response_model=RunResponse)
def run_endpoint(
    payload: RunRequest,
    _: Annotated[User, Depends(require_permission(_ADMIN_PERM))],
) -> RunResponse:
    try:
        suites = load_suites(names=payload.suite_names)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    if not suites:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hiç eşleşen suite bulunamadı",
        )

    results = [run_suite(s, max_workers=payload.max_workers) for s in suites]
    write_reports(results)
    overall = all(r.passed for r in results)
    return RunResponse(overall_passed=overall, results=results)
