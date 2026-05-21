"""Run Store — In-memory (Postgres backend Faz 2'de)."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from .state import AgentState, create_initial_state

logger = logging.getLogger(__name__)


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
    error: str | None = None

    def to_status_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "project_id": self.project_id,
            "status": self.status,
            "input_source": self.input_source,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
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
        return run_id, initial_state

    def get(self, run_id: str) -> RunRecord | None:
        return self._runs.get(run_id)

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
        items.sort(key=lambda r: r.created_at, reverse=True)
        return items[:limit]

    def update_status(self, run_id: str, status: str, error: str | None = None) -> None:
        rec = self._runs.get(run_id)
        if not rec:
            return
        rec.status = status
        if error:
            rec.error = error
        if status in ("completed", "failed", "cancelled"):
            rec.completed_at = datetime.utcnow()

    def update_state(self, run_id: str, state: AgentState) -> None:
        rec = self._runs.get(run_id)
        if rec:
            rec.state = state

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
        for q in self._subscribers.get(run_id, []):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass


_singleton: RunStore | None = None


def get_run_store() -> RunStore:
    global _singleton
    if _singleton is None:
        _singleton = RunStore()
    return _singleton
