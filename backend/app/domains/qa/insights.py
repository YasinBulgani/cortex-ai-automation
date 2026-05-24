"""qa/ insights — velocity, trend, per-team breakdown.

`service.py`'nin üstüne agregasyon katmanı. Dashboard "Insights" sekmesi
ve haftalık raporlar için.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from pydantic import BaseModel

from . import service


class VelocityPoint(BaseModel):
    week_start: str
    tc_created: int
    tc_updated: int
    runs_executed: int


class TrendPoint(BaseModel):
    date: str
    total: int
    passed: int
    failed: int
    pass_rate: float


class OwnerStats(BaseModel):
    owner: str
    tc_count: int
    automation_pct: int
    suites: List[str]


class InsightsResponse(BaseModel):
    velocity: List[VelocityPoint]
    trend: List[TrendPoint]
    owners: List[OwnerStats]
    top_failing: List[dict]
    coverage_by_priority: Dict[str, int]
    generated_at: str


def velocity(weeks: int = 12) -> List[VelocityPoint]:
    """Son N hafta için TC create/update + run sayıları."""
    tcs_lite = service.list_test_cases()
    runs = service.list_runs()

    by_week_created: Dict[str, int] = defaultdict(int)
    by_week_updated: Dict[str, int] = defaultdict(int)
    by_week_runs: Dict[str, int] = defaultdict(int)

    for tc in tcs_lite:
        full = service.get_test_case(tc.id)
        if not full:
            continue
        # `created`/`updated` field'ları frontmatter'da string
        try:
            c = datetime.fromisoformat(str(full.created))
            wk = _week_start(c).isoformat()
            by_week_created[wk] += 1
        except (ValueError, TypeError):
            pass
        try:
            u = datetime.fromisoformat(str(full.updated))
            wk = _week_start(u).isoformat()
            by_week_updated[wk] += 1
        except (ValueError, TypeError):
            pass

    for run in runs:
        try:
            d = datetime.fromisoformat(run.started.replace("Z", "+00:00"))
            wk = _week_start(d).isoformat()
            by_week_runs[wk] += 1
        except (ValueError, TypeError):
            pass

    now = datetime.now(timezone.utc).date()
    points = []
    for i in range(weeks - 1, -1, -1):
        wk_date = now - timedelta(days=now.weekday() + 7 * i)
        wk = wk_date.isoformat()
        points.append(
            VelocityPoint(
                week_start=wk,
                tc_created=by_week_created.get(wk, 0),
                tc_updated=by_week_updated.get(wk, 0),
                runs_executed=by_week_runs.get(wk, 0),
            )
        )
    return points


def pass_rate_trend(days: int = 30) -> List[TrendPoint]:
    """Son N gün için günlük pass rate."""
    runs = service.list_runs()
    by_day: Dict[str, Dict[str, int]] = defaultdict(lambda: {"total": 0, "passed": 0, "failed": 0})

    for run in runs:
        try:
            d = datetime.fromisoformat(run.started.replace("Z", "+00:00")).date().isoformat()
        except (ValueError, TypeError):
            continue
        s = run.summary
        by_day[d]["total"] += s.total
        by_day[d]["passed"] += s.passed
        by_day[d]["failed"] += s.failed

    now = datetime.now(timezone.utc).date()
    points = []
    for i in range(days - 1, -1, -1):
        day = (now - timedelta(days=i)).isoformat()
        m = by_day.get(day, {"total": 0, "passed": 0, "failed": 0})
        pass_rate = (m["passed"] / m["total"]) if m["total"] else 0.0
        points.append(TrendPoint(date=day, **m, pass_rate=round(pass_rate * 100, 1)))
    return points


def owner_stats() -> List[OwnerStats]:
    """TC ownership dağılımı."""
    tcs = service.list_test_cases()
    by_owner: Dict[str, Dict] = defaultdict(lambda: {"count": 0, "automated": 0, "suites": set()})
    for t in tcs:
        b = by_owner[t.owner]
        b["count"] += 1
        if t.automation_status == "automated":
            b["automated"] += 1
        b["suites"].add(t.suite)

    out = []
    for owner, b in sorted(by_owner.items(), key=lambda kv: -kv[1]["count"]):
        pct = int(round((b["automated"] / b["count"]) * 100)) if b["count"] else 0
        out.append(
            OwnerStats(
                owner=owner,
                tc_count=b["count"],
                automation_pct=pct,
                suites=sorted(b["suites"]),
            )
        )
    return out


def top_failing(limit: int = 10) -> List[dict]:
    """En çok fail olan TC'ler."""
    runs = service.list_runs()
    fail_counts: Dict[str, Dict] = defaultdict(lambda: {"fails": 0, "runs": 0, "last_run": None, "last_status": None})

    for run_lite in sorted(runs, key=lambda r: r.started):
        run = service.get_run(run_lite.id)
        if not run:
            continue
        for res in run.results:
            entry = fail_counts[res.tc]
            entry["runs"] += 1
            entry["last_run"] = run.id
            entry["last_status"] = res.status
            if res.status == "fail":
                entry["fails"] += 1

    ranked = []
    for tc_id, m in fail_counts.items():
        if m["fails"] == 0:
            continue
        ranked.append(
            {
                "tc": tc_id,
                "fail_count": m["fails"],
                "run_count": m["runs"],
                "fail_rate": round(m["fails"] / m["runs"] * 100, 1) if m["runs"] else 0,
                "last_run": m["last_run"],
                "last_status": m["last_status"],
            }
        )
    return sorted(ranked, key=lambda x: (-x["fail_count"], -x["fail_rate"]))[:limit]


def insights_response() -> InsightsResponse:
    tcs = service.list_test_cases()
    by_prio = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
    for t in tcs:
        by_prio[t.priority] = by_prio.get(t.priority, 0) + 1

    return InsightsResponse(
        velocity=velocity(12),
        trend=pass_rate_trend(30),
        owners=owner_stats(),
        top_failing=top_failing(10),
        coverage_by_priority=by_prio,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


def _week_start(d: datetime):
    """Pazartesi günü olarak hafta başını döndür."""
    return (d - timedelta(days=d.weekday())).date()
