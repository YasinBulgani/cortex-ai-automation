"""Central orchestration surface for automation runs.

The first implementation is intentionally adapter-based and conservative:
it creates a normalized run record and points callers to the existing
specialized runner UI/API instead of moving runner ownership all at once.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import RLock
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.infra.models import AutomationRun
from .schemas import (
    AutomationBrainSummary,
    AutomationCapability,
    AutomationKind,
    AutomationProvenance,
    AutomationRunCreate,
    AutomationRunList,
    AutomationRunOut,
)


@dataclass(frozen=True)  # slots=True requires Python 3.10+; removed for 3.9 compat
class AutomationAdapter:
    kind: AutomationKind
    label: str
    description: str
    provenance: AutomationProvenance
    route_template: str
    required_fields: tuple[str, ...] = ()

    def capability(self) -> AutomationCapability:
        return AutomationCapability(
            kind=self.kind,
            label=self.label,
            description=self.description,
            provenance=self.provenance,
            required_fields=list(self.required_fields),
            route_hint=self.route_template,
        )

    def next_action(self, run: AutomationRunOut) -> dict[str, str]:
        route = self.route_template.format(project_id=run.project_id)
        if self.kind == "web" and run.target:
            route = f"{route}?feature={run.target}"
        return {
            "type": "open_runner",
            "label": "Koşumu aç",
            "href": route,
        }


ADAPTERS: dict[AutomationKind, AutomationAdapter] = {
    "web": AutomationAdapter(
        kind="web",
        label="Web E2E",
        description="Playwright/Gherkin web otomasyon koşumları",
        provenance="real",
        route_template="/p/{project_id}/executions/new",
    ),
    "mobile": AutomationAdapter(
        kind="mobile",
        label="Mobile Farm",
        description="Appium cihaz farm koşumları ve 2 cihazlı hızlı doğrulama",
        provenance="real",
        route_template="/p/{project_id}/mobile",
        required_fields=("device",),
    ),
    "api": AutomationAdapter(
        kind="api",
        label="API Tests",
        description="API test-case koşumları, assertion sonuçları ve feedback loop",
        provenance="real",
        route_template="/p/{project_id}/api-testing",
    ),
    "llm": AutomationAdapter(
        kind="llm",
        label="LLM Agent",
        description="LLM destekli test üretim, analiz ve iyileştirme akışları",
        provenance="fallback",
        route_template="/p/{project_id}/llm-agent",
    ),
    "regression": AutomationAdapter(
        kind="regression",
        label="Regression",
        description="Risk tabanlı regresyon önerisi ve koşum seçimi",
        provenance="fallback",
        route_template="/p/{project_id}/regression",
    ),
}


def _has_api_targets(request: AutomationRunCreate) -> bool:
    if isinstance(request.metadata.get("test_case_ids"), list):
        return True
    return bool(request.target)


class AutomationRunStore:
    """Small in-memory store used until the run contract is persisted."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._runs: dict[str, AutomationRunOut] = {}

    def create(self, request: AutomationRunCreate, *, created_by: str | None = None, retry_of: str | None = None) -> AutomationRunOut:
        adapter = ADAPTERS[request.kind]
        now = datetime.now(timezone.utc)
        initial_provenance: AutomationProvenance = "fallback"
        if request.execute_now and (
            (request.kind == "web" and request.target) or request.kind == "mobile"
            or (request.kind == "api" and _has_api_targets(request))
            or request.kind == "regression"
        ):
            initial_provenance = "real"
        run = AutomationRunOut(
            id=f"arun_{uuid4().hex[:12]}",
            project_id=request.project_id,
            kind=request.kind,
            name=request.name or f"{adapter.label} run",
            status="queued",
            trigger="retry" if retry_of else request.trigger,
            environment=request.environment,
            device=request.device,
            target=request.target,
            provenance=initial_provenance,
            created_at=now,
            metrics={
                "normalized_contract": True,
                "adapter": request.kind,
            },
            retry_of=retry_of,
            created_by=created_by,
            metadata=request.metadata,
        )
        run.next_action = adapter.next_action(run)
        with self._lock:
            self._runs[run.id] = run
        return run

    def list(self, *, project_id: str | None = None, limit: int = 50) -> list[AutomationRunOut]:
        with self._lock:
            runs = list(self._runs.values())
        if project_id:
            runs = [run for run in runs if run.project_id == project_id]
        runs.sort(key=lambda run: run.created_at, reverse=True)
        return runs[:limit]

    def get(self, run_id: str) -> AutomationRunOut | None:
        with self._lock:
            return self._runs.get(run_id)

    def replace(self, run: AutomationRunOut) -> AutomationRunOut:
        with self._lock:
            self._runs[run.id] = run
        return run


class AutomationBrainService:
    def __init__(self, store: AutomationRunStore | None = None) -> None:
        self.store = store or AutomationRunStore()

    def capabilities(self) -> list[AutomationCapability]:
        return [adapter.capability() for adapter in ADAPTERS.values()]

    def summary(self, db: object = None, *, project_id: str | None = None) -> AutomationBrainSummary:  # noqa: ANN001
        runs = self.store.list(project_id=project_id, limit=100)
        return AutomationBrainSummary(
            capabilities=self.capabilities(),
            active_runs=sum(1 for run in runs if run.status == "running"),
            queued_runs=sum(1 for run in runs if run.status == "queued"),
            last_run=runs[0] if runs else None,
        )

    def create_run(self, db_or_request: "object | AutomationRunCreate", request: "AutomationRunCreate | None" = None, *, created_by: str | None = None) -> AutomationRunOut:  # noqa: ANN001
        # Accept (db, request) or (request,) signatures for service-layer compatibility
        if request is None:
            actual_request = db_or_request  # type: ignore[assignment]
        else:
            actual_request = request
        return self.store.create(actual_request, created_by=created_by)  # type: ignore[arg-type]

    def list_runs(self, db: object = None, *, project_id: str | None = None, limit: int = 50) -> AutomationRunList:  # noqa: ANN001
        items = self.store.list(project_id=project_id, limit=limit)
        return AutomationRunList(items=items, total=len(items))

    def get_run(self, run_id: str) -> AutomationRunOut | None:
        return self.store.get(run_id)

    def cancel_run(self, run_id: str) -> AutomationRunOut | None:
        run = self.store.get(run_id)
        if run is None:
            return None
        if run.status in {"passed", "failed", "cancelled"}:
            return run
        updated = run.model_copy(
            update={
                "status": "cancelled",
                "finished_at": datetime.now(timezone.utc),
                "error": "Kullanıcı tarafından iptal edildi",
            },
        )
        return self.store.replace(updated)

    def retry_run(self, run_id: str, *, created_by: str | None = None) -> AutomationRunOut | None:
        run = self.store.get(run_id)
        if run is None:
            return None
        return self.store.create(
            AutomationRunCreate(
                project_id=run.project_id,
                kind=run.kind,
                name=f"{run.name} retry",
                trigger="retry",
                environment=run.environment,
                device=run.device,
                target=run.target,
                metadata={**run.metadata, "retry_source": run.id},
            ),
            created_by=created_by,
            retry_of=run.id,
        )


class SqlAlchemyAutomationRunStore:
    """SQL-backed run store for the normalized automation contract."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, request: AutomationRunCreate, *, created_by: str | None = None, retry_of: str | None = None) -> AutomationRunOut:
        adapter = ADAPTERS[request.kind]
        now = datetime.now(timezone.utc)
        initial_provenance: AutomationProvenance = "fallback"
        if request.execute_now and (
            (request.kind == "web" and request.target) or request.kind == "mobile"
            or (request.kind == "api" and _has_api_targets(request))
            or request.kind == "regression"
        ):
            initial_provenance = "real"
        run = AutomationRunOut(
            id=f"arun_{uuid4().hex[:12]}",
            project_id=request.project_id,
            kind=request.kind,
            name=request.name or f"{adapter.label} run",
            status="queued",
            trigger="retry" if retry_of else request.trigger,
            environment=request.environment,
            device=request.device,
            target=request.target,
            provenance=initial_provenance,
            created_at=now,
            metrics={
                "normalized_contract": True,
                "adapter": request.kind,
            },
            retry_of=retry_of,
            created_by=created_by,
            metadata=request.metadata,
        )
        run.next_action = adapter.next_action(run)
        self.db.add(self._to_model(run))
        self.db.commit()
        return run

    def list(self, *, project_id: str | None = None, limit: int = 50) -> list[AutomationRunOut]:
        stmt = select(AutomationRun).order_by(AutomationRun.created_at.desc()).limit(limit)
        if project_id:
            stmt = stmt.where(AutomationRun.project_id == project_id)
        return [self._to_out(row) for row in self.db.execute(stmt).scalars().all()]

    def get(self, run_id: str) -> AutomationRunOut | None:
        row = self.db.get(AutomationRun, run_id)
        return self._to_out(row) if row is not None else None

    def replace(self, run: AutomationRunOut) -> AutomationRunOut:
        row = self.db.get(AutomationRun, run.id)
        if row is None:
            self.db.add(self._to_model(run))
        else:
            row.status = run.status
            row.finished_at = run.finished_at
            row.started_at = run.started_at
            row.duration_ms = run.duration_ms
            row.error = run.error
            row.artifacts = run.artifacts
            row.metrics = run.metrics
            row.next_action = run.next_action
            row.run_metadata = run.metadata
        self.db.commit()
        return run

    @staticmethod
    def _to_model(run: AutomationRunOut) -> AutomationRun:
        return AutomationRun(
            id=run.id,
            project_id=run.project_id,
            kind=run.kind,
            name=run.name,
            status=run.status,
            trigger=run.trigger,
            environment=run.environment,
            device=run.device,
            target=run.target,
            provenance=run.provenance,
            created_by=run.created_by,
            retry_of=run.retry_of,
            error=run.error,
            artifacts=run.artifacts,
            metrics=run.metrics,
            next_action=run.next_action,
            run_metadata=run.metadata,
            created_at=run.created_at,
            started_at=run.started_at,
            finished_at=run.finished_at,
            duration_ms=run.duration_ms,
        )

    @staticmethod
    def _to_out(row: AutomationRun) -> AutomationRunOut:
        return AutomationRunOut(
            id=row.id,
            project_id=row.project_id,
            kind=row.kind,  # type: ignore[arg-type]
            name=row.name,
            status=row.status,  # type: ignore[arg-type]
            trigger=row.trigger,  # type: ignore[arg-type]
            environment=row.environment,
            device=row.device,
            target=row.target,
            provenance=row.provenance,  # type: ignore[arg-type]
            created_at=row.created_at,
            started_at=row.started_at,
            finished_at=row.finished_at,
            duration_ms=row.duration_ms,
            artifacts=row.artifacts or [],
            metrics=row.metrics or {},
            next_action=row.next_action,
            error=row.error,
            retry_of=row.retry_of,
            created_by=row.created_by,
            metadata=row.run_metadata or {},
        )


brain_service = AutomationBrainService()
