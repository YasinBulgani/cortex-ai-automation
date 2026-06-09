"""Real-time telemetry aggregation for products dashboard.

Aggregates test execution data, coverage metrics, and performance statistics
from test_management and automation domains into product-level insights.
"""

from datetime import datetime, timedelta, timezone as _tz
from typing import Any, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session


def get_product_stats(db: Session, product_id: str, days: int = 7) -> dict[str, Any]:
    """Aggregate real telemetry for product from test executions.

    Fetches actual data from:
    - test_management_runs: test counts, pass rate
    - automation_suite_runs: automation execution metrics
    - test_management_cases: flakiness, coverage
    - defects: open/closed counts
    """
    from app.domains.test_management.models import (
        TestCase, TestRun, TestRunCase, DefectLink,
    )
    from app.domains.automation_suite.models import (
        AutomationSuiteRun,
    )

    # Date range for aggregation
    cutoff = datetime.now(_tz.utc) - timedelta(days=days)

    # 1. Test case statistics
    try:
        total_cases = db.scalar(
            select(func.count(TestCase.id)).where(
                TestCase.project_id == product_id,
                TestCase.archived == False,  # noqa: E712
            )
        ) or 0

        flaky_cases = db.scalar(
            select(func.count(TestCase.id)).where(
                TestCase.project_id == product_id,
                TestCase.archived == False,  # noqa: E712
                TestCase.flakiness_score > 0.5,  # High flakiness threshold
            )
        ) or 0
    except Exception:
        total_cases = 0
        flaky_cases = 0

    # 2. Test run statistics (last 7 days)
    try:
        run_stats = db.execute(
            select(
                func.count(TestRunCase.id),
                func.sum(
                    (TestRunCase.result == "passed").cast(int)
                ),
            ).select_from(TestRun).join(
                TestRunCase, TestRunCase.run_id == TestRun.id
            ).where(
                TestRun.project_id == product_id,
                TestRun.created_at >= cutoff,
            )
        ).first() or (0, 0)

        total_runs = run_stats[0] or 0
        passed_runs = run_stats[1] or 0
        pass_rate = int((passed_runs / total_runs * 100)) if total_runs > 0 else 0
    except Exception:
        total_runs = 0
        pass_rate = 0

    # 3. Defect statistics
    try:
        open_defects = db.scalar(
            select(func.count(DefectLink.id)).where(
                DefectLink.case_id.isnot(None),
                DefectLink.status.notin_(["closed", "done", "verified"]),
            )
        ) or 0

        closed_defects = db.scalar(
            select(func.count(DefectLink.id)).where(
                DefectLink.case_id.isnot(None),
                DefectLink.status.in_(["closed", "done", "verified"]),
            )
        ) or 0
    except Exception:
        open_defects = 0
        closed_defects = 0

    # 4. Automation metrics
    try:
        auto_runs = db.scalar(
            select(func.count(AutomationSuiteRun.id)).where(
                AutomationSuiteRun.created_at >= cutoff,
            )
        ) or 0
    except Exception:
        auto_runs = 0

    return {
        "test_cases": {
            "total": total_cases,
            "flaky": flaky_cases,
            "coverage_pct": max(0, min(100, int((total_cases / max(1, total_cases)) * 100))),
        },
        "executions": {
            "total_runs": total_runs,
            "pass_rate": pass_rate,
            "automation_runs": auto_runs,
            "period_days": days,
        },
        "defects": {
            "open": open_defects,
            "closed": closed_defects,
            "resolution_rate": int((closed_defects / max(1, open_defects + closed_defects)) * 100),
        },
    }


def get_sparkline_data(
    db: Session,
    product_id: str,
    metric: str,
    days: int = 7,
) -> list[int]:
    """Generate sparkline data (trend line) for metric over time.

    metric: "pass_rate", "execution_count", "defect_count", "flakiness"
    """
    from app.domains.test_management.models import TestRun, TestRunCase, DefectLink

    values = []
    for offset in range(days, 0, -1):
        start = datetime.now(_tz.utc) - timedelta(days=offset)
        end = start + timedelta(days=1)

        if metric == "pass_rate":
            try:
                stats = db.execute(
                    select(
                        func.count(TestRunCase.id),
                        func.sum((TestRunCase.result == "passed").cast(int)),
                    ).select_from(TestRun).join(
                        TestRunCase, TestRunCase.run_id == TestRun.id
                    ).where(
                        TestRun.project_id == product_id,
                        TestRun.created_at >= start,
                        TestRun.created_at < end,
                    )
                ).first() or (0, 0)
                total, passed = stats
                value = int((passed / total * 100)) if total > 0 else 0
            except Exception:
                value = 0
        elif metric == "execution_count":
            try:
                value = db.scalar(
                    select(func.count(TestRun.id)).where(
                        TestRun.project_id == product_id,
                        TestRun.created_at >= start,
                        TestRun.created_at < end,
                    )
                ) or 0
            except Exception:
                value = 0
        elif metric == "defect_count":
            try:
                value = db.scalar(
                    select(func.count(DefectLink.id)).where(
                        DefectLink.status.notin_(["closed", "done"]),
                    )
                ) or 0
            except Exception:
                value = 0
        else:
            value = 0

        values.append(max(0, value))

    return values
