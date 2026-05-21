#!/usr/bin/env python3
"""Create an AI workflow release signoff evidence pack.

The default mode runs non-destructive gates and writes a JSON evidence report.
Soak and DR drills are intentionally opt-in because they write to databases and
artifact directories. Use --confirm-data-write together with the relevant flags
only against an approved staging/prod target.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIR = ROOT / "reports"
TAIL_LIMIT = 4000

IMPORTANT_ENV_KEYS = (
    "APP_ENV",
    "ENV",
    "ENVIRONMENT",
    "NODE_ENV",
    "DATABASE_URL",
    "AGENTS_V2_RUN_STORE",
    "ARTIFACTS_DIR",
    "RESTORE_ARTIFACTS_DIR",
    "PGHOST",
    "PGPORT",
    "PGUSER",
    "SOURCE_DB",
    "RESTORE_DB",
    "CONFIRM_RESTORE",
    "AI_GATEWAY_BASE_URL",
    "GATEWAY_INTERNAL_KEY",
    "SIGNOFF_REQUIRE_LIVE_EVAL",
)


@dataclass(frozen=True)
class Check:
    name: str
    command: list[str]
    required: bool = True
    cwd: Path = ROOT
    timeout_seconds: int = 180
    env: dict[str, str] | None = None


def main() -> int:
    args = parse_args()
    output = args.output or default_output_path()
    output.parent.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "evals").mkdir(parents=True, exist_ok=True)

    started_at = utc_now()
    results: list[dict[str, Any]] = []
    context = build_context(args)

    for check in build_base_checks(args):
        results.append(run_check(check))

    if args.profile == "full":
        for check in build_full_checks():
            results.append(run_check(check))

    results.append(run_soak_if_requested(args))
    results.append(run_dr_drill_if_requested(args))

    failed = [
        item
        for item in results
        if item["status"] == "fail" and item.get("required", False)
    ]
    requested_external_checks = args.run_soak and args.run_dr_drill
    external_checks_passed = requested_external_checks and all(
        item["status"] == "pass"
        for item in results
        if item["name"] in {"workflow_soak", "dr_restore_drill"}
    )
    full_local_passed = args.profile == "full" and not failed

    if failed:
        release_decision = "fail"
    elif full_local_passed and external_checks_passed:
        release_decision = "ready_for_operator_approval"
    elif not requested_external_checks:
        release_decision = "needs_external_soak_and_dr_signoff"
    else:
        release_decision = "needs_remaining_release_gates"

    payload = {
        "schema_version": 1,
        "generated_at": utc_now(),
        "started_at": started_at,
        "finished_at": utc_now(),
        "release_decision": release_decision,
        "llm_quality_score": compute_llm_quality_score(results, release_decision),
        "prompt_center_hash": extract_prompt_center_hash(results),
        "eval_summary": extract_eval_summary(results),
        "failed_required_checks": [item["name"] for item in failed],
        "context": context,
        "checks": results,
        "operator_next_steps": operator_next_steps(release_decision),
    }

    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"release_decision": release_decision, "report": str(output)}, ensure_ascii=False))
    return 1 if failed else 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile",
        choices=("quick", "full"),
        default="quick",
        help="quick runs fast non-destructive gates; full also runs tests/type-checks.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Path for the JSON evidence report. Defaults to reports/ai-workflow-signoff-<timestamp>.json.",
    )
    parser.add_argument(
        "--retention-days",
        type=int,
        default=int(os.environ.get("AI_WORKFLOW_ARTIFACT_RETENTION_DAYS", "30")),
        help="Retention window used by the dry-run artifact cleanup gate.",
    )
    parser.add_argument(
        "--run-soak",
        action="store_true",
        help="Run the DB/artifact workflow soak check. Requires --confirm-data-write.",
    )
    parser.add_argument(
        "--run-dr-drill",
        action="store_true",
        help="Run the destructive restore drill. Requires --confirm-data-write.",
    )
    parser.add_argument(
        "--confirm-data-write",
        action="store_true",
        help="Explicitly confirm that the target DB/artifact directories may be written/reset.",
    )
    parser.add_argument(
        "--confirm-production-target",
        action="store_true",
        help="Second confirmation required when APP_ENV/ENV/ENVIRONMENT/NODE_ENV is prod/production.",
    )
    parser.add_argument(
        "--soak-timeout",
        type=int,
        default=300,
        help="Timeout in seconds for the soak check.",
    )
    parser.add_argument(
        "--soak-profile",
        choices=("baseline", "approval-heavy", "artifact-heavy", "load-100", "load-250", "cancel-storm"),
        default=os.environ.get("AI_WORKFLOW_SOAK_PROFILE", "baseline"),
        help="Synthetic soak profile used when --run-soak is enabled.",
    )
    parser.add_argument(
        "--dr-timeout",
        type=int,
        default=900,
        help="Timeout in seconds for the DR restore drill.",
    )
    return parser.parse_args()


def build_base_checks(args: argparse.Namespace) -> list[Check]:
    return [
        Check(
            name="prompt_manifest_integrity",
            command=["python3", "scripts/ops/check-prompt-manifest.py"],
            timeout_seconds=60,
        ),
        Check(
            name="direct_llm_import_guard",
            command=["python3", "scripts/arch_guard_llm_imports.py"],
            timeout_seconds=60,
        ),
        Check(
            name="ops_script_compile",
            command=[
                "python3",
                "-m",
                "py_compile",
                "scripts/ops/ai-workflow-release-signoff.py",
                "scripts/ops/ai-workflow-artifact-retention.py",
                "scripts/ops/build-llm-workflow-plan-xlsx.py",
                "scripts/ops/check-prompt-manifest.py",
                "backend/app/domains/ai/artifact_retention.py",
                "backend/app/domains/ai/workflow_queue.py",
                "backend/app/domains/ai/metrics.py",
                "backend/app/domains/agents/v2/prompts/registry.py",
                "ai-gateway/app/core/models.py",
                "ai-gateway/app/core/router.py",
                "ai-gateway/app/routes/ai_routes.py",
            ],
            timeout_seconds=60,
        ),
        Check(
            name="artifact_retention_dry_run",
            command=[
                "python3",
                "scripts/ops/ai-workflow-artifact-retention.py",
                "--days",
                str(args.retention_days),
            ],
            timeout_seconds=120,
        ),
        Check(
            name="ops_bash_syntax",
            command=[
                "bash",
                "-n",
                "scripts/ops/backup-postgres-artifacts.sh",
                "scripts/ops/restore-postgres-artifacts.sh",
                "scripts/ops/ai-workflow-dr-drill.sh",
            ],
            timeout_seconds=60,
        ),
        Check(
            name="release_runbook_present",
            command=[
                "python3",
                "-c",
                "from pathlib import Path; paths=['docs/ai-workflow-release-signoff.md','docs/ai-workflow-incident-runbook.md']; [(_ for _ in ()).throw(AssertionError(p)) for p in paths if not Path(p).exists() or not Path(p).read_text(encoding='utf-8').strip()]; print('runbook-ok')",
            ],
            timeout_seconds=60,
        ),
        Check(
            name="yaml_parse",
            command=[
                "python3",
                "-c",
                "import yaml; [yaml.safe_load(open(p)) for p in ['.github/workflows/ai-workflow-release-signoff.yml','.github/workflows/ai-workflow-retention.yml','.github/workflows/eval.yml','.github/workflows/engine-eval.yml','.github/workflows/llm-live-eval.yml','infra/prometheus/rules/bgts-alerts.yml']]; print('yaml-ok')",
            ],
            timeout_seconds=60,
        ),
        Check(
            name="compose_config_local",
            command=["bash", "-lc", "docker-compose config || docker compose config"],
            timeout_seconds=120,
        ),
        Check(
            name="compose_config_prod",
            command=["bash", "-lc", "docker-compose -f docker-compose.prod.yml config || docker compose -f docker-compose.prod.yml config"],
            timeout_seconds=120,
        ),
    ]


def build_full_checks() -> list[Check]:
    env = pythonpath_env()
    checks = [
        Check(
            name="backend_ai_workflow_tests",
            command=[
                "pytest",
                "backend/app/domains/agents/v2/tests/test_ai_gateway.py",
                "backend/app/domains/privacy/tests/test_privacy_service.py",
                "backend/app/domains/agents/v2/tests/test_test_runner_sandbox.py",
                "backend/app/domains/ai/tests/test_structured_output_policies.py",
                "backend/app/domains/ai/tests/test_workflow_excel.py",
                "backend/app/domains/ai/tests/test_workflows_api.py",
                "backend/app/domains/ai/tests/test_artifact_retention.py",
                "backend/app/domains/ai/tests/test_workflow_queue.py",
                "backend/app/domains/agents/v2/tests/test_run_store_and_api.py",
                "backend/app/domains/agents/v2/tests/test_prompt_registry_bridge.py",
                "-q",
            ],
            timeout_seconds=300,
            env=env,
        ),
        Check(
            name="eval_harness_smoke_strict",
            command=[
                "python3",
                "-m",
                "app.domains.evals.cli",
                "--suite",
                "harness_smoke",
                "--strict-skip",
                "--no-report",
                "--json",
                str(REPORTS_DIR / "evals" / "signoff-harness-smoke.json"),
            ],
            timeout_seconds=120,
            env=env,
        ),
        Check(
            name="ai_gateway_tests",
            command=["pytest", "ai-gateway/tests/test_gateway.py", "-q"],
            timeout_seconds=120,
        ),
        Check(
            name="frontend_type_check",
            command=["npm", "run", "type-check"],
            cwd=ROOT / "apps" / "web",
            timeout_seconds=240,
        ),
        Check(
            name="ai_workflow_ui_e2e",
            command=[
                "npx",
                "playwright",
                "test",
                "e2e/ai-workflows.spec.ts",
                "--project=regression",
                "--reporter=list",
            ],
            timeout_seconds=180,
            env={"PLAYWRIGHT_BROWSERS_PATH": str(ROOT / ".pw-browsers")},
        ),
    ]
    checks.append(build_live_eval_check(env))
    return checks


def build_live_eval_check(base_env: dict[str, str]) -> Check:
    required = should_require_live_eval()
    return Check(
        name="live_eval_contract_strict",
        command=[
            "python3",
            "-m",
            "app.domains.evals.cli",
            "--suites-dir",
            "app/domains/evals/live_suites",
            "--suite",
            "ai_gateway_live",
            "--strict-skip",
            "--no-report",
            "--json",
            str(REPORTS_DIR / "evals" / "signoff-live-eval.json"),
        ],
        timeout_seconds=180,
        env={
            **base_env,
            "EVAL_RUN_LLM": "1",
            "EVAL_REPORTS_DIR": str(REPORTS_DIR / "evals-live"),
            "AI_GATEWAY_BASE_URL": os.environ.get("AI_GATEWAY_BASE_URL", "http://127.0.0.1:8080"),
            "GATEWAY_INTERNAL_KEY": os.environ.get("GATEWAY_INTERNAL_KEY", ""),
        },
        required=required,
    )


def should_require_live_eval() -> bool:
    flag = os.environ.get("SIGNOFF_REQUIRE_LIVE_EVAL", "").strip().lower()
    if flag in {"1", "true", "yes", "required"}:
        return True
    return bool(os.environ.get("AI_GATEWAY_BASE_URL") and os.environ.get("GATEWAY_INTERNAL_KEY"))


def run_soak_if_requested(args: argparse.Namespace) -> dict[str, Any]:
    if not args.run_soak:
        return skipped("workflow_soak", "Pass --run-soak to execute this DB/artifact write gate.")
    if not args.confirm_data_write:
        return failed_precondition(
            "workflow_soak",
            "--run-soak writes workflow rows and artifacts; rerun with --confirm-data-write after target approval.",
        )
    if is_prod_like_environment() and not args.confirm_production_target:
        return failed_precondition(
            "workflow_soak",
            "Prod-like environment detected; rerun with --confirm-production-target after release-manager approval.",
        )
    if not os.environ.get("DATABASE_URL"):
        return failed_precondition("workflow_soak", "DATABASE_URL is required for the soak gate.")

    env = pythonpath_env()
    env["AGENTS_V2_RUN_STORE"] = "postgres"
    return run_check(
        Check(
            name="workflow_soak",
            command=["python3", "scripts/ops/ai-workflow-soak.py", "--profile", args.soak_profile],
            timeout_seconds=args.soak_timeout,
            env=env,
        )
    )


def run_dr_drill_if_requested(args: argparse.Namespace) -> dict[str, Any]:
    if not args.run_dr_drill:
        return skipped("dr_restore_drill", "Pass --run-dr-drill to execute this destructive restore rehearsal.")
    if not args.confirm_data_write:
        return failed_precondition(
            "dr_restore_drill",
            "--run-dr-drill recreates the restore DB and artifact directory; rerun with --confirm-data-write after target approval.",
        )
    if is_prod_like_environment() and not args.confirm_production_target:
        return failed_precondition(
            "dr_restore_drill",
            "Prod-like environment detected; rerun with --confirm-production-target after release-manager approval.",
        )
    source_db = os.environ.get("SOURCE_DB")
    restore_db = os.environ.get("RESTORE_DB")
    if source_db and restore_db and source_db == restore_db:
        return failed_precondition("dr_restore_drill", "SOURCE_DB and RESTORE_DB must be different.")
    artifacts_dir = os.environ.get("ARTIFACTS_DIR")
    restore_artifacts_dir = os.environ.get("RESTORE_ARTIFACTS_DIR")
    if artifacts_dir and restore_artifacts_dir and artifacts_dir == restore_artifacts_dir:
        return failed_precondition(
            "dr_restore_drill",
            "ARTIFACTS_DIR and RESTORE_ARTIFACTS_DIR must be different.",
        )

    env = os.environ.copy()
    env["CONFIRM_RESTORE"] = "true"
    return run_check(
        Check(
            name="dr_restore_drill",
            command=["bash", "scripts/ops/ai-workflow-dr-drill.sh"],
            timeout_seconds=args.dr_timeout,
            env=env,
        )
    )


def run_check(check: Check) -> dict[str, Any]:
    started = time.monotonic()
    wall_started = utc_now()
    env = os.environ.copy()
    if check.env:
        env.update(check.env)
    precondition = missing_precondition(check.name, env, check.required)
    if precondition is not None:
        return precondition
    try:
        completed = subprocess.run(
            check.command,
            cwd=check.cwd,
            env=env,
            text=True,
            capture_output=True,
            timeout=check.timeout_seconds,
            check=False,
        )
        duration_ms = int((time.monotonic() - started) * 1000)
        return {
            "name": check.name,
            "status": "pass" if completed.returncode == 0 else "fail",
            "required": check.required,
            "command": check.command,
            "cwd": str(check.cwd),
            "started_at": wall_started,
            "duration_ms": duration_ms,
            "exit_code": completed.returncode,
            "stdout_tail": tail(completed.stdout),
            "stderr_tail": tail(completed.stderr),
        }
    except subprocess.TimeoutExpired as exc:
        duration_ms = int((time.monotonic() - started) * 1000)
        return {
            "name": check.name,
            "status": "fail",
            "required": check.required,
            "command": check.command,
            "cwd": str(check.cwd),
            "started_at": wall_started,
            "duration_ms": duration_ms,
            "exit_code": None,
            "stdout_tail": tail(exc.stdout or ""),
            "stderr_tail": tail(exc.stderr or f"Timed out after {check.timeout_seconds}s"),
        }


def missing_precondition(name: str, env: dict[str, str], required: bool) -> dict[str, Any] | None:
    if name != "live_eval_contract_strict":
        return None
    missing: list[str] = []
    if not env.get("AI_GATEWAY_BASE_URL"):
        missing.append("AI_GATEWAY_BASE_URL")
    if not env.get("GATEWAY_INTERNAL_KEY"):
        missing.append("GATEWAY_INTERNAL_KEY")
    if not missing:
        return None
    status = "fail" if required else "skipped"
    return {
        "name": name,
        "status": status,
        "required": required,
        "command": [
            "python3",
            "-m",
            "app.domains.evals.cli",
            "--suites-dir",
            "app/domains/evals/live_suites",
            "--suite",
            "ai_gateway_live",
            "--strict-skip",
        ],
        "cwd": str(ROOT),
        "started_at": utc_now(),
        "duration_ms": 0,
        "exit_code": None,
        "stdout_tail": "",
        "stderr_tail": "",
        "message": f"Missing required live eval env: {', '.join(missing)}",
    }


def skipped(name: str, reason: str) -> dict[str, Any]:
    return {
        "name": name,
        "status": "skipped",
        "required": False,
        "skipped_reason": reason,
    }


def failed_precondition(name: str, reason: str) -> dict[str, Any]:
    return {
        "name": name,
        "status": "fail",
        "required": True,
        "skipped_reason": reason,
        "exit_code": None,
    }


def build_context(args: argparse.Namespace) -> dict[str, Any]:
    env_values = {
        key: os.environ.get(key)
        for key in ("APP_ENV", "ENV", "ENVIRONMENT", "NODE_ENV")
        if os.environ.get(key)
    }
    return {
        "cwd": str(ROOT),
        "hostname": platform.node(),
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "profile": args.profile,
        "retention_days": args.retention_days,
        "run_soak_requested": args.run_soak,
        "soak_profile": args.soak_profile,
        "run_dr_drill_requested": args.run_dr_drill,
        "data_write_confirmed": args.confirm_data_write,
        "production_target_confirmed": args.confirm_production_target,
        "prod_like_environment": is_prod_like_environment(),
        "environment_names": env_values,
        "env_keys_present": sorted(key for key in IMPORTANT_ENV_KEYS if os.environ.get(key)),
    }


def operator_next_steps(release_decision: str) -> list[str]:
    if release_decision == "fail":
        return ["Fix failed_required_checks, regenerate this evidence pack, then rerun release review."]
    if release_decision == "ready_for_operator_approval":
        return ["Attach this JSON to the release ticket and record the human approval decision."]
    return [
        "Run --profile full for the complete local release gate set.",
        "Against approved staging/prod credentials, rerun with --run-soak --run-dr-drill --confirm-data-write.",
        "For prod-like targets, add --confirm-production-target after release-manager approval.",
        "Attach the generated JSON report to the release ticket before deployment approval.",
    ]


def compute_llm_quality_score(results: list[dict[str, Any]], release_decision: str) -> float:
    weights = {
        "prompt_manifest_integrity": 0.12,
        "direct_llm_import_guard": 0.12,
        "backend_ai_workflow_tests": 0.17,
        "eval_harness_smoke_strict": 0.16,
        "live_eval_contract_strict": 0.06,
        "ai_gateway_tests": 0.06,
        "frontend_type_check": 0.08,
        "ai_workflow_ui_e2e": 0.08,
        "artifact_retention_dry_run": 0.04,
        "yaml_parse": 0.04,
        "compose_config_local": 0.03,
        "compose_config_prod": 0.03,
        "release_runbook_present": 0.04,
    }
    by_name = {item.get("name"): item for item in results}
    score = 0.0
    for name, weight in weights.items():
        if by_name.get(name, {}).get("status") == "pass":
            score += weight
    if release_decision == "ready_for_operator_approval":
        score = min(score + 0.02, 1.0)
    elif release_decision == "needs_external_soak_and_dr_signoff":
        score = min(score, 0.989)
    elif release_decision == "needs_remaining_release_gates":
        score = min(score, 0.95)
    return round(score * 10.0, 2)


def extract_prompt_center_hash(results: list[dict[str, Any]]) -> str | None:
    for item in results:
        if item.get("name") != "prompt_manifest_integrity":
            continue
        match = re.search(r"prompt-manifest-ok\s+([a-f0-9]{64})", item.get("stdout_tail", ""))
        if match:
            return match.group(1)
    return None


def extract_eval_summary(results: list[dict[str, Any]]) -> dict[str, Any] | None:
    for item in results:
        if item.get("name") != "eval_harness_smoke_strict":
            continue
        text = item.get("stdout_tail") or ""
        start = text.find("{")
        if start < 0:
            return None
        try:
            data = json.loads(text[start:])
        except json.JSONDecodeError:
            return None
        return {
            "overall_passed": bool(data.get("overall_passed")),
            "total_suites": int(data.get("total_suites") or 0),
            "failed_suites": int(data.get("failed_suites") or 0),
            "suites": [
                {
                    "name": suite.get("name"),
                    "passed": bool(suite.get("passed")),
                    "skipped": bool(suite.get("skipped")),
                    "cases_total": int(suite.get("cases_total") or 0),
                    "cases_passed": int(suite.get("cases_passed") or 0),
                    "aggregate": suite.get("aggregate") or {},
                }
                for suite in data.get("suites", [])
                if isinstance(suite, dict)
            ],
        }
    return None


def pythonpath_env() -> dict[str, str]:
    existing = os.environ.get("PYTHONPATH")
    backend = str(ROOT / "backend")
    return {"PYTHONPATH": backend if not existing else f"{backend}{os.pathsep}{existing}"}


def is_prod_like_environment() -> bool:
    return any(
        os.environ.get(key, "").lower() in {"prod", "production"}
        for key in ("APP_ENV", "ENV", "ENVIRONMENT", "NODE_ENV")
    )


def default_output_path() -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    return REPORTS_DIR / f"ai-workflow-signoff-{stamp}-pid{os.getpid()}.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def tail(value: str, limit: int = TAIL_LIMIT) -> str:
    if len(value) <= limit:
        return value
    return value[-limit:]


if __name__ == "__main__":
    raise SystemExit(main())
