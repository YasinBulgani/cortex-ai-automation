"""Service layer for Neurex Management.

HTTP-agnostic: raises ValueError (400 Bad Request) or KeyError (404 Not Found)
instead of HTTPException so the service layer is framework-independent.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Optional
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.domains.tspm.models import TspmProject
from app.domains.test_management.models import (
    DEFAULT_TENANT_ID,
    DefectLink,
    ExecutionEvidence,
    RegressionSet,
    RegressionSetCase,
    ReleaseSignoff,
    Requirement,
    RequirementLink,
    TestCase,
    TestCaseStep,
    TestCaseVersion,
    TestCycle,
    TestFolder,
    TestImportJob,
    TestImportJobRow,
    TestManagementAuditEvent,
    TestManagementProject,
    TestPlan,
    TestRun,
    TestRunCase,
    TestRunStepResult,
    TestSuite,
    utcnow,
)
from app.domains.test_management.schemas import (
    DefectLinkCreate,
    DefectLinkUpdate,
    ExecutionSummaryOut,
    ManagementProjectCreate,
    ReleaseReportOut,
    RegressionCandidateOut,
    RegressionSetCaseIn,
    RegressionSetCreate,
    RegressionSelectionFilter,
    RequirementCreate,
    RequirementLinkCreate,
    ReleaseSignoffCreate,
    StepResultUpdate,
    TestCaseCreate,
    TestCaseUpdate,
    TestCycleCreate,
    TestFolderCreate,
    TestImportJobCreate,
    TestPlanCreate,
    TestRunCreate,
    TestSuiteCreate,
)


def _actor_id(user: Any | None) -> Optional[str]:
    return str(getattr(user, "id", "")) or None if user is not None else None


def audit(db: Session, action: str, entity_type: str, entity_id: str | None, project_id: str | None, user: Any | None, payload: dict[str, Any] | None = None) -> None:
    db.add(
        TestManagementAuditEvent(
            project_id=project_id,
            actor_id=_actor_id(user),
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload or {},
        )
    )


def get_project(db: Session, project_id: str) -> TestManagementProject:
    project = db.get(TestManagementProject, project_id)
    if project is not None:
        return project
    project = db.scalar(select(TestManagementProject).where(TestManagementProject.tspm_project_id == project_id))
    if project is not None:
        return project
    return ensure_project_for_tspm(db, project_id, None)


def ensure_project_for_tspm(db: Session, tspm_project_id: str, user: Any | None) -> TestManagementProject:
    project = db.scalar(select(TestManagementProject).where(TestManagementProject.tspm_project_id == tspm_project_id))
    if project is not None:
        return project
    tspm_project = db.get(TspmProject, tspm_project_id)
    if tspm_project is None:
        raise KeyError("Management projesi bulunamadı")
    project = TestManagementProject(
        name=f"{tspm_project.name} Management",
        key=_next_project_key(db, tspm_project.name),
        description=tspm_project.description or "",
        tspm_project_id=tspm_project.id,
        created_by=_actor_id(user),
    )
    db.add(project)
    db.flush()
    audit(db, "project.auto_created", "project", project.id, project.id, user, {"tspm_project_id": tspm_project.id})
    db.commit()
    db.refresh(project)
    return project


def _next_project_key(db: Session, name: str) -> str:
    base = "".join(ch for ch in name.upper() if ch.isalnum())[:8] or "MGMT"
    candidate = base
    index = 1
    while db.scalar(
        select(TestManagementProject.id).where(
            TestManagementProject.tenant_id == DEFAULT_TENANT_ID,
            TestManagementProject.key == candidate,
        )
    ):
        index += 1
        candidate = f"{base[: max(1, 8 - len(str(index)))]}{index}"
    return candidate


def resolve_project_id(db: Session, project_id: str) -> str:
    return get_project(db, project_id).id


def create_project(db: Session, payload: ManagementProjectCreate, user: Any | None) -> TestManagementProject:
    key = payload.key.upper()
    existing = db.scalar(
        select(TestManagementProject).where(
            TestManagementProject.tenant_id == DEFAULT_TENANT_ID,
            TestManagementProject.key == key,
        )
    )
    if existing is not None:
        raise ValueError("Management proje anahtarı zaten kullanılıyor")
    project = TestManagementProject(
        name=payload.name,
        key=key,
        description=payload.description,
        tspm_project_id=payload.tspm_project_id,
        created_by=_actor_id(user),
    )
    db.add(project)
    db.flush()
    audit(db, "project.created", "project", project.id, project.id, user)
    db.commit()
    db.refresh(project)
    return project


def list_projects(db: Session) -> list[TestManagementProject]:
    return list(db.scalars(select(TestManagementProject).order_by(TestManagementProject.created_at.desc())).all())


def management_settings(db: Session, project_id: str) -> dict[str, Any]:
    """Return the effective management policy snapshot for the project."""
    project_id = resolve_project_id(db, project_id)
    case_count = db.scalar(select(func.count()).select_from(TestCase).where(TestCase.project_id == project_id)) or 0
    custom_field_rows = db.scalars(
        select(TestCase.custom_fields).where(TestCase.project_id == project_id, TestCase.custom_fields != {})
    ).all()
    custom_field_names = sorted(
        {
            str(field)
            for fields in custom_field_rows
            if isinstance(fields, dict)
            for field in fields.keys()
        }
    )
    evidence_count = (
        db.scalar(
            select(func.count())
            .select_from(ExecutionEvidence)
            .join(TestRunCase, ExecutionEvidence.run_case_id == TestRunCase.id)
            .join(TestCase, TestRunCase.case_id == TestCase.id)
            .where(TestCase.project_id == project_id)
        )
        or 0
    )
    return {
        "project_id": project_id,
        "permissions": [
            "test_management.read",
            "test_management.write",
            "test_management.execute",
            "test_management.admin",
            "test_management.audit",
        ],
        "workflow_statuses": {
            "case": ["draft", "active", "review", "deprecated", "archived"],
            "run": ["not_started", "running", "passed", "failed", "blocked", "skipped"],
            "plan": ["draft", "approved", "in_progress", "completed", "archived"],
            "import": ["preview", "committed", "failed", "cancelled"],
        },
        "evidence_retention_days": {
            "screenshot": 180,
            "log": 90,
            "video": 30,
            "critical_failed_evidence": 365,
        },
        "aggregation_policy": {
            "run_case_status": "failed > blocked > retest > passed > skipped > not_run",
            "pass_rate_denominator": "passed + failed + blocked + skipped + retest",
            "progress_denominator": "all run cases",
        },
        "custom_field_usage": {
            "defined_fields": custom_field_names,
            "case_count": case_count,
            "cases_with_custom_fields": len(custom_field_rows),
            "evidence_count": evidence_count,
        },
    }


def list_audit_events(db: Session, project_id: str, limit: int = 50) -> list[TestManagementAuditEvent]:
    project_id = resolve_project_id(db, project_id)
    return list(
        db.scalars(
            select(TestManagementAuditEvent)
            .where(TestManagementAuditEvent.project_id == project_id)
            .order_by(TestManagementAuditEvent.created_at.desc())
            .limit(limit)
        ).all()
    )


def _ensure_suite(db: Session, project_id: str, suite_id: str | None) -> TestSuite | None:
    if suite_id is None:
        return None
    suite = db.get(TestSuite, suite_id)
    if suite is None or suite.project_id != project_id:
        raise KeyError("Suite bulunamadı")
    return suite


def _ensure_folder(db: Session, project_id: str, folder_id: str | None) -> TestFolder | None:
    if folder_id is None:
        return None
    folder = db.get(TestFolder, folder_id)
    if folder is None or folder.suite.project_id != project_id:
        raise KeyError("Folder bulunamadı")
    return folder


def create_suite(db: Session, project_id: str, payload: TestSuiteCreate, user: Any | None) -> TestSuite:
    project_id = resolve_project_id(db, project_id)
    suite = TestSuite(project_id=project_id, name=payload.name, description=payload.description, order_index=payload.order_index)
    db.add(suite)
    db.flush()
    audit(db, "suite.created", "suite", suite.id, project_id, user)
    db.commit()
    db.refresh(suite)
    return suite


def create_folder(db: Session, project_id: str, payload: TestFolderCreate, user: Any | None) -> TestFolder:
    project_id = resolve_project_id(db, project_id)
    _ensure_suite(db, project_id, payload.suite_id)
    if payload.parent_id is not None:
        parent = _ensure_folder(db, project_id, payload.parent_id)
        if parent is not None and parent.suite_id != payload.suite_id:
            raise ValueError("Parent folder aynı suite içinde olmalı")
    folder = TestFolder(
        suite_id=payload.suite_id,
        parent_id=payload.parent_id,
        name=payload.name,
        path=payload.path,
        order_index=payload.order_index,
    )
    db.add(folder)
    db.flush()
    audit(db, "folder.created", "folder", folder.id, project_id, user)
    db.commit()
    db.refresh(folder)
    return folder


def _next_case_key(db: Session, project: TestManagementProject) -> str:
    count = db.scalar(select(func.count()).select_from(TestCase).where(TestCase.project_id == project.id)) or 0
    return f"{project.key}-TC-{int(count) + 1001}"


def _case_snapshot(case: TestCase) -> dict[str, Any]:
    return {
        "case": {
            "id": case.id,
            "case_key": case.case_key,
            "title": case.title,
            "objective": case.objective,
            "preconditions": case.preconditions,
            "test_data": case.test_data,
            "priority": case.priority,
            "severity": case.severity,
            "type": case.type,
            "automation_status": case.automation_status,
            "status": case.status,
            "tags": case.tags,
            "custom_fields": case.custom_fields,
        },
        "steps": [
            {
                "step_no": step.step_no,
                "action": step.action,
                "expected_result": step.expected_result,
                "test_data": step.test_data,
                "notes": step.notes,
                "is_required": step.is_required,
            }
            for step in case.steps
        ],
    }


def _add_version(db: Session, case: TestCase, user: Any | None, change_summary: str, changed_fields: Iterable[str] = ()) -> None:
    snapshot = _case_snapshot(case)
    encoded = json.dumps(snapshot, ensure_ascii=False, default=str).encode("utf-8")
    db.add(
        TestCaseVersion(
            case_id=case.id,
            version_no=case.current_version,
            snapshot=snapshot,
            change_summary=change_summary,
            changed_fields=list(changed_fields),
            snapshot_size_bytes=len(encoded),
            created_by=_actor_id(user),
        )
    )


def create_case(db: Session, project_id: str, payload: TestCaseCreate, user: Any | None) -> TestCase:
    project = get_project(db, project_id)
    project_id = project.id
    _ensure_suite(db, project_id, payload.suite_id)
    folder = _ensure_folder(db, project_id, payload.folder_id)
    if folder is not None and payload.suite_id is not None and folder.suite_id != payload.suite_id:
        raise ValueError("Case folder ve suite aynı hiyerarşide olmalı")
    case_suite_id = payload.suite_id or (folder.suite_id if folder is not None else None)
    case = TestCase(
        project_id=project_id,
        suite_id=case_suite_id,
        folder_id=payload.folder_id,
        case_key=payload.case_key or _next_case_key(db, project),
        title=payload.title,
        objective=payload.objective,
        preconditions=payload.preconditions,
        test_data=payload.test_data,
        priority=payload.priority,
        severity=payload.severity,
        type=payload.type,
        automation_status=payload.automation_status,
        status=payload.status,
        source_type=payload.source_type,
        source_ref=payload.source_ref,
        owner_id=payload.owner_id,
        tags=payload.tags,
        custom_fields=payload.custom_fields,
        created_by=_actor_id(user),
        updated_by=_actor_id(user),
    )
    for idx, step in enumerate(payload.steps, start=1):
        case.steps.append(
            TestCaseStep(
                step_no=step.step_no or idx,
                action=step.action,
                expected_result=step.expected_result,
                test_data=step.test_data,
                notes=step.notes,
                is_required=step.is_required,
            )
        )
    db.add(case)
    db.flush()
    _add_version(db, case, user, "Initial version", ["created"])
    audit(db, "case.created", "case", case.id, project_id, user, {"case_key": case.case_key})
    db.commit()
    return get_case(db, project_id, case.id)


def get_case(db: Session, project_id: str, case_id: str) -> TestCase:
    project_id = resolve_project_id(db, project_id)
    case = db.scalar(
        select(TestCase)
        .options(selectinload(TestCase.steps))
        .where(TestCase.project_id == project_id, TestCase.id == case_id)
    )
    if case is None:
        raise KeyError("Test case bulunamadı")
    return case


def list_case_versions(db: Session, project_id: str, case_id: str) -> list[TestCaseVersion]:
    get_case(db, project_id, case_id)
    return list(
        db.scalars(
            select(TestCaseVersion)
            .where(TestCaseVersion.case_id == case_id)
            .order_by(TestCaseVersion.version_no.desc())
        ).all()
    )


def list_cases(db: Session, project_id: str, q: str | None = None, include_archived: bool = False) -> list[TestCase]:
    project_id = resolve_project_id(db, project_id)
    stmt = select(TestCase).options(selectinload(TestCase.steps)).where(TestCase.project_id == project_id)
    if not include_archived:
        stmt = stmt.where(TestCase.archived.is_(False))
    if q:
        like = f"%{q}%"
        stmt = stmt.where(TestCase.title.ilike(like) | TestCase.case_key.ilike(like))
    return list(db.scalars(stmt.order_by(TestCase.created_at.desc())).all())


def repository(db: Session, project_id: str) -> dict[str, Any]:
    project_id = resolve_project_id(db, project_id)
    suites = list(db.scalars(select(TestSuite).where(TestSuite.project_id == project_id).order_by(TestSuite.order_index, TestSuite.name)).all())
    suite_ids = [s.id for s in suites]
    folders = list(db.scalars(select(TestFolder).where(TestFolder.suite_id.in_(suite_ids)).order_by(TestFolder.path)).all()) if suite_ids else []
    cases = list_cases(db, project_id)
    return {"suites": suites, "folders": folders, "cases": cases}


def update_case(db: Session, project_id: str, case_id: str, payload: TestCaseUpdate, user: Any | None) -> TestCase:
    project_id = resolve_project_id(db, project_id)
    case = get_case(db, project_id, case_id)
    before_version = case.current_version
    changed: list[str] = []
    data = payload.model_dump(exclude_unset=True)
    steps = data.pop("steps", None)
    change_summary = data.pop("change_summary", "Manual update")
    if "suite_id" in data:
        _ensure_suite(db, project_id, data["suite_id"])
    if "folder_id" in data:
        folder = _ensure_folder(db, project_id, data["folder_id"])
        next_suite_id = data.get("suite_id", case.suite_id)
        if folder is not None and next_suite_id is not None and folder.suite_id != next_suite_id:
            raise ValueError("Case folder ve suite aynı hiyerarşide olmalı")
        if folder is not None and next_suite_id is None:
            data["suite_id"] = folder.suite_id
    for key, value in data.items():
        setattr(case, key, value)
        changed.append(key)
    if steps is not None:
        case.steps.clear()
        db.flush()
        for step in steps:
            case.steps.append(TestCaseStep(**step))
        changed.append("steps")
    if changed:
        case.current_version = before_version + 1
        case.updated_by = _actor_id(user)
        db.flush()
        _add_version(db, case, user, change_summary, changed)
        audit(db, "case.updated", "case", case.id, project_id, user, {"changed_fields": changed})
    db.commit()
    return get_case(db, project_id, case_id)


def archive_case(db: Session, project_id: str, case_id: str, user: Any | None) -> TestCase:
    project_id = resolve_project_id(db, project_id)
    case = get_case(db, project_id, case_id)
    case.archived = True
    case.status = "archived"
    case.current_version += 1
    db.flush()
    _add_version(db, case, user, "Archived", ["archived", "status"])
    audit(db, "case.archived", "case", case.id, project_id, user)
    db.commit()
    return get_case(db, project_id, case_id)


def create_plan(db: Session, project_id: str, payload: TestPlanCreate, user: Any | None) -> TestPlan:
    project_id = resolve_project_id(db, project_id)
    plan = TestPlan(
        project_id=project_id,
        name=payload.name,
        plan_type=payload.plan_type,
        release_name=payload.release_name,
        scope_summary=payload.scope_summary,
        created_by=_actor_id(user),
    )
    db.add(plan)
    db.flush()
    audit(db, "plan.created", "plan", plan.id, project_id, user)
    db.commit()
    db.refresh(plan)
    return plan


def list_plans(db: Session, project_id: str) -> list[TestPlan]:
    project_id = resolve_project_id(db, project_id)
    return list(
        db.scalars(
            select(TestPlan)
            .where(TestPlan.project_id == project_id)
            .order_by(TestPlan.created_at.desc())
        ).all()
    )


def create_cycle(db: Session, project_id: str, payload: TestCycleCreate, user: Any | None) -> TestCycle:
    project_id = resolve_project_id(db, project_id)
    plan = db.get(TestPlan, payload.plan_id)
    if plan is None or plan.project_id != project_id:
        raise KeyError("Test plan bulunamadı")
    cycle = TestCycle(plan_id=payload.plan_id, name=payload.name, environment=payload.environment, build_version=payload.build_version)
    db.add(cycle)
    db.flush()
    audit(db, "cycle.created", "cycle", cycle.id, project_id, user)
    db.commit()
    db.refresh(cycle)
    return cycle


def list_cycles(db: Session, project_id: str, plan_id: str | None = None) -> list[TestCycle]:
    project_id = resolve_project_id(db, project_id)
    stmt = (
        select(TestCycle)
        .join(TestPlan, TestCycle.plan_id == TestPlan.id)
        .where(TestPlan.project_id == project_id)
        .order_by(TestCycle.created_at.desc())
    )
    if plan_id is not None:
        stmt = stmt.where(TestCycle.plan_id == plan_id)
    return list(db.scalars(stmt).all())


def _regression_candidate(case: TestCase, requirement_case_ids: set[str], filters: RegressionSelectionFilter) -> RegressionCandidateOut:
    score = 0
    reasons: list[str] = []
    if case.priority in {"P0", "P1"}:
        score += 30 if case.priority == "P0" else 20
        reasons.append(f"{case.priority} priority")
    if case.severity in {"blocker", "critical", "major"}:
        score += {"blocker": 30, "critical": 24, "major": 12}.get(case.severity, 0)
        reasons.append(f"{case.severity} severity")
    if case.last_run_status in {"failed", "blocked", "retest"}:
        score += 25
        reasons.append(f"last run {case.last_run_status}")
    if filters.include_not_run and case.last_run_status is None:
        score += 12
        reasons.append("never run")
    if filters.include_without_requirements and case.id not in requirement_case_ids:
        score += 8
        reasons.append("no requirement coverage link")
    if "smoke" in case.tags or case.type == "smoke":
        score += 10
        reasons.append("smoke path")
    if not reasons:
        reasons.append("matched filter")
    return RegressionCandidateOut(
        case_id=case.id,
        case_key=case.case_key,
        title=case.title,
        priority=case.priority,
        severity=case.severity,
        type=case.type,
        status=case.status,
        tags=case.tags,
        last_run_status=case.last_run_status,
        risk_score=score,
        reasons=reasons,
    )


def suggest_regression_candidates(db: Session, project_id: str, filters: RegressionSelectionFilter) -> list[RegressionCandidateOut]:
    project_id = resolve_project_id(db, project_id)
    stmt = (
        select(TestCase)
        .options(selectinload(TestCase.steps))
        .where(TestCase.project_id == project_id, TestCase.archived.is_(False), TestCase.status.in_(["active", "ready"]))
    )
    if filters.priorities:
        stmt = stmt.where(TestCase.priority.in_(filters.priorities))
    if filters.severities:
        stmt = stmt.where(TestCase.severity.in_(filters.severities))
    if filters.types:
        stmt = stmt.where(TestCase.type.in_(filters.types))
    if filters.suite_ids:
        stmt = stmt.where(TestCase.suite_id.in_(filters.suite_ids))
    if filters.folder_ids:
        stmt = stmt.where(TestCase.folder_id.in_(filters.folder_ids))

    cases = list(db.scalars(stmt).all())
    tag_filter = {tag.strip().lower() for tag in filters.tags if tag.strip()}
    if tag_filter:
        cases = [
            case
            for case in cases
            if tag_filter.intersection({tag.lower() for tag in case.tags})
        ]
    if filters.include_last_failed:
        failed = list(
            db.scalars(
                select(TestCase)
                .where(
                    TestCase.project_id == project_id,
                    TestCase.archived.is_(False),
                    TestCase.status.in_(["active", "ready"]),
                    TestCase.last_run_status.in_(["failed", "blocked", "retest"]),
                )
            ).all()
        )
        by_id = {case.id: case for case in cases}
        by_id.update({case.id: case for case in failed})
        cases = list(by_id.values())

    requirement_case_ids = set(
        db.scalars(select(RequirementLink.case_id).where(RequirementLink.project_id == project_id)).all()
    )
    candidates = [_regression_candidate(case, requirement_case_ids, filters) for case in cases]
    candidates.sort(key=lambda item: (-item.risk_score, item.case_key))
    return candidates[: filters.max_cases]


def _regression_set_out(regression_set: RegressionSet) -> dict[str, Any]:
    cases = []
    ordered_cases = sorted(regression_set.cases, key=lambda item: item.order_index)
    for item in ordered_cases:
        case = item.case
        cases.append({
            "id": item.id,
            "case_id": item.case_id,
            "case_version_no": item.case_version_no,
            "case_key": item.case_key_snapshot or case.case_key,
            "title": item.title_snapshot or case.title,
            "priority": item.priority_snapshot or case.priority,
            "severity": item.severity_snapshot or case.severity,
            "type": item.type_snapshot or case.type,
            "last_run_status": case.last_run_status,
            "order_index": item.order_index,
            "risk_score": item.risk_score,
            "reason": item.reason,
            "include_mode": item.include_mode,
        })
    return {
        "id": regression_set.id,
        "project_id": regression_set.project_id,
        "name": regression_set.name,
        "set_type": regression_set.set_type,
        "description": regression_set.description,
        "source_filters": regression_set.source_filters,
        "selection_summary": regression_set.selection_summary,
        "created_by": regression_set.created_by,
        "created_at": regression_set.created_at,
        "cases": cases,
    }


def list_regression_sets(db: Session, project_id: str) -> list[dict[str, Any]]:
    project_id = resolve_project_id(db, project_id)
    sets = list(
        db.scalars(
            select(RegressionSet)
            .options(selectinload(RegressionSet.cases).selectinload(RegressionSetCase.case))
            .where(RegressionSet.project_id == project_id)
            .order_by(RegressionSet.created_at.desc())
        ).all()
    )
    return [_regression_set_out(item) for item in sets]


def create_regression_set(db: Session, project_id: str, payload: RegressionSetCreate, user: Any | None) -> dict[str, Any]:
    project_id = resolve_project_id(db, project_id)
    rows = payload.cases
    if not rows:
        candidates = suggest_regression_candidates(db, project_id, payload.filters)
        rows = [
            RegressionSetCaseIn(
                case_id=item.case_id,
                order_index=index,
                risk_score=item.risk_score,
                reason=", ".join(item.reasons),
                include_mode="suggested",
            )
            for index, item in enumerate(candidates)
        ]
    regression_set = RegressionSet(
        project_id=project_id,
        name=payload.name,
        set_type=payload.set_type,
        description=payload.description,
        source_filters=payload.filters.model_dump(),
        selection_summary={"case_count": len(rows), "risk_total": sum(item.risk_score for item in rows)},
        created_by=_actor_id(user),
    )
    seen_case_ids: set[str] = set()
    for index, item in enumerate(rows):
        if item.case_id in seen_case_ids:
            continue
        case = get_case(db, project_id, item.case_id)
        if case.archived:
            continue
        seen_case_ids.add(item.case_id)
        regression_set.cases.append(
            RegressionSetCase(
                case_id=item.case_id,
                case_version_no=case.current_version,
                case_key_snapshot=case.case_key,
                title_snapshot=case.title,
                priority_snapshot=case.priority,
                severity_snapshot=case.severity,
                type_snapshot=case.type,
                order_index=item.order_index or index,
                risk_score=item.risk_score,
                reason=item.reason,
                include_mode=item.include_mode,
            )
        )
    db.add(regression_set)
    db.flush()
    audit(db, "regression_set.created", "regression_set", regression_set.id, project_id, user, regression_set.selection_summary)
    db.commit()
    regression_set = db.scalar(
        select(RegressionSet)
        .options(selectinload(RegressionSet.cases).selectinload(RegressionSetCase.case))
        .where(RegressionSet.id == regression_set.id)
    )
    return _regression_set_out(regression_set)  # type: ignore[arg-type]


def get_run(db: Session, project_id: str, run_id: str) -> TestRun:
    """Return a single run with nested run_cases and step_results."""
    project_id = resolve_project_id(db, project_id)
    run = db.scalar(
        select(TestRun)
        .options(
            selectinload(TestRun.run_cases).selectinload(TestRunCase.step_results),
            selectinload(TestRun.run_cases).selectinload(TestRunCase.case).selectinload(TestCase.steps),
        )
        .where(TestRun.id == run_id)
    )
    if run is None:
        raise KeyError("Test run bulunamadı")
    # Verify project ownership through cycle→plan.
    if run.cycle.plan.project_id != project_id:
        raise KeyError("Test run bulunamadı")
    for run_case in run.run_cases:
        if not run_case.case_snapshot and run_case.case is not None:
            run_case.case_snapshot = _case_snapshot(run_case.case)
    return run


def list_runs(db: Session, project_id: str, status_filter: str | None = None) -> list[TestRun]:
    """Return all runs for a project, optionally filtered by status."""
    project_id = resolve_project_id(db, project_id)
    q = (
        db.query(TestRun)
        .join(TestCycle, TestRun.cycle_id == TestCycle.id)
        .join(TestPlan, TestCycle.plan_id == TestPlan.id)
        .filter(TestPlan.project_id == project_id)
        .order_by(TestRun.created_at.desc())
    )
    if status_filter:
        q = q.filter(TestRun.status == status_filter)
    return q.all()


def create_run(db: Session, project_id: str, payload: TestRunCreate, user: Any | None) -> TestRun:
    project_id = resolve_project_id(db, project_id)
    cycle = db.get(TestCycle, payload.cycle_id)
    if cycle is None or cycle.plan.project_id != project_id:
        raise KeyError("Test cycle bulunamadı")
    run = TestRun(
        cycle_id=payload.cycle_id,
        name=payload.name,
        source_type=payload.source_type,
        source_ref=payload.source_ref,
        scope_snapshot=payload.scope_snapshot,
    )
    db.add(run)
    db.flush()
    for case_id in payload.case_ids:
        case = get_case(db, project_id, case_id)
        db.add(
            TestRunCase(
                run_id=run.id,
                case_id=case.id,
                case_version_no=case.current_version,
                case_snapshot=_case_snapshot(case),
                assigned_to=payload.assigned_to,
            )
        )
    audit(db, "run.created", "run", run.id, project_id, user, {"case_count": len(payload.case_ids)})
    db.commit()
    db.refresh(run)
    return run


def _sync_run_status(run: TestRun) -> None:
    statuses = [case.status for case in run.run_cases]
    if not statuses:
        run.status = "not_started"
        run.started_at = None
        run.completed_at = None
        return
    terminal = {"passed", "failed", "blocked", "skipped"}
    if any(status not in {"not_run", "queued"} for status in statuses) and run.started_at is None:
        run.started_at = utcnow()
    if all(status in terminal for status in statuses):
        run.status = "completed"
        run.completed_at = run.completed_at or utcnow()
    elif any(status != "not_run" for status in statuses):
        run.status = "running"
        run.completed_at = None
    else:
        run.status = "not_started"
        run.completed_at = None


def update_step_result(db: Session, project_id: str, run_case_id: str, step_no: int, payload: StepResultUpdate, user: Any | None) -> TestRunCase:
    project_id = resolve_project_id(db, project_id)
    run_case = db.get(TestRunCase, run_case_id)
    if run_case is None:
        raise KeyError("Run case bulunamadı")
    # Project guard through case.
    if run_case.case.project_id != project_id:
        raise KeyError("Run case bulunamadı")
    result = db.scalar(select(TestRunStepResult).where(TestRunStepResult.run_case_id == run_case_id, TestRunStepResult.step_no == step_no))
    if result is None:
        result = TestRunStepResult(run_case_id=run_case_id, step_no=step_no)
        db.add(result)
    result.status = payload.status
    result.actual_result = payload.actual_result
    result.comment = payload.comment
    statuses = [r.status for r in run_case.step_results]
    if payload.status not in statuses:
        statuses.append(payload.status)
    if "failed" in statuses:
        run_case.status = "failed"
        run_case.case.last_failed_at = utcnow()
    elif "blocked" in statuses:
        run_case.status = "blocked"
    elif statuses and all(s in {"passed", "skipped"} for s in statuses) and "passed" in statuses:
        run_case.status = "passed"
    else:
        run_case.status = "in_progress"
    run_case.case.last_run_status = run_case.status
    run_case.case.last_run_at = utcnow()
    run_case.case.last_run_id = run_case.run_id
    _sync_run_status(run_case.run)
    audit(db, "run_case.step_updated", "run_case", run_case.id, project_id, user, {"step_no": step_no, "status": payload.status})
    db.commit()
    db.refresh(run_case)
    return run_case


def execution_summary(db: Session, project_id: str) -> ExecutionSummaryOut:
    project_id = resolve_project_id(db, project_id)
    cases = list(
        db.scalars(
            select(TestRunCase)
            .join(TestCase, TestRunCase.case_id == TestCase.id)
            .where(TestCase.project_id == project_id)
        ).all()
    )
    counts = {key: 0 for key in ["not_run", "passed", "failed", "blocked", "skipped", "retest"]}
    for case in cases:
        counts[case.status] = counts.get(case.status, 0) + 1
    total = len(cases)
    terminal = counts["passed"] + counts["failed"] + counts["blocked"] + counts["skipped"] + counts["retest"]
    executed = counts["passed"] + counts["failed"] + counts["blocked"] + counts["skipped"]
    return ExecutionSummaryOut(
        total=total,
        not_run=counts["not_run"],
        passed=counts["passed"],
        failed=counts["failed"],
        blocked=counts["blocked"],
        skipped=counts["skipped"],
        retest=counts["retest"],
        progress_pct=round((terminal / total) * 100, 2) if total else 0,
        pass_rate_pct=round((counts["passed"] / executed) * 100, 2) if executed else 0,
    )


def _days_since(value: datetime | None) -> int | None:
    if value is None:
        return None
    now = utcnow()
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return max(0, (now - value).days)


def release_report(db: Session, project_id: str) -> ReleaseReportOut:
    project_id = resolve_project_id(db, project_id)
    summary = execution_summary(db, project_id)
    traceability = requirement_traceability(db, project_id)
    defects = list_defect_links(db, project_id)
    runs = list_runs(db, project_id)

    closed_statuses = {"closed", "done", "resolved", "fixed", "verified"}
    open_defects = [
        defect for defect in defects
        if defect.status.strip().lower() not in closed_statuses
    ]
    defect_ages = [
        age for age in (_days_since(defect.created_at) for defect in open_defects)
        if age is not None
    ]
    oldest_open_defect_days = max(defect_ages) if defect_ages else 0
    covered_requirements = sum(1 for row in traceability if row.get("covered"))
    stale_requirements = sum(1 for row in traceability if row.get("stale"))
    total_requirements = len(traceability)
    uncovered_requirements = total_requirements - covered_requirements
    coverage_pct = round((covered_requirements / total_requirements) * 100, 2) if total_requirements else 0
    active_runs = len([run for run in runs if run.status in {"running", "not_started"}])

    if summary.failed > 0 or summary.blocked > 0 or open_defects:
        decision = "NO-GO"
    elif stale_requirements > 0 or coverage_pct < 90:
        decision = "Conditional GO"
    elif summary.progress_pct >= 95 and summary.pass_rate_pct >= 95 and coverage_pct >= 95:
        decision = "GO"
    else:
        decision = "Watch"

    blockers: list[dict[str, Any]] = []
    if summary.failed:
        blockers.append({"label": "Failed run cases", "value": summary.failed, "detail": "Must be triaged before release signoff."})
    if summary.blocked:
        blockers.append({"label": "Blocked run cases", "value": summary.blocked, "detail": "Execution is waiting on environment, data, or product fixes."})
    if open_defects:
        blockers.append({"label": "Open defect links", "value": len(open_defects), "detail": f"Oldest open defect is {oldest_open_defect_days} day(s) old."})
    if uncovered_requirements:
        blockers.append({"label": "Uncovered requirements", "value": uncovered_requirements, "detail": "Traceability has release scope without linked coverage."})
    if stale_requirements:
        blockers.append({"label": "Stale requirement links", "value": stale_requirements, "detail": "Requirement source changed after linked test coverage."})

    checklist = [
        {
            "label": "Execution progress",
            "metric": f"{summary.progress_pct:.0f}% / target 95%",
            "status": "pass" if summary.progress_pct >= 95 else "warn" if summary.progress_pct >= 80 else "fail",
        },
        {
            "label": "Pass rate",
            "metric": f"{summary.pass_rate_pct:.0f}% / target 95%",
            "status": "pass" if summary.pass_rate_pct >= 95 else "warn" if summary.pass_rate_pct >= 85 else "fail",
        },
        {"label": "Failed cases", "metric": f"{summary.failed} open", "status": "pass" if summary.failed == 0 else "fail"},
        {"label": "Blocked cases", "metric": f"{summary.blocked} blocked", "status": "pass" if summary.blocked == 0 else "fail"},
        {
            "label": "Requirement coverage",
            "metric": f"{coverage_pct:.0f}% covered",
            "status": "pass" if coverage_pct >= 95 else "warn" if coverage_pct >= 80 else "fail",
        },
        {"label": "Requirement freshness", "metric": f"{stale_requirements} stale", "status": "pass" if stale_requirements == 0 else "warn"},
        {
            "label": "Defect aging",
            "metric": f"{oldest_open_defect_days}d oldest / target 7d",
            "status": "pass" if not open_defects else "warn" if oldest_open_defect_days <= 7 else "fail",
        },
        {"label": "Active runs", "metric": f"{active_runs} in flight", "status": "pass" if active_runs == 0 else "warn"},
    ]

    return ReleaseReportOut(
        project_id=project_id,
        decision=decision,
        generated_at=utcnow(),
        progress_pct=summary.progress_pct,
        pass_rate_pct=summary.pass_rate_pct,
        requirement_coverage_pct=coverage_pct,
        stale_requirement_count=stale_requirements,
        uncovered_requirement_count=uncovered_requirements,
        open_defect_count=len(open_defects),
        oldest_open_defect_days=oldest_open_defect_days,
        active_run_count=active_runs,
        blockers=blockers,
        checklist=checklist,
    )


def list_release_signoffs(db: Session, project_id: str) -> list[ReleaseSignoff]:
    project_id = resolve_project_id(db, project_id)
    stmt = (
        select(ReleaseSignoff)
        .where(ReleaseSignoff.project_id == project_id)
        .order_by(ReleaseSignoff.signed_at.desc(), ReleaseSignoff.created_at.desc())
    )
    return list(db.scalars(stmt).all())


def create_release_signoff(db: Session, project_id: str, payload: ReleaseSignoffCreate, user: Any | None) -> ReleaseSignoff:
    project_id = resolve_project_id(db, project_id)
    report = release_report(db, project_id)
    snapshot = report.model_dump(mode="json")
    signoff = ReleaseSignoff(
        project_id=project_id,
        release_name=payload.release_name,
        decision=payload.decision,
        status=payload.status,
        comment=payload.comment,
        report_snapshot=snapshot,
        signed_by=_actor_id(user),
    )
    db.add(signoff)
    db.flush()
    audit(
        db,
        "release_signoff.created",
        "release_signoff",
        signoff.id,
        project_id,
        user,
        {"decision": payload.decision, "release_name": payload.release_name},
    )
    db.commit()
    db.refresh(signoff)
    return signoff


def export_repository(db: Session, project_id: str) -> dict[str, Any]:
    """Return a portable JSON snapshot for backup or import into another environment."""
    project_id = resolve_project_id(db, project_id)
    repo = repository(db, project_id)
    requirement_links = list(
        db.scalars(
            select(RequirementLink)
            .where(RequirementLink.project_id == project_id)
            .order_by(RequirementLink.external_source, RequirementLink.external_key)
        ).all()
    )
    requirements = list(
        db.scalars(
            select(Requirement)
            .where(Requirement.project_id == project_id)
            .order_by(Requirement.external_source, Requirement.external_key)
        ).all()
    )
    return {
        "schema_version": "test-management.v1",
        "project_id": project_id,
        "exported_at": utcnow().isoformat(),
        "suites": repo["suites"],
        "folders": repo["folders"],
        "cases": repo["cases"],
        "requirements": requirements,
        "requirement_links": requirement_links,
    }


def list_requirements(db: Session, project_id: str) -> list[Requirement]:
    project_id = resolve_project_id(db, project_id)
    stmt = (
        select(Requirement)
        .where(Requirement.project_id == project_id)
        .order_by(Requirement.external_source, Requirement.external_key)
    )
    return list(db.scalars(stmt).all())


def _find_requirement(db: Session, project_id: str, external_source: str, external_key: str) -> Requirement | None:
    return db.scalar(
        select(Requirement).where(
            Requirement.project_id == project_id,
            Requirement.external_source == external_source,
            Requirement.external_key == external_key,
        )
    )


def create_requirement(db: Session, project_id: str, payload: RequirementCreate, user: Any | None) -> Requirement:
    project_id = resolve_project_id(db, project_id)
    existing = _find_requirement(db, project_id, payload.external_source, payload.external_key)
    if existing is not None:
        raise ValueError("Requirement key already exists")

    requirement = Requirement(project_id=project_id, **payload.model_dump())
    db.add(requirement)
    db.flush()
    audit(db, "requirement.created", "requirement", requirement.id, project_id, user)
    db.commit()
    db.refresh(requirement)
    return requirement


def requirement_traceability(db: Session, project_id: str) -> list[dict[str, Any]]:
    """Build a requirements ↔ test-case traceability matrix for the project.

    Returns a list of dicts (one per unique requirement key) each containing:
      requirement_key, title, source, url, covered, stale, cases[]

    Each case entry includes: case_id, case_key, title, last_run_status,
    coverage_status (from the link row).

    Stale = the requirement's source_updated_at is more recent than the
    case's last_run_at (i.e. the requirement changed after the last test run).
    """
    project_id = resolve_project_id(db, project_id)
    requirements = list_requirements(db, project_id)
    links = list(
        db.scalars(
            select(RequirementLink)
            .where(RequirementLink.project_id == project_id)
            .order_by(RequirementLink.external_source, RequirementLink.external_key)
        ).all()
    )

    from collections import defaultdict
    grouped: dict[str, list[RequirementLink]] = defaultdict(list)
    for lnk in links:
        grouped[lnk.requirement_id or f"{lnk.external_source}:{lnk.external_key}"].append(lnk)

    rows = []
    seen_groups: set[str] = set()

    def build_row(req_key: str, title: str, source: str, url: str | None, source_updated_at: datetime | None, req_links: list[RequirementLink]) -> dict[str, Any]:
        cases = []
        covered = False
        stale = False

        for lnk in req_links:
            case = db.get(TestCase, lnk.case_id)
            if case is None or case.project_id != project_id:
                continue
            cases.append({
                "case_id": case.id,
                "case_key": case.case_key,
                "title": case.title,
                "last_run_status": case.last_run_status,
                "coverage_status": lnk.coverage_status,
            })
            if lnk.coverage_status in ("covered", "partial"):
                covered = True
            # Mark stale if requirement was updated after the case's last run.
            updated_at = lnk.source_updated_at or source_updated_at
            if (
                updated_at
                and case.last_run_at
                and updated_at > case.last_run_at
            ):
                stale = True

        return {
            "requirement_key": req_key,
            "title": title,
            "source": source,
            "url": url,
            "covered": covered,
            "stale": stale,
            "cases": cases,
        }

    requirement_by_id = {req.id: req for req in requirements}
    for req in requirements:
        group_key = req.id
        seen_groups.add(group_key)
        rows.append(build_row(req.external_key, req.title, req.external_source, req.url, req.source_updated_at, grouped.get(group_key, [])))

    for group_key, req_links in grouped.items():
        if group_key in seen_groups:
            continue
        first = req_links[0]
        requirement = requirement_by_id.get(first.requirement_id or "")
        if requirement is not None:
            continue
        rows.append(
            build_row(
                first.external_key,
                first.title_snapshot,
                first.external_source,
                first.url,
                first.source_updated_at,
                req_links,
            )
        )

    return rows


def list_requirement_links(db: Session, project_id: str, case_id: str | None = None) -> list[RequirementLink]:
    project_id = resolve_project_id(db, project_id)
    stmt = select(RequirementLink).where(RequirementLink.project_id == project_id)
    if case_id:
        stmt = stmt.where(RequirementLink.case_id == case_id)
    return list(db.scalars(stmt.order_by(RequirementLink.external_source, RequirementLink.external_key)).all())


def create_requirement_link(db: Session, project_id: str, payload: RequirementLinkCreate, user: Any | None) -> RequirementLink:
    project_id = resolve_project_id(db, project_id)
    get_case(db, project_id, payload.case_id)
    data = payload.model_dump()
    requirement_id = data.get("requirement_id")
    if requirement_id:
        requirement = db.get(Requirement, requirement_id)
        if requirement is None or requirement.project_id != project_id:
            raise KeyError("Requirement not found")
        data.update(
            external_source=requirement.external_source,
            external_key=requirement.external_key,
            title_snapshot=requirement.title,
            url=requirement.url,
            source_updated_at=requirement.source_updated_at,
        )
    else:
        requirement = _find_requirement(db, project_id, data["external_source"], data["external_key"])
        if requirement is None:
            requirement = Requirement(
                project_id=project_id,
                external_source=data["external_source"],
                external_key=data["external_key"],
                title=data["title_snapshot"],
                url=data.get("url"),
                source_updated_at=data.get("source_updated_at"),
            )
            db.add(requirement)
            db.flush()
            audit(db, "requirement.created", "requirement", requirement.id, project_id, user, {"source": "link"})
        data["requirement_id"] = requirement.id

    link = RequirementLink(project_id=project_id, **data)
    db.add(link)
    db.flush()
    audit(db, "requirement_link.created", "requirement_link", link.id, project_id, user)
    db.commit()
    db.refresh(link)
    return link


def list_defect_links(db: Session, project_id: str) -> list[DefectLink]:
    project_id = resolve_project_id(db, project_id)
    stmt = (
        select(DefectLink)
        .join(TestRunCase, DefectLink.run_case_id == TestRunCase.id)
        .join(TestCase, TestRunCase.case_id == TestCase.id)
        .where(TestCase.project_id == project_id)
        .order_by(DefectLink.created_at.desc())
    )
    return list(db.scalars(stmt).all())


def create_defect_link(db: Session, project_id: str, payload: DefectLinkCreate, user: Any | None) -> DefectLink:
    project_id = resolve_project_id(db, project_id)
    run_case = db.get(TestRunCase, payload.run_case_id)
    if run_case is None or run_case.case.project_id != project_id:
        raise KeyError("Run case bulunamadı")
    link = DefectLink(**payload.model_dump())
    db.add(link)
    db.flush()
    audit(db, "defect_link.created", "defect_link", link.id, project_id, user)
    db.commit()
    db.refresh(link)
    return link


def update_defect_link(db: Session, project_id: str, defect_id: str, payload: DefectLinkUpdate, user: Any | None) -> DefectLink:
    project_id = resolve_project_id(db, project_id)
    defect = db.get(DefectLink, defect_id)
    if defect is None:
        raise KeyError("Defect bağlantısı bulunamadı")
    run_case = db.get(TestRunCase, defect.run_case_id)
    if run_case is None or run_case.case.project_id != project_id:
        raise KeyError("Defect bağlantısı bulunamadı")
    changed: list[str] = []
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(defect, key, value)
        changed.append(key)
    if "status" in changed:
        normalized = defect.status.strip().lower()
        if normalized in {"resolved", "fixed"} and defect.resolved_at is None:
            defect.resolved_at = utcnow()
            defect.retest_status = "ready"
        if normalized in {"closed", "done", "verified"} and defect.verified_at is None:
            defect.verified_at = utcnow()
            defect.retest_status = "passed"
        if normalized in {"blocked", "reopened"}:
            defect.retest_status = "blocked"
    if changed:
        audit(db, "defect_link.updated", "defect_link", defect.id, project_id, user, {"changed_fields": changed})
    db.commit()
    db.refresh(defect)
    return defect


def _evidence_out(evidence: ExecutionEvidence) -> dict[str, Any]:
    return {
        "id": evidence.id,
        "run_case_id": evidence.run_case_id,
        "step_result_id": evidence.step_result_id,
        "filename": evidence.file_name,
        "content_type": evidence.file_type,
        "url": evidence.storage_url or "",
        "uploaded_at": evidence.uploaded_at.isoformat(),
    }


def list_evidence(db: Session, project_id: str, run_id: str, run_case_id: str) -> list[dict[str, Any]]:
    project_id = resolve_project_id(db, project_id)
    run_case = db.get(TestRunCase, run_case_id)
    if run_case is None or run_case.run_id != run_id or run_case.case.project_id != project_id:
        raise KeyError("Run case bulunamadı")
    return [
        _evidence_out(evidence)
        for evidence in db.scalars(
            select(ExecutionEvidence)
            .where(ExecutionEvidence.run_case_id == run_case_id)
            .order_by(ExecutionEvidence.uploaded_at.desc())
        ).all()
    ]


def create_import_job(db: Session, project_id: str, payload: TestImportJobCreate, user: Any | None) -> TestImportJob:
    project_id = resolve_project_id(db, project_id)
    existing_case_keys = {
        str(key).strip().lower()
        for key in db.scalars(select(TestCase.case_key).where(TestCase.project_id == project_id)).all()
        if str(key).strip()
    }
    existing_titles = {
        str(title).strip().lower()
        for title in db.scalars(select(TestCase.title).where(TestCase.project_id == project_id)).all()
        if str(title).strip()
    }
    staged_case_keys: set[str] = set()
    totals = {"rows": len(payload.rows), "ready": 0, "invalid": 0, "conflict": 0, "duplicate_candidate": 0}
    job = TestImportJob(
        project_id=project_id,
        filename=payload.filename,
        mapping=payload.mapping,
        totals=totals,
        created_by=_actor_id(user),
    )
    for index, row in enumerate(payload.rows, start=1):
        title = str(row.get("title") or row.get("name") or "").strip()
        case_key = str(row.get("case_key") or "").strip()
        normalized_key = case_key.lower()
        normalized_title = title.lower()
        errors: list[dict[str, Any]] = []
        status_value = "ready"
        conflict_key: str | None = None

        if not title:
            errors.append({"field": "title", "message": "Başlık zorunlu"})
            status_value = "invalid"
        elif normalized_key and (normalized_key in existing_case_keys or normalized_key in staged_case_keys):
            errors.append({"field": "case_key", "message": "Bu case key zaten kullanılıyor"})
            status_value = "conflict"
            conflict_key = case_key
        elif normalized_title in existing_titles:
            errors.append({"field": "title", "message": "Aynı başlıkta bir test case olabilir"})
            status_value = "duplicate_candidate"
            conflict_key = title

        if normalized_key:
            staged_case_keys.add(normalized_key)
        totals[status_value] = totals.get(status_value, 0) + 1
        job.rows.append(
            TestImportJobRow(
                row_no=index,
                parsed_data=row,
                status=status_value,
                validation_errors=errors,
                conflict_key=conflict_key,
            )
        )
    db.add(job)
    db.flush()
    audit(db, "import_job.preview_created", "import_job", job.id, project_id, user, job.totals)
    db.commit()
    db.refresh(job)
    return job


def list_import_jobs(db: Session, project_id: str) -> list[TestImportJob]:
    """Return all import jobs for the project, newest first."""
    project_id = resolve_project_id(db, project_id)
    return list(
        db.scalars(
            select(TestImportJob)
            .where(TestImportJob.project_id == project_id)
            .order_by(TestImportJob.created_at.desc())
        ).all()
    )


def get_import_job(db: Session, project_id: str, job_id: str) -> TestImportJob:
    """Return a single import job with rows (for preview/conflict screen)."""
    project_id = resolve_project_id(db, project_id)
    job = db.get(TestImportJob, job_id)
    if job is None or job.project_id != project_id:
        raise KeyError("Import job bulunamadı")
    return job


def commit_import_job(db: Session, project_id: str, job_id: str, user: Any | None) -> TestImportJob:
    """Commit a staged import job — write 'ready' rows as new TestCases."""
    project_id = resolve_project_id(db, project_id)
    job = get_import_job(db, project_id, job_id)
    if job.status != "preview":
        raise ValueError(f"Import job zaten '{job.status}' durumunda — commit edilemez")

    project = get_project(db, project_id)
    created = 0
    for row in job.rows:
        if row.status not in ("ready", "new"):
            continue
        data = row.parsed_data or {}
        title = data.get("title") or data.get("name") or f"Imported case {row.row_no}"
        explicit_case_key = str(data.get("case_key") or "").strip()
        if explicit_case_key:
            existing_case = db.scalar(
                select(TestCase.id).where(TestCase.project_id == project_id, TestCase.case_key == explicit_case_key)
            )
            if existing_case is not None:
                row.status = "conflict"
                row.conflict_key = explicit_case_key
                row.validation_errors = [
                    *list(row.validation_errors or []),
                    {"field": "case_key", "message": "Commit sırasında case key çakışması bulundu"},
                ]
                continue
        raw_steps = data.get("steps") if isinstance(data.get("steps"), list) else []
        tc = TestCase(
            project_id=project_id,
            title=title,
            case_key=explicit_case_key or _next_case_key(db, project),
            priority=data.get("priority", "P2"),
            severity=data.get("severity", "medium"),
            type=data.get("type", "manual"),
            status=data.get("status", "active"),
            source_type="import",
            source_ref=job.id,
            created_by=_actor_id(user),
            updated_by=_actor_id(user),
        )
        for idx, step in enumerate(raw_steps, start=1):
            if not isinstance(step, dict):
                continue
            action = str(step.get("action") or step.get("step") or "").strip()
            expected = str(step.get("expected_result") or step.get("expected") or "").strip()
            if not action or not expected:
                continue
            tc.steps.append(
                TestCaseStep(
                    step_no=int(step.get("step_no") or idx),
                    action=action,
                    expected_result=expected,
                    test_data=step.get("test_data") if isinstance(step.get("test_data"), dict) else {},
                    notes=step.get("notes"),
                )
            )
        db.add(tc)
        db.flush()
        _add_version(db, tc, user, "Imported", ["import"])
        created += 1

    job.status = "committed"
    job.totals = {**job.totals, "committed": created}
    db.flush()
    audit(db, "import_job.committed", "import_job", job.id, project_id, user, {"created": created})
    db.commit()
    db.refresh(job)
    return job


def upload_evidence(
    db: Session,
    project_id: str,
    run_id: str,
    run_case_id: str,
    filename: str,
    content_type: str,
    content: bytes,
    user: Any | None = None,
) -> dict[str, Any]:
    """Store evidence bytes on disk and return a reference dict."""
    project_id = resolve_project_id(db, project_id)
    import os
    storage_dir = os.environ.get("EVIDENCE_STORAGE_DIR", "reports/evidence")
    run_case = db.get(TestRunCase, run_case_id)
    if run_case is None:
        raise KeyError("Run case bulunamadı")
    if run_case.case.project_id != project_id or run_case.run_id != run_id:
        raise KeyError("Run case bulunamadı")

    # Write to disk.
    import uuid as _uuid_module
    artifact_id = str(_uuid_module.uuid4())
    dest_dir = Path(storage_dir) / project_id / run_case_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{artifact_id}_{filename}"
    dest.write_bytes(content)
    evidence = ExecutionEvidence(
        run_case_id=run_case_id,
        file_name=filename,
        file_type=content_type,
        storage_url=str(dest),
        uploaded_by=_actor_id(user),
    )
    db.add(evidence)
    db.flush()
    db.commit()
    db.refresh(evidence)

    return _evidence_out(evidence)
