"""Query-heavy read models for API Testing router endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.domains.api_testing.models import (
    ApiExecutionDetail,
    ApiSpec,
    ApiTestCase,
)
from app.domains.api_testing.schemas import (
    ExecutionDetailItem,
    ExecutionHistoryItem,
    ExecutionHistoryResponse,
    ExecutionRunDetailResponse,
    TestTypeTrendItem,
    TrendDayData,
    TrendResponse,
)


def build_api_testing_stats(db: Session, project_id: str) -> dict:
    from sqlalchemy import func
    from app.domains.api_testing.models import ApiChain, ApiEndpoint, ApiEnvironment

    spec_count = db.query(ApiSpec).filter(ApiSpec.project_id == project_id).count()
    endpoint_count = db.query(ApiEndpoint).join(ApiSpec).filter(
        ApiSpec.project_id == project_id,
    ).count()
    test_case_count = db.query(ApiTestCase).filter(
        ApiTestCase.project_id == project_id,
    ).count()
    ai_generated_count = db.query(ApiTestCase).filter(
        ApiTestCase.project_id == project_id,
        ApiTestCase.ai_generated == True,  # noqa: E712
    ).count()
    chain_count = db.query(ApiChain).filter(
        ApiChain.project_id == project_id,
    ).count()
    env_count = db.query(ApiEnvironment).filter(
        ApiEnvironment.project_id == project_id,
    ).count()

    type_dist = db.query(
        ApiTestCase.test_type, func.count(ApiTestCase.id),
    ).filter(
        ApiTestCase.project_id == project_id,
    ).group_by(ApiTestCase.test_type).all()

    review_dist = db.query(
        ApiTestCase.review_status, func.count(ApiTestCase.id),
    ).filter(
        ApiTestCase.project_id == project_id,
    ).group_by(ApiTestCase.review_status).all()

    pass_count = db.query(ApiTestCase).filter(
        ApiTestCase.project_id == project_id,
        ApiTestCase.last_run_status == "passed",
    ).count()
    fail_count = db.query(ApiTestCase).filter(
        ApiTestCase.project_id == project_id,
        ApiTestCase.last_run_status == "failed",
    ).count()

    return {
        "specs": spec_count,
        "endpoints": endpoint_count,
        "test_cases": test_case_count,
        "ai_generated": ai_generated_count,
        "chains": chain_count,
        "environments": env_count,
        "test_type_distribution": {t: c for t, c in type_dist},
        "review_status_distribution": {s: c for s, c in review_dist},
        "last_run": {
            "passed": pass_count,
            "failed": fail_count,
            "pass_rate": round(pass_count / max(pass_count + fail_count, 1) * 100, 1),
        },
    }


def build_execution_history(
    db: Session,
    project_id: str,
    *,
    page: int,
    per_page: int,
    test_type: Optional[str],
    status: Optional[str],
) -> ExecutionHistoryResponse:
    from sqlalchemy import Date, case, cast, func

    q = (
        db.query(
            ApiExecutionDetail.run_id,
            func.min(ApiExecutionDetail.executed_at).label("timestamp"),
            func.count(ApiExecutionDetail.id).label("total"),
            func.sum(case((ApiExecutionDetail.passed == True, 1), else_=0)).label("passed_count"),  # noqa: E712
            func.sum(case((ApiExecutionDetail.passed == False, 1), else_=0)).label("failed_count"),  # noqa: E712
            func.sum(ApiExecutionDetail.total_ms).label("duration_ms"),
            func.avg(ApiExecutionDetail.total_ms).label("avg_ms"),
        )
        .join(ApiTestCase, ApiExecutionDetail.test_case_id == ApiTestCase.id, isouter=True)
        .filter(ApiTestCase.project_id == project_id)
    )

    if test_type:
        q = q.filter(ApiTestCase.test_type == test_type)

    q = q.group_by(ApiExecutionDetail.run_id)

    if status == "passed":
        q = q.having(func.sum(case((ApiExecutionDetail.passed == False, 1), else_=0)) == 0)  # noqa: E712
    elif status == "failed":
        q = q.having(func.sum(case((ApiExecutionDetail.passed == True, 1), else_=0)) == 0)  # noqa: E712
    elif status == "mixed":
        q = q.having(
            func.sum(case((ApiExecutionDetail.passed == True, 1), else_=0)) > 0,  # noqa: E712
            func.sum(case((ApiExecutionDetail.passed == False, 1), else_=0)) > 0,  # noqa: E712
        )

    count_subq = q.subquery()
    total_count = db.query(func.count()).select_from(count_subq).scalar() or 0

    rows = q.order_by(func.min(ApiExecutionDetail.executed_at).desc()).offset(
        (page - 1) * per_page
    ).limit(per_page).all()

    items: list[ExecutionHistoryItem] = []
    for row in rows:
        total = row.total or 0
        passed = row.passed_count or 0
        failed = row.failed_count or 0
        pass_rate = round(passed / max(total, 1) * 100, 1)

        if failed == 0 and total > 0:
            run_status = "passed"
        elif passed == 0 and total > 0:
            run_status = "failed"
        else:
            run_status = "mixed"

        test_types = db.query(ApiTestCase.test_type).join(
            ApiExecutionDetail, ApiExecutionDetail.test_case_id == ApiTestCase.id,
        ).filter(
            ApiExecutionDetail.run_id == row.run_id,
        ).distinct().all()

        items.append(ExecutionHistoryItem(
            run_id=row.run_id,
            timestamp=row.timestamp,
            total=total,
            passed=passed,
            failed=failed,
            duration_ms=round(row.duration_ms or 0, 2),
            pass_rate=pass_rate,
            status=run_status,
            test_types=[t[0] for t in test_types if t[0]],
        ))

    return ExecutionHistoryResponse(
        items=items,
        total_count=total_count,
        page=page,
        per_page=per_page,
    )


def build_execution_run_detail(
    db: Session,
    project_id: str,
    run_id: str,
) -> ExecutionRunDetailResponse:
    details = (
        db.query(ApiExecutionDetail)
        .join(ApiTestCase, ApiExecutionDetail.test_case_id == ApiTestCase.id, isouter=True)
        .filter(
            ApiExecutionDetail.run_id == run_id,
            ApiTestCase.project_id == project_id,
        )
        .order_by(ApiExecutionDetail.execution_order)
        .all()
    )

    if not details:
        raise ValueError("Run bulunamadi")

    total = len(details)
    passed = sum(1 for d in details if d.passed)
    failed = total - passed
    duration_ms = sum(d.total_ms for d in details)
    pass_rate = round(passed / max(total, 1) * 100, 1)

    if failed == 0:
        run_status = "passed"
    elif passed == 0:
        run_status = "failed"
    else:
        run_status = "mixed"

    detail_items: list[ExecutionDetailItem] = []
    for detail in details:
        tc_title = None
        if detail.test_case_id:
            tc = db.query(ApiTestCase.title).filter(ApiTestCase.id == detail.test_case_id).first()
            if tc:
                tc_title = tc[0]

        detail_items.append(ExecutionDetailItem(
            id=detail.id,
            test_case_id=detail.test_case_id,
            test_case_title=tc_title,
            actual_method=detail.actual_method,
            actual_url=detail.actual_url,
            status_code=detail.status_code,
            total_ms=round(detail.total_ms, 2),
            passed=detail.passed,
            error_message=detail.error_message,
            assertion_results=detail.assertion_results or [],
            schema_valid=detail.schema_valid,
            executed_at=detail.executed_at,
        ))

    return ExecutionRunDetailResponse(
        run_id=run_id,
        timestamp=details[0].executed_at if details else None,
        total=total,
        passed=passed,
        failed=failed,
        duration_ms=round(duration_ms, 2),
        pass_rate=pass_rate,
        status=run_status,
        details=detail_items,
    )


def build_execution_trends(
    db: Session,
    project_id: str,
    *,
    days: int,
) -> TrendResponse:
    from sqlalchemy import Date, case, cast, func

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    daily_q = (
        db.query(
            cast(ApiExecutionDetail.executed_at, Date).label("day"),
            func.count(ApiExecutionDetail.id).label("total"),
            func.sum(case((ApiExecutionDetail.passed == True, 1), else_=0)).label("passed"),  # noqa: E712
            func.sum(case((ApiExecutionDetail.passed == False, 1), else_=0)).label("failed"),  # noqa: E712
            func.avg(ApiExecutionDetail.total_ms).label("avg_ms"),
            func.count(ApiExecutionDetail.run_id.distinct()).label("run_count"),
        )
        .join(ApiTestCase, ApiExecutionDetail.test_case_id == ApiTestCase.id, isouter=True)
        .filter(
            ApiTestCase.project_id == project_id,
            ApiExecutionDetail.executed_at >= cutoff,
        )
        .group_by(cast(ApiExecutionDetail.executed_at, Date))
        .order_by(cast(ApiExecutionDetail.executed_at, Date))
        .all()
    )

    day_data: list[TrendDayData] = []
    total_runs = 0
    total_pass_rates: list[float] = []
    total_avg_ms_list: list[float] = []

    for row in daily_q:
        total = row.total or 0
        passed = row.passed or 0
        failed = row.failed or 0
        pass_rate = round(passed / max(total, 1) * 100, 1)
        avg_ms = round(row.avg_ms or 0, 2)
        run_count = row.run_count or 0

        total_runs += run_count
        if total > 0:
            total_pass_rates.append(pass_rate)
        if avg_ms > 0:
            total_avg_ms_list.append(avg_ms)

        day_data.append(TrendDayData(
            date=str(row.day),
            total=total,
            passed=passed,
            failed=failed,
            pass_rate=pass_rate,
            avg_response_ms=avg_ms,
            run_count=run_count,
        ))

    type_dist_q = (
        db.query(
            ApiTestCase.test_type,
            func.count(ApiExecutionDetail.id).label("count"),
            func.sum(case((ApiExecutionDetail.passed == True, 1), else_=0)).label("passed"),  # noqa: E712
            func.sum(case((ApiExecutionDetail.passed == False, 1), else_=0)).label("failed"),  # noqa: E712
        )
        .join(ApiTestCase, ApiExecutionDetail.test_case_id == ApiTestCase.id)
        .filter(
            ApiTestCase.project_id == project_id,
            ApiExecutionDetail.executed_at >= cutoff,
        )
        .group_by(ApiTestCase.test_type)
        .all()
    )

    type_items: list[TestTypeTrendItem] = []
    most_failed_type = None
    max_failed = 0
    for row in type_dist_q:
        failed_count = row.failed or 0
        type_items.append(TestTypeTrendItem(
            test_type=row.test_type or "unknown",
            count=row.count or 0,
            passed=row.passed or 0,
            failed=failed_count,
        ))
        if failed_count > max_failed:
            max_failed = failed_count
            most_failed_type = row.test_type

    avg_pass_rate = round(sum(total_pass_rates) / max(len(total_pass_rates), 1), 1)
    avg_response_ms = round(sum(total_avg_ms_list) / max(len(total_avg_ms_list), 1), 2)

    return TrendResponse(
        days=day_data,
        total_runs=total_runs,
        avg_pass_rate=avg_pass_rate,
        avg_response_ms=avg_response_ms,
        most_failed_test_type=most_failed_type,
        test_type_distribution=type_items,
    )
