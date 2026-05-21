"""
Flaky Test Detection & Quarantine Service
==========================================

Identifies unreliable tests by analysing pass/fail history, calculates a
flaky score (0-1), and provides quarantine management.

Flaky score formula:
    score = 1 - abs(pass_rate - 0.5) * 2

A test that passes exactly 50 % of the time scores 1.0 (maximally flaky).
A test that always passes or always fails scores 0.0 (stable/broken).

An additional "alternation bonus" is applied: the more a test alternates
between pass and fail in consecutive runs, the higher the flaky signal.

Recommendation thresholds:
    score > 0.6  -> "quarantine"
    score > 0.3  -> "investigate"
    otherwise    -> "stable"
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import case, cast, Date, func
from sqlalchemy.orm import Session

from app.domains.api_testing.models import ApiExecutionDetail, ApiTestCase

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# detect_flaky_tests
# ---------------------------------------------------------------------------

def detect_flaky_tests(
    db: Session,
    project_id: str,
    window_days: int = 30,
    min_runs: int = 3,
) -> List[Dict[str, Any]]:
    """
    Detect flaky tests within a project.

    Returns a list of test dicts sorted by flaky_score descending.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)

    # 1. Fetch test cases with enough runs
    test_cases = (
        db.query(ApiTestCase)
        .filter(
            ApiTestCase.project_id == project_id,
            ApiTestCase.run_count >= min_runs,
        )
        .all()
    )

    results: List[Dict[str, Any]] = []

    for tc in test_cases:
        run_count = tc.run_count or 0
        pass_count = tc.pass_count or 0
        fail_count = tc.fail_count or 0

        if run_count == 0:
            continue

        pass_rate = pass_count / run_count
        fail_rate = fail_count / run_count

        # Base flaky score: 1 - abs(pass_rate - 0.5) * 2
        flaky_score = 1.0 - abs(pass_rate - 0.5) * 2.0

        # 2. Check alternation in recent executions
        recent_executions = (
            db.query(ApiExecutionDetail.passed)
            .filter(
                ApiExecutionDetail.test_case_id == tc.id,
                ApiExecutionDetail.executed_at >= cutoff,
            )
            .order_by(ApiExecutionDetail.executed_at.asc())
            .all()
        )

        alternation_count = 0
        if len(recent_executions) > 1:
            for i in range(1, len(recent_executions)):
                if recent_executions[i].passed != recent_executions[i - 1].passed:
                    alternation_count += 1

        # Alternation bonus: normalised by number of transitions possible
        if len(recent_executions) > 1:
            max_alternations = len(recent_executions) - 1
            alternation_ratio = alternation_count / max_alternations
            # Blend: 70 % base score + 30 % alternation signal
            flaky_score = 0.7 * flaky_score + 0.3 * alternation_ratio

        # Clamp to [0, 1]
        flaky_score = max(0.0, min(1.0, flaky_score))

        # 3. Average duration
        avg_duration_row = (
            db.query(func.avg(ApiExecutionDetail.total_ms))
            .filter(
                ApiExecutionDetail.test_case_id == tc.id,
                ApiExecutionDetail.executed_at >= cutoff,
            )
            .scalar()
        )
        avg_duration_ms = round(float(avg_duration_row or 0.0), 2)

        # 4. Recommendation
        if flaky_score > 0.6:
            recommendation = "quarantine"
        elif flaky_score > 0.3:
            recommendation = "investigate"
        else:
            recommendation = "stable"

        results.append({
            "test_case_id": tc.id,
            "title": tc.title,
            "test_type": tc.test_type,
            "flaky_score": round(flaky_score, 4),
            "run_count": run_count,
            "pass_rate": round(pass_rate, 4),
            "fail_rate": round(fail_rate, 4),
            "alternation_count": alternation_count,
            "last_status": tc.last_run_status or "unknown",
            "avg_duration_ms": avg_duration_ms,
            "recommendation": recommendation,
        })

    # Sort by flaky_score descending
    results.sort(key=lambda x: x["flaky_score"], reverse=True)
    return results


# ---------------------------------------------------------------------------
# get_flaky_trends
# ---------------------------------------------------------------------------

def get_flaky_trends(
    db: Session,
    project_id: str,
    days: int = 30,
) -> List[Dict[str, Any]]:
    """
    Return daily aggregated flaky / quarantine counts over time.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Total test count per day (tests that had executions)
    daily_rows = (
        db.query(
            cast(ApiExecutionDetail.executed_at, Date).label("day"),
            func.count(ApiExecutionDetail.test_case_id.distinct()).label("total_tests"),
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

    # Pre-calculate current quarantined count (quarantine state is point-in-time)
    quarantined_count = (
        db.query(func.count(ApiTestCase.id))
        .filter(
            ApiTestCase.project_id == project_id,
            ApiTestCase.quarantined == True,  # noqa: E712
        )
        .scalar()
    ) or 0

    # For each day, determine how many distinct tests had mixed results that day
    # A test is "flaky on day X" if it had both pass and fail executions that day
    flaky_per_day_rows = (
        db.query(
            cast(ApiExecutionDetail.executed_at, Date).label("day"),
            ApiExecutionDetail.test_case_id,
            func.sum(case((ApiExecutionDetail.passed == True, 1), else_=0)).label("pass_cnt"),   # noqa: E712
            func.sum(case((ApiExecutionDetail.passed == False, 1), else_=0)).label("fail_cnt"),  # noqa: E712
        )
        .join(ApiTestCase, ApiExecutionDetail.test_case_id == ApiTestCase.id, isouter=True)
        .filter(
            ApiTestCase.project_id == project_id,
            ApiExecutionDetail.executed_at >= cutoff,
        )
        .group_by(
            cast(ApiExecutionDetail.executed_at, Date),
            ApiExecutionDetail.test_case_id,
        )
        .all()
    )

    # Build a day -> flaky_count mapping
    flaky_by_day: Dict[str, int] = {}
    for row in flaky_per_day_rows:
        day_str = str(row.day)
        p = row.pass_cnt or 0
        f = row.fail_cnt or 0
        if p > 0 and f > 0:
            flaky_by_day[day_str] = flaky_by_day.get(day_str, 0) + 1

    results: List[Dict[str, Any]] = []
    for row in daily_rows:
        day_str = str(row.day)
        results.append({
            "date": day_str,
            "total_tests": row.total_tests or 0,
            "flaky_count": flaky_by_day.get(day_str, 0),
            "quarantined_count": quarantined_count,
        })

    return results


# ---------------------------------------------------------------------------
# quarantine_test
# ---------------------------------------------------------------------------

def quarantine_test(
    db: Session,
    test_case_id: str,
    reason: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Mark a test case as quarantined.

    Returns the updated test case summary dict.
    """
    tc = db.query(ApiTestCase).filter(ApiTestCase.id == test_case_id).first()
    if tc is None:
        raise ValueError(f"Test case not found: {test_case_id}")

    tc.quarantined = True
    tc.quarantine_reason = reason
    db.commit()
    db.refresh(tc)

    return {
        "test_case_id": tc.id,
        "title": tc.title,
        "quarantined": tc.quarantined,
        "quarantine_reason": tc.quarantine_reason,
    }


# ---------------------------------------------------------------------------
# unquarantine_test  (bonus utility)
# ---------------------------------------------------------------------------

def unquarantine_test(
    db: Session,
    test_case_id: str,
) -> Dict[str, Any]:
    """
    Remove quarantine flag from a test case.
    """
    tc = db.query(ApiTestCase).filter(ApiTestCase.id == test_case_id).first()
    if tc is None:
        raise ValueError(f"Test case not found: {test_case_id}")

    tc.quarantined = False
    tc.quarantine_reason = None
    db.commit()
    db.refresh(tc)

    return {
        "test_case_id": tc.id,
        "title": tc.title,
        "quarantined": tc.quarantined,
        "quarantine_reason": tc.quarantine_reason,
    }


# ---------------------------------------------------------------------------
# get_quarantine_list
# ---------------------------------------------------------------------------

def get_quarantine_list(
    db: Session,
    project_id: str,
) -> List[Dict[str, Any]]:
    """
    Return all quarantined tests for a project.
    """
    quarantined = (
        db.query(ApiTestCase)
        .filter(
            ApiTestCase.project_id == project_id,
            ApiTestCase.quarantined == True,  # noqa: E712
        )
        .order_by(ApiTestCase.updated_at.desc())
        .all()
    )

    results: List[Dict[str, Any]] = []
    for tc in quarantined:
        run_count = tc.run_count or 0
        pass_rate = (tc.pass_count or 0) / max(run_count, 1)

        results.append({
            "test_case_id": tc.id,
            "title": tc.title,
            "test_type": tc.test_type,
            "quarantine_reason": tc.quarantine_reason,
            "run_count": run_count,
            "pass_rate": round(pass_rate, 4),
            "last_status": tc.last_run_status or "unknown",
            "quarantined_at": tc.updated_at.isoformat() if tc.updated_at else None,
        })

    return results
