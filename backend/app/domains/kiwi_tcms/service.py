"""Kiwi TCMS integration service.

HTTP-agnostic: raises ValueError/KeyError, not HTTPException. Owns connection
CRUD (secret encrypted transparently via ``EncryptedString``), connection test,
dry-run preview, and the idempotent import-sync engine that upserts Kiwi data
into the existing ``test_management`` models keyed by ``KiwiIdMap``.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.kiwi_tcms import mappers
from app.domains.kiwi_tcms.client import KiwiClient, KiwiError
from app.domains.kiwi_tcms.models import KiwiConnection, KiwiIdMap, KiwiSyncJob
from app.domains.test_management.models import (
    DefectLink,
    TestCase,
    TestCaseStep,
    TestCycle,
    TestManagementAuditEvent,
    TestManagementProject,
    TestPlan,
    TestRun,
    TestRunCase,
    TestSuite,
)

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _actor_id(user: Any | None) -> Optional[str]:
    return getattr(user, "id", None) if user is not None else None


def _empty_totals() -> dict[str, dict[str, int]]:
    return {
        "suites": {"created": 0, "updated": 0, "skipped": 0, "errors": 0},
        "cases": {"created": 0, "updated": 0, "skipped": 0, "errors": 0},
        "plans": {"created": 0, "updated": 0, "skipped": 0, "errors": 0},
        "runs": {"created": 0, "updated": 0, "skipped": 0, "errors": 0},
        "executions": {"created": 0, "updated": 0, "skipped": 0, "errors": 0},
        "defects": {"created": 0, "updated": 0, "skipped": 0, "errors": 0},
    }


# ── connection CRUD ────────────────────────────────────────────────────
def get_connection(db: Session, project_id: str) -> Optional[KiwiConnection]:
    return db.scalar(select(KiwiConnection).where(KiwiConnection.project_id == project_id))


def connection_out(conn: KiwiConnection) -> dict[str, Any]:
    """Serialize without ever exposing the secret."""
    return {
        "id": conn.id,
        "project_id": conn.project_id,
        "base_url": conn.base_url,
        "username": conn.username,
        "has_secret": bool(conn.secret),
        "kiwi_product_id": conn.kiwi_product_id,
        "verify_ssl": conn.verify_ssl,
        "status": conn.status,
        "last_error": conn.last_error,
        "last_tested_at": conn.last_tested_at,
        "last_synced_at": conn.last_synced_at,
        "created_at": conn.created_at,
        "updated_at": conn.updated_at,
    }


def upsert_connection(db: Session, project_id: str, payload: Any, user: Any | None) -> KiwiConnection:
    """Create or update the project's Kiwi connection.

    A blank/omitted ``secret`` on update keeps the stored one. The secret is
    encrypted at-rest transparently by the ``EncryptedString`` column type.
    """
    project = db.get(TestManagementProject, project_id)
    if project is None:
        raise KeyError(f"Proje bulunamadı: {project_id}")

    conn = get_connection(db, project_id)
    if conn is None:
        conn = KiwiConnection(project_id=project_id, base_url="", username="", created_by=_actor_id(user))
        db.add(conn)

    conn.base_url = payload.base_url.rstrip("/")
    conn.username = payload.username
    conn.verify_ssl = payload.verify_ssl
    conn.kiwi_product_id = payload.kiwi_product_id
    if payload.secret:  # only overwrite when a new secret is supplied
        conn.secret = payload.secret
    conn.updated_at = _utcnow()
    if conn.status == "unconfigured" and conn.secret:
        conn.status = "ok" if conn.last_tested_at else "unconfigured"

    db.commit()
    db.refresh(conn)
    return conn


def _require_ready_connection(db: Session, project_id: str) -> KiwiConnection:
    conn = get_connection(db, project_id)
    if conn is None or not conn.base_url or not conn.secret:
        raise ValueError("Kiwi bağlantısı yapılandırılmamış (URL/kimlik bilgisi eksik)")
    return conn


# ── connection test & preview (async, inline) ─────────────────────────
async def test_connection(db: Session, project_id: str) -> dict[str, Any]:
    conn = _require_ready_connection(db, project_id)
    try:
        async with KiwiClient(conn.base_url, conn.username, conn.secret, verify_ssl=conn.verify_ssl) as kiwi:
            products = await kiwi.list_products()
        conn.status = "ok"
        conn.last_error = None
        conn.last_tested_at = _utcnow()
        db.commit()
        return {
            "ok": True,
            "product_count": len(products),
            "products": [
                {"id": p["id"], "name": p.get("name", f"Product {p['id']}")}
                for p in products
                if "id" in p
            ],
        }
    except KiwiError as exc:
        conn.status = "error"
        conn.last_error = str(exc)
        conn.last_tested_at = _utcnow()
        db.commit()
        return {"ok": False, "error": str(exc), "product_count": 0, "products": []}


async def preview_sync(db: Session, project_id: str) -> dict[str, Any]:
    conn = _require_ready_connection(db, project_id)
    if conn.kiwi_product_id is None:
        raise ValueError("Önizleme için bir Kiwi Product seçilmeli")
    try:
        async with KiwiClient(conn.base_url, conn.username, conn.secret, verify_ssl=conn.verify_ssl) as kiwi:
            pid = conn.kiwi_product_id
            categories = await kiwi.list_categories(pid)
            cases = await kiwi.list_cases(pid)
            plans = await kiwi.list_plans(pid)
            runs = await kiwi.list_runs(pid)
            # Execution count: sum over all runs (potentially many — cap at first 20 for preview)
            exec_count = 0
            for run in runs[:20]:
                execs = await kiwi.list_executions(run["id"])
                exec_count += len(execs)
        return {
            "ok": True,
            "counts": {
                "suites": len(categories),
                "cases": len(cases),
                "plans": len(plans),
                "runs": len(runs),
                "executions": exec_count,
            },
        }
    except KiwiError as exc:
        return {"ok": False, "error": str(exc), "counts": {}}


# ── sync job lifecycle ─────────────────────────────────────────────────
def enqueue_sync(db: Session, project_id: str, dry_run: bool, user: Any | None) -> KiwiSyncJob:
    """Create a queued sync job and dispatch it to the RQ worker."""
    conn = _require_ready_connection(db, project_id)
    if conn.kiwi_product_id is None:
        raise ValueError("Senkron için bir Kiwi Product seçilmeli")

    from app.domains.kiwi_tcms.tasks import run_kiwi_sync_job

    job = KiwiSyncJob(
        connection_id=conn.id,
        project_id=project_id,
        mode="import",
        status="queued",
        dry_run=dry_run,
        totals=_empty_totals(),
        created_by=_actor_id(user),
    )
    db.add(job)
    db.flush()

    try:
        from redis import Redis
        from rq import Queue

        from app.config import settings

        queue = Queue(settings.rq_queue_name, connection=Redis.from_url(settings.redis_url))
        rq_job = queue.enqueue(run_kiwi_sync_job, job.id)
        job.rq_job_id = rq_job.id
    except Exception as exc:  # Redis yoksa job 'queued' kalır; worker sonra alır / manuel tetiklenir
        logger.warning("Kiwi sync RQ enqueue başarısız: %s", exc)

    db.commit()
    db.refresh(job)
    return job


def list_sync_jobs(db: Session, project_id: str, limit: int = 50) -> list[KiwiSyncJob]:
    limit = min(int(limit), 200)
    return list(
        db.scalars(
            select(KiwiSyncJob)
            .where(KiwiSyncJob.project_id == project_id)
            .order_by(KiwiSyncJob.created_at.desc())
            .limit(limit)
        ).all()
    )


def get_sync_job(db: Session, project_id: str, job_id: str) -> KiwiSyncJob:
    job = db.get(KiwiSyncJob, job_id)
    if job is None or job.project_id != project_id:
        raise KeyError(f"Sync job bulunamadı: {job_id}")
    return job


# ── sync engine (sync context; called from RQ worker) ─────────────────
async def _fetch_all(conn: KiwiConnection) -> dict[str, list[dict[str, Any]]]:
    """Pull every object type needed for full sync over a single Kiwi session."""
    async with KiwiClient(conn.base_url, conn.username, conn.secret, verify_ssl=conn.verify_ssl) as kiwi:
        pid = conn.kiwi_product_id
        categories = await kiwi.list_categories(pid)
        cases = await kiwi.list_cases(pid)
        plans = await kiwi.list_plans(pid)
        runs = await kiwi.list_runs(pid)
        # Fetch executions for every run (sequential; acceptable for typical dataset sizes)
        executions: list[dict[str, Any]] = []
        for run in runs:
            try:
                execs = await kiwi.list_executions(run["id"])
                executions.extend(execs)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Kiwi execution fetch hatası (run=%s): %s", run.get("id"), exc)
        # Bugs — tolerate if the endpoint isn't available on this Kiwi version
        bugs: list[dict[str, Any]] = []
        try:
            bugs = await kiwi.list_bugs(pid)
        except Exception as exc:  # noqa: BLE001
            logger.info("Kiwi Bug.filter kullanılamadı (normal): %s", exc)
        return {
            "categories": categories,
            "cases": cases,
            "plans": plans,
            "runs": runs,
            "executions": executions,
            "bugs": bugs,
        }


def execute_sync(db: Session, job: KiwiSyncJob) -> dict[str, Any]:
    """Fetch from Kiwi then upsert suites + cases. Returns totals.

    Idempotent: ``KiwiIdMap`` decides create-vs-update; case fingerprints skip
    unchanged records. With ``job.dry_run`` nothing is persisted.
    """
    conn = job.connection
    project = db.get(TestManagementProject, job.project_id)
    if project is None:
        raise KeyError(f"Proje bulunamadı: {job.project_id}")

    data = asyncio.run(_fetch_all(conn))
    totals = _empty_totals()

    # 1) Categories → Suites. Build external_id → internal suite id map.
    suite_by_ext: dict[str, str] = {}
    for raw in data["categories"]:
        try:
            mapped = mappers.map_category_to_suite(raw)
            suite_id = _upsert_suite(db, project, conn.id, mapped, totals, dry_run=job.dry_run)
            suite_by_ext[mapped["external_id"]] = suite_id
        except Exception as exc:  # one bad record shouldn't abort the whole run
            totals["suites"]["errors"] += 1
            logger.warning("Kiwi suite upsert hatası (cat=%s): %s", raw.get("id"), exc)

    # 2) Cases → Cases (+ steps).
    for raw in data["cases"]:
        try:
            mapped = mappers.map_case_to_neurex(raw)
            suite_id = suite_by_ext.get(mapped.get("category_external_id") or "")
            _upsert_case(db, project, conn.id, mapped, suite_id, totals, dry_run=job.dry_run)
        except Exception as exc:
            totals["cases"]["errors"] += 1
            logger.warning("Kiwi case upsert hatası (case=%s): %s", raw.get("id"), exc)

    # 3) TestPlan → TestPlan. Build external_id → internal plan id map.
    plan_by_ext: dict[str, str] = {}
    for raw in data.get("plans", []):
        try:
            mapped = mappers.map_plan_to_neurex(raw)
            plan_id = _upsert_plan(db, project, conn.id, mapped, totals, dry_run=job.dry_run)
            plan_by_ext[mapped["external_id"]] = plan_id
        except Exception as exc:
            totals["plans"]["errors"] += 1
            logger.warning("Kiwi plan upsert hatası (plan=%s): %s", raw.get("id"), exc)

    # 4) TestRun → TestCycle + TestRun. Build external_id → internal run id map.
    run_by_ext: dict[str, str] = {}
    for raw in data.get("runs", []):
        try:
            mapped = mappers.map_run_to_neurex(raw)
            plan_internal_id = plan_by_ext.get(mapped.get("plan_external_id") or "")
            run_id = _upsert_run(db, project, conn.id, mapped, plan_internal_id, totals, dry_run=job.dry_run)
            run_by_ext[mapped["external_id"]] = run_id
        except Exception as exc:
            totals["runs"]["errors"] += 1
            logger.warning("Kiwi run upsert hatası (run=%s): %s", raw.get("id"), exc)

    # 5) TestExecution → TestRunCase. Build external_id → run-case id map for defect links.
    exec_by_ext: dict[str, str] = {}
    for raw in data.get("executions", []):
        try:
            mapped = mappers.map_execution_to_neurex(raw)
            run_internal_id = run_by_ext.get(mapped.get("run_external_id") or "")
            rc_id = _upsert_execution(db, project, conn.id, mapped, run_internal_id, totals, dry_run=job.dry_run)
            if rc_id:
                exec_by_ext[mapped["external_id"]] = rc_id
        except Exception as exc:
            totals["executions"]["errors"] += 1
            logger.warning("Kiwi execution upsert hatası (exec=%s): %s", raw.get("id"), exc)

    # 6) Bug → DefectLink.
    for raw in data.get("bugs", []):
        try:
            mapped = mappers.map_bug_to_neurex(raw)
            run_case_id = exec_by_ext.get(mapped.get("execution_external_id") or "")
            _upsert_defect(db, conn.id, mapped, run_case_id, totals, dry_run=job.dry_run)
        except Exception as exc:
            totals["defects"]["errors"] += 1
            logger.warning("Kiwi bug upsert hatası (bug=%s): %s", raw.get("id"), exc)

    if job.dry_run:
        db.rollback()
    else:
        conn.last_synced_at = _utcnow()
        db.add(
            TestManagementAuditEvent(
                project_id=project.id,
                actor_id=job.created_by,
                action="kiwi_sync",
                entity_type="kiwi_sync_job",
                entity_id=job.id,
                payload={"totals": totals, "dry_run": False},
            )
        )
        db.commit()

    return totals


def _get_idmap(db: Session, conn_id: str, entity_type: str, external_id: str) -> Optional[KiwiIdMap]:
    return db.scalar(
        select(KiwiIdMap).where(
            KiwiIdMap.connection_id == conn_id,
            KiwiIdMap.entity_type == entity_type,
            KiwiIdMap.external_id == external_id,
        )
    )


def _upsert_suite(
    db: Session,
    project: TestManagementProject,
    conn_id: str,
    mapped: dict[str, Any],
    totals: dict[str, dict[str, int]],
    *,
    dry_run: bool,
) -> str:
    ext_id = mapped["external_id"]
    idmap = _get_idmap(db, conn_id, "suite", ext_id)

    if idmap is not None:
        suite = db.get(TestSuite, idmap.internal_id)
        if suite is not None:
            if not dry_run:
                suite.name = mapped["name"]
                suite.description = mapped["description"]
            totals["suites"]["updated"] += 1
            return suite.id

    # No mapping yet — reuse an existing same-named suite (manual import) if present.
    existing = db.scalar(
        select(TestSuite).where(TestSuite.project_id == project.id, TestSuite.name == mapped["name"])
    )
    if dry_run:
        if existing is not None:
            totals["suites"]["updated"] += 1
            return existing.id
        totals["suites"]["created"] += 1
        return "dry-run"

    suite = existing
    if suite is None:
        suite = TestSuite(project_id=project.id, name=mapped["name"], description=mapped["description"])
        db.add(suite)
        db.flush()
        totals["suites"]["created"] += 1
    else:
        totals["suites"]["updated"] += 1

    db.add(
        KiwiIdMap(
            connection_id=conn_id,
            entity_type="suite",
            external_id=ext_id,
            internal_id=suite.id,
            last_synced_at=_utcnow(),
        )
    )
    return suite.id


def _upsert_case(
    db: Session,
    project: TestManagementProject,
    conn_id: str,
    mapped: dict[str, Any],
    suite_id: Optional[str],
    totals: dict[str, dict[str, int]],
    *,
    dry_run: bool,
) -> None:
    ext_id = mapped["external_id"]
    fingerprint = mappers.case_fingerprint(mapped)
    case_key = f"{project.key}-KIWI-{ext_id}"
    idmap = _get_idmap(db, conn_id, "case", ext_id)

    # Locate the existing case via id map, falling back to the stable case_key.
    case: Optional[TestCase] = None
    if idmap is not None:
        case = db.get(TestCase, idmap.internal_id)
    if case is None:
        case = db.scalar(
            select(TestCase).where(TestCase.project_id == project.id, TestCase.case_key == case_key)
        )

    if case is not None:
        if idmap is not None and idmap.fingerprint == fingerprint:
            totals["cases"]["skipped"] += 1
            return
        if dry_run:
            totals["cases"]["updated"] += 1
            return
        _apply_case_fields(case, mapped, suite_id)
        _replace_steps(db, case, mapped["steps"])
        if idmap is None:
            db.add(
                KiwiIdMap(
                    connection_id=conn_id,
                    entity_type="case",
                    external_id=ext_id,
                    internal_id=case.id,
                    fingerprint=fingerprint,
                    last_synced_at=_utcnow(),
                )
            )
        else:
            idmap.fingerprint = fingerprint
            idmap.last_synced_at = _utcnow()
        totals["cases"]["updated"] += 1
        return

    # Create.
    if dry_run:
        totals["cases"]["created"] += 1
        return
    case = TestCase(
        project_id=project.id,
        suite_id=suite_id,
        case_key=case_key,
        title=mapped["title"],
        objective=mapped["objective"],
        preconditions=mapped["preconditions"],
        priority=mapped["priority"],
        automation_status=mapped["automation_status"],
        status=mapped["status"],
        tags=mapped["tags"],
        source_type="kiwi",
        source_ref=mapped["source_ref"],
    )
    db.add(case)
    db.flush()
    _replace_steps(db, case, mapped["steps"])
    db.add(
        KiwiIdMap(
            connection_id=conn_id,
            entity_type="case",
            external_id=ext_id,
            internal_id=case.id,
            fingerprint=fingerprint,
            last_synced_at=_utcnow(),
        )
    )
    totals["cases"]["created"] += 1


def _apply_case_fields(case: TestCase, mapped: dict[str, Any], suite_id: Optional[str]) -> None:
    case.title = mapped["title"]
    case.objective = mapped["objective"]
    case.preconditions = mapped["preconditions"]
    case.priority = mapped["priority"]
    case.automation_status = mapped["automation_status"]
    case.status = mapped["status"]
    case.tags = mapped["tags"]
    if suite_id is not None:
        case.suite_id = suite_id


def _replace_steps(db: Session, case: TestCase, steps: list[dict[str, Any]]) -> None:
    had_steps = bool(case.steps)
    for existing in list(case.steps):
        db.delete(existing)
    case.steps.clear()
    # Emit the DELETEs before re-inserting the same (case_id, step_no) keys,
    # otherwise the unit-of-work may order the INSERT first → unique violation.
    if had_steps:
        db.flush()
    for step in steps:
        db.add(
            TestCaseStep(
                case_id=case.id,
                step_no=step["step_no"],
                action=step["action"],
                expected_result=step.get("expected_result", ""),
                is_required=step.get("is_required", True),
            )
        )


# ── Faz 2 upsert helpers ───────────────────────────────────────────────
def _upsert_plan(
    db: Session,
    project: TestManagementProject,
    conn_id: str,
    mapped: dict[str, Any],
    totals: dict[str, dict[str, int]],
    *,
    dry_run: bool,
) -> str:
    ext_id = mapped["external_id"]
    fingerprint = mappers.plan_fingerprint(mapped)
    idmap = _get_idmap(db, conn_id, "plan", ext_id)

    if idmap is not None:
        plan = db.get(TestPlan, idmap.internal_id)
        if plan is not None:
            if idmap.fingerprint == fingerprint:
                totals["plans"]["skipped"] += 1
                return plan.id
            if not dry_run:
                plan.name = mapped["name"]
                plan.plan_type = mapped["plan_type"]
                plan.scope_summary = mapped["scope_summary"]
                idmap.fingerprint = fingerprint
                idmap.last_synced_at = _utcnow()
            totals["plans"]["updated"] += 1
            return plan.id

    if dry_run:
        totals["plans"]["created"] += 1
        return "dry-run"

    plan = TestPlan(
        project_id=project.id,
        name=mapped["name"],
        plan_type=mapped["plan_type"],
        scope_summary=mapped["scope_summary"],
    )
    db.add(plan)
    db.flush()
    db.add(KiwiIdMap(
        connection_id=conn_id,
        entity_type="plan",
        external_id=ext_id,
        internal_id=plan.id,
        fingerprint=fingerprint,
        last_synced_at=_utcnow(),
    ))
    totals["plans"]["created"] += 1
    return plan.id


def _upsert_run(
    db: Session,
    project: TestManagementProject,
    conn_id: str,
    mapped: dict[str, Any],
    plan_internal_id: Optional[str],
    totals: dict[str, dict[str, int]],
    *,
    dry_run: bool,
) -> str:
    """Kiwi TestRun → Neurex TestCycle + TestRun (Neurex requires a Cycle as container)."""
    ext_id = mapped["external_id"]
    fingerprint = mappers.run_fingerprint(mapped)
    idmap = _get_idmap(db, conn_id, "run", ext_id)

    if idmap is not None:
        run = db.get(TestRun, idmap.internal_id)
        if run is not None:
            if idmap.fingerprint == fingerprint:
                totals["runs"]["skipped"] += 1
                return run.id
            if not dry_run:
                run.name = mapped["name"]
                run.status = mapped["status"]
                cycle = run.cycle
                if cycle:
                    cycle.build_version = mapped["build_version"]
                    cycle.environment = mapped["environment"]
                    cycle.status = mapped["status"]
                idmap.fingerprint = fingerprint
                idmap.last_synced_at = _utcnow()
            totals["runs"]["updated"] += 1
            return run.id

    if dry_run:
        totals["runs"]["created"] += 1
        return "dry-run"

    # Need a plan to attach the cycle. Create a placeholder plan if not found.
    if plan_internal_id is None:
        placeholder = db.scalar(
            select(TestPlan).where(
                TestPlan.project_id == project.id,
                TestPlan.name == "Kiwi Import",
            )
        )
        if placeholder is None:
            placeholder = TestPlan(project_id=project.id, name="Kiwi Import", plan_type="regression")
            db.add(placeholder)
            db.flush()
        plan_internal_id = placeholder.id

    cycle = TestCycle(
        plan_id=plan_internal_id,
        project_id=project.id,
        name=mapped["name"],
        environment=mapped["environment"],
        build_version=mapped["build_version"],
        status=mapped["status"],
    )
    db.add(cycle)
    db.flush()

    run = TestRun(
        cycle_id=cycle.id,
        name=mapped["name"],
        status=mapped["status"],
        source_type="kiwi",
        environment=mapped["environment"],
    )
    db.add(run)
    db.flush()

    db.add(KiwiIdMap(
        connection_id=conn_id,
        entity_type="run",
        external_id=ext_id,
        internal_id=run.id,
        fingerprint=fingerprint,
        last_synced_at=_utcnow(),
    ))
    totals["runs"]["created"] += 1
    return run.id


def _upsert_execution(
    db: Session,
    project: TestManagementProject,
    conn_id: str,
    mapped: dict[str, Any],
    run_internal_id: Optional[str],
    totals: dict[str, dict[str, int]],
    *,
    dry_run: bool,
) -> Optional[str]:
    """Kiwi TestExecution → Neurex TestRunCase."""
    ext_id = mapped["external_id"]
    idmap = _get_idmap(db, conn_id, "execution", ext_id)

    if idmap is not None:
        rc = db.get(TestRunCase, idmap.internal_id)
        if rc is not None:
            if rc.status == mapped["status"]:
                totals["executions"]["skipped"] += 1
                return rc.id
            if not dry_run:
                rc.status = mapped["status"]
                rc.execution_notes = mapped["execution_notes"]
                idmap.last_synced_at = _utcnow()
            totals["executions"]["updated"] += 1
            return rc.id

    # Locate the internal case via KiwiIdMap
    case_ext_id = mapped.get("case_external_id")
    case_idmap = _get_idmap(db, conn_id, "case", case_ext_id or "") if case_ext_id else None
    case = db.get(TestCase, case_idmap.internal_id) if case_idmap else None

    if case is None or run_internal_id is None:
        # Can't link — skip but don't count as error
        totals["executions"]["skipped"] += 1
        return None

    if dry_run:
        totals["executions"]["created"] += 1
        return "dry-run"

    # Check for existing run-case (handles partial syncs / orphan cleanup)
    existing_rc = db.scalar(
        select(TestRunCase).where(
            TestRunCase.run_id == run_internal_id,
            TestRunCase.case_id == case.id,
        )
    )
    if existing_rc:
        existing_rc.status = mapped["status"]
        existing_rc.execution_notes = mapped["execution_notes"]
        totals["executions"]["updated"] += 1
        rc = existing_rc
    else:
        rc = TestRunCase(
            run_id=run_internal_id,
            case_id=case.id,
            case_version_no=case.current_version,
            case_snapshot={},
            status=mapped["status"],
            execution_notes=mapped["execution_notes"],
        )
        db.add(rc)
        db.flush()
        totals["executions"]["created"] += 1

    db.add(KiwiIdMap(
        connection_id=conn_id,
        entity_type="execution",
        external_id=ext_id,
        internal_id=rc.id,
        last_synced_at=_utcnow(),
    ))
    return rc.id


def _upsert_defect(
    db: Session,
    conn_id: str,
    mapped: dict[str, Any],
    run_case_id: Optional[str],
    totals: dict[str, dict[str, int]],
    *,
    dry_run: bool,
) -> None:
    """Kiwi Bug → Neurex DefectLink (requires a run_case_id)."""
    if not run_case_id:
        totals["defects"]["skipped"] += 1
        return

    ext_id = mapped["external_id"]
    idmap = _get_idmap(db, conn_id, "defect", ext_id)

    if idmap is not None:
        defect = db.get(DefectLink, idmap.internal_id)
        if defect is not None:
            totals["defects"]["skipped"] += 1
            return

    if dry_run:
        totals["defects"]["created"] += 1
        return

    # Prevent duplicate external_key on the same run_case
    existing = db.scalar(
        select(DefectLink).where(
            DefectLink.run_case_id == run_case_id,
            DefectLink.external_source == "kiwi",
            DefectLink.external_key == mapped["external_key"],
        )
    )
    if existing:
        totals["defects"]["skipped"] += 1
        if idmap is None:
            db.add(KiwiIdMap(
                connection_id=conn_id,
                entity_type="defect",
                external_id=ext_id,
                internal_id=existing.id,
                last_synced_at=_utcnow(),
            ))
        return

    defect = DefectLink(
        run_case_id=run_case_id,
        external_source="kiwi",
        external_key=mapped["external_key"],
        title=mapped["title"],
        status=mapped["status"],
        url=mapped["url"],
    )
    db.add(defect)
    db.flush()
    db.add(KiwiIdMap(
        connection_id=conn_id,
        entity_type="defect",
        external_id=ext_id,
        internal_id=defect.id,
        last_synced_at=_utcnow(),
    ))
    totals["defects"]["created"] += 1
