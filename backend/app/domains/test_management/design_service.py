"""Service layer for M-1 (BVA), M-2 (Equivalence Partitioning) and M-9
(Parameterized Cases / Data Tables).

HTTP-agnostic helpers backing ``/design/*`` and ``/cases/*/params|data|expand``
endpoints. Raises ``ValueError`` (→ 400) or ``KeyError`` (→ 404) so the
router can translate to HTTP without leaking implementation details.

Every LLM call goes through ``comments_service._call_llm`` so we share the
same gateway-availability + JSON-extraction logic. When the gateway is not
available (offline tests, local dev) a deterministic heuristic kicks in and
``source`` on the run is recorded as ``"fallback"``.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import uuid as _uuid_mod
from collections.abc import Iterable
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.test_management import service as tm_service
from app.domains.test_management.comments_service import _call_llm, _load_prompt
from app.domains.test_management.models import (
    DEFAULT_TENANT_ID,
    MgmtCaseDataRow,
    MgmtCaseParamSet,
    MgmtDesignInputField,
    MgmtDesignPartition,
    MgmtDesignTechniqueRun,
    TestCase,
    TestManagementAuditEvent,
)
from app.domains.test_management.schemas import (
    ALLOWED_TECHNIQUES,
    BvaRunCreate,
    CaseDataGenerateRequest,
    CaseDataRowIn,
    CaseParamSetCreate,
    DesignFieldSpec,
    DesignRunOut,
    DtRunCreate,
    EqRunCreate,
    GeneratedCaseDraft,
    PairwiseRunCreate,
    PromoteCasesRequest,
    TestCaseCreate,
)

logger = logging.getLogger(__name__)


# ── helpers ──────────────────────────────────────────────────────────────────


def _actor(user: Any | None) -> Optional[str]:
    if user is None:
        return None
    val = getattr(user, "id", None)
    return str(val) if val else None


def _tenant_for(user: Any | None) -> str:
    if user is None:
        return DEFAULT_TENANT_ID
    val = getattr(user, "tenant_id", None)
    return str(val) if val else DEFAULT_TENANT_ID


def _audit(
    db: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: str | None,
    project_id: str | None,
    user: Any | None,
    payload: dict[str, Any] | None = None,
) -> None:
    db.add(
        TestManagementAuditEvent(
            project_id=project_id,
            actor_id=_actor(user),
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload or {},
        )
    )


def _serialize_run(run: MgmtDesignTechniqueRun) -> dict[str, Any]:
    return {
        "id": run.id,
        "tenant_id": run.tenant_id,
        "project_id": run.project_id,
        "requirement_id": run.requirement_id,
        "technique": run.technique,
        "input_spec": dict(run.input_spec or {}),
        "generated_cases": list(run.generated_cases or []),
        "source": run.source,
        "llm_trace_id": run.llm_trace_id,
        "created_by": run.created_by,
        "created_at": run.created_at,
        "partitions": [
            {
                "id": p.id,
                "field_id": p.field_id,
                "partition_label": p.partition_label,
                "is_valid": p.is_valid,
                "sample_value": p.sample_value,
            }
            for p in run.partitions
        ],
    }


def _to_run_out(run: MgmtDesignTechniqueRun) -> DesignRunOut:
    return DesignRunOut.model_validate(_serialize_run(run))


def _normalize_numeric(raw: Optional[str], cast_float: bool = False) -> Optional[float]:
    if raw is None or raw == "":
        return None
    try:
        return float(raw) if cast_float else float(raw)
    except (TypeError, ValueError):
        return None


# ── BVA fallback (deterministic) ─────────────────────────────────────────────


def _fallback_bva(fields: list[DesignFieldSpec]) -> list[GeneratedCaseDraft]:
    """Deterministic boundary-value drafts: min, min+1, nominal, max-1, max, invalid.

    Determinism matters — tests rely on stable output when the LLM gateway
    is offline (gap-finder asserts this).
    """
    drafts: list[GeneratedCaseDraft] = []
    for field in fields:
        name = field.name
        if field.data_type in {"int", "float"}:
            lo = _normalize_numeric(field.min_value)
            hi = _normalize_numeric(field.max_value)
            step = 1.0 if field.data_type == "int" else 0.01
            if lo is not None:
                drafts.append(
                    GeneratedCaseDraft(
                        name=f"{name} = min ({_fmt_num(lo, field.data_type)})",
                        field_name=name,
                        boundary_type="min",
                        inputs={name: _coerce_num(lo, field.data_type)},
                        expected="accepted",
                        rationale="Lower bound is inclusive — must be accepted.",
                    )
                )
                drafts.append(
                    GeneratedCaseDraft(
                        name=f"{name} = min+{step} (just_inside)",
                        field_name=name,
                        boundary_type="just_inside",
                        inputs={name: _coerce_num(lo + step, field.data_type)},
                        expected="accepted",
                        rationale="One unit above min should still be accepted.",
                    )
                )
                drafts.append(
                    GeneratedCaseDraft(
                        name=f"{name} = min-{step} (invalid)",
                        field_name=name,
                        boundary_type="just_outside",
                        inputs={name: _coerce_num(lo - step, field.data_type)},
                        expected="rejected with validation error",
                        rationale="One unit below min must be rejected.",
                    )
                )
            if hi is not None:
                drafts.append(
                    GeneratedCaseDraft(
                        name=f"{name} = max ({_fmt_num(hi, field.data_type)})",
                        field_name=name,
                        boundary_type="max",
                        inputs={name: _coerce_num(hi, field.data_type)},
                        expected="accepted",
                        rationale="Upper bound is inclusive — must be accepted.",
                    )
                )
                drafts.append(
                    GeneratedCaseDraft(
                        name=f"{name} = max-{step} (just_inside)",
                        field_name=name,
                        boundary_type="just_inside",
                        inputs={name: _coerce_num(hi - step, field.data_type)},
                        expected="accepted",
                        rationale="One unit below max should still be accepted.",
                    )
                )
                drafts.append(
                    GeneratedCaseDraft(
                        name=f"{name} = max+{step} (invalid)",
                        field_name=name,
                        boundary_type="just_outside",
                        inputs={name: _coerce_num(hi + step, field.data_type)},
                        expected="rejected with validation error",
                        rationale="One unit above max must be rejected.",
                    )
                )
            if lo is not None and hi is not None:
                mid = (lo + hi) / 2.0
                drafts.append(
                    GeneratedCaseDraft(
                        name=f"{name} = nominal ({_fmt_num(mid, field.data_type)})",
                        field_name=name,
                        boundary_type="nominal",
                        inputs={name: _coerce_num(mid, field.data_type)},
                        expected="accepted",
                        rationale="Mid-range value — happy path.",
                    )
                )
        elif field.data_type == "string":
            min_len = int(_normalize_numeric(field.min_value) or 0)
            max_len = int(_normalize_numeric(field.max_value) or 64)
            if field.nullable:
                drafts.append(
                    GeneratedCaseDraft(
                        name=f"{name} = empty (nullable)",
                        field_name=name,
                        boundary_type="min",
                        inputs={name: ""},
                        expected="accepted",
                        rationale="Field is nullable → empty must be accepted.",
                    )
                )
            else:
                drafts.append(
                    GeneratedCaseDraft(
                        name=f"{name} = empty (invalid)",
                        field_name=name,
                        boundary_type="invalid",
                        inputs={name: ""},
                        expected="rejected with validation error",
                        rationale="Field is required — empty must be rejected.",
                    )
                )
            drafts.append(
                GeneratedCaseDraft(
                    name=f"{name} = len {min_len + 1} (just_inside)",
                    field_name=name,
                    boundary_type="just_inside",
                    inputs={name: "a" * max(min_len + 1, 1)},
                    expected="accepted",
                    rationale="One char above min length.",
                )
            )
            drafts.append(
                GeneratedCaseDraft(
                    name=f"{name} = len {max_len} (max)",
                    field_name=name,
                    boundary_type="max",
                    inputs={name: "a" * max_len},
                    expected="accepted",
                    rationale="At max length, still accepted.",
                )
            )
            drafts.append(
                GeneratedCaseDraft(
                    name=f"{name} = len {max_len + 1} (over-length)",
                    field_name=name,
                    boundary_type="just_outside",
                    inputs={name: "a" * (max_len + 1)},
                    expected="rejected with validation error",
                    rationale="One char above max — rejected.",
                )
            )
        elif field.data_type in {"enum", "bool"}:
            allowed = list(field.allowed_set or ([True, False] if field.data_type == "bool" else []))
            for val in allowed:
                drafts.append(
                    GeneratedCaseDraft(
                        name=f"{name} = {val!r}",
                        field_name=name,
                        boundary_type="nominal",
                        inputs={name: val},
                        expected="accepted",
                        rationale="Allowed value.",
                    )
                )
            drafts.append(
                GeneratedCaseDraft(
                    name=f"{name} = not in allowed_set (invalid)",
                    field_name=name,
                    boundary_type="invalid",
                    inputs={name: "__INVALID__"},
                    expected="rejected with validation error",
                    rationale="Out of allowed set.",
                )
            )
        elif field.data_type == "date":
            # Dates are passed-through as ISO strings.
            if field.min_value:
                drafts.append(
                    GeneratedCaseDraft(
                        name=f"{name} = min ({field.min_value})",
                        field_name=name,
                        boundary_type="min",
                        inputs={name: field.min_value},
                        expected="accepted",
                        rationale="Lower date bound.",
                    )
                )
            if field.max_value:
                drafts.append(
                    GeneratedCaseDraft(
                        name=f"{name} = max ({field.max_value})",
                        field_name=name,
                        boundary_type="max",
                        inputs={name: field.max_value},
                        expected="accepted",
                        rationale="Upper date bound.",
                    )
                )
            drafts.append(
                GeneratedCaseDraft(
                    name=f"{name} = clearly invalid date",
                    field_name=name,
                    boundary_type="invalid",
                    inputs={name: "9999-13-99"},
                    expected="rejected with validation error",
                    rationale="Malformed date string.",
                )
            )
    return drafts


def _fmt_num(val: float, dtype: str) -> str:
    if dtype == "int":
        return str(int(val))
    return f"{val:g}"


def _coerce_num(val: float, dtype: str) -> Any:
    if dtype == "int":
        return int(val)
    return float(val)


# ── EQ fallback ──────────────────────────────────────────────────────────────


def _fallback_eq(
    fields: list[DesignFieldSpec],
) -> tuple[list[dict[str, Any]], list[GeneratedCaseDraft]]:
    """Deterministic equivalence-partition fallback.

    Returns ``(partitions, cases)``. Partitions are keyed by field+label so
    ``promote_cases`` and ``DesignPartitionOut`` can hydrate them.
    """
    partitions: list[dict[str, Any]] = []
    cases: list[GeneratedCaseDraft] = []
    for field in fields:
        name = field.name
        if field.data_type in {"int", "float"}:
            lo = _normalize_numeric(field.min_value)
            hi = _normalize_numeric(field.max_value)
            if lo is not None and hi is not None:
                mid = (lo + hi) / 2.0
                partitions.append(
                    {"field_name": name, "partition_label": "valid mid-range", "is_valid": True, "sample_value": _fmt_num(mid, field.data_type)}
                )
                cases.append(
                    GeneratedCaseDraft(
                        name=f"{name}: valid mid-range",
                        field_name=name,
                        partition_label="valid mid-range",
                        inputs={name: _coerce_num(mid, field.data_type)},
                        expected="accepted",
                        rationale="Representative of the valid interval.",
                    )
                )
            if lo is not None:
                step = 1.0 if field.data_type == "int" else 0.01
                partitions.append(
                    {"field_name": name, "partition_label": "below min", "is_valid": False, "sample_value": _fmt_num(lo - step, field.data_type)}
                )
                cases.append(
                    GeneratedCaseDraft(
                        name=f"{name}: below min",
                        field_name=name,
                        partition_label="below min",
                        inputs={name: _coerce_num(lo - step, field.data_type)},
                        expected="rejected with validation error",
                        rationale="Invalid class: below minimum.",
                    )
                )
            if hi is not None:
                step = 1.0 if field.data_type == "int" else 0.01
                partitions.append(
                    {"field_name": name, "partition_label": "above max", "is_valid": False, "sample_value": _fmt_num(hi + step, field.data_type)}
                )
                cases.append(
                    GeneratedCaseDraft(
                        name=f"{name}: above max",
                        field_name=name,
                        partition_label="above max",
                        inputs={name: _coerce_num(hi + step, field.data_type)},
                        expected="rejected with validation error",
                        rationale="Invalid class: above maximum.",
                    )
                )
            if field.nullable:
                partitions.append(
                    {"field_name": name, "partition_label": "null", "is_valid": True, "sample_value": None}
                )
                cases.append(
                    GeneratedCaseDraft(
                        name=f"{name}: null allowed",
                        field_name=name,
                        partition_label="null",
                        inputs={name: None},
                        expected="accepted",
                        rationale="Nullable field — null is a valid class.",
                    )
                )
        elif field.data_type == "string":
            min_len = int(_normalize_numeric(field.min_value) or 0)
            max_len = int(_normalize_numeric(field.max_value) or 64)
            mid_len = max(min_len + 1, max_len // 2)
            partitions.append(
                {"field_name": name, "partition_label": "valid length", "is_valid": True, "sample_value": "a" * mid_len}
            )
            cases.append(
                GeneratedCaseDraft(
                    name=f"{name}: valid length",
                    field_name=name,
                    partition_label="valid length",
                    inputs={name: "a" * mid_len},
                    expected="accepted",
                )
            )
            partitions.append(
                {"field_name": name, "partition_label": "over-length", "is_valid": False, "sample_value": "a" * (max_len + 1)}
            )
            cases.append(
                GeneratedCaseDraft(
                    name=f"{name}: over-length",
                    field_name=name,
                    partition_label="over-length",
                    inputs={name: "a" * (max_len + 1)},
                    expected="rejected with validation error",
                )
            )
            if not field.nullable:
                partitions.append(
                    {"field_name": name, "partition_label": "empty (required)", "is_valid": False, "sample_value": ""}
                )
                cases.append(
                    GeneratedCaseDraft(
                        name=f"{name}: empty required",
                        field_name=name,
                        partition_label="empty (required)",
                        inputs={name: ""},
                        expected="rejected with validation error",
                    )
                )
        elif field.data_type in {"enum", "bool"}:
            allowed = list(field.allowed_set or ([True, False] if field.data_type == "bool" else []))
            for val in allowed:
                label = f"allowed: {val!r}"
                partitions.append(
                    {"field_name": name, "partition_label": label, "is_valid": True, "sample_value": str(val)}
                )
                cases.append(
                    GeneratedCaseDraft(
                        name=f"{name}: {val!r}",
                        field_name=name,
                        partition_label=label,
                        inputs={name: val},
                        expected="accepted",
                    )
                )
            partitions.append(
                {"field_name": name, "partition_label": "not in allowed_set", "is_valid": False, "sample_value": "__INVALID__"}
            )
            cases.append(
                GeneratedCaseDraft(
                    name=f"{name}: not in allowed_set",
                    field_name=name,
                    partition_label="not in allowed_set",
                    inputs={name: "__INVALID__"},
                    expected="rejected with validation error",
                )
            )
        elif field.data_type == "date":
            partitions.append(
                {"field_name": name, "partition_label": "valid date", "is_valid": True, "sample_value": field.min_value or "2025-01-01"}
            )
            cases.append(
                GeneratedCaseDraft(
                    name=f"{name}: valid date",
                    field_name=name,
                    partition_label="valid date",
                    inputs={name: field.min_value or "2025-01-01"},
                    expected="accepted",
                )
            )
            partitions.append(
                {"field_name": name, "partition_label": "malformed date", "is_valid": False, "sample_value": "9999-13-99"}
            )
            cases.append(
                GeneratedCaseDraft(
                    name=f"{name}: malformed date",
                    field_name=name,
                    partition_label="malformed date",
                    inputs={name: "9999-13-99"},
                    expected="rejected with validation error",
                )
            )
    return partitions, cases


# ── LLM wrappers ─────────────────────────────────────────────────────────────


def _parse_cases(payload: dict[str, Any] | None) -> list[GeneratedCaseDraft]:
    if not payload or not isinstance(payload.get("cases"), list):
        return []
    out: list[GeneratedCaseDraft] = []
    for raw in payload["cases"]:
        if not isinstance(raw, dict):
            continue
        try:
            out.append(
                GeneratedCaseDraft(
                    name=str(raw.get("name") or "Untitled case")[:200],
                    field_name=(str(raw["field_name"]) if raw.get("field_name") else None),
                    boundary_type=(str(raw["boundary_type"]) if raw.get("boundary_type") else None),
                    partition_label=(str(raw["partition_label"]) if raw.get("partition_label") else None),
                    inputs=dict(raw.get("inputs") or {}),
                    expected=str(raw.get("expected") or ""),
                    rationale=(str(raw["rationale"]) if raw.get("rationale") else None),
                )
            )
        except Exception as exc:  # pragma: no cover — defensive
            logger.debug("Skipping malformed LLM case: %s", exc)
    return out


# ── DT fallback (decision table) ─────────────────────────────────────────────


def _fallback_dt(fields: list[DesignFieldSpec]) -> list[GeneratedCaseDraft]:
    """Deterministic decision-table fallback.

    Treats every field as a boolean condition (True / False). Generates a
    minimal representative set capped at 16 rows to keep output manageable.
    """
    import itertools

    conditions = [f.name for f in fields][:8]  # cap at 8 to avoid 256 rows
    combos = list(itertools.product([True, False], repeat=len(conditions)))[:16]
    drafts: list[GeneratedCaseDraft] = []
    for combo in combos:
        inputs = {cond: val for cond, val in zip(conditions, combo)}
        all_true = all(combo)
        label = " & ".join(
            (f"{c}=Y" if v else f"{c}=N") for c, v in zip(conditions, combo)
        )
        drafts.append(
            GeneratedCaseDraft(
                name=f"DT: {label}",
                inputs=inputs,
                expected="action_A" if all_true else "action_B",
                boundary_type="decision_row",
                rationale=(
                    "All conditions true → primary action."
                    if all_true
                    else "At least one condition false → alternative action."
                ),
            )
        )
    return drafts


# ── Pairwise fallback ─────────────────────────────────────────────────────────


def _fallback_pairwise(fields: list[DesignFieldSpec]) -> list[GeneratedCaseDraft]:
    """Greedy pairwise (all-pairs) fallback.

    Builds the minimum set of test cases that covers every pair of parameter
    values at least once. Uses a pure-Python greedy cover algorithm so there
    is no external dependency and the output is deterministic.
    """
    # Build value lists for each field
    field_values: list[tuple[str, list[Any]]] = []
    for f in fields:
        if f.allowed_set:
            vals: list[Any] = list(f.allowed_set)[:10]
        elif f.data_type in {"int", "float"}:
            lo = _normalize_numeric(f.min_value) or 0
            hi = _normalize_numeric(f.max_value) or (lo + 2)
            step = 1.0 if f.data_type == "int" else (hi - lo) / 2
            vals = [_coerce_num(lo, f.data_type), _coerce_num((lo + hi) / 2, f.data_type), _coerce_num(hi, f.data_type)]
        elif f.data_type == "bool":
            vals = [True, False]
        else:
            vals = [f"val_{i}" for i in range(1, 4)]
        if not vals:
            vals = ["default"]
        field_values.append((f.name, vals))

    if not field_values:
        return []

    n = len(field_values)
    # Build set of all required pairs: (field_i, val_i, field_j, val_j) for i < j
    required: set[tuple[int, Any, int, Any]] = set()
    for i in range(n):
        for j in range(i + 1, n):
            for vi in field_values[i][1]:
                for vj in field_values[j][1]:
                    required.add((i, vi, j, vj))

    covered: set[tuple[int, Any, int, Any]] = set()
    test_cases: list[dict[str, Any]] = []

    while covered < required:
        # Greedy: pick a value for each field that covers the most uncovered pairs
        row: dict[str, Any] = {}
        for fi, (fname, fvals) in enumerate(field_values):
            if fname in row:
                continue
            best_val = fvals[0]
            best_score = -1
            for v in fvals:
                score = 0
                # count how many uncovered pairs this value would cover
                for fj, (fname_j, fvals_j) in enumerate(field_values):
                    if fi == fj:
                        continue
                    existing = row.get(fname_j)
                    if existing is not None:
                        # pair with already-assigned field
                        i_, j_ = min(fi, fj), max(fi, fj)
                        vi_ = v if fi < fj else existing
                        vj_ = existing if fi < fj else v
                        if (i_, vi_, j_, vj_) not in covered:
                            score += 1
                    else:
                        # look ahead: count uncovered pairs against all values of fj
                        for vj in fvals_j:
                            i_, j_ = min(fi, fj), max(fi, fj)
                            vi_ = v if fi < fj else vj
                            vj_ = vj if fi < fj else v
                            if (i_, vi_, j_, vj_) not in covered:
                                score += 1
                if score > best_score:
                    best_score = score
                    best_val = v
            row[fname] = best_val

        # Mark pairs covered by this row
        keys = list(row.keys())
        for ai in range(len(keys)):
            for bi in range(ai + 1, len(keys)):
                fname_a, fname_b = keys[ai], keys[bi]
                fi_a = next(i for i, (n, _) in enumerate(field_values) if n == fname_a)
                fi_b = next(i for i, (n, _) in enumerate(field_values) if n == fname_b)
                i_, j_ = min(fi_a, fi_b), max(fi_a, fi_b)
                vi_ = row[fname_a] if fi_a < fi_b else row[fname_b]
                vj_ = row[fname_b] if fi_a < fi_b else row[fname_a]
                covered.add((i_, vi_, j_, vj_))

        if len(test_cases) >= 200:  # safety cap
            break
        test_cases.append(dict(row))

    drafts: list[GeneratedCaseDraft] = []
    for idx, tc in enumerate(test_cases):
        label = ", ".join(f"{k}={v}" for k, v in tc.items())
        drafts.append(
            GeneratedCaseDraft(
                name=f"PW-{idx + 1:03d}: {label}",
                inputs=tc,
                expected="accepted",
                boundary_type="pairwise_row",
                partition_label=label,
                rationale=f"Covers all pairwise interactions for: {label}",
            )
        )
    return drafts


def _generate_bva_cases(
    fields: list[DesignFieldSpec], requirement_text: str = ""
) -> tuple[list[GeneratedCaseDraft], str]:
    system_prompt = _load_prompt("bva_extract_bounds") or (
        'Reply with strict JSON: {"cases": [{"name": str, "field_name": str, '
        '"boundary_type": str, "inputs": object, "expected": str, "rationale": str}]}.'
    )
    user_message = json.dumps(
        {
            "requirement_text": requirement_text,
            "fields": [f.model_dump() for f in fields],
        },
        ensure_ascii=False,
    )
    parsed = _call_llm(
        task_type="mgmt.design.bva_extract_bounds",
        user_message=user_message,
        system_message=system_prompt,
    )
    cases = _parse_cases(parsed)
    if not cases:
        return _fallback_bva(fields), "fallback"
    return cases, "llm"


def _generate_eq_partitions(
    fields: list[DesignFieldSpec], requirement_text: str = ""
) -> tuple[list[dict[str, Any]], list[GeneratedCaseDraft], str]:
    system_prompt = _load_prompt("eq_partition") or (
        'Reply with strict JSON: {"partitions": [...], "cases": [...]}.'
    )
    user_message = json.dumps(
        {
            "requirement_text": requirement_text,
            "fields": [f.model_dump() for f in fields],
        },
        ensure_ascii=False,
    )
    parsed = _call_llm(
        task_type="mgmt.design.eq_partition",
        user_message=user_message,
        system_message=system_prompt,
    )
    cases = _parse_cases(parsed)
    partitions: list[dict[str, Any]] = []
    if parsed and isinstance(parsed.get("partitions"), list):
        for raw in parsed["partitions"]:
            if not isinstance(raw, dict):
                continue
            partitions.append(
                {
                    "field_name": str(raw.get("field_name") or "")[:128],
                    "partition_label": str(raw.get("partition_label") or "")[:128],
                    "is_valid": bool(raw.get("is_valid", True)),
                    "sample_value": (str(raw["sample_value"])[:256] if raw.get("sample_value") is not None else None),
                }
            )
    if not cases or not partitions:
        partitions, cases = _fallback_eq(fields)
        return partitions, cases, "fallback"
    return partitions, cases, "llm"


def _generate_dt_cases(
    fields: list[DesignFieldSpec], requirement_text: str = ""
) -> tuple[list[GeneratedCaseDraft], str]:
    system_prompt = _load_prompt("dt_generate") or (
        'Reply with strict JSON: {"cases": [{"name": str, "inputs": object, '
        '"expected": str, "boundary_type": "decision_row", "rationale": str}]}.'
    )
    user_message = json.dumps(
        {
            "requirement_text": requirement_text,
            "fields": [f.model_dump() for f in fields],
        },
        ensure_ascii=False,
    )
    parsed = _call_llm(
        task_type="mgmt.design.dt_generate",
        user_message=user_message,
        system_message=system_prompt,
    )
    cases = _parse_cases(parsed)
    if not cases:
        return _fallback_dt(fields), "fallback"
    return cases, "llm"


def _generate_pairwise_cases(
    fields: list[DesignFieldSpec], requirement_text: str = ""
) -> tuple[list[GeneratedCaseDraft], str]:
    system_prompt = _load_prompt("pairwise_generate") or (
        'Reply with strict JSON: {"cases": [{"name": str, "inputs": object, '
        '"expected": str, "partition_label": str, "rationale": str}]}.'
    )
    user_message = json.dumps(
        {
            "requirement_text": requirement_text,
            "fields": [f.model_dump() for f in fields],
        },
        ensure_ascii=False,
    )
    parsed = _call_llm(
        task_type="mgmt.design.pairwise_generate",
        user_message=user_message,
        system_message=system_prompt,
    )
    cases = _parse_cases(parsed)
    if not cases:
        return _fallback_pairwise(fields), "fallback"
    return cases, "llm"


def _generate_data_rows_llm(
    schema: dict[str, Any], count: int
) -> tuple[list[dict[str, Any]], str]:
    system_prompt = _load_prompt("data_table_generate") or (
        'Reply with strict JSON: {"rows": [{"values": object, "expected": object, "category": str}]}.'
    )
    user_message = json.dumps({"schema": schema, "count": int(count)}, ensure_ascii=False)
    parsed = _call_llm(
        task_type="mgmt.design.data_table_generate",
        user_message=user_message,
        system_message=system_prompt,
    )
    if parsed and isinstance(parsed.get("rows"), list):
        rows = []
        for raw in parsed["rows"][:count]:
            if not isinstance(raw, dict):
                continue
            rows.append(
                {
                    "values": dict(raw.get("values") or {}),
                    "expected": dict(raw.get("expected") or {}),
                    "category": (str(raw["category"])[:32] if raw.get("category") else None),
                }
            )
        if rows:
            return rows, "llm"
    return _fallback_data_rows(schema, count), "fallback"


def _fallback_data_rows(schema: dict[str, Any], count: int) -> list[dict[str, Any]]:
    """Deterministic data-table fallback.

    Produces ``count`` rows alternating typical / boundary / invalid
    categories so downstream consumers always see at least one of each
    category when ``count >= 3``.
    """
    fields = list((schema or {}).get("fields") or [])
    rows: list[dict[str, Any]] = []
    categories = ["typical", "boundary", "invalid"]
    for i in range(count):
        category = categories[i % len(categories)]
        values: dict[str, Any] = {}
        for field in fields:
            fname = str(field.get("name") or f"field_{len(values)}")
            ftype = str(field.get("type") or "string").lower()
            if category == "invalid":
                values[fname] = None if field.get("required") else "__INVALID__"
            elif ftype in {"int", "integer", "number", "float"}:
                values[fname] = 0 if category == "boundary" else (i + 1)
            elif ftype == "bool" or ftype == "boolean":
                values[fname] = (i % 2 == 0)
            elif ftype == "date":
                values[fname] = "2025-01-01" if category == "boundary" else "2025-06-15"
            else:
                values[fname] = "" if category == "boundary" else f"sample-{i + 1}"
        rows.append(
            {
                "values": values,
                "expected": {"status": "rejected" if category == "invalid" else "accepted"},
                "category": category,
            }
        )
    return rows


# ── Public API ───────────────────────────────────────────────────────────────


def _persist_run(
    db: Session,
    *,
    tenant_id: str,
    user: Any,
    technique: str,
    project_id: Optional[str],
    requirement_id: Optional[str],
    fields: list[DesignFieldSpec],
    requirement_text: str,
    cases: list[GeneratedCaseDraft],
    partitions: Optional[list[dict[str, Any]]],
    source: str,
) -> MgmtDesignTechniqueRun:
    if technique not in ALLOWED_TECHNIQUES:
        raise ValueError(f"technique must be one of {sorted(ALLOWED_TECHNIQUES)}")

    run = MgmtDesignTechniqueRun(
        tenant_id=tenant_id,
        project_id=project_id,
        requirement_id=requirement_id,
        technique=technique,
        input_spec={
            "requirement_text": requirement_text,
            "fields": [f.model_dump() for f in fields],
        },
        generated_cases=[c.model_dump() for c in cases],
        source=source,
        llm_trace_id=_uuid_mod.uuid4().hex[:16] if source == "llm" else None,
        created_by=_actor(user),
    )
    db.add(run)
    db.flush()

    # Persist fields once so the partition rows can FK them.
    field_id_by_name: dict[str, str] = {}
    for spec in fields:
        record = MgmtDesignInputField(
            run_id=run.id,
            name=spec.name,
            data_type=spec.data_type,
            min_value=spec.min_value,
            max_value=spec.max_value,
            allowed_set=list(spec.allowed_set) if spec.allowed_set is not None else None,
            nullable=spec.nullable,
        )
        db.add(record)
        db.flush()
        field_id_by_name[spec.name] = record.id

    if partitions:
        for raw in partitions:
            fname = raw.get("field_name")
            field_id = field_id_by_name.get(fname) if fname else None
            if not field_id:
                # Skip partitions that don't bind to a known field — keeps the
                # FK constraint happy and prevents the LLM from inventing fields.
                continue
            db.add(
                MgmtDesignPartition(
                    run_id=run.id,
                    field_id=field_id,
                    partition_label=str(raw.get("partition_label") or "")[:128],
                    is_valid=bool(raw.get("is_valid", True)),
                    sample_value=(str(raw["sample_value"])[:256] if raw.get("sample_value") is not None else None),
                )
            )

    _audit(
        db,
        action="design.run.create",
        entity_type="mgmt_design_run",
        entity_id=run.id,
        project_id=project_id,
        user=user,
        payload={"technique": technique, "case_count": len(cases), "source": source},
    )
    db.commit()
    db.refresh(run)
    return run


def create_bva_run(
    db: Session, tenant_id: str, user: Any, payload: BvaRunCreate
) -> DesignRunOut:
    if not payload.fields:
        raise ValueError("At least one field is required")
    cases, source = _generate_bva_cases(payload.fields, payload.requirement_text or "")
    run = _persist_run(
        db,
        tenant_id=tenant_id,
        user=user,
        technique="BVA",
        project_id=payload.project_id,
        requirement_id=payload.requirement_id,
        fields=payload.fields,
        requirement_text=payload.requirement_text or "",
        cases=cases,
        partitions=None,
        source=source,
    )
    return _to_run_out(run)


def create_eq_run(
    db: Session, tenant_id: str, user: Any, payload: EqRunCreate
) -> DesignRunOut:
    if not payload.fields:
        raise ValueError("At least one field is required")
    partitions, cases, source = _generate_eq_partitions(
        payload.fields, payload.requirement_text or ""
    )
    run = _persist_run(
        db,
        tenant_id=tenant_id,
        user=user,
        technique="EQ",
        project_id=payload.project_id,
        requirement_id=payload.requirement_id,
        fields=payload.fields,
        requirement_text=payload.requirement_text or "",
        cases=cases,
        partitions=partitions,
        source=source,
    )
    return _to_run_out(run)


def create_dt_run(
    db: Session, tenant_id: str, user: Any, payload: DtRunCreate
) -> DesignRunOut:
    try:
        effective = payload.effective_fields()
    except ValueError as exc:
        raise exc
    req_text = payload.requirement_text or ""
    if payload.actions:
        req_text = f"{req_text}\nExpected actions: {', '.join(payload.actions)}".strip()
    cases, source = _generate_dt_cases(effective, req_text)
    run = _persist_run(
        db,
        tenant_id=tenant_id,
        user=user,
        technique="DT",
        project_id=payload.project_id,
        requirement_id=payload.requirement_id,
        fields=effective,
        requirement_text=req_text,
        cases=cases,
        partitions=None,
        source=source,
    )
    return _to_run_out(run)


def create_pairwise_run(
    db: Session, tenant_id: str, user: Any, payload: PairwiseRunCreate
) -> DesignRunOut:
    if len(payload.fields) < 2:
        raise ValueError("Pairwise requires at least 2 fields")
    cases, source = _generate_pairwise_cases(payload.fields, payload.requirement_text or "")
    run = _persist_run(
        db,
        tenant_id=tenant_id,
        user=user,
        technique="PAIRWISE",
        project_id=payload.project_id,
        requirement_id=payload.requirement_id,
        fields=payload.fields,
        requirement_text=payload.requirement_text or "",
        cases=cases,
        partitions=None,
        source=source,
    )
    return _to_run_out(run)


def get_design_run(db: Session, tenant_id: str, run_id: str) -> DesignRunOut:
    run = db.get(MgmtDesignTechniqueRun, run_id)
    if run is None or run.tenant_id != tenant_id:
        raise KeyError("Design run bulunamadı")
    return _to_run_out(run)


def list_design_runs(
    db: Session,
    tenant_id: str,
    *,
    technique: Optional[str] = None,
    requirement_id: Optional[str] = None,
    project_id: Optional[str] = None,
    limit: int = 100,
) -> list[DesignRunOut]:
    stmt = select(MgmtDesignTechniqueRun).where(MgmtDesignTechniqueRun.tenant_id == tenant_id)
    if technique:
        if technique not in ALLOWED_TECHNIQUES:
            raise ValueError(f"technique must be one of {sorted(ALLOWED_TECHNIQUES)}")
        stmt = stmt.where(MgmtDesignTechniqueRun.technique == technique)
    if requirement_id:
        stmt = stmt.where(MgmtDesignTechniqueRun.requirement_id == requirement_id)
    if project_id:
        stmt = stmt.where(MgmtDesignTechniqueRun.project_id == project_id)
    stmt = stmt.order_by(MgmtDesignTechniqueRun.created_at.desc()).limit(limit)
    return [_to_run_out(r) for r in db.scalars(stmt).all()]


def promote_cases(
    db: Session,
    tenant_id: str,
    user: Any,
    run_id: str,
    request: PromoteCasesRequest,
) -> list[str]:
    run = db.get(MgmtDesignTechniqueRun, run_id)
    if run is None or run.tenant_id != tenant_id:
        raise KeyError("Design run bulunamadı")
    if not run.project_id:
        raise ValueError("Bu run bir projeye bağlı değil — promotion yapılamaz")

    drafts = list(run.generated_cases or [])
    selected_ids: list[str] = []
    for idx in request.case_indexes:
        if idx < 0 or idx >= len(drafts):
            raise ValueError(f"Geçersiz case index: {idx}")
        draft = drafts[idx]
        name = str(draft.get("name") or f"{run.technique} case {idx + 1}")[:500]
        inputs = dict(draft.get("inputs") or {})
        expected = str(draft.get("expected") or "accepted")
        rationale = str(draft.get("rationale") or "")
        boundary_type = str(draft.get("boundary_type") or draft.get("partition_label") or "")

        payload = TestCaseCreate(
            title=name,
            suite_id=request.suite_id,
            folder_id=request.folder_id,
            objective=rationale,
            test_data={"inputs": inputs, "expected": expected, "source": f"design.{run.technique}", "boundary_type": boundary_type},
            tags=[f"design:{run.technique.lower()}"],
            custom_fields={"design_run_id": run.id, "draft_index": idx},
            source_type="design_technique",
            source_ref=run.id,
            steps=[],
        )
        case = tm_service.create_case(db, run.project_id, payload, user)
        selected_ids.append(case.id)

    _audit(
        db,
        action="design.run.promote",
        entity_type="mgmt_design_run",
        entity_id=run.id,
        project_id=run.project_id,
        user=user,
        payload={"case_ids": selected_ids, "count": len(selected_ids)},
    )
    db.commit()
    return selected_ids


# ── M-9 Parameterized cases ──────────────────────────────────────────────────


def _get_case_or_404(db: Session, tenant_id: str, case_id: str) -> TestCase:
    case = db.get(TestCase, case_id)
    if case is None:
        raise KeyError("Test case bulunamadı")
    # We don't have tenant_id on TestCase; rely on project-level scoping done by
    # the caller. Still hand back the row for the service to operate on.
    return case


def _get_param_set_or_404(
    db: Session, tenant_id: str, param_set_id: str
) -> MgmtCaseParamSet:
    ps = db.get(MgmtCaseParamSet, param_set_id)
    if ps is None or ps.tenant_id != tenant_id:
        raise KeyError("Parameter set bulunamadı")
    return ps


def create_param_set(
    db: Session, tenant_id: str, user: Any, payload: CaseParamSetCreate
) -> MgmtCaseParamSet:
    case = _get_case_or_404(db, tenant_id, payload.case_id)
    schema = dict(payload.schema_json or {})
    if "fields" not in schema or not isinstance(schema.get("fields"), list):
        raise ValueError("schema_json must contain a 'fields' list")
    # Normalise field entries.
    cleaned_fields = []
    for raw in schema["fields"]:
        if not isinstance(raw, dict) or not raw.get("name"):
            raise ValueError("Each schema field must be an object with a 'name'")
        cleaned_fields.append(
            {
                "name": str(raw["name"])[:128],
                "type": str(raw.get("type") or "string")[:32],
                "required": bool(raw.get("required", False)),
            }
        )
    ps = MgmtCaseParamSet(
        tenant_id=tenant_id,
        case_id=case.id,
        schema_json={"fields": cleaned_fields},
        created_by=_actor(user),
    )
    db.add(ps)
    db.flush()
    _audit(
        db,
        action="design.params.create",
        entity_type="mgmt_case_param_set",
        entity_id=ps.id,
        project_id=case.project_id,
        user=user,
        payload={"case_id": case.id, "field_count": len(cleaned_fields)},
    )
    db.commit()
    db.refresh(ps)
    return ps


def list_param_sets(
    db: Session, tenant_id: str, case_id: str
) -> list[MgmtCaseParamSet]:
    stmt = (
        select(MgmtCaseParamSet)
        .where(
            MgmtCaseParamSet.tenant_id == tenant_id,
            MgmtCaseParamSet.case_id == case_id,
        )
        .order_by(MgmtCaseParamSet.created_at.desc())
    )
    return list(db.scalars(stmt).all())


def add_data_rows(
    db: Session,
    tenant_id: str,
    user: Any,
    param_set_id: str,
    rows: Iterable[CaseDataRowIn],
) -> list[MgmtCaseDataRow]:
    ps = _get_param_set_or_404(db, tenant_id, param_set_id)
    created: list[MgmtCaseDataRow] = []
    for row in rows:
        record = MgmtCaseDataRow(
            param_set_id=ps.id,
            values=dict(row.values or {}),
            expected=dict(row.expected or {}),
            source_type=row.source_type or "manual",
            category=row.category,
        )
        db.add(record)
        db.flush()
        created.append(record)
    db.commit()
    for record in created:
        db.refresh(record)
    return created


def generate_data_rows(
    db: Session,
    tenant_id: str,
    user: Any,
    request: CaseDataGenerateRequest,
) -> list[MgmtCaseDataRow]:
    ps = _get_param_set_or_404(db, tenant_id, request.param_set_id)
    rows_raw: list[dict[str, Any]]
    if request.source == "csv":
        if not request.csv_content:
            raise ValueError("csv_content required when source='csv'")
        rows_raw = _parse_csv_rows(request.csv_content, ps.schema_json)
    elif request.source == "llm":
        rows_raw, _ = _generate_data_rows_llm(ps.schema_json or {}, request.count)
    else:
        raise ValueError("source must be one of: llm | csv")

    created: list[MgmtCaseDataRow] = []
    for raw in rows_raw:
        record = MgmtCaseDataRow(
            param_set_id=ps.id,
            values=dict(raw.get("values") or {}),
            expected=dict(raw.get("expected") or {}),
            source_type=request.source,
            category=raw.get("category"),
        )
        db.add(record)
        db.flush()
        created.append(record)
    db.commit()
    for record in created:
        db.refresh(record)
    return created


def _parse_csv_rows(csv_content: str, schema: dict[str, Any]) -> list[dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(csv_content))
    field_names = {f.get("name") for f in (schema or {}).get("fields", []) if isinstance(f, dict)}
    rows: list[dict[str, Any]] = []
    for row in reader:
        values = {k: v for k, v in row.items() if k in field_names} if field_names else dict(row)
        rows.append({"values": values, "expected": {}, "category": None})
    return rows


def list_data_rows(
    db: Session, tenant_id: str, param_set_id: str
) -> list[MgmtCaseDataRow]:
    ps = _get_param_set_or_404(db, tenant_id, param_set_id)
    stmt = (
        select(MgmtCaseDataRow)
        .where(MgmtCaseDataRow.param_set_id == ps.id)
        .order_by(MgmtCaseDataRow.created_at.asc())
    )
    return list(db.scalars(stmt).all())


def expand_case(
    db: Session, tenant_id: str, user: Any, case_id: str
) -> dict[str, list[str]]:
    """Materialise one execution per data row across all param sets.

    There is no first-class ``test_management_executions`` table in this
    slice — the existing run / run-case pipeline requires a TestCycle. We
    therefore record an audit event per row and return the data-row ids
    as ``execution_ids`` so the UI can show "expanded N rows" feedback.
    A real run is created later via the standard ``/runs`` flow with the
    case's promoted rows.

    Idempotency: returns the same set of row ids on repeated calls because
    we never duplicate rows — the caller chooses when to add more.

    TODO(M-10): when ``test_management_executions`` lands, replace the audit
    payload with concrete execution inserts and reuse the run_case_ids list.
    """
    case = _get_case_or_404(db, tenant_id, case_id)
    sets = list_param_sets(db, tenant_id, case.id)
    execution_ids: list[str] = []
    for ps in sets:
        for row in list_data_rows(db, tenant_id, ps.id):
            execution_ids.append(row.id)
    _audit(
        db,
        action="design.params.expand",
        entity_type="test_case",
        entity_id=case.id,
        project_id=case.project_id,
        user=user,
        payload={"execution_count": len(execution_ids), "param_set_count": len(sets)},
    )
    db.commit()
    return {"execution_ids": execution_ids, "run_case_ids": []}
