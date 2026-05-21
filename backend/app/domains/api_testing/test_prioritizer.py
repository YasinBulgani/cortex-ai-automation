"""
Test Prioritization Service
============================

Calculates composite priority scores (0-100) for test cases to optimise
test execution order.  Scores are based on five weighted signals:

    1. Failure History   (30 %)
    2. Risk Level        (25 %)
    3. Recency           (15 %)
    4. Data Sensitivity  (15 %)
    5. Change Impact     (15 %)

Public API
----------
- prioritize_tests(db, project_id, changed_paths, max_tests)
- get_prioritization_stats(db, project_id)
- suggest_optimal_suite(db, project_id, time_budget_ms, changed_paths)
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.domains.api_testing.models import (
    ApiEndpoint,
    ApiExecutionDetail,
    ApiTestCase,
)

logger = logging.getLogger(__name__)

# Weight constants
W_FAILURE = 0.30
W_RISK = 0.25
W_RECENCY = 0.15
W_SENSITIVITY = 0.15
W_CHANGE = 0.15

RISK_SCORES = {
    "critical": 1.0,
    "high": 0.75,
    "medium": 0.5,
    "low": 0.25,
}

DEFAULT_DURATION_MS = 1000.0
RECENCY_CAP_DAYS = 30


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _estimate_duration(db: Session, test_case_id: str) -> float:
    """Average total_ms from the last 5 execution details, fallback 1000 ms."""
    try:
        rows = (
            db.query(ApiExecutionDetail.total_ms)
            .filter(ApiExecutionDetail.test_case_id == test_case_id)
            .order_by(ApiExecutionDetail.executed_at.desc())
            .limit(5)
            .all()
        )
        if rows:
            vals = [r[0] for r in rows if r[0] is not None]
            if vals:
                return sum(vals) / len(vals)
    except Exception:
        pass
    return DEFAULT_DURATION_MS


def _path_matches(test_path: str, changed_paths: List[str]) -> bool:
    """Return True if the test's request_path matches any changed path prefix."""
    if not changed_paths:
        return False
    # Normalise: strip leading/trailing slashes for comparison
    test_base = test_path.strip("/").split("?")[0]
    for cp in changed_paths:
        cp_clean = cp.strip("/").split("?")[0]
        if not cp_clean:
            continue
        if test_base.startswith(cp_clean) or cp_clean.startswith(test_base):
            return True
    return False


# ---------------------------------------------------------------------------
# prioritize_tests
# ---------------------------------------------------------------------------

def prioritize_tests(
    db: Session,
    project_id: str,
    changed_paths: Optional[List[str]] = None,
    max_tests: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Calculate a composite priority score (0-100) for each non-quarantined
    test case in *project_id*.  Returns a list of dicts sorted by
    priority_score descending.
    """
    try:
        # Fetch non-quarantined tests with optional endpoint join
        rows = (
            db.query(ApiTestCase, ApiEndpoint)
            .outerjoin(ApiEndpoint, ApiTestCase.endpoint_id == ApiEndpoint.id)
            .filter(
                ApiTestCase.project_id == project_id,
                ApiTestCase.quarantined == False,  # noqa: E712
            )
            .all()
        )

        now = datetime.now(timezone.utc)
        results = []  # type: List[Dict[str, Any]]

        for tc, ep in rows:
            # 1. Failure history  (30 %)
            run_count = tc.run_count or 0
            fail_count = tc.fail_count or 0
            failure_score = fail_count / max(run_count, 1)

            # 2. Risk level  (25 %)
            risk_level = (ep.risk_level if ep and ep.risk_level else "medium").lower()
            risk_score = RISK_SCORES.get(risk_level, 0.5)

            # 3. Recency  (15 %)
            if tc.last_run_at is not None:
                last_run = tc.last_run_at
                if last_run.tzinfo is None:
                    last_run = last_run.replace(tzinfo=timezone.utc)
                delta = (now - last_run).total_seconds() / 86400.0
                recency_score = min(delta / RECENCY_CAP_DAYS, 1.0)
            else:
                recency_score = 1.0  # Never run -> highest recency priority

            # 4. Data sensitivity  (15 %)
            has_pii = bool(ep.has_pii) if ep else False
            has_financial = bool(ep.has_financial) if ep else False
            sensitivity_score = 0.5 * int(has_pii) + 0.5 * int(has_financial)

            # 5. Change impact  (15 %)
            impact_score = 0.0
            if changed_paths:
                impact_score = 1.0 if _path_matches(tc.request_path, changed_paths) else 0.0

            # Composite score  (0 - 100)
            raw = (
                W_FAILURE * failure_score
                + W_RISK * risk_score
                + W_RECENCY * recency_score
                + W_SENSITIVITY * sensitivity_score
                + W_CHANGE * impact_score
            )
            priority_score = round(raw * 100, 2)

            estimated_ms = _estimate_duration(db, tc.id)

            results.append({
                "test_case_id": tc.id,
                "title": tc.title,
                "test_type": tc.test_type,
                "priority_score": priority_score,
                "breakdown": {
                    "failure": round(failure_score * W_FAILURE * 100, 2),
                    "risk": round(risk_score * W_RISK * 100, 2),
                    "recency": round(recency_score * W_RECENCY * 100, 2),
                    "sensitivity": round(sensitivity_score * W_SENSITIVITY * 100, 2),
                    "change_impact": round(impact_score * W_CHANGE * 100, 2),
                },
                "endpoint_method": ep.method if ep else tc.request_method,
                "endpoint_path": ep.path if ep else tc.request_path,
                "risk_level": risk_level,
                "last_run_status": tc.last_run_status,
                "estimated_duration_ms": round(estimated_ms, 2),
            })

        # Sort by priority_score descending
        results.sort(key=lambda x: x["priority_score"], reverse=True)

        if max_tests is not None and max_tests > 0:
            results = results[:max_tests]

        return results

    except Exception:
        logger.exception("Error in prioritize_tests for project %s", project_id)
        return []


# ---------------------------------------------------------------------------
# get_prioritization_stats
# ---------------------------------------------------------------------------

def get_prioritization_stats(
    db: Session,
    project_id: str,
) -> Dict[str, Any]:
    """
    Return summary statistics about the prioritised test suite.
    """
    try:
        items = prioritize_tests(db, project_id)

        quarantined_count = (
            db.query(func.count(ApiTestCase.id))
            .filter(
                ApiTestCase.project_id == project_id,
                ApiTestCase.quarantined == True,  # noqa: E712
            )
            .scalar()
        ) or 0

        total = len(items)
        high = sum(1 for i in items if i["priority_score"] >= 70)
        medium = sum(1 for i in items if 40 <= i["priority_score"] < 70)
        low = sum(1 for i in items if i["priority_score"] < 40)
        avg_score = round(sum(i["priority_score"] for i in items) / max(total, 1), 2)

        risk_dist = {"critical": 0, "high": 0, "medium": 0, "low": 0}  # type: Dict[str, int]
        total_duration = 0.0
        for i in items:
            rl = i.get("risk_level", "medium").lower()
            if rl in risk_dist:
                risk_dist[rl] += 1
            else:
                risk_dist["medium"] += 1
            total_duration += i.get("estimated_duration_ms", DEFAULT_DURATION_MS)

        return {
            "total_tests": total,
            "quarantined_skipped": quarantined_count,
            "high_priority_count": high,
            "medium_priority_count": medium,
            "low_priority_count": low,
            "avg_score": avg_score,
            "risk_distribution": risk_dist,
            "estimated_total_duration_ms": round(total_duration, 2),
        }

    except Exception:
        logger.exception("Error in get_prioritization_stats for project %s", project_id)
        return {
            "total_tests": 0,
            "quarantined_skipped": 0,
            "high_priority_count": 0,
            "medium_priority_count": 0,
            "low_priority_count": 0,
            "avg_score": 0.0,
            "risk_distribution": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "estimated_total_duration_ms": 0.0,
        }


# ---------------------------------------------------------------------------
# suggest_optimal_suite
# ---------------------------------------------------------------------------

def suggest_optimal_suite(
    db: Session,
    project_id: str,
    time_budget_ms: Optional[float] = None,
    changed_paths: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Given an optional time budget in milliseconds, select the optimal subset
    of tests by priority score.

    Returns selected test IDs, total duration, and a coverage summary.
    """
    try:
        items = prioritize_tests(db, project_id, changed_paths=changed_paths)

        selected_ids = []  # type: List[str]
        total_duration = 0.0
        risk_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}  # type: Dict[str, int]
        type_counts = {}  # type: Dict[str, int]

        for item in items:
            est = item.get("estimated_duration_ms", DEFAULT_DURATION_MS)

            if time_budget_ms is not None:
                if total_duration + est > time_budget_ms:
                    continue  # skip this test — would exceed budget

            selected_ids.append(item["test_case_id"])
            total_duration += est

            rl = item.get("risk_level", "medium").lower()
            if rl in risk_counts:
                risk_counts[rl] += 1

            tt = item.get("test_type", "unknown")
            type_counts[tt] = type_counts.get(tt, 0) + 1

        return {
            "selected_test_ids": selected_ids,
            "selected_count": len(selected_ids),
            "total_duration_ms": round(total_duration, 2),
            "time_budget_ms": time_budget_ms,
            "coverage_summary": {
                "by_risk_level": risk_counts,
                "by_test_type": type_counts,
            },
        }

    except Exception:
        logger.exception("Error in suggest_optimal_suite for project %s", project_id)
        return {
            "selected_test_ids": [],
            "selected_count": 0,
            "total_duration_ms": 0.0,
            "time_budget_ms": time_budget_ms,
            "coverage_summary": {
                "by_risk_level": {"critical": 0, "high": 0, "medium": 0, "low": 0},
                "by_test_type": {},
            },
        }
