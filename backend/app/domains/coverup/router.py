"""CoverUp — Coverage-guided test generation API."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_current_user
from app.infra.database import get_db
from app.infra.models import User
from app.domains.tspm.models import TspmProject, TspmProjectMember

from .repository import CoverageReportRepository
from .schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    CoverageReport,
    CoverageReportListItem,
    CoverageUploadRequest,
    GenerateTestRequest,
    GenerateTestResponse,
    GeneratedTest,
    TrendResponse,
)
from .service import (
    analyze_report,
    build_trend_response,
    create_report,
    generate_tests,
    get_report_or_404,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/coverup", tags=["coverup"])

DB = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def _repository(db: Session) -> CoverageReportRepository:
    return CoverageReportRepository(db)


def _is_admin_user(user: User) -> bool:
    for role in user.roles:
        for role_permission in role.permissions:
            if role_permission.permission == "admin.*":
                return True
    return False


def _accessible_project_ids(db: Session, user: User) -> set[str] | None:
    """Return project IDs accessible to the user, or None for admins (all)."""
    if _is_admin_user(user):
        return None
    rows = db.execute(
        select(TspmProjectMember.project_id).where(TspmProjectMember.user_id == user.id)
    ).scalars().all()
    return {str(r) for r in rows}


def _require_project_access(project_id: str, db: Session, user: User) -> TspmProject:
    """Return the project if user has access, else raise 404."""
    project = db.get(TspmProject, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proje bulunamadı")
    ids = _accessible_project_ids(db, user)
    if ids is not None and project_id not in ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proje bulunamadı")
    return project


def _parse_generic(raw: str) -> list[dict[str, Any]]:
    """Bilinmeyen format — boş liste döner. Router 400 ile yanıt verir."""
    return []


from .parsers import parse_cobertura, parse_istanbul, parse_nyc, _parse_lcov, _parse_coveragepy


_PARSERS: dict[str, Any] = {
    "lcov": _parse_lcov,
    "coveragepy": _parse_coveragepy,
    "istanbul": parse_istanbul,
    "nyc": parse_nyc,
    "cobertura": parse_cobertura,
}


def _build_file_coverage(raw_file: dict[str, Any]) -> FileCoverage:
    """Ham parse sonucundan FileCoverage oluştur."""
    hits = raw_file.get("lines_hit", [])
    misses = raw_file.get("lines_missed", [])
    total = len(hits) + len(misses)
    br_total = raw_file.get("branches_total", 0)
    br_hit = raw_file.get("branches_hit", 0)
    fn_total = raw_file.get("functions_total", 0)
    fn_hit = raw_file.get("functions_hit", 0)

    return FileCoverage(
        file_path=raw_file["file_path"],
        total_lines=total,
        covered_lines=len(hits),
        missed_lines=len(misses),
        line_rate=round(len(hits) / total, 4) if total > 0 else 0.0,
        branch_rate=round(br_hit / br_total, 4) if br_total > 0 else 0.0,
        total_branches=br_total,
        covered_branches=br_hit,
        total_functions=fn_total,
        covered_functions=fn_hit,
        missed_line_numbers=misses,
        missed_branch_lines=[],
        uncovered_functions=[],
    )


def _build_summary(file_coverages: list[FileCoverage]) -> CoverageSummary:
    """Dosya listesinden toplam özet oluştur."""
    total_lines = sum(f.total_lines for f in file_coverages)
    covered_lines = sum(f.covered_lines for f in file_coverages)
    missed_lines = sum(f.missed_lines for f in file_coverages)
    total_fn = sum(f.total_functions for f in file_coverages)
    covered_fn = sum(f.covered_functions for f in file_coverages)
    total_br = sum(f.total_branches for f in file_coverages)
    covered_br = sum(f.covered_branches for f in file_coverages)

    return CoverageSummary(
        total_files=len(file_coverages),
        total_lines=total_lines,
        covered_lines=covered_lines,
        missed_lines=missed_lines,
        line_rate=round(covered_lines / total_lines, 4) if total_lines > 0 else 0.0,
        branch_rate=round(covered_br / total_br, 4) if total_br > 0 else 0.0,
        function_rate=round(covered_fn / total_fn, 4) if total_fn > 0 else 0.0,
        total_functions=total_fn,
        covered_functions=covered_fn,
    )


# ── Banking-critical path tespiti ────────────────────────────────────────────

_BANKING_KEYWORDS = [
    "auth", "login", "token", "jwt", "password", "credential",
    "payment", "transfer", "transaction", "balance", "account",
    "kvkk", "gdpr", "pci", "bddk", "audit", "compliance",
    "iban", "swift", "bic", "card", "credit", "debit",
    "kyc", "aml", "fraud", "otp", "2fa", "mfa",
    "encrypt", "decrypt", "hash", "sign", "verify",
]


def _is_banking_critical(file_path: str, function_name: str | None = None) -> list[str]:
    """Dosya/fonksiyon bankacilik-kritik mi? Risk faktorlerini dondur."""
    factors: list[str] = []
    path_lower = file_path.lower()
    fn_lower = (function_name or "").lower()
    combined = path_lower + " " + fn_lower

    for kw in _BANKING_KEYWORDS:
        if kw in combined:
            factors.append(f"banking_keyword:{kw}")

    return factors


def _score_gap(fc: FileCoverage, start: int, end: int) -> float:
    """Gap için risk skoru hesapla (0.0-1.0)."""
    gap_size = end - start + 1
    base = min(gap_size / 50.0, 0.5)  # Buyuk gap = yuksek risk

    # Dosya kapsam orani dusukse risk artar
    coverage_penalty = (1.0 - fc.line_rate) * 0.3

    # Bankacilik kritik mi
    banking_factors = _is_banking_critical(fc.file_path)
    banking_bonus = min(len(banking_factors) * 0.1, 0.3)

    score = base + coverage_penalty + banking_bonus
    return round(min(score, 1.0), 4)


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/upload", response_model=CoverageReport)
def upload_coverage(
    body: CoverageUploadRequest,
    db: DB,
    user: CurrentUser,
) -> CoverageReport:
    """Coverage raporu yükle ve parse et."""
    return create_report(_repository(db), body)


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze_coverage(
    body: AnalyzeRequest,
    db: DB,
    user: CurrentUser,
) -> AnalyzeResponse:
    """Coverage gap'lerini analiz et ve hedefleri belirle."""
    report = get_report_or_404(
        _repository(db),
        body.report_id,
        allowed_project_ids=_accessible_project_ids(db, user),
    )
    return analyze_report(report, body)


@router.post("/generate", response_model=GenerateTestResponse)
def generate_coverage_tests(
    body: GenerateTestRequest,
    db: DB,
    user: CurrentUser,
) -> GenerateTestResponse:
    """Kapsanmayan kod için test üret (AI destekli)."""
    report = get_report_or_404(
        _repository(db),
        body.report_id,
        allowed_project_ids=_accessible_project_ids(db, user),
    )

    # Hedefler belirtilmemisse high-risk hedefleri otomatik sec
    targets = body.targets
    if not targets:
        analyze_result = analyze_coverage(
            AnalyzeRequest(
                report_id=body.report_id,
                min_risk_score=0.5,
                max_targets=body.max_tests,
            ),
            db=db,
            user=user,
        )
        targets = analyze_result.targets

    if not targets:
        return GenerateTestResponse(
            tests=[],
            total_generated=0,
            estimated_total_gain=0.0,
        )

    # AI test generator çalıştır
    try:
        from .test_generator import CoverUpTestGenerator

        generator = CoverUpTestGenerator()
        agent_result = generator.safe_run({
            "targets": [t.model_dump() for t in targets[:body.max_tests]],
            "framework": body.framework,
            "language": body.language,
            "banking_context": body.banking_context,
        })

        if not agent_result.success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Test uretimi başarısız: {agent_result.error}",
            )

        raw_tests = agent_result.data.get("tests", [])
        generated: list[GeneratedTest] = []
        for rt in raw_tests:
            generated.append(GeneratedTest(
                target_file=rt.get("target_file", ""),
                target_function=rt.get("target_function"),
                test_file_path=rt.get("test_file_path", ""),
                test_code=rt.get("test_code", ""),
                test_framework=rt.get("test_framework", body.framework),
                estimated_coverage_gain=rt.get("estimated_coverage_gain", 0.0),
                lines_targeted=rt.get("lines_targeted", []),
            ))

        total_gain = agent_result.data.get("estimated_total_gain", 0.0)

        return GenerateTestResponse(
            tests=generated,
            total_generated=len(generated),
            estimated_total_gain=total_gain,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Test uretimi hatasi: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Test uretimi sırasında hata: {str(exc)[:200]}",
        )


@router.get("/reports", response_model=list[CoverageReportListItem])
def list_reports(
    db: DB,
    user: CurrentUser,
    project_id: str | None = Query(default=None),
) -> list[CoverageReportListItem]:
    """Tüm coverage raporlarini listele."""
    if project_id:
        _require_project_access(project_id, db, user)
        return _repository(db).list_reports(project_ids={project_id})
    return _repository(db).list_reports(project_ids=_accessible_project_ids(db, user))


@router.get("/reports/{report_id}", response_model=CoverageReport)
def get_report(
    report_id: str,
    db: DB,
    user: CurrentUser,
) -> CoverageReport:
    """Belirli bir coverage raporunu getir."""
    return get_report_or_404(
        _repository(db),
        report_id,
        allowed_project_ids=_accessible_project_ids(db, user),
    )


@router.get("/trends", response_model=TrendResponse)
def get_trends(
    db: DB,
    user: CurrentUser,
    project_id: str | None = Query(default=None),
) -> TrendResponse:
    """Coverage trendlerini getir."""
    repository = _repository(db)
    if project_id:
        project = _require_project_access(project_id, db, user)
        return build_trend_response(repository.list_trend_points(project_ids={project.id}))
    return build_trend_response(
        repository.list_trend_points(project_ids=_accessible_project_ids(db, user))
    )


@router.post("/targets", response_model=AnalyzeResponse)
def banking_targets(
    body: AnalyzeRequest,
    db: DB,
    user: CurrentUser,
) -> AnalyzeResponse:
    """Bankacilik-kritik kapsam hedeflerini belirle."""
    report = get_report_or_404(
        _repository(db),
        body.report_id,
        allowed_project_ids=_accessible_project_ids(db, user),
    )
    return analyze_report(report, body, banking_only=True)
