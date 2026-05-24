"""Service layer for Neurex Management."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.domains.test_management.models import (
    DEFAULT_TENANT_ID,
    DefectLink,
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
    ExecutionSummaryOut,
    ManagementProjectCreate,
    RequirementLinkCreate,
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
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Management projesi bulunamadı")
    return project


def create_project(db: Session, payload: ManagementProjectCreate, user: Any | None) -> TestManagementProject:
    key = payload.key.upper()
    existing = db.scalar(
        select(TestManagementProject).where(
            TestManagementProject.tenant_id == DEFAULT_TENANT_ID,
            TestManagementProject.key == key,
        )
    )
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Management proje anahtarı zaten kullanılıyor")
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


def _ensure_suite(db: Session, project_id: str, suite_id: str | None) -> TestSuite | None:
    if suite_id is None:
        return None
    suite = db.get(TestSuite, suite_id)
    if suite is None or suite.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Suite bulunamadı")
    return suite


def _ensure_folder(db: Session, project_id: str, folder_id: str | None) -> TestFolder | None:
    if folder_id is None:
        return None
    folder = db.get(TestFolder, folder_id)
    if folder is None or folder.suite.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Folder bulunamadı")
    return folder


def create_suite(db: Session, project_id: str, payload: TestSuiteCreate, user: Any | None) -> TestSuite:
    get_project(db, project_id)
    suite = TestSuite(project_id=project_id, name=payload.name, description=payload.description, order_index=payload.order_index)
    db.add(suite)
    db.flush()
    audit(db, "suite.created", "suite", suite.id, project_id, user)
    db.commit()
    db.refresh(suite)
    return suite


def create_folder(db: Session, project_id: str, payload: TestFolderCreate, user: Any | None) -> TestFolder:
    _ensure_suite(db, project_id, payload.suite_id)
    if payload.parent_id is not None:
        parent = _ensure_folder(db, project_id, payload.parent_id)
        if parent is not None and parent.suite_id != payload.suite_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Parent folder aynı suite içinde olmalı")
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
    _ensure_suite(db, project_id, payload.suite_id)
    folder = _ensure_folder(db, project_id, payload.folder_id)
    if folder is not None and payload.suite_id is not None and folder.suite_id != payload.suite_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Case folder ve suite aynı hiyerarşide olmalı")
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
    case = db.scalar(
        select(TestCase)
        .options(selectinload(TestCase.steps))
        .where(TestCase.project_id == project_id, TestCase.id == case_id)
    )
    if case is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Test case bulunamadı")
    return case


def list_cases(db: Session, project_id: str, q: str | None = None, include_archived: bool = False) -> list[TestCase]:
    stmt = select(TestCase).options(selectinload(TestCase.steps)).where(TestCase.project_id == project_id)
    if not include_archived:
        stmt = stmt.where(TestCase.archived.is_(False))
    if q:
        like = f"%{q}%"
        stmt = stmt.where(TestCase.title.ilike(like) | TestCase.case_key.ilike(like))
    return list(db.scalars(stmt.order_by(TestCase.created_at.desc())).all())


def repository(db: Session, project_id: str) -> dict[str, Any]:
    get_project(db, project_id)
    suites = list(db.scalars(select(TestSuite).where(TestSuite.project_id == project_id).order_by(TestSuite.order_index, TestSuite.name)).all())
    suite_ids = [s.id for s in suites]
    folders = list(db.scalars(select(TestFolder).where(TestFolder.suite_id.in_(suite_ids)).order_by(TestFolder.path)).all()) if suite_ids else []
    cases = list_cases(db, project_id)
    return {"suites": suites, "folders": folders, "cases": cases}


def update_case(db: Session, project_id: str, case_id: str, payload: TestCaseUpdate, user: Any | None) -> TestCase:
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
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Case folder ve suite aynı hiyerarşide olmalı")
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
    get_project(db, project_id)
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


def create_cycle(db: Session, project_id: str, payload: TestCycleCreate, user: Any | None) -> TestCycle:
    plan = db.get(TestPlan, payload.plan_id)
    if plan is None or plan.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Test plan bulunamadı")
    cycle = TestCycle(plan_id=payload.plan_id, name=payload.name, environment=payload.environment, build_version=payload.build_version)
    db.add(cycle)
    db.flush()
    audit(db, "cycle.created", "cycle", cycle.id, project_id, user)
    db.commit()
    db.refresh(cycle)
    return cycle


def get_run(db: Session, project_id: str, run_id: str) -> TestRun:
    """Return a single run with nested run_cases and step_results."""
    run = db.get(TestRun, run_id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Test run bulunamadı")
    # Verify project ownership through cycle→plan.
    if run.cycle.plan.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Test run bulunamadı")
    return run


def list_runs(db: Session, project_id: str, status_filter: str | None = None) -> list[TestRun]:
    """Return all runs for a project, optionally filtered by status."""
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
    cycle = db.get(TestCycle, payload.cycle_id)
    if cycle is None or cycle.plan.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Test cycle bulunamadı")
    run = TestRun(cycle_id=payload.cycle_id, name=payload.name)
    db.add(run)
    db.flush()
    for case_id in payload.case_ids:
        case = get_case(db, project_id, case_id)
        db.add(
            TestRunCase(
                run_id=run.id,
                case_id=case.id,
                case_version_no=case.current_version,
                assigned_to=payload.assigned_to,
            )
        )
    audit(db, "run.created", "run", run.id, project_id, user, {"case_count": len(payload.case_ids)})
    db.commit()
    db.refresh(run)
    return run


def update_step_result(db: Session, project_id: str, run_case_id: str, step_no: int, payload: StepResultUpdate, user: Any | None) -> TestRunCase:
    run_case = db.get(TestRunCase, run_case_id)
    if run_case is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run case bulunamadı")
    # Project guard through case.
    if run_case.case.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run case bulunamadı")
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
    audit(db, "run_case.step_updated", "run_case", run_case.id, project_id, user, {"step_no": step_no, "status": payload.status})
    db.commit()
    db.refresh(run_case)
    return run_case


def execution_summary(db: Session, project_id: str) -> ExecutionSummaryOut:
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


def export_repository(db: Session, project_id: str) -> dict[str, Any]:
    """Return a portable JSON snapshot for backup or import into another environment."""
    repo = repository(db, project_id)
    requirement_links = list(
        db.scalars(
            select(RequirementLink)
            .where(RequirementLink.project_id == project_id)
            .order_by(RequirementLink.external_source, RequirementLink.external_key)
        ).all()
    )
    return {
        "schema_version": "test-management.v1",
        "project_id": project_id,
        "exported_at": utcnow().isoformat(),
        "suites": repo["suites"],
        "folders": repo["folders"],
        "cases": repo["cases"],
        "requirement_links": requirement_links,
    }


def list_requirement_links(db: Session, project_id: str, case_id: str | None = None) -> list[RequirementLink]:
    get_project(db, project_id)
    stmt = select(RequirementLink).where(RequirementLink.project_id == project_id)
    if case_id:
        stmt = stmt.where(RequirementLink.case_id == case_id)
    return list(db.scalars(stmt.order_by(RequirementLink.external_source, RequirementLink.external_key)).all())


def create_requirement_link(db: Session, project_id: str, payload: RequirementLinkCreate, user: Any | None) -> RequirementLink:
    get_case(db, project_id, payload.case_id)
    link = RequirementLink(project_id=project_id, **payload.model_dump())
    db.add(link)
    db.flush()
    audit(db, "requirement_link.created", "requirement_link", link.id, project_id, user)
    db.commit()
    db.refresh(link)
    return link


def list_defect_links(db: Session, project_id: str) -> list[DefectLink]:
    get_project(db, project_id)
    stmt = (
        select(DefectLink)
        .join(TestRunCase, DefectLink.run_case_id == TestRunCase.id)
        .join(TestCase, TestRunCase.case_id == TestCase.id)
        .where(TestCase.project_id == project_id)
        .order_by(DefectLink.created_at.desc())
    )
    return list(db.scalars(stmt).all())


def create_defect_link(db: Session, project_id: str, payload: DefectLinkCreate, user: Any | None) -> DefectLink:
    run_case = db.get(TestRunCase, payload.run_case_id)
    if run_case is None or run_case.case.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run case bulunamadı")
    link = DefectLink(**payload.model_dump())
    db.add(link)
    db.flush()
    audit(db, "defect_link.created", "defect_link", link.id, project_id, user)
    db.commit()
    db.refresh(link)
    return link


def create_import_job(db: Session, project_id: str, payload: TestImportJobCreate, user: Any | None) -> TestImportJob:
    get_project(db, project_id)
    job = TestImportJob(
        project_id=project_id,
        filename=payload.filename,
        mapping=payload.mapping,
        totals={"rows": len(payload.rows), "ready": len(payload.rows), "errors": 0},
        created_by=_actor_id(user),
    )
    for index, row in enumerate(payload.rows, start=1):
        job.rows.append(TestImportJobRow(row_no=index, parsed_data=row, status="ready"))
    db.add(job)
    db.flush()
    audit(db, "import_job.preview_created", "import_job", job.id, project_id, user, job.totals)
    db.commit()
    db.refresh(job)
    return job


def list_import_jobs(db: Session, project_id: str) -> list[TestImportJob]:
    """Return all import jobs for the project, newest first."""
    get_project(db, project_id)
    return list(
        db.scalars(
            select(TestImportJob)
            .where(TestImportJob.project_id == project_id)
            .order_by(TestImportJob.created_at.desc())
        ).all()
    )


def get_import_job(db: Session, project_id: str, job_id: str) -> TestImportJob:
    """Return a single import job with rows (for preview/conflict screen)."""
    job = db.get(TestImportJob, job_id)
    if job is None or job.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Import job bulunamadı")
    return job


def commit_import_job(db: Session, project_id: str, job_id: str, user: Any | None) -> TestImportJob:
    """Commit a staged import job — write 'ready' rows as new TestCases."""
    job = get_import_job(db, project_id, job_id)
    if job.status != "preview":
        raise HTTPException(status.HTTP_409_CONFLICT, f"Import job zaten '{job.status}' durumunda — commit edilemez")

    created = 0
    for row in job.rows:
        if row.status not in ("ready", "new"):
            continue
        data = row.parsed_data or {}
        title = data.get("title") or data.get("name") or f"Imported case {row.row_no}"
        tc = TestCase(
            project_id=project_id,
            title=title,
            case_key=data.get("case_key") or None,
            priority=data.get("priority", "P2"),
            severity=data.get("severity", "medium"),
            type=data.get("type", "manual"),
            status=data.get("status", "active"),
            source_type="import",
            source_ref=job.id,
        )
        db.add(tc)
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
    run_case_id: str,
    filename: str,
    content_type: str,
    content: bytes,
) -> dict[str, Any]:
    """Store evidence bytes on disk and return a reference dict."""
    import os
    storage_dir = os.environ.get("EVIDENCE_STORAGE_DIR", "reports/evidence")
    run_case = db.get(TestRunCase, run_case_id)
    if run_case is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run case bulunamadı")
    if run_case.case.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run case bulunamadı")

    # Write to disk.
    import uuid as _uuid_module
    artifact_id = str(_uuid_module.uuid4())
    dest_dir = Path(storage_dir) / project_id / run_case_id
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{artifact_id}_{filename}"
    dest.write_bytes(content)

    return {
        "id": artifact_id,
        "run_case_id": run_case_id,
        "filename": filename,
        "content_type": content_type,
        "url": f"/evidence/{project_id}/{run_case_id}/{artifact_id}_{filename}",
        "uploaded_at": utcnow().isoformat(),
    }
