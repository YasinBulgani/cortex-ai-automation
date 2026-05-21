"""Run Store — In-memory (Postgres backend Faz 2'de)."""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from .state import AgentState, create_initial_state

logger = logging.getLogger(__name__)


@dataclass
class RunArtifact:
    artifact_id: str
    kind: str
    name: str
    storage_path: str
    mime_type: str = "application/octet-stream"
    size_bytes: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "kind": self.kind,
            "name": self.name,
            "storage_path": self.storage_path,
            "mime_type": self.mime_type,
            "size_bytes": self.size_bytes,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


@dataclass
class RunRecord:
    run_id: str
    project_id: str
    tenant_id: str
    user_id: str
    input_source: str
    status: str = "queued"
    created_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    state: AgentState = field(default_factory=dict)  # type: ignore[arg-type]
    events: list[dict] = field(default_factory=list)
    artifacts: list[RunArtifact] = field(default_factory=list)
    approvals: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None

    def to_status_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "project_id": self.project_id,
            "status": self.status,
            "input_source": self.input_source,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "error": self.error,
            "event_count": len(self.events),
            "artifact_count": len(self.artifacts),
            "approval_count": len(self.approvals),
            "cost_usd": self.state.get("cost_usd", 0.0) if self.state else 0.0,
            "tokens_used": self.state.get("tokens_used", 0) if self.state else 0,
            "llm_calls_count": self.state.get("llm_calls_count", 0) if self.state else 0,
            "errors": self.state.get("errors", []) if self.state else [],
            "intent_graph": self.state.get("intent_graph") if self.state else None,
            "app_map": self.state.get("app_map") if self.state else None,
            "scenarios": self.state.get("scenarios", []) if self.state else [],
            "generated_code": self.state.get("generated_code") if self.state else None,
            "run_result": self.state.get("run_result") if self.state else None,
            "healing_result": self.state.get("healing_result") if self.state else None,
            "review": self.state.get("review") if self.state else None,
            "report": self.state.get("report") if self.state else None,
        }


class RunStore:
    def __init__(self) -> None:
        self._runs: dict[str, RunRecord] = {}
        self._subscribers: dict[str, list[asyncio.Queue]] = {}
        self._dead_letters: list[dict[str, Any]] = []
        self._persist_mode = self._resolve_persist_mode()
        self._db_failed = False

    def create(
        self,
        *,
        project_id: str,
        user_id: str,
        tenant_id: str,
        input_source: str,
        input_payload: dict[str, Any],
    ) -> tuple[str, AgentState]:
        run_id = str(uuid4())
        initial_state = create_initial_state(
            project_id=project_id, user_id=user_id, tenant_id=tenant_id,
            run_id=run_id, input_source=input_source, input_payload=input_payload,
        )
        record = RunRecord(
            run_id=run_id, project_id=project_id, tenant_id=tenant_id,
            user_id=user_id, input_source=input_source, state=initial_state,
        )
        self._runs[run_id] = record
        self._persist_create(record, input_payload)
        return run_id, initial_state

    def get(self, run_id: str) -> RunRecord | None:
        rec = self._runs.get(run_id)
        if rec:
            return rec
        rec = self._load_run_from_db(run_id)
        if rec:
            self._runs[run_id] = rec
        return rec

    def list(
        self,
        *,
        project_id: str | None = None,
        tenant_id: str | None = None,
        limit: int = 50,
    ) -> list[RunRecord]:
        items = list(self._runs.values())
        if project_id:
            items = [r for r in items if r.project_id == project_id]
        if tenant_id:
            items = [r for r in items if r.tenant_id == tenant_id]
        for record in self._load_runs_from_db(
            project_id=project_id,
            tenant_id=tenant_id,
            limit=limit,
        ):
            if record.run_id not in self._runs:
                self._runs[record.run_id] = record
                items.append(record)
        items.sort(key=lambda r: r.created_at, reverse=True)
        return items[:limit]

    def update_status(self, run_id: str, status: str, error: str | None = None) -> None:
        rec = self._runs.get(run_id)
        if not rec:
            return
        rec.status = status
        if error:
            rec.error = error
        if status in ("completed", "failed", "failed_validation", "cancelled"):
            rec.completed_at = datetime.utcnow()
        self._persist_status(run_id, status, error)
        _record_workflow_status(rec.state.get("workflow_type"), status)

    def update_state(self, run_id: str, state: AgentState) -> None:
        rec = self._runs.get(run_id)
        if rec:
            rec.state = state
        self._persist_state(run_id, state)

    def list_events(self, run_id: str) -> list[dict[str, Any]]:
        rec = self._runs.get(run_id)
        if not rec:
            return []
        return list(rec.events)

    def add_artifact(
        self,
        run_id: str,
        *,
        kind: str,
        name: str,
        storage_path: str,
        mime_type: str = "application/octet-stream",
        size_bytes: int = 0,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        rec = self._runs.get(run_id)
        if not rec:
            return None
        metadata = _artifact_metadata_with_integrity(storage_path, size_bytes, metadata)
        if not size_bytes:
            size_bytes = int(metadata.get("size_bytes_verified") or 0)
        for artifact in rec.artifacts:
            if artifact.kind == kind and artifact.storage_path == storage_path:
                return artifact.to_dict()
        artifact = RunArtifact(
            artifact_id=str(uuid4()),
            kind=kind,
            name=name,
            storage_path=storage_path,
            mime_type=mime_type,
            size_bytes=size_bytes,
            metadata=metadata,
        )
        rec.artifacts.append(artifact)
        self._persist_artifact(run_id, artifact)
        return artifact.to_dict()

    def list_artifacts(self, run_id: str) -> list[dict[str, Any]]:
        rec = self._runs.get(run_id)
        if not rec:
            return []
        return [artifact.to_dict() for artifact in rec.artifacts]

    def record_approval(
        self,
        run_id: str,
        *,
        actor_id: str,
        decision: str,
        note: str | None = None,
    ) -> dict[str, Any] | None:
        rec = self._runs.get(run_id)
        if not rec:
            return None
        approval = {
            "approval_id": str(uuid4()),
            "run_id": run_id,
            "actor_id": actor_id,
            "decision": decision,
            "note": note,
            "created_at": datetime.utcnow(),
        }
        rec.approvals.append(approval)
        approvals = list(rec.state.get("approvals", [])) if rec.state else []
        approvals.append(approval)
        rec.state["approvals"] = approvals
        self._persist_approval(approval)
        _record_workflow_approval(decision)
        return approval

    def record_dead_letter(
        self,
        *,
        run_id: str | None,
        queue_name: str,
        reason: str,
        payload: dict[str, Any] | None = None,
        retry_count: int = 0,
        last_error: str | None = None,
    ) -> dict[str, Any]:
        item = {
            "dead_letter_id": str(uuid4()),
            "run_id": run_id,
            "queue_name": queue_name,
            "reason": reason,
            "payload": payload or {},
            "retry_count": retry_count,
            "last_error": last_error,
            "created_at": datetime.utcnow(),
        }
        self._dead_letters.append(item)
        self._persist_dead_letter(item)
        _record_workflow_dead_letter(queue_name, reason)
        return item

    def list_dead_letters(self, limit: int = 100) -> list[dict[str, Any]]:
        items = list(self._dead_letters)
        for item in self._load_dead_letters_from_db(limit=limit):
            if item["dead_letter_id"] not in {existing["dead_letter_id"] for existing in items}:
                items.append(item)
        items.sort(key=lambda item: item["created_at"], reverse=True)
        return items[:limit]

    def subscribe(self, run_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers.setdefault(run_id, []).append(q)
        return q

    def unsubscribe(self, run_id: str, q: asyncio.Queue) -> None:
        if run_id in self._subscribers:
            try:
                self._subscribers[run_id].remove(q)
            except ValueError:
                pass

    def publish(self, run_id: str, event: dict) -> None:
        rec = self._runs.get(run_id)
        if rec:
            rec.events.append(event)
        self._persist_event(run_id, event)
        _record_workflow_event(event.get("event_type"))
        for q in self._subscribers.get(run_id, []):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass

    def _persistence_enabled(self) -> bool:
        return self._persist_mode in {"auto", "postgres", "db"} and not self._db_failed

    def _resolve_persist_mode(self) -> str:
        mode = os.getenv("AGENTS_V2_RUN_STORE", "auto").strip().lower()
        if mode != "auto":
            return mode
        try:
            from app.config import settings

            if settings.is_production_like:
                return "postgres"
        except Exception as exc:
            logger.debug("agents/v2 run store prod-mode detection skipped: %s", exc)
        return mode

    def _persist_create(self, record: RunRecord, input_payload: dict[str, Any]) -> None:
        if not self._persistence_enabled():
            return
        project_id = _uuid_or_none(record.project_id)
        if project_id is None:
            return
        try:
            from app.infra.database import SessionLocal
            from app.infra.models import AgentV2Run

            workflow = input_payload.get("workflow") if isinstance(input_payload, dict) else {}
            with SessionLocal() as db:
                db.merge(
                    AgentV2Run(
                        id=record.run_id,
                        tenant_id=_uuid_or_none(record.tenant_id),
                        project_id=project_id,
                        user_id=_uuid_or_none(record.user_id),
                        input_source=record.input_source,
                        input_payload=_jsonable(input_payload),
                        status=record.status,
                        workflow_type=workflow.get("type") if isinstance(workflow, dict) else None,
                        dry_run=bool(workflow.get("dry_run")) if isinstance(workflow, dict) else False,
                        requires_approval=(
                            bool(workflow.get("requires_approval"))
                            if isinstance(workflow, dict)
                            else False
                        ),
                        errors=[],
                        created_at=record.created_at,
                    )
                )
                db.commit()
        except SQLAlchemyError as exc:
            self._handle_db_error("create", exc)

    def _persist_status(self, run_id: str, status: str, error: str | None) -> None:
        if not self._persistence_enabled() or _uuid_or_none(run_id) is None:
            return
        try:
            from app.infra.database import SessionLocal
            from app.infra.models import AgentV2Run, utcnow

            with SessionLocal() as db:
                row = db.get(AgentV2Run, run_id)
                if row is None:
                    return
                row.status = status
                if status == "running" and row.started_at is None:
                    row.started_at = utcnow()
                if status in {"completed", "failed", "failed_validation", "cancelled"}:
                    row.completed_at = utcnow()
                if error:
                    row.error_message = error
                db.commit()
        except SQLAlchemyError as exc:
            self._handle_db_error("status", exc)

    def _persist_state(self, run_id: str, state: AgentState) -> None:
        if not self._persistence_enabled() or _uuid_or_none(run_id) is None:
            return
        try:
            from app.infra.database import SessionLocal
            from app.infra.models import AgentV2Run

            with SessionLocal() as db:
                row = db.get(AgentV2Run, run_id)
                if row is None:
                    return
                row.intent_graph = _jsonable(state.get("intent_graph"))
                row.app_map = _jsonable(state.get("app_map"))
                row.scenarios = _jsonable(state.get("scenarios"))
                row.generated_code = _jsonable(state.get("generated_code"))
                row.run_result = _jsonable(state.get("run_result"))
                row.healing_result = _jsonable(state.get("healing_result"))
                row.review = _jsonable(state.get("review"))
                row.report = _jsonable(state.get("report"))
                row.errors = _jsonable(state.get("errors", [])) or []
                row.tokens_used = int(state.get("tokens_used", 0) or 0)
                row.llm_calls_count = int(state.get("llm_calls_count", 0) or 0)
                row.cost_usd = float(state.get("cost_usd", 0.0) or 0.0)
                completed_at = state.get("completed_at")
                if isinstance(completed_at, datetime):
                    row.completed_at = completed_at
                db.commit()
        except SQLAlchemyError as exc:
            self._handle_db_error("state", exc)

    def _persist_event(self, run_id: str, event: dict[str, Any]) -> None:
        if not self._persistence_enabled() or _uuid_or_none(run_id) is None:
            return
        try:
            from app.infra.database import SessionLocal
            from app.infra.models import AgentV2RunEvent

            with SessionLocal() as db:
                db.add(
                    AgentV2RunEvent(
                        run_id=run_id,
                        event_type=str(event.get("event_type", "message")),
                        agent_name=event.get("agent_name"),
                        message=event.get("message"),
                        payload=_jsonable(event) or {},
                    )
                )
                db.commit()
        except SQLAlchemyError as exc:
            self._handle_db_error("event", exc)

    def _persist_artifact(self, run_id: str, artifact: RunArtifact) -> None:
        if not self._persistence_enabled() or _uuid_or_none(run_id) is None:
            return
        try:
            from app.infra.database import SessionLocal
            from app.infra.models import AgentV2RunArtifact

            with SessionLocal() as db:
                existing = db.scalar(
                    select(AgentV2RunArtifact).where(
                        AgentV2RunArtifact.run_id == run_id,
                        AgentV2RunArtifact.kind == artifact.kind,
                        AgentV2RunArtifact.storage_path == artifact.storage_path,
                    )
                )
                if existing is None:
                    db.add(
                        AgentV2RunArtifact(
                            id=artifact.artifact_id,
                            run_id=run_id,
                            kind=artifact.kind,
                            name=artifact.name,
                            storage_path=artifact.storage_path,
                            mime_type=artifact.mime_type,
                            size_bytes=artifact.size_bytes,
                            metadata_json=_jsonable(artifact.metadata) or {},
                            created_at=artifact.created_at,
                        )
                    )
                    db.commit()
        except SQLAlchemyError as exc:
            self._handle_db_error("artifact", exc)

    def _persist_approval(self, approval: dict[str, Any]) -> None:
        if not self._persistence_enabled() or _uuid_or_none(approval.get("run_id")) is None:
            return
        try:
            from app.infra.database import SessionLocal
            from app.infra.models import AgentV2RunApproval

            with SessionLocal() as db:
                db.add(
                    AgentV2RunApproval(
                        id=approval["approval_id"],
                        run_id=approval["run_id"],
                        actor_user_id=_uuid_or_none(approval.get("actor_id")),
                        decision=approval["decision"],
                        note=approval.get("note"),
                        created_at=approval["created_at"],
                    )
                )
                db.commit()
        except SQLAlchemyError as exc:
            self._handle_db_error("approval", exc)

    def _persist_dead_letter(self, item: dict[str, Any]) -> None:
        if not self._persistence_enabled():
            return
        try:
            from app.infra.database import SessionLocal
            from app.infra.models import AgentV2DeadLetter

            with SessionLocal() as db:
                db.add(
                    AgentV2DeadLetter(
                        id=item["dead_letter_id"],
                        run_id=_uuid_or_none(item.get("run_id")),
                        queue_name=item["queue_name"],
                        reason=item["reason"],
                        payload=_jsonable(item.get("payload")) or {},
                        retry_count=int(item.get("retry_count") or 0),
                        last_error=item.get("last_error"),
                        created_at=item["created_at"],
                    )
                )
                db.commit()
        except SQLAlchemyError as exc:
            self._handle_db_error("dead_letter", exc)

    def _load_run_from_db(self, run_id: str) -> RunRecord | None:
        if not self._persistence_enabled() or _uuid_or_none(run_id) is None:
            return None
        try:
            from app.infra.database import SessionLocal
            from app.infra.models import AgentV2Run

            with SessionLocal() as db:
                row = db.get(AgentV2Run, run_id)
                if row is None:
                    return None
                return self._record_from_row(row)
        except SQLAlchemyError as exc:
            self._handle_db_error("load", exc)
            return None

    def _load_runs_from_db(
        self,
        *,
        project_id: str | None,
        tenant_id: str | None,
        limit: int,
    ) -> list[RunRecord]:
        if not self._persistence_enabled():
            return []
        project_uuid = _uuid_or_none(project_id) if project_id else None
        tenant_uuid = _uuid_or_none(tenant_id) if tenant_id else None
        if project_id and project_uuid is None:
            return []
        try:
            from app.infra.database import SessionLocal
            from app.infra.models import AgentV2Run

            stmt = select(AgentV2Run).order_by(AgentV2Run.created_at.desc()).limit(limit)
            if project_uuid:
                stmt = stmt.where(AgentV2Run.project_id == project_uuid)
            if tenant_uuid:
                stmt = stmt.where(AgentV2Run.tenant_id == tenant_uuid)
            with SessionLocal() as db:
                return [self._record_from_row(row) for row in db.scalars(stmt).all()]
        except SQLAlchemyError as exc:
            self._handle_db_error("list", exc)
            return []

    def _load_dead_letters_from_db(self, *, limit: int) -> list[dict[str, Any]]:
        if not self._persistence_enabled():
            return []
        try:
            from app.infra.database import SessionLocal
            from app.infra.models import AgentV2DeadLetter

            stmt = (
                select(AgentV2DeadLetter)
                .order_by(AgentV2DeadLetter.created_at.desc())
                .limit(limit)
            )
            with SessionLocal() as db:
                return [
                    {
                        "dead_letter_id": str(row.id),
                        "run_id": str(row.run_id) if row.run_id else None,
                        "queue_name": row.queue_name,
                        "reason": row.reason,
                        "payload": row.payload or {},
                        "retry_count": row.retry_count,
                        "last_error": row.last_error,
                        "created_at": row.created_at,
                    }
                    for row in db.scalars(stmt).all()
                ]
        except SQLAlchemyError as exc:
            self._handle_db_error("dead_letter_list", exc)
            return []

    def _record_from_row(self, row: Any) -> RunRecord:
        state = create_initial_state(
            project_id=str(row.project_id),
            user_id=str(row.user_id or "anonymous"),
            tenant_id=str(row.tenant_id or "default"),
            run_id=str(row.id),
            input_source=row.input_source,
            input_payload=row.input_payload or {},
        )
        state["created_at"] = row.created_at
        state["status"] = row.status
        state["intent_graph"] = row.intent_graph
        state["app_map"] = row.app_map
        state["scenarios"] = row.scenarios or []
        state["generated_code"] = row.generated_code
        state["run_result"] = row.run_result
        state["healing_result"] = row.healing_result
        state["review"] = row.review
        state["report"] = row.report
        state["errors"] = row.errors or []
        state["tokens_used"] = int(row.tokens_used or 0)
        state["cost_usd"] = float(row.cost_usd or 0.0)
        state["llm_calls_count"] = int(row.llm_calls_count or 0)
        state["completed_at"] = row.completed_at
        state["workflow_type"] = row.workflow_type
        state["dry_run"] = bool(row.dry_run)
        state["requires_approval"] = bool(row.requires_approval)

        record = RunRecord(
            run_id=str(row.id),
            project_id=str(row.project_id),
            tenant_id=str(row.tenant_id or "default"),
            user_id=str(row.user_id or "anonymous"),
            input_source=row.input_source,
            status=row.status,
            created_at=row.created_at,
            completed_at=row.completed_at,
            state=state,
            error=row.error_message,
        )
        record.events = [
            _event_from_row(event)
            for event in sorted(row.events, key=lambda item: item.created_at)
        ]
        record.artifacts = [
            RunArtifact(
                artifact_id=str(artifact.id),
                kind=artifact.kind,
                name=artifact.name,
                storage_path=artifact.storage_path,
                mime_type=artifact.mime_type,
                size_bytes=artifact.size_bytes,
                created_at=artifact.created_at,
                metadata=artifact.metadata_json or {},
            )
            for artifact in sorted(row.artifacts, key=lambda item: item.created_at)
        ]
        record.approvals = [
            {
                "approval_id": str(approval.id),
                "run_id": str(approval.run_id),
                "actor_id": str(approval.actor_user_id or "anonymous"),
                "decision": approval.decision,
                "note": approval.note,
                "created_at": approval.created_at,
            }
            for approval in sorted(row.approvals, key=lambda item: item.created_at)
        ]
        return record

    def _handle_db_error(self, operation: str, exc: SQLAlchemyError) -> None:
        if self._persist_mode in {"postgres", "db"}:
            raise exc
        self._db_failed = True
        logger.warning("agents/v2 run store DB persistence disabled after %s error: %s", operation, exc)


def _uuid_or_none(value: object) -> str | None:
    if value is None:
        return None
    try:
        return str(UUID(str(value)))
    except (TypeError, ValueError, AttributeError):
        return None


def _jsonable(value: Any) -> Any:
    if value is None:
        return None
    return json.loads(json.dumps(value, default=str, ensure_ascii=False))


def _artifact_metadata_with_integrity(
    storage_path: str,
    size_bytes: int,
    metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    merged = dict(metadata or {})
    if str(storage_path).strip().lower().startswith(("http://", "https://")):
        return merged

    path = Path(storage_path).expanduser()
    if not path.exists() or not path.is_file():
        return merged

    try:
        stat_size = path.stat().st_size
        merged.setdefault("hash_algorithm", "sha256")
        merged.setdefault("sha256", _sha256_file(path))
        merged.setdefault("size_bytes_verified", int(stat_size))
        if size_bytes and int(size_bytes) != int(stat_size):
            merged.setdefault(
                "size_bytes_mismatch",
                {"declared": int(size_bytes), "actual": int(stat_size)},
            )
    except OSError as exc:
        logger.debug("artifact integrity metadata skipped for %s: %s", storage_path, exc)
    return merged


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _event_from_row(row: Any) -> dict[str, Any]:
    payload = dict(row.payload or {})
    payload.setdefault("event_type", row.event_type)
    payload.setdefault("agent_name", row.agent_name)
    payload.setdefault("message", row.message)
    payload.setdefault("timestamp", row.created_at.isoformat())
    payload.setdefault("run_id", str(row.run_id))
    return payload


def _record_workflow_status(workflow_type: object, status: str) -> None:
    try:
        from app.domains.ai.metrics import record_workflow_status

        record_workflow_status(
            workflow_type=str(workflow_type) if workflow_type else None,
            status=status,
        )
    except Exception as exc:
        logger.debug("workflow status metric skipped: %s", exc)


def _record_workflow_event(event_type: object) -> None:
    try:
        from app.domains.ai.metrics import record_workflow_event

        record_workflow_event(event_type=str(event_type) if event_type else None)
    except Exception as exc:
        logger.debug("workflow event metric skipped: %s", exc)


def _record_workflow_approval(decision: str) -> None:
    try:
        from app.domains.ai.metrics import record_workflow_approval

        record_workflow_approval(decision=decision)
    except Exception as exc:
        logger.debug("workflow approval metric skipped: %s", exc)


def _record_workflow_dead_letter(queue_name: str, reason: str) -> None:
    try:
        from app.domains.ai.metrics import record_workflow_dead_letter

        record_workflow_dead_letter(queue_name=queue_name, reason=reason)
    except Exception as exc:
        logger.debug("workflow dead-letter metric skipped: %s", exc)


_singleton: RunStore | None = None


def get_run_store() -> RunStore:
    global _singleton
    if _singleton is None:
        _singleton = RunStore()
    return _singleton
