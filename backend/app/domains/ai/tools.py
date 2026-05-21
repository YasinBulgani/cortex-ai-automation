"""
Tool Use / Function Calling — LLM'e izin verilen aciklanmis araclar.

Mimari:
    1. Her tool bir Python fonksiyonu + JSON schema ile tanimlanir.
    2. LLM OpenAI/Anthropic tool-calling API'siyle bu araci cagirir.
    3. Backend araci calistirir, sonucu LLM'e geri gonderir.
    4. LLM nihai cevabi uretir (multi-turn).

Guvenlik:
    - Yalnizca whitelist'teki tool'lar cagrilabilir.
    - Her tool için parametre validation (Pydantic).
    - Rate limit + audit log (llm_traces'e phase="tool_call").
    - Banking kritik: NO mutation tools (read-only). Cari modulde yalnizca SELECT.

Kullanilabilir araclar:
    - get_project_stats(project_id)         — senaryo/koşu/başarı özeti
    - get_recent_failures(project_id, days) — son N gun başarısız test'ler
    - get_coverage_gaps(project_id)         — bağlı senaryosu olmayan gereksinim
    - get_scenario_by_id(scenario_id)       — tek senaryo detayı
    - list_scenarios(project_id, filter)    — senaryo listesi

Not: Yazma tool'lari (create_scenario, update_scenario) ayri bir mutation_tools
modulune ayrilmali — human-in-the-loop onayi ile (Faz H confidence queue'ya bagli).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Optional

from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)


# ── Tool schemas ────────────────────────────────────────────────────────


class GetProjectStatsArgs(BaseModel):
    project_id: str = Field(..., min_length=1)


class GetRecentFailuresArgs(BaseModel):
    project_id: str = Field(..., min_length=1)
    days: int = Field(default=7, ge=1, le=30)
    limit: int = Field(default=20, ge=1, le=100)


class GetCoverageGapsArgs(BaseModel):
    project_id: str = Field(..., min_length=1)


class GetScenarioByIdArgs(BaseModel):
    scenario_id: str = Field(..., min_length=1)


class ListScenariosArgs(BaseModel):
    project_id: str = Field(..., min_length=1)
    status: Optional[str] = Field(default=None, pattern=r"^(draft|pending|approved|rejected)$")
    limit: int = Field(default=50, ge=1, le=200)


# ── Tool implementations (read-only) ────────────────────────────────────


def _get_project_stats(args: GetProjectStatsArgs) -> dict[str, Any]:
    from app.infra.database import SessionLocal
    from app.domains.tspm.models import (
        TspmExecution,
        TspmExecutionMetrics,
        TspmProject,
        TspmRequirement,
        TspmScenario,
        TspmTestCase,
    )
    from sqlalchemy import func, select

    with SessionLocal() as db:
        p = db.get(TspmProject, args.project_id)
        if p is None:
            return {"error": "project_not_found"}

        scenario_count = db.scalar(select(func.count(TspmScenario.id)).where(TspmScenario.project_id == p.id)) or 0
        requirement_count = db.scalar(select(func.count(TspmRequirement.id)).where(TspmRequirement.project_id == p.id)) or 0
        pending_tc = db.scalar(
            select(func.count(TspmTestCase.id)).where(
                TspmTestCase.project_id == p.id,
                TspmTestCase.review_status == "pending",
            )
        ) or 0
        exec_count = db.scalar(select(func.count(TspmExecution.id)).where(TspmExecution.project_id == p.id)) or 0

        latest_metrics = db.scalar(
            select(TspmExecutionMetrics)
            .where(TspmExecutionMetrics.project_id == p.id)
            .order_by(TspmExecutionMetrics.executed_at.desc())
        )

        return {
            "project_id": p.id,
            "project_name": p.name,
            "scenarios": scenario_count,
            "requirements": requirement_count,
            "pending_ai_test_cases": pending_tc,
            "executions": exec_count,
            "latest_pass_rate": round(latest_metrics.pass_rate, 1) if latest_metrics else None,
            "latest_executed_at": latest_metrics.executed_at.isoformat() if latest_metrics and latest_metrics.executed_at else None,
        }


def _get_recent_failures(args: GetRecentFailuresArgs) -> dict[str, Any]:
    from app.infra.database import SessionLocal
    from app.domains.tspm.models import TspmExecution, TspmExecutionResult, TspmScenario
    from sqlalchemy import select
    from datetime import datetime, timedelta, timezone

    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
    with SessionLocal() as db:
        execs = list(db.scalars(
            select(TspmExecution)
            .where(TspmExecution.project_id == args.project_id, TspmExecution.created_at >= cutoff)
            .order_by(TspmExecution.created_at.desc())
        ))
        exec_ids = [e.id for e in execs]
        if not exec_ids:
            return {"project_id": args.project_id, "failures": []}

        rows = list(db.scalars(
            select(TspmExecutionResult)
            .where(
                TspmExecutionResult.execution_id.in_(exec_ids),
                TspmExecutionResult.status == "failed",
            )
            .limit(args.limit)
        ))

        failures = []
        for r in rows:
            sc = db.get(TspmScenario, r.scenario_id) if r.scenario_id else None
            failures.append({
                "scenario_id": r.scenario_id,
                "scenario_title": sc.title if sc else None,
                "note": (r.note or "")[:300],
                "execution_id": r.execution_id,
            })
        return {
            "project_id": args.project_id,
            "days": args.days,
            "total": len(failures),
            "failures": failures,
        }


def _get_coverage_gaps(args: GetCoverageGapsArgs) -> dict[str, Any]:
    from app.infra.database import SessionLocal
    from app.domains.tspm.models import TspmRequirement, TspmScenarioRequirement
    from sqlalchemy import select

    with SessionLocal() as db:
        all_reqs = list(db.scalars(
            select(TspmRequirement).where(TspmRequirement.project_id == args.project_id)
        ))
        linked_ids = set(
            db.scalars(
                select(TspmScenarioRequirement.requirement_id)
                .join(TspmRequirement, TspmRequirement.id == TspmScenarioRequirement.requirement_id)
                .where(TspmRequirement.project_id == args.project_id)
            )
        )
        gaps = []
        for req in all_reqs:
            if req.id in linked_ids:
                continue
            gaps.append({
                "requirement_id": req.id,
                "external_id": req.external_id,
                "title": req.title,
                "priority": req.priority,
            })
        return {
            "project_id": args.project_id,
            "total_requirements": len(all_reqs),
            "uncovered": len(gaps),
            "gaps": gaps[:50],
        }


def _get_scenario_by_id(args: GetScenarioByIdArgs) -> dict[str, Any]:
    from app.infra.database import SessionLocal
    from app.domains.tspm.models import TspmScenario

    with SessionLocal() as db:
        sc = db.get(TspmScenario, args.scenario_id)
        if sc is None:
            return {"error": "scenario_not_found"}
        return {
            "id": sc.id,
            "title": sc.title,
            "description": sc.description,
            "status": sc.status,
            "tags": sc.tags,
            "steps": sc.steps,
        }


def _list_scenarios(args: ListScenariosArgs) -> dict[str, Any]:
    from app.infra.database import SessionLocal
    from app.domains.tspm.models import TspmScenario
    from sqlalchemy import select

    with SessionLocal() as db:
        stmt = select(TspmScenario).where(TspmScenario.project_id == args.project_id)
        if args.status:
            stmt = stmt.where(TspmScenario.status == args.status)
        stmt = stmt.order_by(TspmScenario.updated_at.desc()).limit(args.limit)
        items = list(db.scalars(stmt))
        return {
            "project_id": args.project_id,
            "total": len(items),
            "scenarios": [
                {
                    "id": s.id,
                    "title": s.title,
                    "status": s.status,
                    "tags": (s.tags or [])[:5],
                }
                for s in items
            ],
        }


# ── Registry ───────────────────────────────────────────────────────────


@dataclass
class ToolSpec:
    name: str
    description: str
    schema_cls: type[BaseModel]
    handler: Callable[[Any], dict[str, Any]]


_TOOLS: dict[str, ToolSpec] = {
    "get_project_stats": ToolSpec(
        name="get_project_stats",
        description=(
            "Bir projenin senaryo sayisi, kapsam, bekleyen AI test case sayisi, "
            "son koşu başarı orani gibi özet metriklerini dondurur. "
            "Sadece okuma yapar, hicbir degisiklik yapmaz."
        ),
        schema_cls=GetProjectStatsArgs,
        handler=_get_project_stats,
    ),
    "get_recent_failures": ToolSpec(
        name="get_recent_failures",
        description=(
            "Son N gundeki başarısız test koşu sonuclarini (scenario_id + hata notu) dondurur. "
            "Debug/analiz için — LLM root cause soracagi durumlarda kullanilir."
        ),
        schema_cls=GetRecentFailuresArgs,
        handler=_get_recent_failures,
    ),
    "get_coverage_gaps": ToolSpec(
        name="get_coverage_gaps",
        description=(
            "Projedeki hicbir senaryo ile bagli olmayan gereksinimleri (coverage gap) dondurur. "
            "Gap analizi / yeni senaryo onerisi için kullanilir."
        ),
        schema_cls=GetCoverageGapsArgs,
        handler=_get_coverage_gaps,
    ),
    "get_scenario_by_id": ToolSpec(
        name="get_scenario_by_id",
        description="Tek bir senaryonun tam detayini (steps, tags, description) dondurur.",
        schema_cls=GetScenarioByIdArgs,
        handler=_get_scenario_by_id,
    ),
    "list_scenarios": ToolSpec(
        name="list_scenarios",
        description="Projedeki senaryolari durum filtresi ile listeler.",
        schema_cls=ListScenariosArgs,
        handler=_list_scenarios,
    ),
}


# ── Public API ───────────────────────────────────────────────────────────


def list_tools() -> list[ToolSpec]:
    return list(_TOOLS.values())


def tool_names() -> list[str]:
    return list(_TOOLS.keys())


def tools_enabled(tenant_id: Optional[str] = None) -> bool:
    """Feature flag: ai.tools — default False (opt-in)."""
    try:
        from app.domains.feature_flags.service import feature_flags
        return feature_flags.is_enabled("ai.tools", tenant_id=tenant_id, default=False)
    except Exception:
        return False


def openai_tools_payload() -> list[dict]:
    """OpenAI `tools=[...]` API'sinin beklediği format."""
    payload = []
    for spec in _TOOLS.values():
        try:
            schema = spec.schema_cls.model_json_schema()
            # Strict mode OpenAI 2024-08-06 gereksinimleri
            schema.pop("title", None)
            schema["additionalProperties"] = False
        except Exception:
            continue
        payload.append({
            "type": "function",
            "function": {
                "name": spec.name,
                "description": spec.description,
                "parameters": schema,
                "strict": True,
            },
        })
    return payload


def anthropic_tools_payload() -> list[dict]:
    """Anthropic `tools=[...]` API'sinin beklediği format."""
    payload = []
    for spec in _TOOLS.values():
        try:
            schema = spec.schema_cls.model_json_schema()
            schema.pop("title", None)
        except Exception:
            continue
        payload.append({
            "name": spec.name,
            "description": spec.description,
            "input_schema": schema,
        })
    return payload


def execute_tool(name: str, arguments: dict) -> dict[str, Any]:
    """
    Tool'u guvenli çalıştır.

    Args:
        name:       Tool adi
        arguments:  LLM'den gelen JSON argumanlar

    Returns:
        {"ok": bool, "result": ..., "error": ...}
    """
    spec = _TOOLS.get(name)
    if spec is None:
        return {"ok": False, "error": f"unknown_tool:{name}"}

    if not tools_enabled():
        return {"ok": False, "error": "tools_disabled_by_flag"}

    try:
        parsed = spec.schema_cls.model_validate(arguments)
    except ValidationError as exc:
        return {"ok": False, "error": "validation_error", "details": exc.errors()}

    try:
        result = spec.handler(parsed)
        return {"ok": True, "result": result}
    except Exception as exc:
        logger.exception("tool %s calisirken hata", name)
        return {"ok": False, "error": "execution_error", "detail": str(exc)[:300]}
