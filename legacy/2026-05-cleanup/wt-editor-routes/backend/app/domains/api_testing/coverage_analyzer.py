"""
Coverage Gap Analyzer
=====================

Analyses which API endpoints have test coverage and which don't.
Produces gap reports with severity ratings and generates
recommendations for missing test types.

Python 3.9 compatible — no ``X | Y`` unions, no ``from __future__``.
"""

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.domains.api_testing.models import ApiEndpoint, ApiSpec, ApiTestCase

logger = logging.getLogger(__name__)

# ── Test-type requirements per risk level ────────────────────────────
# critical endpoints need ALL types, low-risk just positive+negative.

ALL_TEST_TYPES = [
    "positive",
    "negative",
    "boundary",
    "security",
    "compliance",
    "performance",
    "edge_case",
    "regression",
    "contract",
]

REQUIRED_TYPES_BY_RISK: Dict[str, List[str]] = {
    "critical": list(ALL_TEST_TYPES),
    "high": ["positive", "negative", "boundary", "security", "compliance", "contract"],
    "medium": ["positive", "negative", "boundary", "security"],
    "low": ["positive", "negative"],
}

# ── Gap severity ordering (for sorting) ─────────────────────────────
_SEVERITY_ORDER: Dict[str, int] = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
}


def _classify_gap_severity(
    risk_level: str,
    test_count: int,
    missing_types: List[str],
) -> str:
    """Determine gap severity based on the rules in the spec."""
    risk = risk_level.lower() if risk_level else "low"

    # critical: endpoint risk=critical AND no tests at all
    if risk == "critical" and test_count == 0:
        return "critical"

    # high: risk=high AND no tests, OR risk=critical AND missing security/compliance
    if risk == "high" and test_count == 0:
        return "high"
    if risk == "critical" and (
        "security" in missing_types or "compliance" in missing_types
    ):
        return "high"

    # medium: risk=medium AND no tests, OR missing >3 test types
    if risk == "medium" and test_count == 0:
        return "medium"
    if len(missing_types) > 3:
        return "medium"

    # low: everything else
    return "low"


def _build_recommendation(
    method: str,
    path: str,
    risk_level: str,
    has_pii: bool,
    has_financial: bool,
    test_count: int,
    missing_types: List[str],
) -> str:
    """Build a human-readable recommendation string for a gap."""
    parts: List[str] = []

    if test_count == 0:
        parts.append(
            f"{method} {path} has NO test coverage at all (risk={risk_level})."
        )
    else:
        parts.append(
            f"{method} {path} has {test_count} test(s) but is missing "
            f"{len(missing_types)} type(s): {', '.join(missing_types)}."
        )

    if has_pii:
        parts.append("Endpoint handles PII data — KVKK compliance tests are essential.")
    if has_financial:
        parts.append(
            "Endpoint processes financial data — BDDK/PCI-DSS compliance "
            "and security tests are critical."
        )
    if "security" in missing_types:
        parts.append("Add OWASP API Top-10 security tests (injection, auth bypass, etc.).")
    if "boundary" in missing_types:
        parts.append("Add boundary/edge-value tests for input parameters.")
    if "compliance" in missing_types and (has_pii or has_financial):
        parts.append("Add regulatory compliance test cases.")

    return " ".join(parts)


# =====================================================================
# Public API
# =====================================================================


def analyze_coverage(
    db: Session,
    project_id: str,
    spec_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Analyze test coverage for all endpoints in a project.

    Parameters
    ----------
    db : Session
        SQLAlchemy database session.
    project_id : str
        The project to analyse.
    spec_id : str, optional
        Restrict analysis to endpoints from a single spec.

    Returns
    -------
    dict
        Coverage summary, gap list, breakdowns by risk level and test type.
    """

    # ── 1. Fetch endpoints ───────────────────────────────────────────
    ep_query = db.query(ApiEndpoint).join(ApiSpec).filter(
        ApiSpec.project_id == project_id,
    )
    if spec_id:
        ep_query = ep_query.filter(ApiEndpoint.spec_id == spec_id)

    endpoints: List[ApiEndpoint] = ep_query.all()

    # ── 2. Fetch test cases for project ──────────────────────────────
    test_cases: List[ApiTestCase] = (
        db.query(ApiTestCase)
        .filter(ApiTestCase.project_id == project_id)
        .all()
    )

    # ── 3. Index test cases by (request_method, request_path) ────────
    # Also index by endpoint_id for direct FK matches
    tc_by_method_path: Dict[Tuple[str, str], List[ApiTestCase]] = defaultdict(list)
    tc_by_endpoint_id: Dict[str, List[ApiTestCase]] = defaultdict(list)

    for tc in test_cases:
        key = (tc.request_method.upper(), tc.request_path)
        tc_by_method_path[key].append(tc)
        if tc.endpoint_id:
            tc_by_endpoint_id[tc.endpoint_id].append(tc)

    # ── 4. Analyse each endpoint ─────────────────────────────────────
    gaps: List[Dict[str, Any]] = []
    covered_count = 0
    uncovered_count = 0
    critical_uncovered = 0

    by_risk: Dict[str, Dict[str, int]] = {}
    by_type: Dict[str, Dict[str, int]] = defaultdict(lambda: {"count": 0, "endpoints_covered": 0})

    # Track endpoint ids covered per test type (for by_test_type stats)
    type_endpoint_sets: Dict[str, set] = defaultdict(set)

    for ep in endpoints:
        risk = (ep.risk_level or "low").lower()

        # Merge test cases found by FK relationship AND by method+path
        matching_tcs_map: Dict[str, ApiTestCase] = {}
        for tc in tc_by_endpoint_id.get(ep.id, []):
            matching_tcs_map[tc.id] = tc
        for tc in tc_by_method_path.get((ep.method.upper(), ep.path), []):
            matching_tcs_map[tc.id] = tc

        matching_tcs = list(matching_tcs_map.values())
        test_count = len(matching_tcs)

        # Determine which test types are present
        types_present: List[str] = sorted(set(tc.test_type for tc in matching_tcs))

        # Track test-type stats
        for tt in types_present:
            type_endpoint_sets[tt].add(ep.id)

        # Determine missing types for this risk level
        required = REQUIRED_TYPES_BY_RISK.get(risk, REQUIRED_TYPES_BY_RISK["low"])
        types_missing = [t for t in required if t not in types_present]

        # Compute pass rate
        total_runs = sum(tc.run_count for tc in matching_tcs)
        total_passes = sum(tc.pass_count for tc in matching_tcs)
        pass_rate = round(total_passes / max(total_runs, 1) * 100, 1) if total_runs else 0.0

        # Coverage tracking
        if test_count > 0:
            covered_count += 1
        else:
            uncovered_count += 1
            if risk == "critical":
                critical_uncovered += 1

        # Risk-level breakdown
        if risk not in by_risk:
            by_risk[risk] = {"total": 0, "covered": 0}
        by_risk[risk]["total"] += 1
        if test_count > 0:
            by_risk[risk]["covered"] += 1

        # Build gap entry (always include — even fully-covered endpoints
        # might have missing types)
        gap_severity = _classify_gap_severity(risk, test_count, types_missing)

        if types_missing or test_count == 0:
            recommendation = _build_recommendation(
                ep.method, ep.path, risk,
                ep.has_pii, ep.has_financial,
                test_count, types_missing,
            )

            gaps.append({
                "endpoint_id": ep.id,
                "method": ep.method,
                "path": ep.path,
                "risk_level": risk,
                "has_pii": ep.has_pii,
                "has_financial": ep.has_financial,
                "test_count": test_count,
                "test_types_present": types_present,
                "test_types_missing": types_missing,
                "gap_severity": gap_severity,
                "pass_rate": pass_rate,
                "recommendation": recommendation,
            })

    # ── 5. Sort gaps by severity ─────────────────────────────────────
    gaps.sort(key=lambda g: (_SEVERITY_ORDER.get(g["gap_severity"], 99), -len(g["test_types_missing"])))

    # ── 6. Aggregate test-type statistics ────────────────────────────
    type_counter: Dict[str, int] = defaultdict(int)
    for tc in test_cases:
        type_counter[tc.test_type] += 1

    by_test_type: Dict[str, Dict[str, int]] = {}
    for tt in ALL_TEST_TYPES:
        by_test_type[tt] = {
            "count": type_counter.get(tt, 0),
            "endpoints_covered": len(type_endpoint_sets.get(tt, set())),
        }

    # ── 7. Risk-level rates ──────────────────────────────────────────
    by_risk_out: Dict[str, Dict[str, Any]] = {}
    for rl, data in by_risk.items():
        total = data["total"]
        covered = data["covered"]
        by_risk_out[rl] = {
            "total": total,
            "covered": covered,
            "rate": round(covered / max(total, 1) * 100, 1),
        }

    total_endpoints = len(endpoints)
    coverage_rate = round(covered_count / max(total_endpoints, 1) * 100, 1)

    return {
        "summary": {
            "total_endpoints": total_endpoints,
            "covered_endpoints": covered_count,
            "uncovered_endpoints": uncovered_count,
            "coverage_rate": coverage_rate,
            "critical_uncovered": critical_uncovered,
        },
        "gaps": gaps,
        "by_risk_level": by_risk_out,
        "by_test_type": by_test_type,
    }


def suggest_tests_for_gaps(
    db: Session,
    project_id: str,
    max_gaps: int = 5,
) -> List[Dict[str, Any]]:
    """
    Take the top *max_gaps* coverage gaps and return actionable
    suggestions for what tests should be created.

    Parameters
    ----------
    db : Session
        SQLAlchemy database session.
    project_id : str
        The project to analyse.
    max_gaps : int
        Maximum number of gaps to return suggestions for (default 5).

    Returns
    -------
    list[dict]
        Each dict contains endpoint info plus a ``suggestion`` string.
    """
    analysis = analyze_coverage(db, project_id)
    top_gaps = analysis["gaps"][:max_gaps]

    suggestions: List[Dict[str, Any]] = []
    for gap in top_gaps:
        # Build a more detailed suggestion per missing type
        detailed_parts: List[str] = []

        for mtype in gap["test_types_missing"]:
            if mtype == "positive":
                detailed_parts.append(
                    f"[positive] Add happy-path test for {gap['method']} {gap['path']} "
                    f"with valid parameters and verify 2xx response."
                )
            elif mtype == "negative":
                detailed_parts.append(
                    f"[negative] Add tests with invalid/missing parameters, "
                    f"expect 4xx error responses with proper error messages."
                )
            elif mtype == "boundary":
                detailed_parts.append(
                    f"[boundary] Test min/max values, empty strings, "
                    f"oversized payloads, and numeric overflow scenarios."
                )
            elif mtype == "security":
                detailed_parts.append(
                    f"[security] Add OWASP API Top-10 tests: injection, "
                    f"broken auth, excessive data exposure, rate limiting."
                )
            elif mtype == "compliance":
                tags = ""
                if gap.get("has_pii"):
                    tags += "KVKK "
                if gap.get("has_financial"):
                    tags += "BDDK/PCI-DSS "
                detailed_parts.append(
                    f"[compliance] Add {tags.strip() or 'regulatory'} compliance "
                    f"tests — data masking, audit logging, consent checks."
                )
            elif mtype == "performance":
                detailed_parts.append(
                    f"[performance] Add response-time assertions (<500ms), "
                    f"concurrent request tests, and throughput benchmarks."
                )
            elif mtype == "edge_case":
                detailed_parts.append(
                    f"[edge_case] Test race conditions, idempotency, "
                    f"special character encoding, and duplicate requests."
                )
            elif mtype == "regression":
                detailed_parts.append(
                    f"[regression] Create regression tests capturing "
                    f"known past failures for this endpoint."
                )
            elif mtype == "contract":
                detailed_parts.append(
                    f"[contract] Validate response schema matches the "
                    f"OpenAPI spec definition for all status codes."
                )

        suggestions.append({
            "endpoint_id": gap["endpoint_id"],
            "method": gap["method"],
            "path": gap["path"],
            "risk_level": gap["risk_level"],
            "gap_severity": gap["gap_severity"],
            "test_count": gap["test_count"],
            "test_types_missing": gap["test_types_missing"],
            "suggestion": " ".join(detailed_parts),
        })

    return suggestions
