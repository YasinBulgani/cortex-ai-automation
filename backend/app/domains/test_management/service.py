"""Service layer for Neurex Management.

HTTP-agnostic: raises ValueError (400 Bad Request) or KeyError (404 Not Found)
instead of HTTPException so the service layer is framework-independent.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import datetime, timezone as _tz
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.domains.test_management.models import (
    DEFAULT_TENANT_ID,
    DefectLink,
    ExecutionEvidence,
    ExplorationSession,
    RegressionSet,
    RegressionSetCase,
    ReleaseSignoff,
    Requirement,
    RequirementLink,
    SharedStep,
    TestCase,
    TestCaseDependency,
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
    GeneratedCaseOut,
    GeneratedStepOut,
    ManagementProjectCreate,
    RegressionCandidateOut,
    RegressionSelectionFilter,
    RegressionSetCaseIn,
    RegressionSetCreate,
    ReleaseReportOut,
    ReleaseSignoffCreate,
    RequirementCreate,
    RequirementLinkCreate,
    RequirementLinkOut,
    RequirementOut,
    RequirementUpdate,
    StandupAnomaly,
    TestCaseOut,
    TestFolderOut,
    TestSuiteOut,
    StandupOut,
    StepResultUpdate,
    TestCaseCloneRequest,
    TestCaseCreate,
    TestCaseGenerateRequest,
    TestCaseImproveRequest,
    TestCaseImproveResponse,
    TestCaseUpdate,
    TestCycleCreate,
    TestFolderCreate,
    TestFolderUpdate,
    TestImportJobCreate,
    TestPlanAIGenerateRequest,
    TestPlanAIGenerateResponse,
    TestPlanCreate,
    TestPlanUpdate,
    TestCycleUpdate,
    TestRunCreate,
    TestRunUpdate,
    TestSuiteCreate,
    TestSuiteUpdate,
    RequirementLinkUpdate,
    SharedStepCreate,
    SharedStepUpdate,
)
from app.domains.tspm.models import TspmProject
from app.infra.otel_decorators import otel_span


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


def list_projects(db: Session, user: Any | None = None) -> list[TestManagementProject]:
    q = select(TestManagementProject).order_by(TestManagementProject.created_at.desc())
    if user is not None and hasattr(user, "tenant_id") and user.tenant_id:
        q = q.where(TestManagementProject.tenant_id == str(user.tenant_id))
    return list(db.scalars(q).all())


def update_management_user_settings(db: Session, project_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    """Proje bazında özelleştirilebilir ayarları güncelle ve kaydet."""
    project_id = resolve_project_id(db, project_id)
    project = db.scalars(
        select(TestManagementProject).where(TestManagementProject.id == project_id)
    ).first()
    if not project:
        raise ValueError(f"Management project not found: {project_id}")

    current: dict[str, Any] = project.settings_data or {}
    # Sadece None olmayan değerleri güncelle
    merged = {**current, **{k: v for k, v in updates.items() if v is not None}}
    project.settings_data = merged
    db.commit()
    return merged


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
    # Kullanıcı ayarlarını da al
    project = db.scalars(
        select(TestManagementProject).where(TestManagementProject.id == project_id)
    ).first()
    user_settings: dict[str, Any] = (project.settings_data or {}) if project else {}

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
        "user_settings": user_settings,
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


def update_suite(db: Session, project_id: str, suite_id: str, payload: TestSuiteUpdate, user: Any | None) -> TestSuite:
    project_id = resolve_project_id(db, project_id)
    suite = _ensure_suite(db, project_id, suite_id)
    assert suite is not None  # _ensure_suite raises KeyError when missing
    data = payload.model_dump(exclude_unset=True)
    for field in ("name", "description", "order_index", "status"):
        if field in data and data[field] is not None:
            setattr(suite, field, data[field])
    audit(db, "suite.updated", "suite", suite.id, project_id, user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("Bu isimde bir suite zaten var") from exc
    db.refresh(suite)
    return suite


def delete_suite(db: Session, project_id: str, suite_id: str, user: Any | None) -> None:
    project_id = resolve_project_id(db, project_id)
    suite = _ensure_suite(db, project_id, suite_id)
    assert suite is not None  # _ensure_suite raises KeyError when missing
    # Folders cascade-delete; cases detach to "unassigned" via FK ON DELETE SET NULL.
    db.delete(suite)
    audit(db, "suite.deleted", "suite", suite_id, project_id, user)
    db.commit()


def _would_create_cycle(db: Session, folder_id: str, new_parent_id: str) -> bool:
    """new_parent_id'nin ataları arasında folder_id var mı?"""
    current_id = new_parent_id
    visited: set[str] = set()
    while current_id:
        if current_id == folder_id:
            return True
        if current_id in visited:
            break
        visited.add(current_id)
        parent_folder = db.get(TestFolder, current_id)
        current_id = parent_folder.parent_id if parent_folder else None
    return False


def update_folder(db: Session, project_id: str, folder_id: str, payload: TestFolderUpdate, user: Any | None) -> TestFolder:
    project_id = resolve_project_id(db, project_id)
    folder = _ensure_folder(db, project_id, folder_id)
    assert folder is not None  # _ensure_folder raises KeyError when missing
    data = payload.model_dump(exclude_unset=True)
    if "parent_id" in data:
        new_parent_id = data["parent_id"]
        if new_parent_id == folder.id:
            raise ValueError("Folder kendi kendisinin parent'ı olamaz")
        if new_parent_id is not None and _would_create_cycle(db, folder.id, new_parent_id):
            raise ValueError("Bu taşıma döngüsel bir folder yapısı oluştururdu")
        if new_parent_id is not None:
            parent = _ensure_folder(db, project_id, new_parent_id)
            if parent is not None and parent.suite_id != folder.suite_id:
                raise ValueError("Parent folder aynı suite içinde olmalı")
        folder.parent_id = new_parent_id
    if "suite_id" in data and data["suite_id"] is not None:
        _ensure_suite(db, project_id, data["suite_id"])
        folder.suite_id = data["suite_id"]
        folder.parent_id = None  # taşıma kök seviyeye alır
    for field in ("name", "path", "order_index"):
        if field in data and data[field] is not None:
            setattr(folder, field, data[field])
    audit(db, "folder.updated", "folder", folder.id, project_id, user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("Bu yolda bir folder zaten var") from exc
    db.refresh(folder)
    return folder


def delete_folder(db: Session, project_id: str, folder_id: str, user: Any | None) -> None:
    project_id = resolve_project_id(db, project_id)
    folder = _ensure_folder(db, project_id, folder_id)
    assert folder is not None  # _ensure_folder raises KeyError when missing
    # Child folders cascade-delete (parent_id ON DELETE CASCADE); cases detach via folder_id SET NULL.
    db.delete(folder)
    audit(db, "folder.deleted", "folder", folder_id, project_id, user)
    db.commit()


def _next_case_key(db: Session, project: TestManagementProject) -> str:
    # Derive from the highest existing numeric suffix (not the count) so deleting a
    # case never causes a key collision → unique-constraint 500 on the next create.
    prefix = f"{project.key}-TC-"
    keys = db.scalars(
        select(TestCase.case_key).where(
            TestCase.project_id == project.id,
            TestCase.case_key.like(f"{prefix}%"),
        )
    ).all()
    max_n = 1000
    for k in keys:
        suffix = (k or "").rsplit("-", 1)[-1]
        if suffix.isdigit():
            max_n = max(max_n, int(suffix))
    return f"{prefix}{max_n + 1}"


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


@otel_span("test_mgmt.get_case", sample=0.2)
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


@otel_span("test_mgmt.list_cases", sample=0.1)
def list_cases(
    db: Session,
    project_id: str,
    q: str | None = None,
    include_archived: bool = False,
    limit: int | None = None,
    offset: int = 0,
    priority: str | None = None,
    status: str | None = None,
    automation_status: str | None = None,
    suite_id: str | None = None,
    folder_id: str | None = None,
    owner_id: str | None = None,
) -> list[TestCase]:
    project_id = resolve_project_id(db, project_id)
    stmt = select(TestCase).options(selectinload(TestCase.steps)).where(TestCase.project_id == project_id)
    if not include_archived:
        stmt = stmt.where(TestCase.archived.is_(False))
    if q:
        like = f"%{q}%"
        stmt = stmt.where(TestCase.title.ilike(like) | TestCase.case_key.ilike(like))
    if priority:
        stmt = stmt.where(TestCase.priority == priority)
    if status:
        stmt = stmt.where(TestCase.status == status)
    if automation_status:
        stmt = stmt.where(TestCase.automation_status == automation_status)
    if suite_id:
        stmt = stmt.where(TestCase.suite_id == suite_id)
    if folder_id:
        stmt = stmt.where(TestCase.folder_id == folder_id)
    if owner_id:
        stmt = stmt.where(TestCase.owner_id == owner_id)
    stmt = stmt.order_by(TestCase.created_at.desc())
    if offset:
        stmt = stmt.offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)
    return list(db.scalars(stmt).all())


@otel_span("test_mgmt.count_cases", sample=0.1)
def count_cases(
    db: Session,
    project_id: str,
    q: str | None = None,
    include_archived: bool = False,
    priority: str | None = None,
    status: str | None = None,
    automation_status: str | None = None,
    suite_id: str | None = None,
    folder_id: str | None = None,
    owner_id: str | None = None,
) -> int:
    """Return total count of test cases matching the given filters (no pagination)."""
    from sqlalchemy import func as _func

    project_id = resolve_project_id(db, project_id)
    stmt = select(_func.count()).select_from(TestCase).where(TestCase.project_id == project_id)
    if not include_archived:
        stmt = stmt.where(TestCase.archived.is_(False))
    if q:
        like = f"%{q}%"
        stmt = stmt.where(TestCase.title.ilike(like) | TestCase.case_key.ilike(like))
    if priority:
        stmt = stmt.where(TestCase.priority == priority)
    if status:
        stmt = stmt.where(TestCase.status == status)
    if automation_status:
        stmt = stmt.where(TestCase.automation_status == automation_status)
    if suite_id:
        stmt = stmt.where(TestCase.suite_id == suite_id)
    if folder_id:
        stmt = stmt.where(TestCase.folder_id == folder_id)
    if owner_id:
        stmt = stmt.where(TestCase.owner_id == owner_id)
    return db.scalar(stmt) or 0


def list_sub_cases(db: Session, project_id: str, parent_id: str) -> list[TestCase]:
    """List all direct sub-cases of a parent case."""
    project_id = resolve_project_id(db, project_id)
    # Verify parent exists and belongs to project
    get_case(db, project_id, parent_id)
    return list(db.scalars(
        select(TestCase)
        .options(selectinload(TestCase.steps))
        .where(TestCase.project_id == project_id, TestCase.parent_id == parent_id, TestCase.archived.is_(False))
        .order_by(TestCase.created_at.asc())
    ).all())


def create_sub_case(db: Session, project_id: str, parent_id: str, payload: TestCaseCreate, user: Any | None) -> TestCase:
    """Create a sub-case under a parent case, inheriting suite/folder."""
    parent = get_case(db, project_id, parent_id)
    # Inherit suite/folder from parent unless overridden
    if payload.suite_id is None:
        payload = payload.model_copy(update={"suite_id": parent.suite_id})
    if payload.folder_id is None:
        payload = payload.model_copy(update={"folder_id": parent.folder_id})
    case = create_case(db, project_id, payload, user)
    # Set parent_id after creation
    case_obj = db.get(TestCase, case.id)
    if case_obj:
        case_obj.parent_id = parent_id
        db.commit()
        db.refresh(case_obj)
    audit(db, "case.sub_case_created", "case", case.id, project_id, user, {"parent_id": parent_id})
    return case


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


def ai_generate_plan(
    db: Session,
    project_id: str,
    payload: TestPlanAIGenerateRequest,
    user: Any | None = None,
) -> TestPlanAIGenerateResponse:
    """AI ile test planı adı, özeti ve scope önerileri üretir."""
    from app.domains.ai import service as ai_svc

    project_id = resolve_project_id(db, project_id)
    suites = list(db.scalars(select(TestSuite).where(TestSuite.project_id == project_id)).all())
    suite_names = ", ".join(s.name for s in suites[:20]) or "Henüz suite yok"

    prompt = (
        f"Release adı: {payload.release_name}\n"
        f"Hedef: {payload.goal or 'Belirtilmemiş'}\n"
        f"Plan türü: {payload.plan_type}\n"
        f"Mevcut suite'ler: {suite_names}\n\n"
        "Bu release için test planı oluştur. JSON formatında yanıt ver:\n"
        '{"name": "plan adı", "scope_summary": "kapsamlı özet", '
        '"suggested_suite_ids": [], "suggestions": ["öneri1", "öneri2"]}'
    )

    try:
        raw = ai_svc.call_llm(
            "Sen kıdemli bir QA yöneticisisin. Test planları oluştur. JSON döndür.",
            prompt,
            json_mode=True,
            _trace_project_id=project_id,
            _trace_user_id=_actor_id(user),
            _trace_task_type="plan_generation",
        )
        data = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        data = {}

    return TestPlanAIGenerateResponse(
        name=data.get("name") or f"{payload.release_name} Test Planı",
        scope_summary=data.get("scope_summary") or f"{payload.release_name} için test kapsamı",
        suggested_suite_ids=data.get("suggested_suite_ids") or [],
        suggestions=data.get("suggestions") or [],
    )


async def ai_generate_plan_async(
    db: Session,
    project_id: str,
    payload: TestPlanAIGenerateRequest,
    user: Any | None = None,
) -> TestPlanAIGenerateResponse:
    """AI ile test planı adı, özeti ve scope önerileri üretir (async version)."""
    from app.domains.ai import service as ai_svc

    project_id = resolve_project_id(db, project_id)
    suites = list(db.scalars(select(TestSuite).where(TestSuite.project_id == project_id)).all())
    suite_names = ", ".join(s.name for s in suites[:20]) or "Henüz suite yok"

    prompt = (
        f"Release adı: {payload.release_name}\n"
        f"Hedef: {payload.goal or 'Belirtilmemiş'}\n"
        f"Plan türü: {payload.plan_type}\n"
        f"Mevcut suite'ler: {suite_names}\n\n"
        "Bu release için test planı oluştur. JSON formatında yanıt ver:\n"
        '{"name": "plan adı", "scope_summary": "kapsamlı özet", '
        '"suggested_suite_ids": [], "suggestions": ["öneri1", "öneri2"]}'
    )

    try:
        raw = await ai_svc.async_call_llm(
            "Sen kıdemli bir QA yöneticisisin. Test planları oluştur. JSON döndür.",
            prompt,
            json_mode=True,
            _trace_project_id=project_id,
            _trace_user_id=_actor_id(user),
            _trace_task_type="plan_generation",
        )
        data = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        data = {}

    return TestPlanAIGenerateResponse(
        name=data.get("name") or f"{payload.release_name} Test Planı",
        scope_summary=data.get("scope_summary") or f"{payload.release_name} için test kapsamı",
        suggested_suite_ids=data.get("suggested_suite_ids") or [],
        suggestions=data.get("suggestions") or [],
    )


def improve_case(
    db: Session,
    project_id: str,
    case_id: str,
    payload: TestCaseImproveRequest,
    user: Any | None = None,
) -> TestCaseImproveResponse:
    """AI kullanarak mevcut case'i iyileştirir."""
    from app.domains.ai import service as ai_svc

    project_id = resolve_project_id(db, project_id)
    case = get_case(db, project_id, case_id)

    existing_steps = "\n".join(
        f"{s.step_no}. {s.action} → {s.expected_result}"
        for s in sorted(case.steps, key=lambda x: x.step_no)
    ) if case.steps else "Adım yok"

    prompt = (
        f"Mevcut test case:\n"
        f"Başlık: {case.title}\n"
        f"Amaç: {case.objective or '—'}\n"
        f"Ön Koşullar: {case.preconditions or '—'}\n"
        f"Adımlar:\n{existing_steps}\n\n"
        f"Odak: {payload.focus}\n\n"
        "Bu test case'i iyileştir. JSON formatında yanıt ver:\n"
        '{"title": "...", "objective": "...", "preconditions": "...", '
        '"steps": [{"step_no": 1, "action": "...", "expected_result": "...", "is_required": true}], '
        '"suggestions": ["öneri1", "öneri2"]}'
    )

    try:
        raw = ai_svc.call_llm(
            "Sen kıdemli bir QA mühendisisin. Test case'leri iyileştir. JSON döndür.",
            prompt,
            json_mode=True,
            _trace_project_id=project_id,
            _trace_user_id=_actor_id(user),
            _trace_task_type="case_improvement",
        )
        data = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        data = {}

    steps = None
    if "steps" in data and isinstance(data["steps"], list):
        steps = [
            GeneratedStepOut(
                step_no=s.get("step_no", i + 1),
                action=s.get("action", ""),
                expected_result=s.get("expected_result", ""),
                is_required=s.get("is_required", True),
            )
            for i, s in enumerate(data["steps"])
        ]

    return TestCaseImproveResponse(
        title=data.get("title"),
        objective=data.get("objective"),
        preconditions=data.get("preconditions"),
        steps=steps,
        suggestions=data.get("suggestions", []),
    )


async def improve_case_async(
    db: Session,
    project_id: str,
    case_id: str,
    payload: TestCaseImproveRequest,
    user: Any | None = None,
) -> TestCaseImproveResponse:
    """AI kullanarak mevcut case'i iyileştirir (async version)."""
    from app.domains.ai import service as ai_svc

    project_id = resolve_project_id(db, project_id)
    case = get_case(db, project_id, case_id)

    existing_steps = "\n".join(
        f"{s.step_no}. {s.action} → {s.expected_result}"
        for s in sorted(case.steps, key=lambda x: x.step_no)
    ) if case.steps else "Adım yok"

    prompt = (
        f"Mevcut test case:\n"
        f"Başlık: {case.title}\n"
        f"Amaç: {case.objective or '—'}\n"
        f"Ön Koşullar: {case.preconditions or '—'}\n"
        f"Adımlar:\n{existing_steps}\n\n"
        f"Odak: {payload.focus}\n\n"
        "Bu test case'i iyileştir. JSON formatında yanıt ver:\n"
        '{"title": "...", "objective": "...", "preconditions": "...", '
        '"steps": [{"step_no": 1, "action": "...", "expected_result": "...", "is_required": true}], '
        '"suggestions": ["öneri1", "öneri2"]}'
    )

    try:
        raw = await ai_svc.async_call_llm(
            "Sen kıdemli bir QA mühendisisin. Test case'leri iyileştir. JSON döndür.",
            prompt,
            json_mode=True,
            _trace_project_id=project_id,
            _trace_user_id=_actor_id(user),
            _trace_task_type="case_improvement",
        )
        data = json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        data = {}

    steps = None
    if "steps" in data and isinstance(data["steps"], list):
        steps = [
            GeneratedStepOut(
                step_no=s.get("step_no", i + 1),
                action=s.get("action", ""),
                expected_result=s.get("expected_result", ""),
                is_required=s.get("is_required", True),
            )
            for i, s in enumerate(data["steps"])
        ]

    return TestCaseImproveResponse(
        title=data.get("title"),
        objective=data.get("objective"),
        preconditions=data.get("preconditions"),
        steps=steps,
        suggestions=data.get("suggestions", []),
    )


def delete_case(db: Session, project_id: str, case_id: str, user: Any | None) -> None:
    project_id = resolve_project_id(db, project_id)
    case = get_case(db, project_id, case_id)
    audit(db, "case.deleted", "case", case.id, project_id, user)
    db.delete(case)
    db.commit()


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


def update_plan(db: Session, project_id: str, plan_id: str, payload: TestPlanUpdate, user: Any | None) -> TestPlan:
    project_id = resolve_project_id(db, project_id)
    plan = db.scalar(select(TestPlan).where(TestPlan.id == plan_id, TestPlan.project_id == project_id))
    if plan is None:
        raise KeyError("Plan bulunamadı")
    changed: list[str] = []
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(plan, key, value)
        changed.append(key)
    if changed:
        audit(db, "plan.updated", "plan", plan.id, project_id, user, {"changed_fields": changed})
    db.commit()
    db.refresh(plan)
    return plan


def delete_plan(db: Session, project_id: str, plan_id: str, user: Any | None) -> None:
    project_id = resolve_project_id(db, project_id)
    plan = db.scalar(select(TestPlan).where(TestPlan.id == plan_id, TestPlan.project_id == project_id))
    if plan is None:
        raise KeyError("Plan bulunamadı")
    audit(db, "plan.deleted", "plan", plan_id, project_id, user)
    db.delete(plan)
    db.commit()


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


def update_cycle(db: Session, project_id: str, cycle_id: str, payload: TestCycleUpdate, user: Any | None) -> TestCycle:
    project_id = resolve_project_id(db, project_id)
    cycle = db.scalar(
        select(TestCycle)
        .join(TestPlan, TestCycle.plan_id == TestPlan.id)
        .where(TestCycle.id == cycle_id, TestPlan.project_id == project_id)
    )
    if cycle is None:
        raise KeyError("Cycle bulunamadı")
    changed: list[str] = []
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(cycle, key, value)
        changed.append(key)
    if changed:
        audit(db, "cycle.updated", "cycle", cycle.id, project_id, user, {"changed_fields": changed})
    db.commit()
    db.refresh(cycle)
    return cycle


def delete_cycle(db: Session, project_id: str, cycle_id: str, user: Any | None) -> None:
    project_id = resolve_project_id(db, project_id)
    cycle = db.scalar(
        select(TestCycle)
        .join(TestPlan, TestCycle.plan_id == TestPlan.id)
        .where(TestCycle.id == cycle_id, TestPlan.project_id == project_id)
    )
    if cycle is None:
        raise KeyError("Cycle bulunamadı")
    audit(db, "cycle.deleted", "cycle", cycle_id, project_id, user)
    db.delete(cycle)
    db.commit()


def list_cycles(
    db: Session,
    project_id: str,
    plan_id: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[TestCycle]:
    project_id = resolve_project_id(db, project_id)
    stmt = (
        select(TestCycle)
        .join(TestPlan, TestCycle.plan_id == TestPlan.id)
        .where(TestPlan.project_id == project_id)
        .order_by(TestCycle.created_at.desc())
    )
    if plan_id is not None:
        stmt = stmt.where(TestCycle.plan_id == plan_id)
    if offset:
        stmt = stmt.offset(offset)
    if limit is not None:
        stmt = stmt.limit(limit)
    return list(db.scalars(stmt).all())


def count_cycles(
    db: Session,
    project_id: str,
    plan_id: str | None = None,
) -> int:
    """Return total count of test cycles matching the given filters (no pagination)."""
    from sqlalchemy import func as _func

    project_id = resolve_project_id(db, project_id)
    stmt = (
        select(_func.count())
        .select_from(TestCycle)
        .join(TestPlan, TestCycle.plan_id == TestPlan.id)
        .where(TestPlan.project_id == project_id)
    )
    if plan_id is not None:
        stmt = stmt.where(TestCycle.plan_id == plan_id)
    return db.scalar(stmt) or 0


def _compute_risk_score(case_data: dict) -> float:
    score = 0.0
    # Son çalışma başarısız ise yüksek risk
    last_status = case_data.get("last_run_status")
    if last_status == "failed": score += 0.5
    elif last_status == "blocked": score += 0.3
    elif last_status is None: score += 0.2  # hiç test edilmemiş
    # Yüksek öncelikli case
    priority = case_data.get("priority", "P3")
    if priority == "P0": score += 0.3
    elif priority == "P1": score += 0.2
    elif priority == "P2": score += 0.1
    return round(min(score, 1.0), 2)


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
    for candidate in candidates:
        candidate_data = {"last_run_status": candidate.last_run_status, "priority": candidate.priority}
        candidate.risk_score = _compute_risk_score(candidate_data)
    candidates = sorted(candidates, key=lambda x: x.risk_score, reverse=True)
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


def add_cases_to_regression_set(
    db: Session, project_id: str, set_id: str, case_ids: list[str], user: Any | None
) -> dict[str, Any]:
    project_id = resolve_project_id(db, project_id)
    regression_set = db.scalar(
        select(RegressionSet)
        .options(selectinload(RegressionSet.cases).selectinload(RegressionSetCase.case))
        .where(RegressionSet.id == set_id, RegressionSet.project_id == project_id)
    )
    if regression_set is None:
        raise ValueError("Regression set not found")
    existing_ids = {c.case_id for c in regression_set.cases}
    max_order = max((c.order_index for c in regression_set.cases), default=-1)
    for i, cid in enumerate(case_ids):
        if cid in existing_ids:
            continue
        case = get_case(db, project_id, cid)
        if case.archived:
            continue
        regression_set.cases.append(
            RegressionSetCase(
                case_id=cid,
                case_version_no=case.current_version,
                case_key_snapshot=case.case_key,
                title_snapshot=case.title,
                priority_snapshot=case.priority,
                severity_snapshot=case.severity,
                type_snapshot=case.type,
                order_index=max_order + 1 + i,
                risk_score=0,
                reason="Manual selection",
                include_mode="manual",
            )
        )
        existing_ids.add(cid)
    regression_set.selection_summary = {"case_count": len(regression_set.cases)}
    db.flush()
    db.commit()
    regression_set = db.scalar(
        select(RegressionSet)
        .options(selectinload(RegressionSet.cases).selectinload(RegressionSetCase.case))
        .where(RegressionSet.id == set_id)
    )
    return _regression_set_out(regression_set)  # type: ignore[arg-type]


def remove_case_from_regression_set(
    db: Session, project_id: str, set_id: str, case_id: str, user: Any | None
) -> dict[str, Any]:
    project_id = resolve_project_id(db, project_id)
    regression_set = db.scalar(
        select(RegressionSet)
        .options(selectinload(RegressionSet.cases).selectinload(RegressionSetCase.case))
        .where(RegressionSet.id == set_id, RegressionSet.project_id == project_id)
    )
    if regression_set is None:
        raise ValueError("Regression set not found")
    regression_set.cases = [c for c in regression_set.cases if c.case_id != case_id]
    regression_set.selection_summary = {"case_count": len(regression_set.cases)}
    db.flush()
    db.commit()
    regression_set = db.scalar(
        select(RegressionSet)
        .options(selectinload(RegressionSet.cases).selectinload(RegressionSetCase.case))
        .where(RegressionSet.id == set_id)
    )
    return _regression_set_out(regression_set)  # type: ignore[arg-type]


def update_regression_set(
    db: Session, project_id: str, set_id: str, payload: Any, user: Any | None
) -> dict[str, Any]:
    project_id = resolve_project_id(db, project_id)
    regression_set = db.scalar(
        select(RegressionSet)
        .options(selectinload(RegressionSet.cases).selectinload(RegressionSetCase.case))
        .where(RegressionSet.id == set_id, RegressionSet.project_id == project_id)
    )
    if regression_set is None:
        raise ValueError("Regression set not found")
    if payload.name is not None:
        regression_set.name = payload.name
    if payload.set_type is not None:
        regression_set.set_type = payload.set_type
    if payload.description is not None:
        regression_set.description = payload.description
    db.flush()
    db.commit()
    regression_set = db.scalar(
        select(RegressionSet)
        .options(selectinload(RegressionSet.cases).selectinload(RegressionSetCase.case))
        .where(RegressionSet.id == set_id)
    )
    return _regression_set_out(regression_set)  # type: ignore[arg-type]


def delete_regression_set(
    db: Session, project_id: str, set_id: str, user: Any | None
) -> None:
    project_id = resolve_project_id(db, project_id)
    regression_set = db.scalar(
        select(RegressionSet).where(
            RegressionSet.id == set_id, RegressionSet.project_id == project_id
        )
    )
    if regression_set is None:
        raise ValueError("Regression set not found")
    db.delete(regression_set)
    db.commit()


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


def list_runs(db: Session, project_id: str, limit: int = 50, offset: int = 0, cycle_id: Optional[str] = None, status_filter: str | None = None) -> list[TestRun]:
    """Return runs for a project with pagination, optionally filtered by cycle or status.

    Eager loads cycle and plan to prevent N+1 queries.
    """
    project_id = resolve_project_id(db, project_id)
    q = (
        select(TestRun)
        .options(
            selectinload(TestRun.cycle).selectinload(TestCycle.plan),
            selectinload(TestRun.run_cases).selectinload(TestRunCase.step_results),
            selectinload(TestRun.run_cases).selectinload(TestRunCase.case).selectinload(TestCase.steps),
        )
        .join(TestCycle, TestRun.cycle_id == TestCycle.id)
        .join(TestPlan, TestCycle.plan_id == TestPlan.id)
        .where(TestPlan.project_id == project_id)
    )
    if cycle_id:
        q = q.where(TestRun.cycle_id == cycle_id)
    if status_filter:
        q = q.where(TestRun.status == status_filter)
    return list(db.scalars(q.order_by(TestRun.created_at.desc()).limit(limit).offset(offset)).all())


def count_runs(
    db: Session,
    project_id: str,
    cycle_id: Optional[str] = None,
    status_filter: str | None = None,
) -> int:
    """Return total count of runs matching the given filters (no pagination)."""
    from sqlalchemy import func as _func

    project_id = resolve_project_id(db, project_id)
    q = (
        select(_func.count())
        .select_from(TestRun)
        .join(TestCycle, TestRun.cycle_id == TestCycle.id)
        .join(TestPlan, TestCycle.plan_id == TestPlan.id)
        .where(TestPlan.project_id == project_id)
    )
    if cycle_id:
        q = q.where(TestRun.cycle_id == cycle_id)
    if status_filter:
        q = q.where(TestRun.status == status_filter)
    return db.scalar(q) or 0


def compare_runs(db: Session, project_id: str, base_run_id: str, target_run_id: str) -> dict[str, Any]:
    """Diff two runs by matching run-cases on case_id.

    Buckets (from the target run's perspective vs the base run):
      newly_failed  — passed/blocked/etc in base, failed in target  (regressions)
      fixed         — failed in base, passed in target
      still_failing — failed in both
      new_cases     — present in target, absent from base
      removed_cases — present in base, absent from target
    Also returns per-run pass-rate summary.
    """
    base = get_run(db, project_id, base_run_id)
    target = get_run(db, project_id, target_run_id)

    def _index(run: TestRun) -> dict[str, TestRunCase]:
        idx: dict[str, TestRunCase] = {}
        for rc in run.run_cases:
            key = rc.case_id or (rc.case_snapshot or {}).get("case", {}).get("id")
            if key:
                idx[str(key)] = rc
        return idx

    def _meta(rc: TestRunCase) -> dict[str, Any]:
        snap = (rc.case_snapshot or {}).get("case", {}) if rc.case_snapshot else {}
        case = rc.case
        return {
            "case_id": rc.case_id,
            "case_key": (case.case_key if case else None) or snap.get("case_key"),
            "title": (case.title if case else None) or snap.get("title") or "(silinmiş case)",
            "priority": (case.priority if case else None) or snap.get("priority"),
        }

    base_idx = _index(base)
    target_idx = _index(target)

    newly_failed: list[dict[str, Any]] = []
    fixed: list[dict[str, Any]] = []
    still_failing: list[dict[str, Any]] = []
    new_cases: list[dict[str, Any]] = []
    removed_cases: list[dict[str, Any]] = []

    for key, t_rc in target_idx.items():
        b_rc = base_idx.get(key)
        if b_rc is None:
            new_cases.append({**_meta(t_rc), "base_status": None, "target_status": t_rc.status})
            continue
        row = {**_meta(t_rc), "base_status": b_rc.status, "target_status": t_rc.status}
        if t_rc.status == "failed" and b_rc.status != "failed":
            newly_failed.append(row)
        elif t_rc.status != "failed" and b_rc.status == "failed":
            if t_rc.status in ("passed",):
                fixed.append(row)
        elif t_rc.status == "failed" and b_rc.status == "failed":
            still_failing.append(row)

    for key, b_rc in base_idx.items():
        if key not in target_idx:
            removed_cases.append({**_meta(b_rc), "base_status": b_rc.status, "target_status": None})

    def _summary(run: TestRun) -> dict[str, Any]:
        total = len(run.run_cases)
        passed = sum(1 for rc in run.run_cases if rc.status == "passed")
        failed = sum(1 for rc in run.run_cases if rc.status == "failed")
        return {
            "id": run.id,
            "name": run.name,
            "status": run.status,
            "environment": run.environment,
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": round(passed / total * 100, 1) if total else 0.0,
        }

    return {
        "base": _summary(base),
        "target": _summary(target),
        "newly_failed": newly_failed,
        "fixed": fixed,
        "still_failing": still_failing,
        "new_cases": new_cases,
        "removed_cases": removed_cases,
    }


def list_my_work(
    db: Session,
    project_id: str,
    user_id: str,
    scope: str = "open",
) -> list[dict[str, Any]]:
    """Return run-cases assigned to a given user across all runs in a project.

    scope="open"  → only actionable items (run-case status not_run/running and run not completed)
    scope="all"   → every assigned run-case regardless of status
    """
    project_id = resolve_project_id(db, project_id)
    q = (
        select(TestRunCase, TestRun)
        .join(TestRun, TestRunCase.run_id == TestRun.id)
        .join(TestCycle, TestRun.cycle_id == TestCycle.id)
        .join(TestPlan, TestCycle.plan_id == TestPlan.id)
        .where(TestPlan.project_id == project_id)
        .where(TestRunCase.assigned_to == user_id)
    )
    if scope == "open":
        q = q.where(TestRunCase.status.in_(("not_run", "running")))
        q = q.where(TestRun.status != "completed")
    rows = db.execute(
        q.order_by(TestRun.created_at.desc(), TestRunCase.id)
    ).all()

    items: list[dict[str, Any]] = []
    for run_case, run in rows:
        snap = (run_case.case_snapshot or {}).get("case", {}) if run_case.case_snapshot else {}
        case = run_case.case
        items.append(
            {
                "run_case_id": run_case.id,
                "run_id": run.id,
                "run_name": run.name,
                "run_status": run.status,
                "environment": run.environment,
                "case_id": run_case.case_id,
                "case_key": (case.case_key if case else None) or snap.get("case_key"),
                "case_title": (case.title if case else None) or snap.get("title") or "(silinmiş case)",
                "priority": (case.priority if case else None) or snap.get("priority"),
                "type": (case.type if case else None) or snap.get("type"),
                "status": run_case.status,
                "started_at": run_case.started_at,
                "completed_at": run_case.completed_at,
            }
        )
    return items


# ── Exploratory testing sessions ────────────────────────────────────────────────

def list_exploration_sessions(db: Session, project_id: str) -> list[ExplorationSession]:
    project_id = resolve_project_id(db, project_id)
    return list(
        db.scalars(
            select(ExplorationSession)
            .where(ExplorationSession.project_id == project_id)
            .order_by(ExplorationSession.created_at.desc())
        ).all()
    )


def get_exploration_session(db: Session, project_id: str, session_id: str) -> ExplorationSession:
    project_id = resolve_project_id(db, project_id)
    sess = db.get(ExplorationSession, session_id)
    if sess is None or sess.project_id != project_id:
        raise KeyError("Keşif oturumu bulunamadı")
    return sess


def create_exploration_session(db: Session, project_id: str, payload: Any, user: Any | None) -> ExplorationSession:
    project_id = resolve_project_id(db, project_id)
    sess = ExplorationSession(
        project_id=project_id,
        title=payload.title,
        charter=payload.charter,
        areas=payload.areas,
        environment=payload.environment,
        timebox_minutes=payload.timebox_minutes,
        tester_id=_actor_id(user),
    )
    db.add(sess)
    db.flush()
    audit(db, "exploration.created", "exploration_session", sess.id, project_id, user)
    db.commit()
    db.refresh(sess)
    return sess


def update_exploration_session(db: Session, project_id: str, session_id: str, payload: Any, user: Any | None) -> ExplorationSession:
    sess = get_exploration_session(db, project_id, session_id)
    data = payload.model_dump(exclude_unset=True)
    new_status = data.get("status")
    if new_status == "active" and sess.started_at is None:
        sess.started_at = utcnow()
    if new_status in ("completed", "aborted") and sess.ended_at is None:
        sess.ended_at = utcnow()
    for key, value in data.items():
        setattr(sess, key, value)
    db.flush()
    audit(db, "exploration.updated", "exploration_session", sess.id, sess.project_id, user, {"fields": list(data.keys())})
    db.commit()
    db.refresh(sess)
    return sess


def add_exploration_note(db: Session, project_id: str, session_id: str, payload: Any, user: Any | None) -> ExplorationSession:
    import uuid as _uuid_mod

    sess = get_exploration_session(db, project_id, session_id)
    note = {
        "id": _uuid_mod.uuid4().hex,
        "ts": utcnow().isoformat(),
        "kind": payload.kind,
        "text": payload.text,
    }
    # JSONB column: reassign a new list so SQLAlchemy detects the change.
    sess.notes = [*(sess.notes or []), note]
    db.flush()
    db.commit()
    db.refresh(sess)
    return sess


def delete_exploration_note(db: Session, project_id: str, session_id: str, note_id: str, user: Any | None) -> ExplorationSession:
    sess = get_exploration_session(db, project_id, session_id)
    sess.notes = [n for n in (sess.notes or []) if n.get("id") != note_id]
    db.flush()
    db.commit()
    db.refresh(sess)
    return sess


def delete_exploration_session(db: Session, project_id: str, session_id: str, user: Any | None) -> None:
    sess = get_exploration_session(db, project_id, session_id)
    db.delete(sess)
    audit(db, "exploration.deleted", "exploration_session", session_id, sess.project_id, user)
    db.commit()


def create_run(db: Session, project_id: str, payload: TestRunCreate, user: Any | None) -> TestRun:
    project_id = resolve_project_id(db, project_id)
    cycle_id = payload.cycle_id
    if cycle_id:
        cycle = db.get(TestCycle, cycle_id)
        if cycle is None or cycle.plan.project_id != project_id:
            raise KeyError("Test cycle bulunamadı")
    else:
        # Auto-resolve: use first existing cycle, or create a default plan+cycle
        cycle = db.scalar(
            select(TestCycle)
            .join(TestPlan, TestCycle.plan_id == TestPlan.id)
            .where(TestPlan.project_id == project_id)
            .order_by(TestCycle.created_at)
        )
        if cycle is None:
            default_plan = TestPlan(project_id=project_id, name="Default Plan", plan_type="sprint")
            db.add(default_plan)
            db.flush()
            cycle = TestCycle(plan_id=default_plan.id, name="Sprint 1")
            db.add(cycle)
            db.flush()
        cycle_id = cycle.id
    run = TestRun(
        cycle_id=cycle_id,
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


def update_run(db: Session, project_id: str, run_id: str, payload: TestRunUpdate, user: Any | None) -> TestRun:
    project_id = resolve_project_id(db, project_id)
    run = db.scalar(
        select(TestRun)
        .join(TestCycle, TestRun.cycle_id == TestCycle.id)
        .join(TestPlan, TestCycle.plan_id == TestPlan.id)
        .where(TestRun.id == run_id, TestPlan.project_id == project_id)
    )
    if run is None:
        raise KeyError("Test run bulunamadı")
    changed: list[str] = []
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(run, key, value)
        changed.append(key)
    if changed:
        audit(db, "run.updated", "run", run.id, project_id, user, {"changed_fields": changed})
    db.commit()
    db.refresh(run)
    return run


def delete_run(db: Session, project_id: str, run_id: str, user: Any | None) -> None:
    project_id = resolve_project_id(db, project_id)
    run = db.scalar(
        select(TestRun)
        .join(TestCycle, TestRun.cycle_id == TestCycle.id)
        .join(TestPlan, TestCycle.plan_id == TestPlan.id)
        .where(TestRun.id == run_id, TestPlan.project_id == project_id)
    )
    if run is None:
        raise KeyError("Test run bulunamadı")
    audit(db, "run.deleted", "run", run_id, project_id, user)
    db.delete(run)
    db.commit()


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


def update_run_case(db: Session, project_id: str, run_case_id: str, payload: Any, user: Any | None) -> TestRunCase:
    """Set the overall status of a test run case directly (TestRail-style case-level result).

    This is the primary execute flow: click Pass/Fail/Block/Skip/Retest for the whole case
    without needing to update every step individually.
    """
    project_id = resolve_project_id(db, project_id)
    run_case = db.get(TestRunCase, run_case_id)
    if run_case is None:
        raise KeyError("Run case bulunamadı")
    if run_case.case.project_id != project_id:
        raise KeyError("Run case bulunamadı")

    old_status = run_case.status
    run_case.status = payload.status
    if payload.actual_result is not None:
        run_case.actual_result = payload.actual_result
    if payload.execution_notes is not None:
        run_case.execution_notes = payload.execution_notes

    now = utcnow()
    if old_status == "not_run" and payload.status != "not_run":
        run_case.started_at = run_case.started_at or now
    if payload.status in {"passed", "failed", "blocked", "skipped"}:
        run_case.completed_at = now
        # Persist execution duration: prefer the client-measured value (more accurate —
        # it tracks active time on the case), otherwise derive it from started_at.
        client_duration = getattr(payload, "duration_seconds", None)
        if client_duration is not None:
            run_case.duration_seconds = client_duration
        elif run_case.started_at is not None and run_case.duration_seconds is None:
            run_case.duration_seconds = max(0, int((now - run_case.started_at).total_seconds()))

    # Update the case's last-run metadata
    run_case.case.last_run_status = run_case.status
    run_case.case.last_run_at = now
    run_case.case.last_run_id = run_case.run_id
    if run_case.status == "failed":
        run_case.case.last_failed_at = now

    _sync_run_status(run_case.run)
    audit(db, "run_case.updated", "run_case", run_case.id, project_id, user, {"status": payload.status})
    db.commit()
    db.refresh(run_case)
    return run_case


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


def dashboard_summary(db: Session, project_id: str) -> dict[str, Any]:
    """Single endpoint aggregating all dashboard metrics — replaces 7 parallel queries."""
    project_id = resolve_project_id(db, project_id)

    # Cases
    all_cases = list(db.scalars(
        select(TestCase).where(TestCase.project_id == project_id, TestCase.archived == False)  # noqa: E712
    ).all())
    total_cases = len(all_cases)

    # Suite / folder counts
    suite_count = db.scalar(
        select(func.count()).select_from(TestSuite).where(TestSuite.project_id == project_id)
    ) or 0
    folder_count = db.scalar(
        select(func.count()).select_from(TestFolder)
        .join(TestSuite, TestFolder.suite_id == TestSuite.id)
        .where(TestSuite.project_id == project_id)
    ) or 0

    # Last run status from cases
    failed_cases  = sum(1 for c in all_cases if c.last_run_status == "failed")
    blocked_cases = sum(1 for c in all_cases if c.last_run_status == "blocked")
    not_run_cases = sum(1 for c in all_cases if not c.last_run_status or c.last_run_status == "not_run")

    # Active runs
    active_runs = db.scalar(
        select(func.count()).select_from(TestRun)
        .join(TestCycle, TestRun.cycle_id == TestCycle.id)
        .where(TestCycle.project_id == project_id, TestRun.status.in_(["running", "in_progress"]))
    ) or 0

    # Pass rate from execution summary
    try:
        es = execution_summary(db, project_id)
        pass_rate = es.pass_rate_pct
    except Exception:
        pass_rate = 0.0

    # Critical defects
    critical_defects = db.scalar(
        select(func.count()).select_from(DefectLink)
        .join(TestRunCase, DefectLink.run_case_id == TestRunCase.id)
        .join(TestCase, TestRunCase.case_id == TestCase.id)
        .where(TestCase.project_id == project_id, DefectLink.severity.in_(["critical", "blocker"]))
    ) or 0

    # Coverage
    req_links = list(db.scalars(
        select(RequirementLink).where(RequirementLink.project_id == project_id)
    ).all())
    covered = sum(1 for r in req_links if r.coverage_status == "covered")
    coverage_pct = round(covered / len(req_links) * 100) if req_links else 0

    return {
        "total_cases": total_cases,
        "active_runs": active_runs,
        "pass_rate_pct": pass_rate,
        "failed_cases": failed_cases,
        "blocked_cases": blocked_cases,
        "not_run_cases": not_run_cases,
        "critical_defects": critical_defects,
        "coverage_pct": coverage_pct,
        "suite_count": suite_count,
        "folder_count": folder_count,
    }


def _days_since(value: datetime | None) -> int | None:
    if value is None:
        return None
    now = utcnow()
    if value.tzinfo is None:
        value = value.replace(tzinfo=_tz.utc)
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
        role=getattr(payload, "role", None),
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
        "suites": [TestSuiteOut.model_validate(s).model_dump(mode="json") for s in repo["suites"]],
        "folders": [TestFolderOut.model_validate(f).model_dump(mode="json") for f in repo["folders"]],
        "cases": [TestCaseOut.model_validate(c).model_dump(mode="json") for c in repo["cases"]],
        "requirements": [RequirementOut.model_validate(r).model_dump(mode="json") for r in requirements],
        "requirement_links": [RequirementLinkOut.model_validate(rl).model_dump(mode="json") for rl in requirement_links],
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
    import secrets as _secrets
    project_id = resolve_project_id(db, project_id)
    # Auto-generate external_key when not provided
    if not payload.external_key:
        payload = payload.model_copy(update={"external_key": f"REQ-{_secrets.token_hex(4).upper()}"})
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


def update_requirement(db: Session, project_id: str, req_id: str, payload: Any, user: Any | None) -> Requirement:
    project_id = resolve_project_id(db, project_id)
    req = db.scalar(select(Requirement).where(Requirement.id == req_id, Requirement.project_id == project_id))
    if req is None:
        raise KeyError("Requirement bulunamadı")
    changed: list[str] = []
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(req, key, value)
        changed.append(key)
    if changed:
        audit(db, "requirement.updated", "requirement", req.id, project_id, user, {"changed_fields": changed})
    db.commit()
    db.refresh(req)
    return req


def delete_requirement(db: Session, project_id: str, req_id: str, user: Any | None) -> None:
    project_id = resolve_project_id(db, project_id)
    req = db.scalar(select(Requirement).where(Requirement.id == req_id, Requirement.project_id == project_id))
    if req is None:
        raise KeyError("Requirement bulunamadı")
    audit(db, "requirement.deleted", "requirement", req_id, project_id, user)
    db.delete(req)
    db.commit()


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

    def build_row(
        requirement_id: str,
        req_key: str,
        external_key: str,
        title: str,
        source: str,
        url: str | None,
        status: str,
        priority: str,
        source_updated_at: datetime | None,
        req_links: list[RequirementLink],
    ) -> dict[str, Any]:
        cases = []
        stale = False
        full = 0       # fully-covered links
        partial = 0    # partially-covered links

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
            if lnk.coverage_status == "covered":
                full += 1
            elif lnk.coverage_status == "partial":
                partial += 1
            # Mark stale if requirement was updated after the case's last run.
            updated_at = lnk.source_updated_at or source_updated_at
            if (
                updated_at
                and case.last_run_at
                and updated_at > case.last_run_at
            ):
                stale = True

        total = len(cases)
        # Partial links count as half coverage. covered=True only when fully covered.
        coverage_pct = round((full + 0.5 * partial) / total * 100) if total else 0
        covered = total > 0 and coverage_pct >= 100

        return {
            "requirement_id": requirement_id,
            "requirement_key": req_key,
            "external_key": external_key,
            "title": title,
            "status": status,
            "priority": priority,
            "source": source,
            "url": url,
            "covered": covered,
            "stale": stale,
            "coverage_pct": coverage_pct,
            "cases": cases,
        }

    requirement_by_id = {req.id: req for req in requirements}
    for req in requirements:
        group_key = req.id
        seen_groups.add(group_key)
        rows.append(build_row(
            req.id, req.external_key, req.external_key, req.title, req.external_source, req.url,
            req.status, req.priority, req.source_updated_at, grouped.get(group_key, []),
        ))

    for group_key, req_links in grouped.items():
        if group_key in seen_groups:
            continue
        first = req_links[0]
        requirement = requirement_by_id.get(first.requirement_id or "")
        if requirement is not None:
            continue
        rows.append(
            build_row(
                first.requirement_id or group_key,
                first.external_key,
                first.external_key,
                first.title_snapshot,
                first.external_source,
                first.url,
                "",
                "",
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


def update_requirement_link(db: Session, project_id: str, req_id: str, payload: RequirementLinkUpdate, user: Any | None) -> RequirementLink:
    project_id = resolve_project_id(db, project_id)
    link = db.scalar(select(RequirementLink).where(RequirementLink.id == req_id, RequirementLink.project_id == project_id))
    if link is None:
        raise KeyError("Requirement link bulunamadı")
    changed: list[str] = []
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(link, key, value)
        changed.append(key)
    if changed:
        audit(db, "requirement_link.updated", "requirement_link", link.id, project_id, user, {"changed_fields": changed})
    db.commit()
    db.refresh(link)
    return link


def delete_requirement_link(db: Session, project_id: str, req_id: str, user: Any | None) -> None:
    project_id = resolve_project_id(db, project_id)
    link = db.scalar(select(RequirementLink).where(RequirementLink.id == req_id, RequirementLink.project_id == project_id))
    if link is None:
        raise KeyError("Requirement link bulunamadı")
    audit(db, "requirement_link.deleted", "requirement_link", req_id, project_id, user)
    db.delete(link)
    db.commit()


def list_defect_links(db: Session, project_id: str, case_id: str | None = None) -> list[DefectLink]:
    project_id = resolve_project_id(db, project_id)
    stmt = (
        select(DefectLink)
        .join(TestRunCase, DefectLink.run_case_id == TestRunCase.id)
        .join(TestCase, TestRunCase.case_id == TestCase.id)
        .where(TestCase.project_id == project_id)
    )
    if case_id:
        stmt = stmt.where(TestRunCase.case_id == case_id)
    stmt = stmt.order_by(DefectLink.created_at.desc())
    return list(db.scalars(stmt).all())


def search_defects(db: Session, project_id: str, q: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    """Return distinct defects in a project (deduped by external_key) for the 'link existing' picker.

    Each entry keeps the most recent DefectLink row as the representative and counts how many
    run-cases share the same external_key.
    """
    project_id = resolve_project_id(db, project_id)
    stmt = (
        select(DefectLink)
        .join(TestRunCase, DefectLink.run_case_id == TestRunCase.id)
        .join(TestCase, TestRunCase.case_id == TestCase.id)
        .where(TestCase.project_id == project_id)
    )
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(DefectLink.title.ilike(like), DefectLink.external_key.ilike(like)))
    stmt = stmt.order_by(DefectLink.created_at.desc())
    rows = list(db.scalars(stmt).all())

    by_key: dict[str, dict[str, Any]] = {}
    for d in rows:
        entry = by_key.get(d.external_key)
        if entry is None:
            by_key[d.external_key] = {
                "defect_id": d.id,
                "external_key": d.external_key,
                "external_source": d.external_source,
                "title": d.title,
                "status": d.status,
                "severity": d.severity,
                "priority": d.priority,
                "url": d.url,
                "root_cause": d.root_cause,
                "link_count": 1,
            }
        else:
            entry["link_count"] += 1
    return list(by_key.values())[:limit]


def link_existing_defect(
    db: Session,
    project_id: str,
    run_case_id: str,
    defect_id: str,
    step_result_id: str | None,
    user: Any | None,
) -> DefectLink:
    """Attach an already-recorded defect to another failed run-case.

    Creates a new DefectLink row for ``run_case_id`` that reuses the source defect's
    external_key, title and metadata. Idempotent: if this run-case already references
    the same external_key, the existing link is returned untouched.
    """
    project_id = resolve_project_id(db, project_id)
    run_case = db.get(TestRunCase, run_case_id)
    if run_case is None or run_case.case is None or run_case.case.project_id != project_id:
        raise KeyError("Run case bulunamadı")
    source = db.get(DefectLink, defect_id)
    if source is None:
        raise KeyError("Defect bulunamadı")
    # Verify the source defect belongs to the same project.
    src_rc = db.get(TestRunCase, source.run_case_id)
    if src_rc is None or src_rc.case is None or src_rc.case.project_id != project_id:
        raise KeyError("Defect bulunamadı")
    # Idempotency: same defect already linked to this run-case.
    existing = db.scalar(
        select(DefectLink).where(
            DefectLink.run_case_id == run_case_id,
            DefectLink.external_key == source.external_key,
        )
    )
    if existing is not None:
        return existing
    link = DefectLink(
        run_case_id=run_case_id,
        step_result_id=step_result_id,
        external_source=source.external_source,
        external_key=source.external_key,
        title=source.title,
        status=source.status,
        severity=source.severity,
        priority=source.priority,
        root_cause=source.root_cause,
        url=source.url,
    )
    db.add(link)
    db.flush()
    audit(db, "defect_link.linked_existing", "defect_link", link.id, project_id, user, {"external_key": source.external_key})
    db.commit()
    db.refresh(link)
    return link


def create_defect_link(db: Session, project_id: str, payload: DefectLinkCreate, user: Any | None) -> DefectLink:
    import secrets as _secrets
    project_id = resolve_project_id(db, project_id)
    # run_case_id is optional — only validate when provided
    if payload.run_case_id:
        run_case = db.get(TestRunCase, payload.run_case_id)
        if run_case is None or run_case.case.project_id != project_id:
            raise KeyError("Run case bulunamadı")
    # Auto-generate external_key when not provided
    data = payload.model_dump(exclude={"description", "type"})
    if not data.get("external_key"):
        data["external_key"] = f"DEF-{_secrets.token_hex(4).upper()}"
    link = DefectLink(**data)
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
    # Only validate run_case when it's linked
    if defect.run_case_id:
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


def delete_defect_link(db: Session, project_id: str, defect_id: str, user: Any | None) -> None:
    project_id = resolve_project_id(db, project_id)
    defect = db.get(DefectLink, defect_id)
    if defect is None:
        raise KeyError("Defect bağlantısı bulunamadı")
    # Only validate run_case when the defect is linked to one
    if defect.run_case_id:
        run_case = db.get(TestRunCase, defect.run_case_id)
        if run_case is None or run_case.case.project_id != project_id:
            raise KeyError("Defect bağlantısı bulunamadı")
    audit(db, "defect_link.deleted", "defect_link", defect_id, project_id, user)
    db.delete(defect)
    db.commit()


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


# ── AI Test Case Üretimi ──────────────────────────────────────────────────────

def _bdd_steps_to_management(bdd_steps: list[dict]) -> list[dict]:
    """BDD adımlarını (keyword/text) management step formatına (action/expected_result) dönüştür."""
    result = []
    pending_action = None
    for i, step in enumerate(bdd_steps):
        text = step.get("text", "")
        keyword = step.get("keyword", "").strip().lower()
        if keyword in ("o zaman", "then", "ve aynı zamanda", "and then"):
            if pending_action is not None:
                result.append({
                    "step_no": len(result) + 1,
                    "action": pending_action,
                    "expected_result": text,
                    "is_required": True,
                })
                pending_action = None
            else:
                result.append({
                    "step_no": len(result) + 1,
                    "action": f"Doğrula: {text}",
                    "expected_result": text,
                    "is_required": True,
                })
        else:
            if pending_action is not None:
                result.append({
                    "step_no": len(result) + 1,
                    "action": pending_action,
                    "expected_result": "",
                    "is_required": True,
                })
            pending_action = text
    if pending_action is not None:
        result.append({
            "step_no": len(result) + 1,
            "action": pending_action,
            "expected_result": "",
            "is_required": True,
        })
    return result


def generate_test_cases(
    db: Session,
    project_id: str,
    payload: TestCaseGenerateRequest,
    user: Any | None = None,
) -> list[GeneratedCaseOut]:
    """AI kullanarak test case'leri üretir; save=True ise DB'ye kaydeder."""
    from app.domains.ai import service as ai_service

    project_id = resolve_project_id(db, project_id)

    try:
        raw_scenarios = ai_service.generate_scenarios(
            description=payload.prompt,
            count=payload.count,
            project_id=project_id,
            user_id=_actor_id(user),
        )
    except Exception:
        raw_scenarios = []

    results: list[GeneratedCaseOut] = []
    for sc in raw_scenarios:
        bdd_steps = sc.get("steps", [])
        mgmt_steps = _bdd_steps_to_management(bdd_steps)
        priority_map = {"high": "P0", "medium": "P1", "low": "P2"}
        priority = priority_map.get(sc.get("priority", "medium"), payload.priority)

        saved_id: str | None = None
        if payload.save:
            tc_create = TestCaseCreate(
                title=sc.get("title", "AI Üretilen Senaryo"),
                objective=sc.get("description", ""),
                suite_id=payload.suite_id,
                folder_id=payload.folder_id,
                priority=priority,
                type=payload.type,
                status="draft",
                source_type="ai_generated",
                tags=sc.get("tags", []),
                steps=[
                    {"step_no": s["step_no"], "action": s["action"],
                     "expected_result": s["expected_result"], "is_required": s["is_required"],
                     "test_data": {}}
                    for s in mgmt_steps
                ],
            )
            tc = create_case(db, project_id, tc_create, user)
            saved_id = tc.id

        results.append(GeneratedCaseOut(
            title=sc.get("title", "AI Üretilen Senaryo"),
            objective=sc.get("description", ""),
            preconditions="",
            priority=priority,
            tags=sc.get("tags", []),
            steps=[
                GeneratedStepOut(
                    step_no=s["step_no"],
                    action=s["action"],
                    expected_result=s["expected_result"],
                    is_required=s["is_required"],
                )
                for s in mgmt_steps
            ],
            saved_id=saved_id,
        ))

    return results


async def generate_test_cases_async(
    db: Session,
    project_id: str,
    payload: TestCaseGenerateRequest,
    user: Any | None = None,
) -> list[GeneratedCaseOut]:
    """AI kullanarak test case'leri üretir (async version); save=True ise DB'ye kaydeder."""
    from app.domains.ai import service as ai_service

    project_id = resolve_project_id(db, project_id)

    try:
        raw_scenarios = await ai_service.async_generate_scenarios(
            description=payload.prompt,
            count=payload.count,
            project_id=project_id,
            user_id=_actor_id(user),
        )
    except Exception:
        raw_scenarios = []

    results: list[GeneratedCaseOut] = []
    for sc in raw_scenarios:
        bdd_steps = sc.get("steps", [])
        mgmt_steps = _bdd_steps_to_management(bdd_steps)
        priority_map = {"high": "P0", "medium": "P1", "low": "P2"}
        priority = priority_map.get(sc.get("priority", "medium"), payload.priority)

        saved_id: str | None = None
        if payload.save:
            tc_create = TestCaseCreate(
                title=sc.get("title", "AI Üretilen Senaryo"),
                objective=sc.get("description", ""),
                suite_id=payload.suite_id,
                folder_id=payload.folder_id,
                priority=priority,
                type=payload.type,
                status="draft",
                source_type="ai_generated",
                tags=sc.get("tags", []),
                steps=[
                    {"step_no": s["step_no"], "action": s["action"],
                     "expected_result": s["expected_result"], "is_required": s["is_required"],
                     "test_data": {}}
                    for s in mgmt_steps
                ],
            )
            tc = create_case(db, project_id, tc_create, user)
            saved_id = tc.id

        results.append(GeneratedCaseOut(
            title=sc.get("title", "AI Üretilen Senaryo"),
            objective=sc.get("description", ""),
            preconditions="",
            priority=priority,
            tags=sc.get("tags", []),
            steps=[
                GeneratedStepOut(
                    step_no=s["step_no"],
                    action=s["action"],
                    expected_result=s["expected_result"],
                    is_required=s["is_required"],
                )
                for s in mgmt_steps
            ],
            saved_id=saved_id,
        ))

    return results


# ── Case Clone ────────────────────────────────────────────────────────────────

def clone_case(
    db: Session,
    project_id: str,
    case_id: str,
    payload: TestCaseCloneRequest,
    user: Any | None = None,
) -> TestCase:
    """Mevcut bir case'i kopyalar ve yeni bir case döner."""
    project_id = resolve_project_id(db, project_id)
    source = get_case(db, project_id, case_id)

    new_title = payload.title or f"{source.title} (Kopya)"
    suite_id  = payload.suite_id or source.suite_id
    folder_id = payload.folder_id or source.folder_id

    tc_create = TestCaseCreate(
        title=new_title,
        suite_id=suite_id,
        folder_id=folder_id,
        objective=source.objective or "",
        preconditions=source.preconditions or "",
        priority=source.priority,
        severity=source.severity,
        type=source.type,
        automation_status=source.automation_status,
        status="draft",
        source_type="manual",
        tags=list(source.tags or []),
        custom_fields=dict(source.custom_fields or {}),
        steps=[
            {"step_no": s.step_no, "action": s.action,
             "expected_result": s.expected_result,
             "test_data": dict(s.test_data or {}),
             "is_required": s.is_required}
            for s in sorted(source.steps, key=lambda x: x.step_no)
        ],
    )
    return create_case(db, project_id, tc_create, user)


# ── Standup ───────────────────────────────────────────────────────────────────

def get_standup(
    db: Session,
    project_id: str,
    run_id: str | None = None,
) -> StandupOut:
    """Aktif veya belirtilen run için standup verisini hesaplar."""
    from app.domains.test_management import intelligence_service

    project_id = resolve_project_id(db, project_id)

    # En son aktif run'u seç
    if run_id:
        run = db.get(TestRun, run_id)
        if not run or run.project_id != project_id:
            raise KeyError("Run bulunamadı")
    else:
        stmt = (
            select(TestRun)
            .join(TestCycle, TestRun.cycle_id == TestCycle.id)
            .where(TestCycle.project_id == project_id)
            .where(TestRun.status.in_(["in_progress", "not_started"]))
            .order_by(TestRun.created_at.desc())
        )
        run = db.scalars(stmt).first()
        if not run:
            # En son tamamlanan run
            stmt2 = (
                select(TestRun)
                .join(TestCycle, TestRun.cycle_id == TestCycle.id)
                .where(TestCycle.project_id == project_id)
                .order_by(TestRun.created_at.desc())
            )
            run = db.scalars(stmt2).first()
        if not run:
            return StandupOut(
                health_score=0, summary_health="healthy",
                eta_hours=None, remaining_cases=0, total_cases=0,
                completed_cases=0, pass_rate=0, blocked=0, failed=0,
                velocity_per_hour=0, anomalies=[], run_name="Run yok",
                predicted_completion=None, will_meet_gate=True,
                blocking_factors=[],
            )

    report = intelligence_service.get_run_intelligence(db, project_id, run.id)
    eta    = intelligence_service._predict_eta(run, list(db.scalars(
        select(TestRunCase).where(TestRunCase.run_id == run.id)
    ).all()))

    run_cases = list(db.scalars(select(TestRunCase).where(TestRunCase.run_id == run.id)).all())
    total     = len(run_cases)
    done_set  = {"passed", "failed", "blocked", "skipped"}
    completed = len([rc for rc in run_cases if rc.status in done_set])
    passed    = len([rc for rc in run_cases if rc.status == "passed"])
    failed_ct = len([rc for rc in run_cases if rc.status == "failed"])
    blocked_ct= len([rc for rc in run_cases if rc.status == "blocked"])
    pass_rate = round((passed / completed * 100) if completed > 0 else 0, 1)

    health_score = max(0.0, min(100.0, pass_rate - (failed_ct * 2) - (blocked_ct * 1)))
    if health_score >= 70:
        summary_health = "healthy"
    elif health_score >= 40:
        summary_health = "at_risk"
    else:
        summary_health = "critical"

    blocking_factors: list[str] = []
    if blocked_ct > 0:
        blocking_factors.append(f"{blocked_ct} bloke case var")
    if failed_ct > 0:
        blocking_factors.append(f"{failed_ct} başarısız case var")
    if total - completed > 0 and (total - completed) / max(total, 1) > 0.5:
        blocking_factors.append("Koşum ilerlemesi düşük")

    anomalies: list[StandupAnomaly] = []
    for a in (report.anomalies or []):
        anomalies.append(StandupAnomaly(severity=getattr(a, "severity", "medium"), title=getattr(a, "title", str(a))))

    eta_hours = None
    predicted = None
    predicted_end = getattr(eta, "predicted_end_at", None) or getattr(eta, "predicted_completion", None) if eta else None
    if predicted_end:
        now = datetime.now(_tz.utc)
        diff = (predicted_end.replace(tzinfo=_tz.utc) if predicted_end.tzinfo is None else predicted_end) - now
        eta_hours = max(0.0, diff.total_seconds() / 3600)
        predicted = predicted_end.isoformat()

    velocity = getattr(report, "velocity_per_hour", 0.0) or 0.0

    return StandupOut(
        health_score=round(health_score, 1),
        summary_health=summary_health,
        eta_hours=round(eta_hours, 1) if eta_hours is not None else None,
        remaining_cases=total - completed,
        total_cases=total,
        completed_cases=completed,
        pass_rate=pass_rate,
        blocked=blocked_ct,
        failed=failed_ct,
        velocity_per_hour=round(velocity, 2),
        anomalies=anomalies,
        run_name=run.name,
        predicted_completion=predicted,
        will_meet_gate=summary_health != "critical",
        blocking_factors=blocking_factors,
    )


# ── Shared Steps ──────────────────────────────────────────────────────────────

def list_shared_steps(db: Session, project_id: str) -> list[SharedStep]:
    project_id = resolve_project_id(db, project_id)
    return list(db.scalars(
        select(SharedStep)
        .where(SharedStep.project_id == project_id)
        .order_by(SharedStep.name)
    ).all())


def get_shared_step(db: Session, project_id: str, step_id: str) -> SharedStep:
    project_id = resolve_project_id(db, project_id)
    step = db.scalar(select(SharedStep).where(SharedStep.id == step_id, SharedStep.project_id == project_id))
    if step is None:
        raise KeyError("Shared step bulunamadı")
    return step


def create_shared_step(db: Session, project_id: str, payload: SharedStepCreate, user: Any | None) -> SharedStep:
    project_id = resolve_project_id(db, project_id)
    step = SharedStep(
        project_id=project_id,
        name=payload.name,
        description=payload.description,
        steps=[s.model_dump() for s in payload.steps],
        tags=payload.tags,
        created_by=_actor_id(user),
    )
    db.add(step)
    db.flush()
    audit(db, "shared_step.created", "shared_step", step.id, project_id, user)
    db.commit()
    db.refresh(step)
    return step


def update_shared_step(db: Session, project_id: str, step_id: str, payload: SharedStepUpdate, user: Any | None) -> SharedStep:
    step = get_shared_step(db, project_id, step_id)
    changed: list[str] = []
    data = payload.model_dump(exclude_unset=True)
    if "steps" in data and data["steps"] is not None:
        data["steps"] = [s.model_dump() if hasattr(s, "model_dump") else s for s in data["steps"]]
    for key, value in data.items():
        setattr(step, key, value)
        changed.append(key)
    if changed:
        audit(db, "shared_step.updated", "shared_step", step.id, resolve_project_id(db, project_id), user, {"changed_fields": changed})
    db.commit()
    db.refresh(step)
    return step


def delete_shared_step(db: Session, project_id: str, step_id: str, user: Any | None) -> None:
    step = get_shared_step(db, project_id, step_id)
    pid = resolve_project_id(db, project_id)
    audit(db, "shared_step.deleted", "shared_step", step_id, pid, user)
    db.delete(step)
    db.commit()


def increment_shared_step_usage(db: Session, step_id: str) -> None:
    step = db.get(SharedStep, step_id)
    if step:
        step.usage_count += 1


# ── Case Dependencies ──────────────────────────────────────────────────────────

def list_case_dependencies(db: Session, project_id: str, case_id: str) -> list[dict]:
    get_case(db, project_id, case_id)  # existence check
    deps = db.scalars(select(TestCaseDependency).where(TestCaseDependency.case_id == case_id)).all()
    result = []
    for d in deps:
        dep_case = db.get(TestCase, d.depends_on_id)
        result.append({
            "id": d.id, "case_id": d.case_id, "depends_on_id": d.depends_on_id,
            "dep_type": d.dep_type,
            "depends_on_key": dep_case.case_key if dep_case else "",
            "depends_on_title": dep_case.title if dep_case else "",
            "created_at": d.created_at,
        })
    return result


def add_case_dependency(db: Session, project_id: str, case_id: str, payload: Any, user: Any | None) -> dict:
    parent = get_case(db, project_id, case_id)
    dep_case = get_case(db, project_id, payload.depends_on_id)
    if dep_case.id == parent.id:
        raise ValueError("Bir case kendisine bağımlı olamaz")
    dep = TestCaseDependency(case_id=case_id, depends_on_id=payload.depends_on_id, dep_type=payload.dep_type)
    db.add(dep)
    db.flush()
    audit(db, "case.dependency_added", "case", case_id, resolve_project_id(db, project_id), user, {"depends_on": payload.depends_on_id})
    db.commit()
    db.refresh(dep)
    return {
        "id": dep.id, "case_id": dep.case_id, "depends_on_id": dep.depends_on_id,
        "dep_type": dep.dep_type,
        "depends_on_key": dep_case.case_key, "depends_on_title": dep_case.title,
        "created_at": dep.created_at,
    }


def remove_case_dependency(db: Session, project_id: str, case_id: str, dep_id: str, user: Any | None) -> None:
    get_case(db, project_id, case_id)
    dep = db.get(TestCaseDependency, dep_id)
    if dep is None or dep.case_id != case_id:
        raise KeyError("Bağımlılık bulunamadı")
    db.delete(dep)
    db.commit()


def get_plan_impact_summary(db: Session, project_id: str, plan_id: str) -> dict:
    """Plan silinmeden önce etkilenecek kayıt sayılarını döner."""
    pid = resolve_project_id(db, project_id)
    plan = db.get(TestPlan, plan_id)
    if not plan or plan.project_id != pid:
        raise KeyError(f"Plan not found: {plan_id}")

    cycle_ids = [c.id for c in plan.cycles]
    run_ids: list[str] = []
    run_case_ids: list[str] = []

    for cycle in plan.cycles:
        for run in cycle.runs:
            run_ids.append(run.id)
            for rc in run.run_cases:
                run_case_ids.append(rc.id)

    run_case_count = len(run_case_ids)

    # Count evidence via SQL — TestRunCase has no evidence_files relationship
    evidence_count = 0
    if run_case_ids:
        evidence_count = (
            db.scalar(
                select(func.count())
                .select_from(ExecutionEvidence)
                .where(ExecutionEvidence.run_case_id.in_(run_case_ids))
            )
            or 0
        )

    return {
        "plan_id": plan_id,
        "plan_name": plan.name,
        "cycle_count": len(cycle_ids),
        "run_count": len(run_ids),
        "run_case_count": run_case_count,
        "evidence_count": evidence_count,
    }


def search_cases(db: Session, project_id: str, q: str = "", limit: int = 100) -> list[TestCase]:
    """Search test cases by title or case_key within a project.

    Returns up to `limit` active (non-archived) cases matching the query.
    """
    project_id = resolve_project_id(db, project_id)
    stmt = select(TestCase).where(
        TestCase.project_id == project_id,
        TestCase.archived == False,  # noqa: E712
    )
    if q:
        from sqlalchemy import or_
        stmt = stmt.where(
            or_(
                TestCase.title.ilike(f"%{q}%"),
                TestCase.case_key.ilike(f"%{q}%"),
            )
        )
    return list(db.scalars(stmt.limit(limit)).all())


def list_evidence_by_run_case(db: Session, project_id: str, run_case_id: str) -> list[dict[str, Any]]:
    """Return evidence for a run-case without requiring run_id in the path.

    Validates that the run-case belongs to the given project to prevent IDOR.
    """
    project_id = resolve_project_id(db, project_id)
    run_case = db.get(TestRunCase, run_case_id)
    if run_case is None or run_case.case.project_id != project_id:
        raise KeyError("Run case bulunamadı")
    return [
        _evidence_out(evidence)
        for evidence in db.scalars(
            select(ExecutionEvidence)
            .where(ExecutionEvidence.run_case_id == run_case_id)
            .order_by(ExecutionEvidence.uploaded_at.desc())
        ).all()
    ]


def dashboard_summary_fast(db: Session, project_id: str) -> dict[str, Any]:
    """Lightweight dashboard stats — avoids the heavy execution_summary call.

    Returns the same shape as dashboard_summary but skips pass-rate and
    coverage calculations so the response is faster for initial page load.
    The frontend can call /reports/dashboard-summary for the full dataset.
    """
    project_id = resolve_project_id(db, project_id)

    total_cases = db.scalar(
        select(func.count()).select_from(TestCase)
        .where(TestCase.project_id == project_id, TestCase.archived.is_(False))
    ) or 0

    suite_count = db.scalar(
        select(func.count()).select_from(TestSuite).where(TestSuite.project_id == project_id)
    ) or 0

    active_runs = db.scalar(
        select(func.count()).select_from(TestRun)
        .join(TestCycle, TestRun.cycle_id == TestCycle.id)
        .where(TestCycle.project_id == project_id, TestRun.status.in_(["running", "in_progress"]))
    ) or 0

    failed_cases = db.scalar(
        select(func.count()).select_from(TestCase)
        .where(TestCase.project_id == project_id, TestCase.last_run_status == "failed", TestCase.archived.is_(False))
    ) or 0

    critical_defects = db.scalar(
        select(func.count()).select_from(DefectLink)
        .join(TestRunCase, DefectLink.run_case_id == TestRunCase.id)
        .join(TestCase, TestRunCase.case_id == TestCase.id)
        .where(TestCase.project_id == project_id, DefectLink.severity.in_(["critical", "blocker"]))
    ) or 0

    # Total defects linked to this project
    defect_count = db.scalar(
        select(func.count()).select_from(DefectLink)
        .join(TestRunCase, DefectLink.run_case_id == TestRunCase.id)
        .join(TestCase, TestRunCase.case_id == TestCase.id)
        .where(TestCase.project_id == project_id)
    ) or 0

    open_defects = db.scalar(
        select(func.count()).select_from(DefectLink)
        .join(TestRunCase, DefectLink.run_case_id == TestRunCase.id)
        .join(TestCase, TestRunCase.case_id == TestCase.id)
        .where(TestCase.project_id == project_id, DefectLink.status.in_(["open", "in_progress", "reopened"]))
    ) or 0

    resolved_defects = db.scalar(
        select(func.count()).select_from(DefectLink)
        .join(TestRunCase, DefectLink.run_case_id == TestRunCase.id)
        .join(TestCase, TestRunCase.case_id == TestCase.id)
        .where(TestCase.project_id == project_id, DefectLink.status.in_(["resolved", "closed", "verified"]))
    ) or 0

    requirement_count = db.scalar(
        select(func.count()).select_from(Requirement)
        .where(Requirement.project_id == project_id)
    ) or 0

    return {
        "total_cases": total_cases,
        "active_runs": active_runs,
        "failed_cases": failed_cases,
        "critical_defects": critical_defects,
        "suite_count": suite_count,
        "defect_count": defect_count,
        "open_defects": open_defects,
        "resolved_defects": resolved_defects,
        "requirement_count": requirement_count,
    }


def get_run_trend(db: Session, project_id: str, limit: int = 20) -> list[dict]:
    """Son N test koşusunun geçme oranı trendi."""
    from sqlalchemy import text as sa_text
    result = db.execute(
        sa_text("""
            SELECT
                r.id AS run_id,
                r.name,
                r.created_at,
                COUNT(rc.id) AS total_cases,
                COUNT(CASE WHEN rc.status = 'passed' THEN 1 END) AS passed,
                COUNT(CASE WHEN rc.status = 'failed' THEN 1 END) AS failed,
                CASE
                    WHEN COUNT(rc.id) = 0 THEN 0.0
                    ELSE ROUND(
                        COUNT(CASE WHEN rc.status = 'passed' THEN 1 END)::numeric
                        / COUNT(rc.id) * 100, 1
                    )
                END AS pass_rate_pct
            FROM test_management_runs r
            JOIN test_management_cycles c ON r.cycle_id = c.id
            LEFT JOIN test_management_run_cases rc ON rc.run_id = r.id
            WHERE c.project_id = :project_id
            GROUP BY r.id, r.name, r.created_at
            ORDER BY r.created_at DESC
            LIMIT :limit
        """),
        {"project_id": project_id, "limit": limit},
    )
    rows = result.mappings().all()
    return [
        {
            "run_id": str(row["run_id"]),
            "name": row["name"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "total_cases": int(row["total_cases"]),
            "passed": int(row["passed"]),
            "failed": int(row["failed"]),
            "pass_rate_pct": float(row["pass_rate_pct"]),
        }
        for row in rows
    ]


# ── Review Workflow ────────────────────────────────────────────────────────────

def _get_case_or_404(db: Session, project_id: str, case_id: str) -> TestCase:
    real_pid = resolve_project_id(db, project_id)
    case = db.get(TestCase, case_id)
    if case is None or case.project_id != real_pid:
        raise KeyError("Test case bulunamadı")
    return case


def _notify_review_outcome(db: Session, case: TestCase, outcome: str, comment: Optional[str]) -> None:
    """Notify the case author when their case is approved/rejected. Best-effort (non-critical)."""
    recipient = case.created_by or case.owner_id
    if not recipient:
        return
    try:
        from app.domains.test_management import comments_service  # noqa: PLC0415

        approved = outcome == "approved"
        comments_service.emit_notification(
            db,
            user_id=recipient,
            kind="case_review_approved" if approved else "case_review_rejected",
            title=(
                f"Test case onaylandı: {case.case_key}"
                if approved
                else f"Test case reddedildi: {case.case_key}"
            ),
            body=comment or "",
            link_path=f"/management/cases/{case.id}",
            severity="info" if approved else "warn",
            project_id=case.project_id,
            commit=True,
        )
    except Exception:
        pass  # Notification failure must not break the review action.


def submit_case_for_review(
    db: Session, project_id: str, case_id: str, user: Any, comment: Optional[str] = None
) -> TestCase:
    """Author submits a test case for peer review (draft → pending)."""
    case = _get_case_or_404(db, project_id, case_id)
    if case.review_status not in ("none", "rejected"):
        raise ValueError(f"Review gönderilemez: mevcut durum '{case.review_status}'")
    case.review_status = "pending"
    case.review_by = None
    case.review_at = None
    case.review_comment = comment
    audit(db, "case.review_submitted", "case", case.id, case.project_id, user, {"comment": comment})
    db.commit()
    db.refresh(case)
    return case


def approve_case_review(
    db: Session, project_id: str, case_id: str, user: Any, comment: Optional[str] = None
) -> TestCase:
    """Reviewer approves a test case (pending → approved → status=active)."""
    case = _get_case_or_404(db, project_id, case_id)
    if case.review_status != "pending":
        raise ValueError(f"Onaylanamaz: mevcut durum '{case.review_status}'")
    # Four-eyes principle: the author (creator) or owner may not approve their own case.
    actor = _actor_id(user)
    if actor and actor in (case.created_by, case.owner_id):
        raise ValueError("Kendi oluşturduğunuz test case'ini onaylayamazsınız (dört-göz prensibi).")
    case.review_status = "approved"
    case.review_by = _actor_id(user)
    case.review_at = utcnow()
    case.review_comment = comment
    if case.status == "draft":
        case.status = "active"
    audit(db, "case.review_approved", "case", case.id, case.project_id, user, {"comment": comment})
    db.commit()
    db.refresh(case)
    _notify_review_outcome(db, case, "approved", comment)
    return case


def reject_case_review(
    db: Session, project_id: str, case_id: str, user: Any, comment: Optional[str] = None
) -> TestCase:
    """Reviewer rejects a test case (pending → rejected), returns to draft."""
    case = _get_case_or_404(db, project_id, case_id)
    if case.review_status != "pending":
        raise ValueError(f"Reddedilemez: mevcut durum '{case.review_status}'")
    # Four-eyes principle: the author (creator) or owner may not review their own case.
    actor = _actor_id(user)
    if actor and actor in (case.created_by, case.owner_id):
        raise ValueError("Kendi oluşturduğunuz test case'ini reddedemezsiniz (dört-göz prensibi).")
    case.review_status = "rejected"
    case.review_by = _actor_id(user)
    case.review_at = utcnow()
    case.review_comment = comment
    if case.status == "active":
        case.status = "draft"
    audit(db, "case.review_rejected", "case", case.id, case.project_id, user, {"comment": comment})
    db.commit()
    db.refresh(case)
    _notify_review_outcome(db, case, "rejected", comment)
    return case


# ── Flakiness Tracking ─────────────────────────────────────────────────────────

def recompute_case_flakiness(db: Session, case_id: str) -> None:
    """Recompute pass/fail counts and flakiness score for a single test case.

    Flakiness score = transitions between different adjacent results / (run_count - 1).
    A score of 0.0 means perfectly stable; 1.0 means alternating every run.
    """
    from sqlalchemy import text as sa_text

    result = db.execute(
        sa_text("""
            SELECT
                COUNT(*) AS total,
                COUNT(CASE WHEN rc.status = 'passed' THEN 1 END) AS passed,
                COUNT(CASE WHEN rc.status = 'failed' THEN 1 END) AS failed
            FROM test_management_run_cases rc
            WHERE rc.case_id = :case_id
              AND rc.status IN ('passed', 'failed')
        """),
        {"case_id": case_id},
    ).mappings().one_or_none()

    if not result or int(result["total"]) == 0:
        db.execute(
            sa_text("""
                UPDATE test_management_cases
                SET run_count=0, pass_count=0, fail_count=0, flakiness_score=0
                WHERE id = :cid
            """),
            {"cid": case_id},
        )
        db.commit()
        return

    total = int(result["total"])
    passed = int(result["passed"])
    failed = int(result["failed"])

    # Compute transitions (alternations) using window function
    transitions_result = db.execute(
        sa_text("""
            SELECT COUNT(*) AS transitions
            FROM (
                SELECT
                    rc.status,
                    LAG(rc.status) OVER (ORDER BY r.created_at) AS prev_status
                FROM test_management_run_cases rc
                JOIN test_management_runs r ON r.id = rc.run_id
                WHERE rc.case_id = :case_id
                  AND rc.status IN ('passed', 'failed')
            ) sub
            WHERE status != prev_status AND prev_status IS NOT NULL
        """),
        {"case_id": case_id},
    ).scalar()

    transitions = int(transitions_result or 0)
    flakiness = round(transitions / max(total - 1, 1), 4) if total > 1 else 0.0

    db.execute(
        sa_text("""
            UPDATE test_management_cases
            SET run_count=:total, pass_count=:passed, fail_count=:failed, flakiness_score=:score
            WHERE id = :cid
        """),
        {"total": total, "passed": passed, "failed": failed, "score": flakiness, "cid": case_id},
    )
    db.commit()


def list_flaky_cases(
    db: Session,
    project_id: str,
    threshold: float = 0.2,
    min_runs: int = 3,
    limit: int = 50,
    include_manual: bool = False,
) -> dict:
    """Return test cases above the flakiness threshold, ordered by score desc.

    Flakiness is an automation-stability signal; for purely manual cases a non-zero
    score usually reflects human inconsistency rather than a flaky test, so by default
    manual-only cases are excluded. Pass include_manual=True to keep them.
    """
    real_pid = resolve_project_id(db, project_id)
    stmt = (
        select(TestCase)
        .where(
            TestCase.project_id == real_pid,
            TestCase.flakiness_score >= threshold,
            TestCase.run_count >= min_runs,
            TestCase.archived.is_(False),
        )
        .order_by(TestCase.flakiness_score.desc())
        .limit(limit)
    )
    if not include_manual:
        stmt = stmt.where(TestCase.automation_status.in_(("automated", "in_progress")))
    cases = db.execute(stmt).scalars().all()
    return {"items": cases, "total": len(cases), "threshold": threshold}


def get_review_queue(
    db: Session,
    project_id: str,
    status: str = "pending",
    limit: int = 50,
) -> list[TestCase]:
    """Return cases in a specific review status for the project."""
    real_pid = resolve_project_id(db, project_id)
    return (
        db.execute(
            select(TestCase)
            .where(
                TestCase.project_id == real_pid,
                TestCase.review_status == status,
                TestCase.archived.is_(False),
            )
            .order_by(TestCase.updated_at.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
