"""
QA Orchestrator — Agentic Plan-Act-Verify Autonomous Testing Cycle
===================================================================

Autonomous QA orchestrator that runs Plan -> Act -> Verify cycles.

Each cycle:
  1. PLAN  — Analyses the current state (coverage, flaky tests, etc.),
             queries CrossAgentMemory & KnowledgeStore, then creates a
             step-by-step test plan via LLM.
  2. ACT   — Executes each plan step by calling the appropriate service
             (coverage_analyzer, flaky_detector, assertion_suggester,
             self_healer, test_prioritizer, ServiceTestAgent, etc.).
  3. VERIFY — Compares before/after state, scores effectiveness, and
              produces next-step recommendations.

Python 3.9 compatible.
"""

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal plan store (in-memory, keyed by plan_id)
# ---------------------------------------------------------------------------

_plan_store: Dict[str, Dict[str, Any]] = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ═══════════════════════════════════════════════════════════════════════
# QAOrchestrator
# ═══════════════════════════════════════════════════════════════════════

class QAOrchestrator:
    """Autonomous QA orchestrator — Plan -> Act -> Verify."""

    MAX_REPLANS = 2

    def __init__(self, db: Session, project_id: str, user_id: Optional[str] = None):
        self.db = db
        self.project_id = project_id
        self.user_id = user_id
        self.steps: List[Dict[str, Any]] = []
        self.status = "idle"  # idle, planning, acting, verifying, complete, error
        self._replan_count = 0

    # ------------------------------------------------------------------
    # Lazy helpers
    # ------------------------------------------------------------------

    def _get_agent(self):  # type: ignore[return]
        """Lazy-import BaseAgent to avoid circular imports."""
        from app.domains.agents.banking_team.base_agent import BaseAgent
        agent = BaseAgent()
        agent.name = "qa_orchestrator"
        agent.inject_project_context = True
        agent._project_id = self.project_id
        agent._user_id = self.user_id
        return agent

    def _publish(self, event_type: str, data: Dict[str, Any], tags: Optional[List[str]] = None) -> None:
        """Fire-and-forget publish to CrossAgentMemory."""
        try:
            from app.domains.ai.cross_agent_memory import CrossAgentMemory
            CrossAgentMemory.publish(
                agent_name="qa_orchestrator",
                event_type=event_type,
                data={"project_id": self.project_id, **data},
                tags=tags or [],
            )
        except Exception as exc:
            logger.debug("QAOrchestrator publish failed: %s", exc)

    def _get_cross_agent_context(self) -> str:
        """Query CrossAgentMemory for relevant context."""
        try:
            from app.domains.ai.cross_agent_memory import CrossAgentMemory
            return CrossAgentMemory.get_context_for_agent(
                agent_name="qa_orchestrator",
                project_id=self.project_id,
                max_chars=2000,
            )
        except Exception:
            return ""

    def _get_knowledge_context(self, goal: str) -> str:
        """Query KnowledgeStore for domain knowledge related to the goal."""
        try:
            from app.domains.ai.knowledge_store import KnowledgeStore
            store = KnowledgeStore(project_id=self.project_id)
            try:
                chunks = store.retrieve(goal, top_k=3)
                if not chunks:
                    return ""
                parts = ["## DOMAIN KNOWLEDGE"]
                for c in chunks:
                    parts.append(
                        "[%s | sim:%.2f] %s" % (c.source, c.similarity, c.content[:300])
                    )
                return "\n".join(parts)
            finally:
                store.close()
        except Exception:
            return ""

    def _get_coverage_snapshot(self) -> Dict[str, Any]:
        """Get current coverage analysis (fire-and-forget on error)."""
        try:
            from app.domains.api_testing.coverage_analyzer import analyze_coverage
            return analyze_coverage(self.db, self.project_id)
        except Exception as exc:
            logger.debug("Coverage snapshot failed: %s", exc)
            return {"summary": {"coverage_rate": 0.0, "total_endpoints": 0, "covered_endpoints": 0, "uncovered_endpoints": 0, "critical_uncovered": 0}, "gaps": []}

    # ==================================================================
    # PLAN
    # ==================================================================

    def plan(self, goal: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Use LLM to create a test plan based on the goal.

        Returns a plan dict with steps, estimated durations, and coverage targets.
        """
        self.status = "planning"
        plan_id = str(uuid4())

        # Gather context from multiple sources
        cross_ctx = self._get_cross_agent_context()
        knowledge_ctx = self._get_knowledge_context(goal)
        coverage = self._get_coverage_snapshot()

        coverage_before = coverage.get("summary", {}).get("coverage_rate", 0.0)
        gaps = coverage.get("gaps", [])
        top_gaps_text = json.dumps(gaps[:10], ensure_ascii=False, default=str)[:2000] if gaps else "Yok"

        user_context_text = ""
        if context:
            user_context_text = json.dumps(context, ensure_ascii=False, default=str)[:1000]

        # Build LLM prompt
        system_prompt = (
            "Sen bankacilik sektorunde deneyimli bir QA orkestrasyon ajansin. "
            "Verilen hedefe ulasmak icin adim adim bir test plani olustur. "
            "Her adim icin uygun aksiyonu sec.\n\n"
            "KULLANILABILIR AKSIYONLAR:\n"
            "- analyze_coverage: Mevcut test kapsamini analiz et\n"
            "- generate_tests: Eksik testleri AI ile uret\n"
            "- execute_tests: Testleri calistir\n"
            "- analyze_results: Test sonuclarini LLM ile analiz et\n"
            "- heal_failures: Basarisiz testleri self-healing ile duzelt\n"
            "- suggest_assertions: Eksik assertion onerileri uret\n"
            "- detect_flaky: Flaky testleri tespit et\n"
            "- prioritize: Testleri onceliklendir\n"
            "- report: Ozet rapor olustur\n\n"
            "YALNIZCA JSON formatinda yanit ver."
        )

        user_prompt = (
            "## HEDEF\n%s\n\n"
            "## MEVCUT KAPSAM\n"
            "Coverage orani: %%%.1f\n"
            "Toplam endpoint: %d | Kapsamda: %d | Kapsamda olmayan: %d\n"
            "Kritik kapsamda olmayan: %d\n\n"
            "## EN ONEMLI BOSLUKLAR\n%s\n\n"
            "%s%s%s"
            "## BEKLENEN CIKTI FORMATI\n"
            '{"steps": [{"step_id": 1, "action": "analyze_coverage", '
            '"description": "...", "target": null, "params": {}, '
            '"depends_on": [], "estimated_duration_ms": 5000}], '
            '"expected_coverage_after": 85.0}'
        ) % (
            goal,
            coverage_before,
            coverage.get("summary", {}).get("total_endpoints", 0),
            coverage.get("summary", {}).get("covered_endpoints", 0),
            coverage.get("summary", {}).get("uncovered_endpoints", 0),
            coverage.get("summary", {}).get("critical_uncovered", 0),
            top_gaps_text,
            ("## KULLANICI BAGLAMI\n%s\n\n" % user_context_text) if user_context_text else "",
            ("## CROSS-AGENT BILGILERI\n%s\n\n" % cross_ctx) if cross_ctx else "",
            ("## DOMAIN BILGISI\n%s\n\n" % knowledge_ctx) if knowledge_ctx else "",
        )

        steps = []  # type: List[Dict[str, Any]]
        expected_coverage_after = coverage_before

        try:
            agent = self._get_agent()
            result = agent.call_json(system=system_prompt, user=user_prompt)

            if not result.get("parse_error"):
                raw_steps = result.get("steps", [])
                for i, s in enumerate(raw_steps):
                    steps.append({
                        "step_id": s.get("step_id", i + 1),
                        "action": s.get("action", "report"),
                        "description": s.get("description", ""),
                        "target": s.get("target"),
                        "params": s.get("params", {}),
                        "depends_on": s.get("depends_on", []),
                        "estimated_duration_ms": s.get("estimated_duration_ms", 5000),
                        "status": "pending",
                        "result": None,
                    })
                expected_coverage_after = result.get("expected_coverage_after", coverage_before)
        except Exception as exc:
            logger.warning("QAOrchestrator plan LLM failed, using default plan: %s", exc)

        # Fallback: if LLM failed or returned nothing, create a sensible default plan
        if not steps:
            steps = self._default_plan(gaps)
            expected_coverage_after = min(coverage_before + 15.0, 100.0)

        estimated_total = sum(s.get("estimated_duration_ms", 5000) for s in steps)

        plan = {
            "plan_id": plan_id,
            "project_id": self.project_id,
            "user_id": self.user_id,
            "goal": goal,
            "steps": steps,
            "estimated_total_duration_ms": estimated_total,
            "coverage_before": coverage_before,
            "expected_coverage_after": expected_coverage_after,
            "status": "planned",
            "created_at": _now_iso(),
            "context": context,
        }

        # Store plan
        _plan_store[plan_id] = plan
        self.steps = steps
        self.status = "planned"

        self._publish("analysis_complete", {
            "summary": "QA plan created: %d steps, goal=%s" % (len(steps), goal[:100]),
            "plan_id": plan_id,
            "step_count": len(steps),
            "coverage_before": coverage_before,
        }, tags=["qa_orchestrator", "plan"])

        return plan

    def _default_plan(self, gaps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate a sensible default plan when LLM is unavailable."""
        steps = [
            {
                "step_id": 1,
                "action": "analyze_coverage",
                "description": "Mevcut test kapsamini analiz et ve bosluklari belirle",
                "target": None,
                "params": {},
                "depends_on": [],
                "estimated_duration_ms": 3000,
                "status": "pending",
                "result": None,
            },
            {
                "step_id": 2,
                "action": "detect_flaky",
                "description": "Flaky testleri tespit et ve karantinaya al",
                "target": None,
                "params": {},
                "depends_on": [],
                "estimated_duration_ms": 3000,
                "status": "pending",
                "result": None,
            },
            {
                "step_id": 3,
                "action": "prioritize",
                "description": "Testleri onceliklendir",
                "target": None,
                "params": {},
                "depends_on": [1],
                "estimated_duration_ms": 2000,
                "status": "pending",
                "result": None,
            },
        ]

        # If there are coverage gaps, add test generation step
        if gaps:
            steps.append({
                "step_id": 4,
                "action": "generate_tests",
                "description": "Kapsam bosluklari icin yeni testler uret",
                "target": None,
                "params": {"max_gaps": min(len(gaps), 5)},
                "depends_on": [1],
                "estimated_duration_ms": 15000,
                "status": "pending",
                "result": None,
            })
            steps.append({
                "step_id": 5,
                "action": "suggest_assertions",
                "description": "Mevcut testler icin eksik assertion onerileri",
                "target": None,
                "params": {},
                "depends_on": [1],
                "estimated_duration_ms": 5000,
                "status": "pending",
                "result": None,
            })

        steps.append({
            "step_id": len(steps) + 1,
            "action": "report",
            "description": "Sonuclari ozetle ve raporla",
            "target": None,
            "params": {},
            "depends_on": [s["step_id"] for s in steps],
            "estimated_duration_ms": 2000,
            "status": "pending",
            "result": None,
        })

        return steps

    # ==================================================================
    # ACT
    # ==================================================================

    def act(self, plan_id: str) -> Dict[str, Any]:
        """
        Execute the plan step by step.

        Returns step-by-step execution log.
        """
        plan = _plan_store.get(plan_id)
        if not plan:
            return {"error": "Plan not found", "plan_id": plan_id}
        if plan.get("project_id") != self.project_id:
            return {"error": "Plan not found", "plan_id": plan_id}

        self.status = "acting"
        plan["status"] = "executing"
        steps = plan["steps"]
        execution_log = []  # type: List[Dict[str, Any]]
        completed_ids = set()  # type: set

        for step in steps:
            step_id = step["step_id"]

            # Check dependencies
            deps = step.get("depends_on", [])
            deps_met = all(d in completed_ids for d in deps)
            if not deps_met:
                step["status"] = "skipped"
                step["result"] = {"reason": "Dependencies not met: %s" % deps}
                execution_log.append({
                    "step_id": step_id,
                    "action": step["action"],
                    "status": "skipped",
                    "duration_ms": 0,
                })
                continue

            # Execute step
            t0 = time.monotonic()
            try:
                result = self._execute_step(step)
                step["status"] = "completed"
                step["result"] = result
                completed_ids.add(step_id)

                duration_ms = round((time.monotonic() - t0) * 1000, 2)
                execution_log.append({
                    "step_id": step_id,
                    "action": step["action"],
                    "status": "completed",
                    "duration_ms": duration_ms,
                    "result_summary": self._summarize_result(result),
                })

                self._publish("pattern_detected", {
                    "summary": "Step %d (%s) completed" % (step_id, step["action"]),
                    "plan_id": plan_id,
                    "step_id": step_id,
                    "action": step["action"],
                }, tags=["qa_orchestrator", "step_complete"])

            except Exception as exc:
                duration_ms = round((time.monotonic() - t0) * 1000, 2)
                step["status"] = "failed"
                step["result"] = {"error": str(exc)}

                execution_log.append({
                    "step_id": step_id,
                    "action": step["action"],
                    "status": "failed",
                    "duration_ms": duration_ms,
                    "error": str(exc)[:500],
                })

                logger.warning(
                    "QAOrchestrator step %d (%s) failed: %s",
                    step_id, step["action"], exc,
                )

                # Re-plan on failure (up to MAX_REPLANS)
                if self._replan_count < self.MAX_REPLANS:
                    self._replan_count += 1
                    logger.info(
                        "QAOrchestrator re-planning (attempt %d/%d)",
                        self._replan_count, self.MAX_REPLANS,
                    )
                    # Mark remaining steps as skipped, they will be re-planned
                    # Continue to next step instead of breaking
                    continue

        plan["status"] = "executed"
        plan["execution_log"] = execution_log
        self.status = "acted"

        return {
            "plan_id": plan_id,
            "status": "executed",
            "steps_total": len(steps),
            "steps_completed": sum(1 for s in steps if s["status"] == "completed"),
            "steps_failed": sum(1 for s in steps if s["status"] == "failed"),
            "steps_skipped": sum(1 for s in steps if s["status"] == "skipped"),
            "execution_log": execution_log,
        }

    def _execute_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch step to appropriate service."""
        action = step["action"]
        params = step.get("params", {})
        target = step.get("target")

        if action == "analyze_coverage":
            return self._step_analyze_coverage(params, target)
        elif action == "generate_tests":
            return self._step_generate_tests(params, target)
        elif action == "execute_tests":
            return self._step_execute_tests(params, target)
        elif action == "analyze_results":
            return self._step_analyze_results(params, target)
        elif action == "heal_failures":
            return self._step_heal_failures(params, target)
        elif action == "suggest_assertions":
            return self._step_suggest_assertions(params, target)
        elif action == "detect_flaky":
            return self._step_detect_flaky(params, target)
        elif action == "prioritize":
            return self._step_prioritize(params, target)
        elif action == "report":
            return self._step_report(params, target)
        else:
            return {"warning": "Unknown action: %s" % action}

    # ── Step implementations ─────────────────────────────────────────

    def _step_analyze_coverage(self, params: Dict[str, Any], target: Optional[str]) -> Dict[str, Any]:
        from app.domains.api_testing.coverage_analyzer import analyze_coverage
        spec_id = target or params.get("spec_id")
        return analyze_coverage(self.db, self.project_id, spec_id=spec_id)

    def _step_generate_tests(self, params: Dict[str, Any], target: Optional[str]) -> Dict[str, Any]:
        """Generate tests for coverage gaps using ServiceTestAgent."""
        from app.domains.api_testing.coverage_analyzer import suggest_tests_for_gaps
        max_gaps = params.get("max_gaps", 5)
        suggestions = suggest_tests_for_gaps(self.db, self.project_id, max_gaps=max_gaps)

        # Try to use ServiceTestAgent for AI-powered generation
        generated_count = 0
        try:
            from app.domains.agents.banking_team.service_test_agent import ServiceTestAgent
            from app.domains.api_testing.models import ApiEndpoint, ApiSpec

            # Get endpoints from gaps
            endpoint_ids = [s.get("endpoint_id") for s in suggestions if s.get("endpoint_id")]
            if endpoint_ids:
                endpoints = (
                    self.db.query(ApiEndpoint)
                    .filter(ApiEndpoint.id.in_(endpoint_ids))
                    .all()
                )
                ep_data = []
                for ep in endpoints:
                    ep_data.append({
                        "method": ep.method,
                        "path": ep.path,
                        "summary": ep.summary or "",
                        "risk_level": ep.risk_level or "medium",
                        "has_pii": ep.has_pii,
                        "has_financial": ep.has_financial,
                        "parameters": ep.parameters or [],
                    })

                if ep_data:
                    agent = ServiceTestAgent()
                    result = agent.safe_run({
                        "mode": "test_generation",
                        "endpoints": ep_data,
                        "regulations": ["BDDK", "KVKK"],
                    })
                    if result.success:
                        generated_count = len(result.data.get("test_cases", []))
        except Exception as exc:
            logger.warning("ServiceTestAgent generation failed: %s", exc)

        return {
            "gap_suggestions": suggestions,
            "gap_count": len(suggestions),
            "tests_generated": generated_count,
        }

    def _step_execute_tests(self, params: Dict[str, Any], target: Optional[str]) -> Dict[str, Any]:
        """Execute tests — returns summary. Actual execution requires the execution engine."""
        run_id = target or params.get("run_id")
        if not run_id:
            return {"status": "skipped", "reason": "No run_id provided for execution"}

        # Try to use execution engine if available
        try:
            from app.domains.api_testing.models import ApiExecutionDetail
            details = (
                self.db.query(ApiExecutionDetail)
                .filter(ApiExecutionDetail.run_id == run_id)
                .all()
            )
            passed = sum(1 for d in details if d.passed)
            failed = len(details) - passed
            return {
                "run_id": run_id,
                "total": len(details),
                "passed": passed,
                "failed": failed,
            }
        except Exception as exc:
            return {"status": "info", "message": "Execution engine not available: %s" % str(exc)[:200]}

    def _step_analyze_results(self, params: Dict[str, Any], target: Optional[str]) -> Dict[str, Any]:
        """LLM analysis of test results."""
        # Gather recent execution data
        try:
            from app.domains.api_testing.models import ApiExecutionDetail, ApiTestCase
            from sqlalchemy import select

            recent = (
                self.db.query(ApiExecutionDetail)
                .filter(ApiExecutionDetail.passed == False)  # noqa: E712
                .order_by(ApiExecutionDetail.executed_at.desc())
                .limit(20)
                .all()
            )

            if not recent:
                return {"analysis": "No recent failures found", "failure_count": 0}

            failure_summaries = []
            for d in recent:
                tc = self.db.query(ApiTestCase).filter(ApiTestCase.id == d.test_case_id).first() if d.test_case_id else None
                failure_summaries.append({
                    "test": tc.title if tc else "Unknown",
                    "status_code": d.status_code,
                    "error": (d.error_message or "")[:200],
                })

            # Use LLM for analysis
            agent = self._get_agent()
            agent.max_tokens = 2048
            result = agent.call_json(
                system=(
                    "Sen bir QA analiz uzmanisin. Test basarisizlik verilerini analiz et, "
                    "ortak paternleri bul ve onceliklendirme onerileri ver. "
                    "JSON formatinda yanit ver."
                ),
                user="Basarisiz testler:\n%s" % json.dumps(failure_summaries, ensure_ascii=False),
            )
            return {"analysis": result, "failure_count": len(recent)}

        except Exception as exc:
            return {"analysis": "Analysis failed: %s" % str(exc)[:200], "failure_count": 0}

    def _step_heal_failures(self, params: Dict[str, Any], target: Optional[str]) -> Dict[str, Any]:
        """Self-heal failed tests."""
        run_id = target or params.get("run_id")
        if not run_id:
            return {"status": "skipped", "reason": "No run_id provided for healing"}

        from app.domains.api_testing.self_healer import heal_and_retry
        return heal_and_retry(self.db, self.project_id, run_id)

    def _step_suggest_assertions(self, params: Dict[str, Any], target: Optional[str]) -> Dict[str, Any]:
        """Suggest assertions for test cases."""
        test_case_id = target or params.get("test_case_id")

        if test_case_id:
            from app.domains.api_testing.assertion_suggester import suggest_assertions
            return suggest_assertions(self.db, self.project_id, test_case_id)

        # Bulk suggest for project
        from app.domains.api_testing.assertion_suggester import bulk_suggest
        test_type = params.get("test_type")
        return bulk_suggest(self.db, self.project_id, test_type=test_type)

    def _step_detect_flaky(self, params: Dict[str, Any], target: Optional[str]) -> Dict[str, Any]:
        """Detect flaky tests."""
        from app.domains.api_testing.flaky_detector import detect_flaky_tests
        window_days = params.get("window_days", 30)
        min_runs = params.get("min_runs", 3)
        results = detect_flaky_tests(
            self.db, self.project_id,
            window_days=window_days, min_runs=min_runs,
        )
        flaky_count = sum(1 for r in results if r.get("recommendation") == "quarantine")
        investigate_count = sum(1 for r in results if r.get("recommendation") == "investigate")
        return {
            "total_analyzed": len(results),
            "flaky_count": flaky_count,
            "investigate_count": investigate_count,
            "results": results[:20],
        }

    def _step_prioritize(self, params: Dict[str, Any], target: Optional[str]) -> Dict[str, Any]:
        """Prioritize tests."""
        from app.domains.api_testing.test_prioritizer import prioritize_tests, suggest_optimal_suite
        changed_paths = params.get("changed_paths")
        max_tests = params.get("max_tests")

        prioritized = prioritize_tests(
            self.db, self.project_id,
            changed_paths=changed_paths,
            max_tests=max_tests,
        )

        # Also get optimal suite suggestion
        time_budget = params.get("time_budget_ms")
        suite = suggest_optimal_suite(
            self.db, self.project_id,
            time_budget_ms=time_budget,
            changed_paths=changed_paths,
        )

        return {
            "prioritized_count": len(prioritized),
            "top_priority": prioritized[:10],
            "optimal_suite": suite,
        }

    def _step_report(self, params: Dict[str, Any], target: Optional[str]) -> Dict[str, Any]:
        """Generate a summary report of the cycle."""
        coverage = self._get_coverage_snapshot()
        summary = coverage.get("summary", {})

        return {
            "coverage_rate": summary.get("coverage_rate", 0.0),
            "total_endpoints": summary.get("total_endpoints", 0),
            "covered_endpoints": summary.get("covered_endpoints", 0),
            "uncovered_endpoints": summary.get("uncovered_endpoints", 0),
            "critical_uncovered": summary.get("critical_uncovered", 0),
            "gaps_remaining": len(coverage.get("gaps", [])),
            "generated_at": _now_iso(),
        }

    @staticmethod
    def _summarize_result(result: Dict[str, Any]) -> str:
        """Create a one-line summary of a step result."""
        if not result:
            return "empty"
        # Pick the most informative keys
        keys_to_check = [
            "coverage_rate", "gap_count", "tests_generated", "flaky_count",
            "prioritized_count", "total_failures", "healed",
            "total_suggestions", "failure_count", "total_analyzed",
        ]
        parts = []
        for k in keys_to_check:
            if k in result:
                parts.append("%s=%s" % (k, result[k]))
        if parts:
            return ", ".join(parts[:5])
        # Fallback: summary from nested dict
        summary = result.get("summary", {})
        if isinstance(summary, dict) and summary:
            return str(summary)[:200]
        return str(result)[:150]

    # ==================================================================
    # VERIFY
    # ==================================================================

    def verify(self, plan_id: str) -> Dict[str, Any]:
        """
        After execution, verify the results.

        Compares coverage before/after, checks if goal was achieved,
        identifies remaining gaps, scores the cycle effectiveness.
        """
        plan = _plan_store.get(plan_id)
        if not plan:
            return {"error": "Plan not found", "plan_id": plan_id}
        if plan.get("project_id") != self.project_id:
            return {"error": "Plan not found", "plan_id": plan_id}

        self.status = "verifying"

        coverage_before = plan.get("coverage_before", 0.0)
        coverage_after_data = self._get_coverage_snapshot()
        coverage_after = coverage_after_data.get("summary", {}).get("coverage_rate", 0.0)
        coverage_delta = round(coverage_after - coverage_before, 2)

        # Aggregate step results
        steps = plan.get("steps", [])
        tests_generated = 0
        tests_executed = 0
        tests_passed = 0
        failures_healed = 0
        flaky_detected = 0
        assertions_added = 0

        for step in steps:
            result = step.get("result") or {}
            if step["action"] == "generate_tests":
                tests_generated += result.get("tests_generated", 0)
            elif step["action"] == "execute_tests":
                tests_executed += result.get("total", 0)
                tests_passed += result.get("passed", 0)
            elif step["action"] == "heal_failures":
                failures_healed += result.get("healed", 0)
            elif step["action"] == "detect_flaky":
                flaky_detected += result.get("flaky_count", 0)
            elif step["action"] == "suggest_assertions":
                assertions_added += result.get("total_suggestions", 0)

        # Score the cycle effectiveness (0-100)
        quality_score = self._calculate_quality_score(
            coverage_delta=coverage_delta,
            tests_generated=tests_generated,
            failures_healed=failures_healed,
            flaky_detected=flaky_detected,
            assertions_added=assertions_added,
            steps_completed=sum(1 for s in steps if s.get("status") == "completed"),
            steps_total=len(steps),
        )

        # Check if goal was achieved
        goal_achieved = coverage_delta > 0 or tests_generated > 0 or failures_healed > 0

        # Generate recommendations
        recommendations = self._generate_recommendations(
            coverage_after_data, tests_generated, failures_healed, flaky_detected,
        )

        verification = {
            "plan_id": plan_id,
            "goal_achieved": goal_achieved,
            "coverage_before": coverage_before,
            "coverage_after": coverage_after,
            "coverage_delta": coverage_delta,
            "tests_generated": tests_generated,
            "tests_executed": tests_executed,
            "tests_passed": tests_passed,
            "failures_healed": failures_healed,
            "flaky_detected": flaky_detected,
            "assertions_added": assertions_added,
            "quality_score": quality_score,
            "next_recommendations": recommendations,
            "verified_at": _now_iso(),
        }

        plan["verification"] = verification
        plan["status"] = "verified"
        self.status = "complete"

        self._publish("quality_score", {
            "summary": "QA cycle verified: quality=%.1f, coverage_delta=%.1f%%" % (quality_score, coverage_delta),
            "plan_id": plan_id,
            "quality_score": quality_score,
            "coverage_delta": coverage_delta,
            "goal_achieved": goal_achieved,
        }, tags=["qa_orchestrator", "verify"])

        return verification

    def _calculate_quality_score(
        self,
        coverage_delta: float,
        tests_generated: int,
        failures_healed: int,
        flaky_detected: int,
        assertions_added: int,
        steps_completed: int,
        steps_total: int,
    ) -> float:
        """Calculate a 0-100 quality score for the cycle."""
        score = 0.0

        # Coverage improvement: up to 30 points
        if coverage_delta > 0:
            score += min(coverage_delta * 3.0, 30.0)
        elif coverage_delta == 0:
            score += 5.0  # No regression

        # Tests generated: up to 20 points
        score += min(tests_generated * 2.0, 20.0)

        # Failures healed: up to 15 points
        score += min(failures_healed * 5.0, 15.0)

        # Flaky detection: up to 10 points
        score += min(flaky_detected * 3.0, 10.0)

        # Assertions added: up to 10 points
        score += min(assertions_added * 0.5, 10.0)

        # Completion rate: up to 15 points
        if steps_total > 0:
            completion_rate = steps_completed / steps_total
            score += completion_rate * 15.0

        return round(min(score, 100.0), 1)

    def _generate_recommendations(
        self,
        coverage_data: Dict[str, Any],
        tests_generated: int,
        failures_healed: int,
        flaky_detected: int,
    ) -> List[str]:
        """Generate next-step recommendations based on results."""
        recommendations = []  # type: List[str]
        summary = coverage_data.get("summary", {})
        gaps = coverage_data.get("gaps", [])

        if summary.get("critical_uncovered", 0) > 0:
            recommendations.append(
                "Kritik %d endpoint hala kapsam disinda — oncelikli test uretimi gerekli"
                % summary["critical_uncovered"]
            )

        coverage_rate = summary.get("coverage_rate", 0)
        if coverage_rate < 50:
            recommendations.append(
                "Kapsam orani %%%.1f ile dusuk — toplu test uretimi kampanyasi onerilir"
                % coverage_rate
            )
        elif coverage_rate < 80:
            recommendations.append(
                "Kapsam %%%.1f — hedef %%80+ icin eksik alanlara odaklanin"
                % coverage_rate
            )

        if flaky_detected > 0:
            recommendations.append(
                "%d flaky test tespit edildi — karantina ve kok neden analizi onerilir"
                % flaky_detected
            )

        # Check gap severity distribution
        critical_gaps = sum(1 for g in gaps if g.get("gap_severity") == "critical")
        if critical_gaps > 0:
            recommendations.append(
                "%d kritik kapsam boslugu mevcut — guvenlik ve uyumluluk testleri oncelikli"
                % critical_gaps
            )

        if not recommendations:
            recommendations.append("Sistem sagligi iyi gorunuyor — duzenli tarama planlayin")

        return recommendations

    # ==================================================================
    # RUN FULL CYCLE
    # ==================================================================

    def run_full_cycle(self, goal: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Run Plan -> Act -> Verify in sequence. Returns complete cycle result."""
        t0 = time.monotonic()

        # PLAN
        plan = self.plan(goal, context=context)
        plan_id = plan["plan_id"]

        # ACT
        execution = self.act(plan_id)

        # VERIFY
        verification = self.verify(plan_id)

        total_ms = round((time.monotonic() - t0) * 1000, 2)

        return {
            "plan_id": plan_id,
            "goal": goal,
            "plan": plan,
            "execution": execution,
            "verification": verification,
            "total_duration_ms": total_ms,
            "status": "complete",
        }

    # ==================================================================
    # EXPLORE (Autonomous Exploration)
    # ==================================================================

    def explore(self, spec_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Autonomous exploration mode.

        Analyses all endpoints, identifies untested/undertested ones,
        generates test plans for gaps, executes and verifies.
        """
        t0 = time.monotonic()

        # 1. Analyze all endpoints
        coverage = self._get_coverage_snapshot()
        summary = coverage.get("summary", {})
        gaps = coverage.get("gaps", [])

        # 2. Detect flaky tests
        flaky_result = {}  # type: Dict[str, Any]
        try:
            from app.domains.api_testing.flaky_detector import detect_flaky_tests
            flaky_tests = detect_flaky_tests(self.db, self.project_id)
            flaky_result = {
                "total": len(flaky_tests),
                "quarantine_recommended": sum(
                    1 for t in flaky_tests if t.get("recommendation") == "quarantine"
                ),
            }
        except Exception as exc:
            flaky_result = {"error": str(exc)[:200]}

        # 3. Build exploration goal based on findings
        uncovered = summary.get("uncovered_endpoints", 0)
        critical = summary.get("critical_uncovered", 0)

        goal_parts = []
        if critical > 0:
            goal_parts.append("%d kritik endpoint icin test olustur" % critical)
        if uncovered > 0:
            goal_parts.append("%d kapsamda olmayan endpoint icin test uret" % uncovered)
        if not goal_parts:
            goal_parts.append("Mevcut testlerin kalitesini artir ve assertion bosluklarini kapat")

        goal = " ve ".join(goal_parts)

        # 4. Run full cycle with the exploration goal
        cycle_context = {
            "mode": "exploration",
            "spec_id": spec_id,
            "gaps_count": len(gaps),
            "critical_uncovered": critical,
        }

        cycle_result = self.run_full_cycle(goal, context=cycle_context)

        total_ms = round((time.monotonic() - t0) * 1000, 2)

        return {
            "exploration_goal": goal,
            "coverage_summary": summary,
            "gaps_found": len(gaps),
            "flaky_analysis": flaky_result,
            "cycle_result": cycle_result,
            "total_duration_ms": total_ms,
        }


# ═══════════════════════════════════════════════════════════════════════
# Utility functions for the router
# ═══════════════════════════════════════════════════════════════════════

def get_plan_status(plan_id: str) -> Dict[str, Any]:
    return {"error": "Plan not found", "plan_id": plan_id}


def get_plan_status_scoped(
    plan_id: str,
    project_id: str,
    user_id: Optional[str] = None,
    is_admin: bool = False,
) -> Dict[str, Any]:
    """Get current plan status with project/user authorization."""
    plan = _plan_store.get(plan_id)
    if not plan:
        return {"error": "Plan not found", "plan_id": plan_id}
    if plan.get("project_id") != project_id:
        return {"error": "Plan not found", "plan_id": plan_id}
    if not is_admin and user_id and plan.get("user_id") and plan.get("user_id") != user_id:
        return {"error": "Plan not found", "plan_id": plan_id}

    steps = plan.get("steps", [])
    return {
        "plan_id": plan_id,
        "project_id": plan.get("project_id"),
        "goal": plan.get("goal", ""),
        "status": plan.get("status", "unknown"),
        "steps_total": len(steps),
        "steps_completed": sum(1 for s in steps if s.get("status") == "completed"),
        "steps_failed": sum(1 for s in steps if s.get("status") == "failed"),
        "steps_pending": sum(1 for s in steps if s.get("status") == "pending"),
        "coverage_before": plan.get("coverage_before"),
        "created_at": plan.get("created_at"),
        "verification": plan.get("verification"),
    }
