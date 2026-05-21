from __future__ import annotations

from app.domains.ai.cross_agent_memory import CrossAgentMemory
from app.domains.ai import qa_orchestrator


def test_cross_agent_memory_filters_by_project() -> None:
    CrossAgentMemory.reset(run_id="run-1", project_id="proj-1")
    CrossAgentMemory.publish(
        agent_name="agent-a",
        event_type="quality_score",
        data={"project_id": "proj-1", "score": 8.5},
        tags=["quality"],
    )
    CrossAgentMemory.publish(
        agent_name="agent-b",
        event_type="quality_score",
        data={"project_id": "proj-2", "score": 6.0},
        tags=["quality"],
    )

    entries = CrossAgentMemory.query(project_id="proj-1", event_types=["quality_score"])
    stats = CrossAgentMemory.stats(project_id="proj-1")

    assert len(entries) == 1
    assert entries[0]["project_id"] == "proj-1"
    assert stats["total_entries"] == 1


def test_cross_agent_memory_context_requires_project_scope() -> None:
    CrossAgentMemory.reset(run_id="run-2", project_id="proj-1")
    CrossAgentMemory.publish(
        agent_name="agent-a",
        event_type="risk_finding",
        data={"project_id": "proj-1", "summary": "critical transfer issue"},
        tags=["risk"],
    )

    assert CrossAgentMemory.get_context_for_agent("agent-b", project_id="proj-2") == ""


def test_get_plan_status_scoped_hides_other_project_plan() -> None:
    qa_orchestrator._plan_store.clear()
    qa_orchestrator._plan_store["plan-1"] = {
        "plan_id": "plan-1",
        "project_id": "proj-1",
        "user_id": "user-1",
        "goal": "increase coverage",
        "status": "planned",
        "steps": [],
    }

    result = qa_orchestrator.get_plan_status_scoped(
        "plan-1",
        project_id="proj-2",
        user_id="user-1",
    )

    assert result["error"] == "Plan not found"


def test_get_plan_status_scoped_hides_other_user_plan() -> None:
    qa_orchestrator._plan_store.clear()
    qa_orchestrator._plan_store["plan-2"] = {
        "plan_id": "plan-2",
        "project_id": "proj-1",
        "user_id": "owner-user",
        "goal": "heal failures",
        "status": "planned",
        "steps": [],
    }

    result = qa_orchestrator.get_plan_status_scoped(
        "plan-2",
        project_id="proj-1",
        user_id="other-user",
        is_admin=False,
    )

    assert result["error"] == "Plan not found"
