"""Pure mapping helpers: Kiwi TCMS objects → Neurex Management shapes.

No DB, no I/O — everything here is deterministic and unit-testable. The service
layer consumes these dicts to upsert ``test_management`` models. Kiwi's
``*.filter`` serialization flattens related fields (e.g. ``category__name``,
``priority__value``); readers below are defensive about which key is present.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

# ── value maps ─────────────────────────────────────────────────────────
# Kiwi priority values are typically P1..P5 (P1 = highest).
_PRIORITY_MAP = {
    "P1": "critical",
    "P2": "high",
    "P3": "medium",
    "P4": "low",
    "P5": "low",
}

# Kiwi TestCaseStatus names → Neurex case status.
_CASE_STATUS_MAP = {
    "PROPOSED": "draft",
    "CONFIRMED": "ready",
    "NEED_UPDATE": "draft",
    "DISABLED": "deprecated",
}

# Kiwi TestExecutionStatus names → Neurex run-case status.
_EXEC_STATUS_MAP = {
    "IDLE": "not_run",
    "RUNNING": "in_progress",
    "PASSED": "passed",
    "FAILED": "failed",
    "BLOCKED": "blocked",
    "ERROR": "failed",
    "WAIVED": "skipped",
}


def _first(raw: dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Return the first present, non-None value among ``keys``."""
    for k in keys:
        if k in raw and raw[k] is not None:
            return raw[k]
    return default


def map_priority(value: Any) -> str:
    return _PRIORITY_MAP.get(str(value or "").strip().upper(), "medium")


def map_case_status(name: Any) -> str:
    return _CASE_STATUS_MAP.get(str(name or "").strip().upper(), "draft")


def map_execution_status(name: Any) -> str:
    return _EXEC_STATUS_MAP.get(str(name or "").strip().upper(), "not_run")


# ── category → suite ───────────────────────────────────────────────────
def map_category_to_suite(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "external_id": str(raw["id"]),
        "name": (_first(raw, "name", default="") or "").strip() or f"Kategori {raw['id']}",
        "description": _first(raw, "description", default="") or "",
    }


# ── case → case (+ steps) ──────────────────────────────────────────────
def _parse_steps(text: Any) -> list[dict[str, Any]]:
    """Kiwi stores the scenario as a single free-text/markdown ``text`` field.

    Phase 1 keeps it as one step; structured step extraction is a later concern.
    """
    body = (text or "").strip()
    if not body:
        return []
    return [{"step_no": 1, "action": body, "expected_result": "", "is_required": True}]


def map_case_to_neurex(raw: dict[str, Any]) -> dict[str, Any]:
    is_automated = bool(_first(raw, "is_automated", default=False))
    tags = _first(raw, "tag", "tags", default=[]) or []
    if not isinstance(tags, list):
        tags = [str(tags)]
    return {
        "external_id": str(raw["id"]),
        "category_external_id": (
            str(raw["category"]) if _first(raw, "category") is not None else None
        ),
        "title": (_first(raw, "summary", default="") or "").strip() or f"Kiwi case {raw['id']}",
        "objective": _first(raw, "notes", default="") or "",
        "preconditions": _first(raw, "setup", default="") or "",
        "priority": map_priority(_first(raw, "priority__value", "priority")),
        "automation_status": "automated" if is_automated else "manual",
        "status": map_case_status(_first(raw, "case_status__name", "case_status")),
        "tags": [str(t) for t in tags],
        "source_ref": f"kiwi:case:{raw['id']}",
        "steps": _parse_steps(_first(raw, "text", default="")),
    }


def case_fingerprint(mapped: dict[str, Any]) -> str:
    """Stable hash of the mapped case used to skip unchanged records on re-sync."""
    material = {
        "title": mapped["title"],
        "objective": mapped["objective"],
        "preconditions": mapped["preconditions"],
        "priority": mapped["priority"],
        "automation_status": mapped["automation_status"],
        "status": mapped["status"],
        "tags": sorted(mapped["tags"]),
        "steps": mapped["steps"],
    }
    encoded = json.dumps(material, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]


# ── TestPlan → TestPlan ────────────────────────────────────────────────
_PLAN_TYPE_MAP = {
    "master": "regression",
    "release": "regression",
    "iteration": "regression",
    "canary": "smoke",
    "smoke": "smoke",
}


def map_plan_to_neurex(raw: dict[str, Any]) -> dict[str, Any]:
    plan_type_raw = str(_first(raw, "type__name", "type", default="") or "").lower()
    return {
        "external_id": str(raw["id"]),
        "name": (_first(raw, "name", default="") or "").strip() or f"Kiwi Plan {raw['id']}",
        "plan_type": _PLAN_TYPE_MAP.get(plan_type_raw, "regression"),
        "scope_summary": _first(raw, "text", default="") or "",
    }


def plan_fingerprint(mapped: dict[str, Any]) -> str:
    material = {"name": mapped["name"], "plan_type": mapped["plan_type"]}
    encoded = json.dumps(material, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]


# ── TestRun → TestCycle + TestRun ─────────────────────────────────────
_RUN_STATUS_MAP = {
    "RUNNING": "in_progress",
    "FINISHED": "completed",
    "STOPPED": "completed",
    "IDLE": "planned",
}


def map_run_status(name: Any) -> str:
    return _RUN_STATUS_MAP.get(str(name or "").strip().upper(), "planned")


def map_run_to_neurex(raw: dict[str, Any]) -> dict[str, Any]:
    """Kiwi TestRun → shapes for Neurex TestCycle (wrapping a single TestRun)."""
    build = _first(raw, "build__name", "build", default="") or ""
    environment = _first(raw, "environment__name", "environment", default="") or ""
    return {
        "external_id": str(raw["id"]),
        "plan_external_id": str(raw["plan"]) if _first(raw, "plan") is not None else None,
        "name": (_first(raw, "summary", "name", default="") or "").strip() or f"Kiwi Run {raw['id']}",
        "build_version": str(build) if build else None,
        "environment": str(environment) if environment else None,
        "status": map_run_status(_first(raw, "status__name", "status")),
    }


def run_fingerprint(mapped: dict[str, Any]) -> str:
    material = {"name": mapped["name"], "status": mapped["status"], "build_version": mapped["build_version"]}
    encoded = json.dumps(material, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]


# ── TestExecution → TestRunCase ────────────────────────────────────────
def map_execution_to_neurex(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "external_id": str(raw["id"]),
        "run_external_id": str(raw["run"]) if _first(raw, "run") is not None else None,
        "case_external_id": str(raw["case"]) if _first(raw, "case") is not None else None,
        "status": map_execution_status(_first(raw, "status__name", "status")),
        "actual_result": _first(raw, "tested_by__username", default=None),
        "execution_notes": _first(raw, "notes", default="") or "",
    }


# ── Bug → DefectLink ──────────────────────────────────────────────────
def map_bug_to_neurex(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "external_id": str(raw["id"]),
        "execution_external_id": str(raw["execution"]) if _first(raw, "execution") is not None else None,
        "external_key": str(_first(raw, "bug_id", "id", default=raw["id"])),
        "title": (_first(raw, "summary", "bug_id", default="") or f"Bug {raw['id']}").strip()[:500],
        "url": _first(raw, "url", default=None),
        "status": "open",
    }
