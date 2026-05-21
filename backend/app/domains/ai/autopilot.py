"""Nexus AI Autopilot.

Bu servis sıfır insan müdahalesi omurgasının ilk çalışan parçasıdır:
proje sinyallerini okur, risk çıkarır, öneri üretir ve güvenli aksiyonları
kontrollü şekilde uygular.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domains.tspm.models import (
    TspmAutopilotRun,
    TspmExecution,
    TspmExecutionMetrics,
    TspmProject,
    TspmScenario,
    utcnow,
)

logger = logging.getLogger(__name__)

AutopilotMode = Literal["observe", "assist", "autonomous"]
RiskLevel = Literal["low", "medium", "high", "critical"]


RISK_WEIGHT: dict[str, int] = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


def _risk_max(*levels: str) -> RiskLevel:
    selected = max(levels or ["low"], key=lambda level: RISK_WEIGHT.get(level, 1))
    return selected if selected in RISK_WEIGHT else "low"  # type: ignore[return-value]


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


class NexusAutopilot:
    """Project-scoped AI autopilot runner."""

    def __init__(self, db: Session, project_id: str):
        self.db = db
        self.project_id = project_id

    def run(
        self,
        *,
        mode: AutopilotMode = "autonomous",
        apply_safe_actions: bool = True,
        trigger: str = "manual",
    ) -> dict[str, Any]:
        project = self.db.get(TspmProject, self.project_id)
        if project is None or project.archived:
            raise ValueError("Proje bulunamadı veya arşivlenmiş.")

        run = TspmAutopilotRun(
            project_id=self.project_id,
            trigger=trigger,
            mode=mode,
            status="running",
            started_at=utcnow(),
        )
        self.db.add(run)
        self.db.flush()

        try:
            snapshot = self.collect_snapshot()
            recommendations, actions, risk_level = self.decide(snapshot)
            action_results = self.apply_actions(
                actions,
                mode=mode,
                apply_safe_actions=apply_safe_actions,
            )
            status = "completed"
            if any(result.get("status") == "failed" for result in action_results):
                status = "partial"

            run.status = status
            run.risk_level = risk_level
            run.summary = self._summarize(snapshot, recommendations, action_results, risk_level)
            run.snapshot = snapshot
            run.recommendations = recommendations
            run.actions = actions
            run.action_results = action_results
            run.completed_at = utcnow()
            self.db.commit()
            self.db.refresh(run)
            self._publish(run)
            return self.serialize_run(run)
        except Exception as exc:
            logger.exception("Nexus Autopilot run failed")
            run.status = "failed"
            run.risk_level = "critical"
            run.error = str(exc)[:1000]
            run.completed_at = utcnow()
            self.db.commit()
            self.db.refresh(run)
            return self.serialize_run(run)

    def collect_snapshot(self) -> dict[str, Any]:
        recent_metrics = list(
            self.db.scalars(
                select(TspmExecutionMetrics)
                .where(TspmExecutionMetrics.project_id == self.project_id)
                .order_by(TspmExecutionMetrics.executed_at.desc())
                .limit(10)
            )
        )
        latest_metric = recent_metrics[0] if recent_metrics else None
        latest_execution = self.db.scalars(
            select(TspmExecution)
            .where(TspmExecution.project_id == self.project_id)
            .order_by(TspmExecution.created_at.desc())
            .limit(1)
        ).first()

        scenario_count = self.db.scalar(
            select(func.count(TspmScenario.id)).where(TspmScenario.project_id == self.project_id)
        ) or 0
        execution_count = self.db.scalar(
            select(func.count(TspmExecution.id)).where(TspmExecution.project_id == self.project_id)
        ) or 0

        recent_pass_rates = [metric.pass_rate for metric in recent_metrics if metric.total > 0]
        avg_pass_rate = sum(recent_pass_rates) / len(recent_pass_rates) if recent_pass_rates else 0.0
        failed_total = sum(metric.failed for metric in recent_metrics)
        stale_after = datetime.now(timezone.utc) - timedelta(days=7)
        latest_metric_at = latest_metric.executed_at if latest_metric else None
        stale_metrics = latest_metric_at is None or latest_metric_at < stale_after

        llm_quality: dict[str, Any] = {}
        try:
            from app.domains.ai.quality_metrics import get_llm_quality_metrics

            llm_quality = get_llm_quality_metrics(days=7).get("overview", {})
        except Exception as exc:
            logger.debug("LLM quality snapshot unavailable: %s", exc)

        return {
            "project_id": self.project_id,
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "scenario_count": int(scenario_count),
            "execution_count": int(execution_count),
            "latest_execution": {
                "id": latest_execution.id if latest_execution else None,
                "name": latest_execution.name if latest_execution else None,
                "status": latest_execution.status if latest_execution else None,
                "created_at": _iso(latest_execution.created_at if latest_execution else None),
                "simulated": latest_execution.simulated if latest_execution else None,
            },
            "latest_metrics": {
                "execution_id": latest_metric.execution_id if latest_metric else None,
                "total": latest_metric.total if latest_metric else 0,
                "passed": latest_metric.passed if latest_metric else 0,
                "failed": latest_metric.failed if latest_metric else 0,
                "pass_rate": latest_metric.pass_rate if latest_metric else 0.0,
                "executed_at": _iso(latest_metric_at),
            },
            "recent_window": {
                "metrics_count": len(recent_metrics),
                "avg_pass_rate": round(avg_pass_rate, 2),
                "failed_total": failed_total,
                "stale_metrics": stale_metrics,
            },
            "llm_quality": llm_quality,
        }

    def decide(self, snapshot: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], RiskLevel]:
        recommendations: list[dict[str, Any]] = []
        actions: list[dict[str, Any]] = []
        risk: RiskLevel = "low"

        scenario_count = int(snapshot.get("scenario_count") or 0)
        execution_count = int(snapshot.get("execution_count") or 0)
        latest_status = (snapshot.get("latest_execution") or {}).get("status")
        latest_pass_rate = float((snapshot.get("latest_metrics") or {}).get("pass_rate") or 0.0)
        failed_total = int((snapshot.get("recent_window") or {}).get("failed_total") or 0)
        stale_metrics = bool((snapshot.get("recent_window") or {}).get("stale_metrics"))
        llm_quality = snapshot.get("llm_quality") or {}
        llm_success = float(llm_quality.get("success_rate") or 0.0)
        json_parse_rate = float(llm_quality.get("json_parse_rate") or 0.0)

        if scenario_count == 0:
            risk = _risk_max(risk, "medium")
            recommendations.append({
                "priority": "high",
                "title": "İlk test kapsamını oluştur",
                "detail": "Projede senaryo görünmüyor. NL Test Üretici veya Dokümandan Otomasyon ile başlangıç kapsamı üretilmeli.",
                "target": "nl-test-gen",
            })
            actions.append({
                "type": "recommend_route",
                "safe": True,
                "target": "nl-test-gen",
                "reason": "Senaryo yok; otomatik kod üretmeden önce brief/kapsam gerekir.",
            })

        if execution_count == 0 or stale_metrics:
            risk = _risk_max(risk, "medium")
            recommendations.append({
                "priority": "medium",
                "title": "Taze kalite sinyali üret",
                "detail": "Son 7 güne ait güvenilir koşu metriği yok. QA Orkestratör ile keşif veya plan döngüsü önerilir.",
                "target": "qa-orchestrator",
            })
            actions.append({
                "type": "qa_plan",
                "safe": True,
                "goal": "Projede taze kalite sinyali üretmek için kapsam, flaky ve assertion durumunu analiz et",
            })

        if latest_status in {"failed", "error", "broken"} or failed_total > 0 or (latest_pass_rate and latest_pass_rate < 75):
            risk = _risk_max(risk, "high")
            recommendations.append({
                "priority": "critical" if latest_pass_rate and latest_pass_rate < 50 else "high",
                "title": "Başarısızlık sinyallerini otomatik incele",
                "detail": "Son koşularda hata veya düşük pass rate var. Güvenli modda QA Orkestratör tam döngüsü başlatılabilir.",
                "target": "qa-orchestrator",
            })
            actions.append({
                "type": "qa_full_cycle",
                "safe": True,
                "goal": "Son koşu başarısızlıklarını analiz et, flaky ve healing sinyallerini çıkar, güvenli kalite aksiyonlarını raporla",
            })

        if llm_success and llm_success < 80:
            risk = _risk_max(risk, "medium")
            recommendations.append({
                "priority": "medium",
                "title": "LLM başarı oranını incele",
                "detail": f"Son 7 günlük LLM başarı oranı %{llm_success:.1f}. Model, prompt veya JSON şema disiplini incelenmeli.",
                "target": "ai-metrics",
            })

        if json_parse_rate and json_parse_rate < 85:
            risk = _risk_max(risk, "medium")
            recommendations.append({
                "priority": "medium",
                "title": "Yapısal çıktı kalitesini güçlendir",
                "detail": f"JSON parse oranı %{json_parse_rate:.1f}. Merkezi prompt kuralları ve schema repair aksiyonları izlenmeli.",
                "target": "ai-metrics",
            })

        if not recommendations:
            recommendations.append({
                "priority": "low",
                "title": "Sistem kararlı görünüyor",
                "detail": "Kritik sinyal yok. Düzenli metrik izleme ve dönemsel raporlama yeterli.",
                "target": "reports",
            })
            actions.append({
                "type": "knowledge_note",
                "safe": True,
                "note": "Autopilot sistem sağlığını düşük riskte değerlendirdi.",
            })

        actions.append({
            "type": "knowledge_ingest",
            "safe": True,
            "note": "Autopilot karar özeti proje hafızasına yazılır.",
        })
        return recommendations, actions, risk

    def apply_actions(
        self,
        actions: list[dict[str, Any]],
        *,
        mode: AutopilotMode,
        apply_safe_actions: bool,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []

        for action in actions:
            action_type = action.get("type")
            safe = bool(action.get("safe"))
            if mode == "observe":
                results.append({"type": action_type, "status": "skipped", "reason": "observe mode"})
                continue
            if not safe or not apply_safe_actions:
                results.append({"type": action_type, "status": "planned", "reason": "apply disabled or unsafe"})
                continue

            try:
                if action_type == "qa_plan":
                    results.append(self._apply_qa_plan(action))
                elif action_type == "qa_full_cycle":
                    if mode != "autonomous":
                        results.append({"type": action_type, "status": "planned", "reason": "assist mode"})
                    else:
                        results.append(self._apply_qa_full_cycle(action))
                elif action_type == "knowledge_ingest":
                    results.append(self._apply_knowledge_ingest(action))
                else:
                    results.append({"type": action_type, "status": "recorded", "action": action})
            except Exception as exc:
                logger.warning("Autopilot action failed: %s", exc)
                results.append({"type": action_type, "status": "failed", "error": str(exc)[:500]})

        return results

    def _apply_qa_plan(self, action: dict[str, Any]) -> dict[str, Any]:
        from app.domains.ai.qa_orchestrator import QAOrchestrator

        orchestrator = QAOrchestrator(db=self.db, project_id=self.project_id)
        plan = orchestrator.plan(goal=action.get("goal") or "Proje kalite durumunu analiz et")
        return {
            "type": "qa_plan",
            "status": "completed",
            "plan_id": plan.get("plan_id"),
            "steps": len(plan.get("steps") or []),
        }

    def _apply_qa_full_cycle(self, action: dict[str, Any]) -> dict[str, Any]:
        from app.domains.ai.qa_orchestrator import QAOrchestrator

        orchestrator = QAOrchestrator(db=self.db, project_id=self.project_id)
        result = orchestrator.run_full_cycle(goal=action.get("goal") or "Proje kalite durumunu iyileştir")
        return {
            "type": "qa_full_cycle",
            "status": "completed",
            "plan_id": result.get("plan_id"),
            "goal_achieved": result.get("verification", {}).get("goal_achieved"),
            "quality_score": result.get("verification", {}).get("quality_score"),
        }

    def _apply_knowledge_ingest(self, action: dict[str, Any]) -> dict[str, Any]:
        try:
            from app.domains.ai.knowledge_store import KnowledgeStore

            store = KnowledgeStore()
            ok = store.ingest(
                text=f"Nexus AI Autopilot: {action.get('note', 'Karar özeti üretildi.')}",
                source="insight",
                metadata={"project_id": self.project_id, "agent": "nexus_autopilot"},
            )
            return {"type": "knowledge_ingest", "status": "completed", "embedded": ok}
        except Exception as exc:
            return {"type": "knowledge_ingest", "status": "skipped", "reason": str(exc)[:300]}

    def _summarize(
        self,
        snapshot: dict[str, Any],
        recommendations: list[dict[str, Any]],
        action_results: list[dict[str, Any]],
        risk_level: RiskLevel,
    ) -> str:
        completed = sum(1 for result in action_results if result.get("status") == "completed")
        return (
            f"Nexus AI Autopilot risk={risk_level}; "
            f"{len(recommendations)} öneri, {completed}/{len(action_results)} otomatik aksiyon tamamlandı. "
            f"Senaryo={snapshot.get('scenario_count')}, koşu={snapshot.get('execution_count')}."
        )

    def _publish(self, run: TspmAutopilotRun) -> None:
        try:
            from app.domains.ai.cross_agent_memory import CrossAgentMemory

            CrossAgentMemory.publish(
                agent_name="nexus_autopilot",
                event_type="analysis_complete",
                data={
                    "summary": run.summary,
                    "project_id": run.project_id,
                    "run_id": run.id,
                    "risk_level": run.risk_level,
                },
                tags=["nexus_autopilot", run.risk_level],
            )
        except Exception:
            logger.debug("Autopilot memory publish skipped", exc_info=True)

    @staticmethod
    def serialize_run(run: TspmAutopilotRun) -> dict[str, Any]:
        return {
            "id": run.id,
            "project_id": run.project_id,
            "trigger": run.trigger,
            "mode": run.mode,
            "status": run.status,
            "risk_level": run.risk_level,
            "summary": run.summary,
            "snapshot": run.snapshot or {},
            "recommendations": run.recommendations or [],
            "actions": run.actions or [],
            "action_results": run.action_results or [],
            "error": run.error,
            "started_at": _iso(run.started_at),
            "completed_at": _iso(run.completed_at),
        }


def list_autopilot_runs(db: Session, project_id: str, limit: int = 20) -> list[dict[str, Any]]:
    runs = list(
        db.scalars(
            select(TspmAutopilotRun)
            .where(TspmAutopilotRun.project_id == project_id)
            .order_by(TspmAutopilotRun.started_at.desc())
            .limit(min(max(limit, 1), 100))
        )
    )
    return [NexusAutopilot.serialize_run(run) for run in runs]


def latest_autopilot_status(db: Session, project_id: str) -> dict[str, Any]:
    latest = db.scalars(
        select(TspmAutopilotRun)
        .where(TspmAutopilotRun.project_id == project_id)
        .order_by(TspmAutopilotRun.started_at.desc())
        .limit(1)
    ).first()
    if latest is None:
        snapshot = NexusAutopilot(db, project_id).collect_snapshot()
        return {
            "project_id": project_id,
            "has_run": False,
            "latest_run": None,
            "snapshot": snapshot,
        }
    return {
        "project_id": project_id,
        "has_run": True,
        "latest_run": NexusAutopilot.serialize_run(latest),
    }
