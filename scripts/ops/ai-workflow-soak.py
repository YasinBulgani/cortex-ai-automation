#!/usr/bin/env python3
"""Local AI workflow durability/load soak check.

This script assumes DATABASE_URL points at an isolated test database that has
already been migrated to Alembic head. It writes workflow runs/events/artifacts,
simulates a process restart by resetting the run-store singleton, and verifies
that state can be replayed from Postgres.
"""
from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4


TERMINAL_STATUSES = {"completed", "failed", "failed_validation", "cancelled"}
STRUCTURED_WORKFLOW_TYPES = (
    "test_generation",
    "analysis",
    "code_generation",
    "review",
    "repair",
    "report",
)


@dataclass(frozen=True)
class SoakProfile:
    name: str
    runs: int
    approval_ratio: float
    artifact_bytes: int
    dead_letter_interval: int
    cancel_interval: int
    failed_validation_interval: int
    active_interval: int


PROFILES: dict[str, SoakProfile] = {
    "baseline": SoakProfile(
        name="baseline",
        runs=20,
        approval_ratio=0.5,
        artifact_bytes=64,
        dead_letter_interval=20,
        cancel_interval=0,
        failed_validation_interval=0,
        active_interval=0,
    ),
    "approval-heavy": SoakProfile(
        name="approval-heavy",
        runs=60,
        approval_ratio=0.8,
        artifact_bytes=96,
        dead_letter_interval=15,
        cancel_interval=0,
        failed_validation_interval=0,
        active_interval=0,
    ),
    "artifact-heavy": SoakProfile(
        name="artifact-heavy",
        runs=80,
        approval_ratio=0.4,
        artifact_bytes=16 * 1024,
        dead_letter_interval=20,
        cancel_interval=0,
        failed_validation_interval=0,
        active_interval=8,
    ),
    "load-100": SoakProfile(
        name="load-100",
        runs=100,
        approval_ratio=0.35,
        artifact_bytes=512,
        dead_letter_interval=12,
        cancel_interval=10,
        failed_validation_interval=9,
        active_interval=11,
    ),
    "load-250": SoakProfile(
        name="load-250",
        runs=250,
        approval_ratio=0.35,
        artifact_bytes=1024,
        dead_letter_interval=10,
        cancel_interval=9,
        failed_validation_interval=8,
        active_interval=7,
    ),
    "cancel-storm": SoakProfile(
        name="cancel-storm",
        runs=120,
        approval_ratio=0.25,
        artifact_bytes=256,
        dead_letter_interval=15,
        cancel_interval=3,
        failed_validation_interval=12,
        active_interval=5,
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile",
        choices=tuple(PROFILES),
        default="baseline",
        help="Synthetic soak profile to execute.",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=None,
        help="Override the run count for the selected profile.",
    )
    parser.add_argument(
        "--artifact-bytes",
        type=int,
        default=None,
        help="Override artifact payload size in bytes.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional JSON output file path for the soak evidence report.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    profile = resolve_profile(args)
    os.environ.setdefault("AGENTS_V2_RUN_STORE", "postgres")
    artifacts_dir = Path(os.environ.get("ARTIFACTS_DIR", f"/tmp/neurex-soak-artifacts/{profile.name}"))
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    from app.config import settings
    import app.domains.agents.v2.run_store as rs_mod
    from app.domains.ai.workflows_router import _build_workflow_health

    settings.artifacts_dir = str(artifacts_dir)
    rs_mod._singleton = None
    store = rs_mod.get_run_store()
    expected_statuses: Counter[str] = Counter()
    expected_workflow_types: Counter[str] = Counter()
    expected_dead_letters = 0
    expected_approvals = 0
    expected_artifact_bytes = 0
    created_ids: list[str] = []

    for index in range(1, profile.runs + 1):
        workflow_type = STRUCTURED_WORKFLOW_TYPES[(index - 1) % len(STRUCTURED_WORKFLOW_TYPES)]
        requires_approval = index <= int(profile.runs * profile.approval_ratio)
        run_id, state = store.create(
            project_id=str(uuid4()),
            user_id="soak-user",
            tenant_id="00000000-0000-0000-0000-000000000001",
            input_source="text",
            input_payload={
                "text": f"{profile.name} workflow {index}",
                "workflow": {
                    "type": workflow_type,
                    "dry_run": True,
                    "requires_approval": requires_approval,
                },
            },
        )
        llm_calls_count = 1 + (index % 4)
        state.update(
            {
                "workflow_type": workflow_type,
                "dry_run": True,
                "requires_approval": requires_approval,
                "tokens_used": index * 10,
                "cost_usd": round(index * 0.001, 6),
                "llm_calls_count": llm_calls_count,
            }
        )
        store.update_state(run_id, state)
        store.update_status(run_id, "queued")
        publish_event(
            store,
            run_id,
            "workflow_created",
            {"index": index, "profile": profile.name, "workflow_type": workflow_type},
        )
        publish_event(store, run_id, "queue_enqueued", {"backend": "soak", "profile": profile.name})

        if requires_approval:
            approval = store.record_approval(
                run_id,
                actor_id="soak-approver",
                decision="approved",
                note=f"{profile.name} approval",
            )
            expected_approvals += 1
            publish_event(
                store,
                run_id,
                "approval_recorded",
                {"approval_id": approval["approval_id"] if approval else None},
            )
        else:
            approval = None

        store.update_status(run_id, "running")
        publish_event(store, run_id, "soak_progress", {"index": index, "phase": "running"})

        status = determine_status(profile, index, requires_approval)
        attach_artifact = status not in {"queued"}
        if attach_artifact:
            artifact_path = artifacts_dir / run_id / "soak.txt"
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_text(build_artifact_payload(run_id, profile.artifact_bytes), encoding="utf-8")
            artifact = store.add_artifact(
                run_id,
                kind="soak_artifact",
                name="soak.txt",
                storage_path=str(artifact_path),
                mime_type="text/plain",
                size_bytes=artifact_path.stat().st_size,
                metadata={"approval_id": approval["approval_id"] if approval else None},
            )
            expected_artifact_bytes += int(artifact["size_bytes"] if artifact else artifact_path.stat().st_size)
            publish_event(
                store,
                run_id,
                "artifact_created",
                {"artifact_id": artifact["artifact_id"] if artifact else None},
            )

        if status == "completed":
            store.update_status(run_id, "completed")
            publish_event(store, run_id, "workflow_completed", {"result": "ok"})
        elif status == "failed_validation":
            store.update_status(run_id, "failed_validation", "synthetic schema mismatch")
            publish_event(
                store,
                run_id,
                "failed_validation",
                {"reason": "synthetic schema mismatch", "profile": profile.name},
            )
        elif status == "cancelled":
            state["cancelled"] = True
            state["status"] = "cancelled"
            store.update_state(run_id, state)
            store.update_status(run_id, "cancelled", "synthetic cancel storm")
            publish_event(store, run_id, "cancelled", {"reason": "synthetic cancel storm"})
        elif status == "pending_approval":
            store.update_status(run_id, "pending_approval")
            publish_event(store, run_id, "approval_required", {"reason": "synthetic hold"})
        elif status == "running":
            store.update_status(run_id, "running")
        else:
            raise AssertionError(f"Unsupported synthetic status: {status}")

        if profile.dead_letter_interval and index % profile.dead_letter_interval == 0:
            store.record_dead_letter(
                run_id=run_id,
                queue_name="ai_workflows",
                reason=f"{profile.name} synthetic dead letter",
                payload={"profile": profile.name, "index": index},
                retry_count=index % 4,
                last_error="synthetic",
            )
            expected_dead_letters += 1

        expected_statuses[status] += 1
        expected_workflow_types[workflow_type] += 1
        created_ids.append(run_id)

    rs_mod._singleton = None
    replay = rs_mod.get_run_store()
    replayed = verify_replay(
        replay,
        created_ids=created_ids,
        expected_statuses=expected_statuses,
        expected_dead_letters=expected_dead_letters,
    )
    health = _build_workflow_health(limit=1000).model_dump(mode="json")
    profile_summary = build_profile_summary(replay, created_ids)

    if int(profile_summary["runs_total"]) != profile.runs:
        raise AssertionError(f"profile runs_total={profile_summary['runs_total']} expected {profile.runs}")
    if profile_summary["by_status"] != dict(expected_statuses):
        raise AssertionError(f"profile by_status mismatch: {profile_summary['by_status']} != {dict(expected_statuses)}")
    if profile_summary["by_workflow_type"] != dict(expected_workflow_types):
        raise AssertionError(
            f"profile by_workflow_type mismatch: {profile_summary['by_workflow_type']} != {dict(expected_workflow_types)}"
        )
    if int(profile_summary["approval_count"]) != expected_approvals:
        raise AssertionError(f"approval_count mismatch: {profile_summary['approval_count']} != {expected_approvals}")
    if int(profile_summary["dead_letters_total"]) != expected_dead_letters:
        raise AssertionError(
            f"dead_letters_total mismatch: {profile_summary['dead_letters_total']} != {expected_dead_letters}"
        )
    if int(profile_summary["artifact_bytes"]) < expected_artifact_bytes:
        raise AssertionError(
            f"artifact_bytes mismatch: {profile_summary['artifact_bytes']} < {expected_artifact_bytes}"
        )

    result = {
        "profile": profile.name,
        "created_runs": profile.runs,
        "replayed_runs": replayed,
        "expected_statuses": dict(expected_statuses),
        "expected_workflow_types": dict(expected_workflow_types),
        "expected_dead_letters": expected_dead_letters,
        "artifact_dir": str(artifacts_dir),
        "profile_summary": profile_summary,
        "health": health,
    }
    serialized = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized + "\n", encoding="utf-8")
    print(serialized)
    return 0


def resolve_profile(args: argparse.Namespace) -> SoakProfile:
    base = PROFILES[args.profile]
    return SoakProfile(
        name=base.name,
        runs=args.runs or base.runs,
        approval_ratio=base.approval_ratio,
        artifact_bytes=args.artifact_bytes or base.artifact_bytes,
        dead_letter_interval=base.dead_letter_interval,
        cancel_interval=base.cancel_interval,
        failed_validation_interval=base.failed_validation_interval,
        active_interval=base.active_interval,
    )


def determine_status(profile: SoakProfile, index: int, requires_approval: bool) -> str:
    if profile.cancel_interval and index % profile.cancel_interval == 0:
        return "cancelled"
    if profile.failed_validation_interval and index % profile.failed_validation_interval == 0:
        return "failed_validation"
    if profile.active_interval and index % profile.active_interval == 0:
        return "pending_approval" if requires_approval else "running"
    return "completed"


def publish_event(store, run_id: str, event_type: str, data: dict[str, object]) -> None:
    store.publish(
        run_id,
        {
            "event_type": event_type,
            "run_id": run_id,
            "workflow_id": run_id,
            "data": data,
        },
    )


def build_artifact_payload(run_id: str, target_size: int) -> str:
    prefix = f"artifact for {run_id}\n"
    if target_size <= len(prefix):
        return prefix
    padding = "x" * (target_size - len(prefix))
    return prefix + padding


def verify_replay(
    store,
    *,
    created_ids: list[str],
    expected_statuses: Counter[str],
    expected_dead_letters: int,
) -> int:
    missing: list[str] = []
    actual_statuses: Counter[str] = Counter()
    replayed = 0
    for run_id in created_ids:
        rec = store.get(run_id)
        if not rec:
            missing.append(run_id)
            continue
        replayed += 1
        actual_statuses[rec.status] += 1
        if not store.list_events(run_id):
            raise AssertionError(f"{run_id} events were not replayed")
        if rec.status != "queued":
            artifacts = store.list_artifacts(run_id)
            if rec.status != "running" and not artifacts:
                raise AssertionError(f"{run_id} artifacts were not replayed")
            if artifacts and "sha256" not in artifacts[0].get("metadata", {}):
                raise AssertionError(f"{run_id} artifact integrity metadata missing")
        if rec.status in TERMINAL_STATUSES and rec.completed_at is None:
            raise AssertionError(f"{run_id} terminal completed_at missing")
        if rec.status == "cancelled" and not any(
            event.get("event_type") == "cancelled" for event in store.list_events(run_id)
        ):
            raise AssertionError(f"{run_id} cancelled event missing")

    if missing:
        raise AssertionError(f"Missing replayed runs: {missing[:3]}")
    if actual_statuses != expected_statuses:
        raise AssertionError(f"Replayed status mismatch: {dict(actual_statuses)} != {dict(expected_statuses)}")

    dead_letters = store.list_dead_letters(limit=max(expected_dead_letters + 5, 25))
    if len(dead_letters) < expected_dead_letters:
        raise AssertionError(f"Dead letter replay mismatch: {len(dead_letters)} < {expected_dead_letters}")
    return replayed


def build_profile_summary(store, created_ids: list[str]) -> dict[str, object]:
    run_ids = set(created_ids)
    by_status: Counter[str] = Counter()
    by_workflow_type: Counter[str] = Counter()
    event_counts: Counter[str] = Counter()
    totals = {
        "artifact_count": 0,
        "artifact_bytes": 0,
        "approval_count": 0,
        "cost_usd": 0.0,
        "tokens_used": 0,
        "llm_calls_count": 0,
    }
    active_runs = 0

    for run_id in created_ids:
        rec = store.get(run_id)
        if rec is None:
            continue
        by_status[rec.status] += 1
        workflow_type = str(rec.state.get("workflow_type") or "")
        if workflow_type:
            by_workflow_type[workflow_type] += 1
        if rec.status in {"pending_approval", "queued", "running"}:
            active_runs += 1
        totals["artifact_count"] += len(rec.artifacts)
        totals["artifact_bytes"] += sum(int(item.size_bytes or 0) for item in rec.artifacts)
        totals["approval_count"] += len(rec.approvals)
        totals["cost_usd"] += float(rec.state.get("cost_usd", 0.0) or 0.0)
        totals["tokens_used"] += int(rec.state.get("tokens_used", 0) or 0)
        totals["llm_calls_count"] += int(rec.state.get("llm_calls_count", 0) or 0)
        for event in rec.events:
            event_counts[str(event.get("event_type") or "message")] += 1

    dead_letters = [
        item
        for item in store.list_dead_letters(limit=max(len(created_ids) * 2, 100))
        if item.get("run_id") in run_ids
    ]

    return {
        "runs_total": len(created_ids),
        "active_runs": active_runs,
        "by_status": dict(by_status),
        "by_workflow_type": dict(by_workflow_type),
        "event_counts": dict(event_counts),
        "artifact_count": int(totals["artifact_count"]),
        "artifact_bytes": int(totals["artifact_bytes"]),
        "approval_count": int(totals["approval_count"]),
        "dead_letters_total": len(dead_letters),
        "cost_usd": round(float(totals["cost_usd"]), 6),
        "tokens_used": int(totals["tokens_used"]),
        "llm_calls_count": int(totals["llm_calls_count"]),
    }


if __name__ == "__main__":
    raise SystemExit(main())
