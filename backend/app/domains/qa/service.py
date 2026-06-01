"""qa/ filesystem reader/writer service layer.

Repo'daki qa/ klasörünü doğrudan okur. Cache kullanmaz (her istekte tarar);
77 TC için yeterince hızlı (<100ms). Cache ileride trace.csv'den okuma ile
eklenecek.
"""
from __future__ import annotations

import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from .models import (
    CoverageMatrixRow,
    CoverageResponse,
    CreateTestCaseRequest,
    HealthReport,
    Plan,
    PreCondition,
    Requirement,
    TestCase,
    TestCaseListItem,
    TestRun,
    TestRunListItem,
)


# Repo kökünü bul: backend/app/domains/qa/service.py'den 5 yukarı çık
_HERE = Path(__file__).resolve()
REPO_ROOT = _HERE.parents[4]
QA_ROOT = REPO_ROOT / "qa"


def _load_yaml(path: Path) -> dict:
    """js-yaml JSON_SCHEMA ile uyumlu yükleme (date'leri string olarak tut).

    PyYAML safe_load default'unda `2026-05-22` → `datetime.date` object'i
    döner. Pydantic `str` field'larında bu validation fail eder. Tüm
    date/datetime değerlerini ISO string'e çevirip döndürüyoruz.
    """
    from datetime import date, datetime as _dt
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text) or {}
    return _stringify_dates(data)


def _stringify_dates(obj):
    """Date / datetime / time object'lerini ISO string'e dönüştür (recursive)."""
    from datetime import date, datetime as _dt, time
    if isinstance(obj, dict):
        return {k: _stringify_dates(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_stringify_dates(v) for v in obj]
    if isinstance(obj, (_dt, date, time)):
        return obj.isoformat()
    return obj


def _parse_frontmatter(text: str) -> Tuple[Dict[str, Any], str]:
    """Markdown dosyasından frontmatter ve body'i ayır."""
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    fm_text = text[4:end]
    body = text[end + 5 :]
    try:
        fm = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError:
        fm = {}
    # Date object'leri string'e çevir
    for k, v in list(fm.items()):
        if isinstance(v, (datetime,)):
            fm[k] = v.isoformat()
        elif hasattr(v, "isoformat") and not isinstance(v, str):
            fm[k] = v.isoformat()
    return fm, body


def _serialize_frontmatter(fm: Dict[str, Any]) -> str:
    """Dict → YAML frontmatter (deterministic key order)."""
    # Sıralama: id, title, suite, priority, type, status, owner, ...
    canonical_order = [
        "id", "title", "suite", "priority", "type", "status", "owner",
        "created", "updated", "estimated_minutes", "automation",
        "requirements", "pre_conditions", "tags", "configurations", "open_defects",
    ]
    ordered = {}
    for key in canonical_order:
        if key in fm:
            ordered[key] = fm[key]
    for key in fm:
        if key not in ordered:
            ordered[key] = fm[key]
    yaml_text = yaml.safe_dump(ordered, allow_unicode=True, sort_keys=False, default_flow_style=False)
    return f"---\n{yaml_text}---\n"


def list_test_cases(
    suite: Optional[str] = None,
    priority: Optional[str] = None,
    automation_status: Optional[str] = None,
    search: Optional[str] = None,
) -> List[TestCaseListItem]:
    cases_dir = QA_ROOT / "cases"
    if not cases_dir.exists():
        return []

    # Run history'den last_status build et
    last_by_tc = _build_last_status_map()

    items: List[TestCaseListItem] = []
    for tc_file in sorted(cases_dir.rglob("TC-*.md")):
        try:
            text = tc_file.read_text(encoding="utf-8")
            fm, _body = _parse_frontmatter(text)
            if not fm:
                continue

            if suite and fm.get("suite") != suite:
                continue
            if priority and fm.get("priority") != priority:
                continue
            auto = (fm.get("automation") or {}).get("status")
            if automation_status and auto != automation_status:
                continue
            if search:
                hay = f"{fm.get('id','')} {fm.get('title','')} {fm.get('suite','')}".lower()
                if search.lower() not in hay:
                    continue

            last = last_by_tc.get(fm.get("id", ""))
            items.append(
                TestCaseListItem(
                    id=fm.get("id", ""),
                    title=fm.get("title", ""),
                    suite=fm.get("suite", ""),
                    priority=fm.get("priority", "P2"),
                    type=fm.get("type", ["functional"]),
                    status=fm.get("status", "draft"),
                    automation_status=auto or "not-automated",
                    owner=fm.get("owner", "@unassigned"),
                    last_run=last[0] if last else None,
                    last_status=last[1] if last else None,
                    open_defects_count=len(fm.get("open_defects", []) or []),
                )
            )
        except Exception:
            continue

    return items


def get_test_case(tc_id: str) -> Optional[TestCase]:
    cases_dir = QA_ROOT / "cases"
    if not cases_dir.exists():
        return None
    for tc_file in cases_dir.rglob("TC-*.md"):
        try:
            text = tc_file.read_text(encoding="utf-8")
            fm, body = _parse_frontmatter(text)
            if fm.get("id") == tc_id:
                fm["body"] = body
                # automation field auto-fill
                if "automation" not in fm:
                    fm["automation"] = {"status": "not-automated"}
                return TestCase(**fm)
        except Exception:
            continue
    return None


def create_test_case(req: CreateTestCaseRequest) -> TestCase:
    """new-tc.mjs equivalent — yeni TC dosyası yarat."""
    suite_to_domain = {
        "auth": "AUTH", "projects": "PRJ", "scenarios": "SCN", "executions": "EXC",
        "approvals": "APR", "rbac": "RBAC", "flows": "FLW", "integrations": "INT",
        "api-tests": "API", "reports": "RPT", "admin": "ADM", "billing": "BIL",
        "notifications": "NTF", "schedules": "SCH", "imports": "IMP", "regression": "REG",
        "requirements": "REQ", "members": "MEM", "dashboard": "DASH", "bdd": "BDD",
        "ai": "AI", "mobile": "MOB", "a11y": "A11Y", "performance": "PERF",
        "security": "SEC", "synthetic-data": "SYN", "engine": "ENG",
        "visual-regression": "VIS", "recorder": "REC", "datasim": "DSM",
        "infrastructure": "INF", "qa-engine": "QA", "runs": "RUN",
    }
    domain = suite_to_domain.get(req.suite)
    if not domain:
        raise ValueError(f"Unknown suite: {req.suite}")

    suite_dir = QA_ROOT / "cases" / req.suite
    suite_dir.mkdir(parents=True, exist_ok=True)

    existing_ids = []
    for f in suite_dir.glob("TC-*.md"):
        m = re.match(rf"TC-{domain}-(\d+)", f.name)
        if m:
            existing_ids.append(int(m.group(1)))
    seq = (max(existing_ids) + 1) if existing_ids else 1
    tc_id = f"TC-{domain}-{seq:03d}"

    slug = _slugify(req.title)
    file_path = suite_dir / f"{tc_id}-{slug}.md"

    today = datetime.now(timezone.utc).date().isoformat()
    fm = {
        "id": tc_id,
        "title": req.title,
        "suite": req.suite,
        "priority": req.priority,
        "type": list(req.type),
        "status": "draft",
        "owner": req.owner,
        "created": today,
        "updated": today,
        "estimated_minutes": req.estimated_minutes,
        "automation": {"status": "not-automated"},
        "requirements": [],
        "pre_conditions": [],
        "tags": [],
    }

    body = req.body or (
        f"\n# {tc_id} — {req.title}\n\n"
        "## Önkoşul\n*(Doldurulacak)*\n\n"
        "## Adımlar\n\n| # | Adım | Beklenen Sonuç |\n|---|------|----------------|\n"
        "| 1 | *(adımı yaz)* | *(beklenen sonuç)* |\n"
    )

    file_path.write_text(_serialize_frontmatter(fm) + body, encoding="utf-8")
    return TestCase(**fm, body=body)


def update_test_case(tc_id: str, updates: Dict[str, Any]) -> Optional[TestCase]:
    cases_dir = QA_ROOT / "cases"
    for tc_file in cases_dir.rglob("TC-*.md"):
        text = tc_file.read_text(encoding="utf-8")
        fm, body = _parse_frontmatter(text)
        if fm.get("id") != tc_id:
            continue
        # Body ayrı update edilir
        new_body = updates.pop("body", None)
        for k, v in updates.items():
            if v is not None:
                fm[k] = v
        fm["updated"] = datetime.now(timezone.utc).date().isoformat()
        if new_body is not None:
            body = new_body
        tc_file.write_text(_serialize_frontmatter(fm) + body, encoding="utf-8")
        if "automation" not in fm:
            fm["automation"] = {"status": "not-automated"}
        return TestCase(**fm, body=body)
    return None


def list_runs() -> List[TestRunListItem]:
    runs_dir = QA_ROOT / "runs"
    if not runs_dir.exists():
        return []
    items = []
    for run_file in sorted(runs_dir.rglob("TR-*.yml"), reverse=True):
        try:
            data = _load_yaml(run_file)
            items.append(
                TestRunListItem(
                    id=data["id"],
                    plan=data.get("plan", "?"),
                    started=str(data.get("started", "")),
                    executor=data.get("executor", "?"),
                    summary=data.get("summary", {"total": 0, "passed": 0, "failed": 0, "blocked": 0, "skipped": 0}),
                )
            )
        except Exception:
            continue
    return items


def get_run(run_id: str) -> Optional[TestRun]:
    runs_dir = QA_ROOT / "runs"
    for run_file in runs_dir.rglob(f"{run_id}.yml"):
        try:
            data = _load_yaml(run_file)
            return TestRun(**data)
        except Exception:
            continue
    return None


def create_run(plan: str, executor: str, environment: dict, results: List[dict]) -> TestRun:
    """run-record.mjs equivalent — yeni run YAML yarat."""
    now = datetime.now(timezone.utc)
    yyyy, mm, dd = now.strftime("%Y"), now.strftime("%m"), now.strftime("%d")
    name = plan.upper().replace("TP-", "").replace(".", "-").replace("_", "-")

    month_dir = QA_ROOT / "runs" / yyyy / mm
    month_dir.mkdir(parents=True, exist_ok=True)

    seq = 1
    prefix = f"TR-{yyyy}-{mm}-{dd}-{name}-"
    for f in month_dir.glob(f"{prefix}*"):
        seq += 1
    run_id = f"{prefix}{seq:03d}"

    summary = {"total": 0, "passed": 0, "failed": 0, "blocked": 0, "skipped": 0, "untested": 0}
    for r in results:
        summary["total"] += 1
        st = r.get("status", "untested")
        if st in summary:
            summary[st] += 1
        else:
            summary["untested"] += 1

    doc = {
        "id": run_id,
        "plan": plan,
        "started": now.isoformat(),
        "ended": now.isoformat(),
        "executor": executor,
        "environment": environment,
        "summary": summary,
        "results": results,
    }
    file_path = month_dir / f"{run_id}.yml"
    file_path.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return TestRun(**doc)


def list_plans() -> List[Plan]:
    plans_dir = QA_ROOT / "plans"
    if not plans_dir.exists():
        return []
    plans = []
    for f in sorted(plans_dir.glob("*.yml")):
        try:
            data = _load_yaml(f)
            plans.append(Plan(**data))
        except Exception:
            continue
    return plans


def list_requirements() -> List[Requirement]:
    req_dir = QA_ROOT / "requirements"
    if not req_dir.exists():
        return []
    reqs = []
    for f in sorted(req_dir.glob("REQ-*.md")):
        try:
            text = f.read_text(encoding="utf-8")
            fm, _body = _parse_frontmatter(text)
            if fm:
                reqs.append(Requirement(**fm))
        except Exception:
            continue
    return reqs


def list_pre_conditions() -> List[PreCondition]:
    pre_dir = QA_ROOT / "shared" / "pre-conditions"
    if not pre_dir.exists():
        return []
    items = []
    for f in sorted(pre_dir.glob("PRE-*.md")):
        try:
            text = f.read_text(encoding="utf-8")
            fm, _body = _parse_frontmatter(text)
            if fm:
                items.append(PreCondition(**fm))
        except Exception:
            continue
    return items


def coverage_summary() -> CoverageResponse:
    tcs = list_test_cases()
    total = len(tcs)
    automated = sum(1 for t in tcs if t.automation_status == "automated")

    suites: Dict[str, Dict[str, int]] = {}
    for t in tcs:
        s = suites.setdefault(t.suite, {"P0": 0, "P1": 0, "P2": 0, "P3": 0, "total": 0, "automated": 0})
        s[t.priority] += 1
        s["total"] += 1
        if t.automation_status == "automated":
            s["automated"] += 1

    rows = []
    for suite_name in sorted(suites.keys()):
        m = suites[suite_name]
        pct = int(round((m["automated"] / m["total"]) * 100)) if m["total"] else 0
        rows.append(
            CoverageMatrixRow(
                suite=suite_name,
                P0=m["P0"], P1=m["P1"], P2=m["P2"], P3=m["P3"],
                total=m["total"], automated=m["automated"], automation_pct=pct,
            )
        )

    return CoverageResponse(
        total_tcs=total,
        automated_count=automated,
        automation_pct=int(round((automated / total) * 100)) if total else 0,
        suites=rows,
    )


def health_score() -> HealthReport:
    """Mirror of qa/tools/health-check.mjs — Python implementation."""
    tcs = list_test_cases()
    runs = list_runs()
    reqs = list_requirements()

    # 1. Validation (20 pts) — qa/tools/validate.mjs çalıştır
    validate_score, validate_note = _run_validate()

    # 2. Automation (20 pts)
    auto = sum(1 for t in tcs if t.automation_status == "automated")
    auto_pct = (auto / len(tcs)) if tcs else 0
    automation_score = round(auto_pct * 20)

    # 3. Requirements (15 pts) — full TC load needed
    tc_full = [get_test_case(t.id) for t in tcs]
    tc_with_req = sum(1 for t in tc_full if t and t.requirements)
    req_pct = (tc_with_req / len(tcs)) if tcs else 0
    req_score = round(req_pct * 15)

    # 4. Pre-conditions (10 pts)
    tc_with_pre = sum(1 for t in tc_full if t and t.pre_conditions)
    pre_pct = (tc_with_pre / len(tcs)) if tcs else 0
    pre_score = round(pre_pct * 10)

    # 5. Run freshness (15 pts)
    run_score = 0
    run_note = "no runs"
    if runs:
        latest_started = max((r.started for r in runs), default="")
        if latest_started:
            try:
                latest = datetime.fromisoformat(latest_started.replace("Z", "+00:00"))
                days = (datetime.now(timezone.utc) - latest).total_seconds() / 86400
                if days < 1:
                    run_score = 15
                elif days < 7:
                    run_score = 12
                elif days < 30:
                    run_score = 6
                else:
                    run_score = 2
                run_note = f"{days:.1f} gün önce"
            except (ValueError, TypeError):
                run_note = "parse error"

    # 6. Flakiness (10 pts)
    tc_history: Dict[str, List[str]] = {}
    for r in sorted(runs, key=lambda x: x.started):
        run_full = get_run(r.id)
        if not run_full:
            continue
        for res in run_full.results:
            tc_history.setdefault(res.tc, []).append(res.status)
    flaky_count = 0
    for hist in tc_history.values():
        if len(hist) < 3:
            continue
        flips = sum(1 for i in range(1, len(hist)) if hist[i] != hist[i - 1] and hist[i] in ("pass", "fail"))
        if flips / (len(hist) - 1) >= 0.3:
            flaky_count += 1
    flaky_score = 10
    flaky_note = "0 flaky"
    if tc_history:
        flaky_pct = flaky_count / len(tc_history)
        flaky_score = max(0, round(10 - flaky_pct * 30))
        flaky_note = f"{flaky_count}/{len(tc_history)} flaky"

    # 7. Open defects (10 pts)
    open_defects = sum(t.open_defects_count for t in tcs)
    defect_score = 10 if open_defects == 0 else 6 if open_defects < 5 else 3 if open_defects < 10 else 0

    total = (
        validate_score + automation_score + req_score + pre_score + run_score + flaky_score + defect_score
    )

    grade = "A" if total >= 90 else "B" if total >= 75 else "C" if total >= 60 else "D" if total >= 40 else "F"

    return HealthReport(
        total=total,
        max=100,
        grade=grade,
        components={
            "validation": {"score": validate_score, "max": 20, "note": validate_note},
            "automation": {"score": automation_score, "max": 20, "note": f"{auto}/{len(tcs)} = {int(auto_pct*100)}%"},
            "requirements": {"score": req_score, "max": 15, "note": f"{tc_with_req}/{len(tcs)} TC linked"},
            "pre_conditions": {"score": pre_score, "max": 10, "note": f"{tc_with_pre}/{len(tcs)} TC linked"},
            "run_freshness": {"score": run_score, "max": 15, "note": run_note},
            "flakiness": {"score": flaky_score, "max": 10, "note": flaky_note},
            "open_defects": {"score": defect_score, "max": 10, "note": f"{open_defects} açık"},
        },
        stats={"test_cases": len(tcs), "requirements": len(reqs), "runs": len(runs)},
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


def _run_validate() -> Tuple[int, str]:
    """qa/tools/validate.mjs --json çalıştır, fail=0 ise 20 puan."""
    try:
        result = subprocess.run(
            ["node", str(QA_ROOT / "tools" / "validate.mjs"), "--quiet", "--json"],
            capture_output=True,
            text=True,
            cwd=str(QA_ROOT),
            timeout=30,
        )
        if result.returncode == 0:
            return 20, "0 fail"
        return 0, "validate FAILED"
    except Exception as e:
        return 0, f"node not available ({type(e).__name__})"


def _build_last_status_map() -> Dict[str, Tuple[str, str]]:
    """Tüm runs'tan her TC için son status'u çıkar."""
    runs = list_runs()
    last_by_tc: Dict[str, Tuple[str, str]] = {}
    # Eskiden yeniye sırala (sonuncu kazanır)
    for r in sorted(runs, key=lambda x: x.started):
        run_full = get_run(r.id)
        if not run_full:
            continue
        for res in run_full.results:
            last_by_tc[res.tc] = (r.id, res.status)
    return last_by_tc


def _slugify(text: str, max_length: int = 50) -> str:
    tr_map = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    text = text.translate(tr_map).lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:max_length].rstrip("-")
