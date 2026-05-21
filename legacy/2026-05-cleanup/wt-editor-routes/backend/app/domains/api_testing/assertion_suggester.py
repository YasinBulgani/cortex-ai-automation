"""
Assertion Suggestion Service
=============================

Analyzes test cases and their linked endpoint schemas to suggest
additional assertions. Combines rule-based heuristics (fast, no LLM)
with optional LLM-enhanced suggestions for complex endpoints.

Banking-domain focus: KVKK, BDDK, PCI-DSS specific checks.

Usage:
    from app.domains.api_testing.assertion_suggester import (
        suggest_assertions,
        bulk_suggest,
        get_assertion_stats,
    )
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.domains.api_testing.models import (
    ApiEndpoint,
    ApiSpec,
    ApiTestCase,
)

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

# Assertion types that the system can suggest
SUGGESTION_TYPES = (
    "status_code", "json_path", "header", "schema",
    "security", "performance", "regex",
)

# Priority levels
PRIORITY_CRITICAL = "critical"
PRIORITY_HIGH = "high"
PRIORITY_MEDIUM = "medium"
PRIORITY_LOW = "low"

# Categories
CAT_FUNCTIONAL = "functional"
CAT_SECURITY = "security"
CAT_COMPLIANCE = "compliance"
CAT_PERFORMANCE = "performance"

# PII fields that should never leak in error responses
PII_FIELDS = [
    "tc_kimlik", "tckn", "identity_number", "national_id",
    "ssn", "social_security", "pasaport", "passport",
    "email", "e_posta", "phone", "telefon", "mobile",
    "address", "adres", "iban", "account_number", "hesap_no",
    "card_number", "kart_no", "cvv", "cvc", "expiry",
    "date_of_birth", "dogum_tarihi", "password", "sifre",
]

# Financial precision patterns
FINANCIAL_FIELDS = [
    "balance", "bakiye", "amount", "tutar", "fee", "komisyon",
    "interest", "faiz", "total", "toplam", "price", "fiyat",
    "exchange_rate", "kur", "installment", "taksit",
]

# BDDK-required audit fields
BDDK_AUDIT_FIELDS = [
    "transaction_id", "islem_id", "timestamp", "zaman_damgasi",
    "audit_trail", "denetim_izi", "reference_number", "referans_no",
    "channel", "kanal", "ip_address",
]

# Test types that are considered negative/error scenarios
NEGATIVE_TEST_TYPES = ("negative", "security", "boundary")

# Expected status codes per test type
EXPECTED_STATUS_MAP = {
    "positive": [200, 201, 204],
    "negative": [400, 401, 403, 404, 422],
    "boundary": [400, 422],
    "security": [401, 403],
    "compliance": [200, 201],
    "performance": [200],
    "edge_case": [200, 400],
    "regression": [200],
    "contract": [200],
}


def _make_suggestion(
    suggestion_type: str,
    field: str,
    operator: str,
    expected: Any,
    reason: str,
    priority: str,
    category: str,
) -> Dict[str, Any]:
    """Build a single suggestion dict."""
    return {
        "type": suggestion_type,
        "field": field,
        "operator": operator,
        "expected": expected,
        "reason": reason,
        "priority": priority,
        "category": category,
    }


# ═══════════════════════════════════════════════════════════════════════
# RULE-BASED SUGGESTIONS  (no LLM, fast)
# ═══════════════════════════════════════════════════════════════════════

def _existing_assertion_types(assertions: List[dict]) -> Dict[str, List[dict]]:
    """Index existing assertions by type for quick lookup."""
    index = {}  # type: Dict[str, List[dict]]
    for a in assertions:
        a_type = a.get("type", "")
        if a_type not in index:
            index[a_type] = []
        index[a_type].append(a)
    return index


def _suggest_status_code(
    test_type: str,
    existing: Dict[str, List[dict]],
) -> List[Dict[str, Any]]:
    """Always suggest a status code assertion if missing."""
    if "status_code" in existing:
        return []

    expected_codes = EXPECTED_STATUS_MAP.get(test_type, [200])
    if len(expected_codes) == 1:
        return [_make_suggestion(
            "status_code", "status_code", "eq", expected_codes[0],
            "Her test mutlaka HTTP status code kontrol etmelidir",
            PRIORITY_CRITICAL, CAT_FUNCTIONAL,
        )]
    return [_make_suggestion(
        "status_code", "status_code", "one_of", expected_codes,
        "Her test mutlaka HTTP status code kontrol etmelidir",
        PRIORITY_CRITICAL, CAT_FUNCTIONAL,
    )]


def _suggest_content_type(
    existing: Dict[str, List[dict]],
) -> List[Dict[str, Any]]:
    """Suggest Content-Type header check if missing."""
    # Check both 'header' and 'content_type' assertion types
    for a in existing.get("header", []):
        field = (a.get("path") or a.get("key") or "").lower()
        if "content-type" in field:
            return []
    if "content_type" in existing:
        return []

    return [_make_suggestion(
        "header", "Content-Type", "contains", "application/json",
        "Response Content-Type basliginin dogru formatta oldugu kontrol edilmeli",
        PRIORITY_HIGH, CAT_FUNCTIONAL,
    )]


def _suggest_response_time(
    risk_level: str,
    existing: Dict[str, List[dict]],
) -> List[Dict[str, Any]]:
    """Suggest response time assertion based on risk level."""
    if "response_time" in existing:
        return []

    threshold = 500 if risk_level in ("critical", "high") else 2000
    return [_make_suggestion(
        "performance", "response_time", "lt", threshold,
        "Response suresi %dms altinda olmali (%s risk seviyesi)" % (threshold, risk_level),
        PRIORITY_HIGH if risk_level in ("critical", "high") else PRIORITY_MEDIUM,
        CAT_PERFORMANCE,
    )]


def _suggest_pii_checks(
    test_type: str,
    has_pii: bool,
    existing: Dict[str, List[dict]],
) -> List[Dict[str, Any]]:
    """For PII endpoints, check that sensitive fields do not leak in error responses."""
    if not has_pii:
        return []
    # Only relevant for negative/error test types
    if test_type not in NEGATIVE_TEST_TYPES:
        return []

    suggestions = []  # type: List[Dict[str, Any]]
    # Check that error responses don't expose PII
    for pii_field in PII_FIELDS[:8]:  # top 8 most critical
        already_checked = False
        for a in existing.get("json_path", []) + existing.get("not_exists", []):
            if pii_field in (a.get("path") or ""):
                already_checked = True
                break
        if not already_checked:
            suggestions.append(_make_suggestion(
                "security", "$.%s" % pii_field, "not_exists", None,
                "KVKK: Hata yaniti icerisinde '%s' alani ifsa edilmemeli" % pii_field,
                PRIORITY_CRITICAL, CAT_COMPLIANCE,
            ))
    return suggestions


def _suggest_financial_checks(
    has_financial: bool,
    response_schemas: Optional[dict],
    existing: Dict[str, List[dict]],
) -> List[Dict[str, Any]]:
    """For financial endpoints, check decimal precision and currency format."""
    if not has_financial:
        return []

    suggestions = []  # type: List[Dict[str, Any]]

    # Suggest decimal precision check for financial fields
    for fin_field in FINANCIAL_FIELDS[:6]:
        already_checked = False
        for a in existing.get("json_path", []) + existing.get("regex", []):
            if fin_field in (a.get("path") or a.get("field") or ""):
                already_checked = True
                break
        if not already_checked:
            suggestions.append(_make_suggestion(
                "regex", "$.data.%s" % fin_field, "matches",
                r"^\d+\.\d{2}$",
                "BDDK: Finansal alan '%s' iki ondalik hassasiyetinde olmali" % fin_field,
                PRIORITY_HIGH, CAT_COMPLIANCE,
            ))

    # Suggest currency format check
    currency_checked = False
    for a in existing.get("json_path", []):
        if "currency" in (a.get("path") or ""):
            currency_checked = True
            break
    if not currency_checked:
        suggestions.append(_make_suggestion(
            "json_path", "$.data.currency", "matches",
            r"^[A-Z]{3}$",
            "BDDK: Para birimi ISO 4217 formatinda (TRY, USD, EUR) olmali",
            PRIORITY_MEDIUM, CAT_COMPLIANCE,
        ))

    return suggestions


def _suggest_schema_validation(
    response_schemas: Optional[dict],
    existing: Dict[str, List[dict]],
) -> List[Dict[str, Any]]:
    """If response_schemas are available, suggest schema validation."""
    if not response_schemas:
        return []
    if "schema" in existing:
        return []

    # Find the primary success schema (200 or 201)
    schema = None  # type: Optional[dict]
    for code in ("200", "201"):
        if code in response_schemas:
            schema = response_schemas[code]
            break
    if not schema:
        return []

    return [_make_suggestion(
        "schema", "response_body", "validates", schema,
        "Endpoint'in tanimli response schema'sina uygunluk dogrulanmali",
        PRIORITY_HIGH, CAT_FUNCTIONAL,
    )]


def _suggest_auth_checks(
    auth_required: bool,
    test_type: str,
    existing: Dict[str, List[dict]],
) -> List[Dict[str, Any]]:
    """If endpoint requires auth, suggest auth-related assertions."""
    if not auth_required:
        return []

    suggestions = []  # type: List[Dict[str, Any]]

    # For security test types, verify 401/403 when no token provided
    if test_type == "security":
        has_auth_status = False
        for a in existing.get("status_code", []):
            exp = a.get("expected")
            if exp in (401, 403) or (isinstance(exp, list) and (401 in exp or 403 in exp)):
                has_auth_status = True
                break
        if not has_auth_status:
            suggestions.append(_make_suggestion(
                "status_code", "status_code", "one_of", [401, 403],
                "Yetkisiz erisimde 401/403 donmesi gerekiyor",
                PRIORITY_CRITICAL, CAT_SECURITY,
            ))

    # Check Authorization header exists in request
    if test_type in ("positive", "compliance", "performance"):
        auth_header_checked = False
        for a in existing.get("header", []):
            if "authorization" in (a.get("path") or a.get("key") or "").lower():
                auth_header_checked = True
                break
        if not auth_header_checked:
            suggestions.append(_make_suggestion(
                "header", "Authorization", "exists", True,
                "Auth gerektiren endpoint'lerde token header'i kontrol edilmeli",
                PRIORITY_MEDIUM, CAT_SECURITY,
            ))

    return suggestions


def _suggest_compliance_checks(
    compliance_tags: List[str],
    test_type: str,
    has_financial: bool,
    existing: Dict[str, List[dict]],
) -> List[Dict[str, Any]]:
    """KVKK, BDDK, PCI-DSS specific compliance assertions."""
    suggestions = []  # type: List[Dict[str, Any]]

    if "KVKK" in compliance_tags:
        # KVKK: anonymization check - sensitive data should be masked
        kvkk_checked = any(
            "kvkk" in (a.get("reason") or a.get("message") or "").lower()
            for atype_list in existing.values()
            for a in atype_list
        )
        if not kvkk_checked:
            suggestions.append(_make_suggestion(
                "security", "$.data", "not_contains", "tc_kimlik",
                "KVKK: Yanit icerisinde maskelenmemis TCKN verisi olmamali",
                PRIORITY_CRITICAL, CAT_COMPLIANCE,
            ))

    if "BDDK" in compliance_tags and has_financial:
        # BDDK: audit fields must be present in financial transactions
        for audit_field in BDDK_AUDIT_FIELDS[:4]:
            audit_checked = False
            for a in existing.get("json_path", []) + existing.get("exists", []):
                if audit_field in (a.get("path") or ""):
                    audit_checked = True
                    break
            if not audit_checked and test_type in ("positive", "compliance"):
                suggestions.append(_make_suggestion(
                    "json_path", "$.%s" % audit_field, "exists", True,
                    "BDDK: Finansal islem yanitinda '%s' alani bulunmali" % audit_field,
                    PRIORITY_HIGH, CAT_COMPLIANCE,
                ))

    if "PCI-DSS" in compliance_tags:
        # PCI-DSS: card data must be masked
        pci_fields = ["card_number", "kart_no", "cvv", "cvc", "expiry"]
        for field in pci_fields:
            pci_checked = False
            for a in existing.get("regex", []) + existing.get("json_path", []):
                if field in (a.get("path") or a.get("field") or ""):
                    pci_checked = True
                    break
            if not pci_checked:
                suggestions.append(_make_suggestion(
                    "security", "$.%s" % field, "not_exists", None,
                    "PCI-DSS: Kart verisi '%s' maskelenmeli veya yanita dahil edilmemeli" % field,
                    PRIORITY_CRITICAL, CAT_COMPLIANCE,
                ))

    return suggestions


def _suggest_type_specific(
    test_type: str,
    existing: Dict[str, List[dict]],
    request_method: str,
) -> List[Dict[str, Any]]:
    """Suggestions based on the test_type."""
    suggestions = []  # type: List[Dict[str, Any]]

    if test_type == "boundary":
        # Boundary tests should check error message format
        error_msg_checked = any(
            "error" in (a.get("path") or "").lower() or "message" in (a.get("path") or "").lower()
            for a in existing.get("json_path", [])
        )
        if not error_msg_checked:
            suggestions.append(_make_suggestion(
                "json_path", "$.error", "exists", True,
                "Sinir deger testlerinde hata mesaji alani kontrol edilmeli",
                PRIORITY_MEDIUM, CAT_FUNCTIONAL,
            ))

    elif test_type == "contract":
        # Contract tests should have schema validation
        if "schema" not in existing:
            suggestions.append(_make_suggestion(
                "schema", "response_body", "validates", {},
                "Sozlesme testlerinde response schema dogrulamasi zorunlu",
                PRIORITY_CRITICAL, CAT_FUNCTIONAL,
            ))

    elif test_type == "performance":
        # Performance tests need response time check
        if "response_time" not in existing:
            suggestions.append(_make_suggestion(
                "performance", "response_time", "lt", 500,
                "Performans testlerinde response suresi kontrolu zorunlu",
                PRIORITY_CRITICAL, CAT_PERFORMANCE,
            ))

    elif test_type == "positive" and request_method in ("POST", "PUT"):
        # Positive mutation tests should check the response has an ID
        id_checked = any(
            "id" in (a.get("path") or "").lower()
            for a in existing.get("json_path", [])
        )
        if not id_checked:
            suggestions.append(_make_suggestion(
                "json_path", "$.data.id", "exists", True,
                "Basarili POST/PUT yanitinda kayit ID'si donmeli",
                PRIORITY_MEDIUM, CAT_FUNCTIONAL,
            ))

    return suggestions


def _get_rule_based_suggestions(
    test_case: "ApiTestCase",
    endpoint: Optional["ApiEndpoint"],
) -> List[Dict[str, Any]]:
    """Collect all rule-based suggestions for a test case."""
    assertions = test_case.assertions or []
    existing = _existing_assertion_types(assertions)

    risk_level = "medium"
    has_pii = False
    has_financial = False
    auth_required = True
    compliance_tags = []  # type: List[str]
    response_schemas = None  # type: Optional[dict]

    if endpoint:
        risk_level = endpoint.risk_level or "medium"
        has_pii = endpoint.has_pii or False
        has_financial = endpoint.has_financial or False
        auth_required = endpoint.auth_required if endpoint.auth_required is not None else True
        compliance_tags = endpoint.compliance_tags or []
        response_schemas = endpoint.response_schemas or None

    suggestions = []  # type: List[Dict[str, Any]]

    # 1. Status code check (always)
    suggestions.extend(_suggest_status_code(test_case.test_type, existing))

    # 2. Content-Type header
    suggestions.extend(_suggest_content_type(existing))

    # 3. Response time
    suggestions.extend(_suggest_response_time(risk_level, existing))

    # 4. PII leak prevention
    suggestions.extend(_suggest_pii_checks(test_case.test_type, has_pii, existing))

    # 5. Financial precision
    suggestions.extend(_suggest_financial_checks(has_financial, response_schemas, existing))

    # 6. Schema validation
    suggestions.extend(_suggest_schema_validation(response_schemas, existing))

    # 7. Auth checks
    suggestions.extend(_suggest_auth_checks(auth_required, test_case.test_type, existing))

    # 8. Compliance-specific
    suggestions.extend(_suggest_compliance_checks(
        compliance_tags, test_case.test_type, has_financial, existing,
    ))

    # 9. Test-type specific
    suggestions.extend(_suggest_type_specific(
        test_case.test_type, existing, test_case.request_method,
    ))

    return suggestions


# ═══════════════════════════════════════════════════════════════════════
# LLM-ENHANCED SUGGESTIONS  (optional, failure-safe)
# ═══════════════════════════════════════════════════════════════════════

def _get_llm_suggestions(
    test_case: "ApiTestCase",
    endpoint: Optional["ApiEndpoint"],
) -> List[Dict[str, Any]]:
    """
    Use LLM to suggest field-level validations for complex endpoints.
    This is wrapped in try/except and never blocks the response.
    """
    if endpoint is None:
        return []
    response_schemas = endpoint.response_schemas or {}
    if not response_schemas:
        return []

    try:
        from app.domains.agents.banking_team.base_agent import BaseAgent
        from app.domains.ai.smart_model_router import route_model

        # Route model based on endpoint characteristics
        rec = route_model(
            task_type="test_generation",
            complexity="medium",
            has_financial=endpoint.has_financial or False,
            has_pii=endpoint.has_pii or False,
            risk_level=endpoint.risk_level or "medium",
        )

        agent = BaseAgent()
        agent.name = "AssertionSuggester"
        agent.model = rec.model
        agent.temperature = rec.temperature
        agent.max_tokens = min(rec.max_tokens, 4096)
        agent.inject_project_context = False

        system_prompt = (
            "Sen bir bankacilik API test assertion uzmansin. "
            "Verilen endpoint schemasi ve test case bilgisine gore "
            "ek assertion onerileri uret. "
            "Yalnizca JSON formatinda yanit ver.\n\n"
            "Yanit formati:\n"
            '{"suggestions": [\n'
            '  {"type": "json_path", "field": "$.data.fieldName", '
            '"operator": "exists", "expected": true, '
            '"reason": "Neden bu assertion gerekli", '
            '"priority": "high", "category": "functional"}\n'
            "]}\n\n"
            "Assertion tipleri: status_code, json_path, header, schema, "
            "security, performance, regex\n"
            "Operatorler: eq, gt, lt, contains, matches, exists, not_exists\n"
            "Oncelikler: critical, high, medium, low\n"
            "Kategoriler: functional, security, compliance, performance\n"
            "En fazla 5 oneri ver."
        )

        user_prompt = (
            "Endpoint: %s %s\n"
            "Risk: %s | PII: %s | Financial: %s\n"
            "Compliance: %s\n"
            "Test Type: %s\n"
            "Mevcut assertion sayisi: %d\n\n"
            "Response Schemas:\n%s\n\n"
            "Mevcut Assertions:\n%s"
        ) % (
            endpoint.method, endpoint.path,
            endpoint.risk_level, endpoint.has_pii, endpoint.has_financial,
            ", ".join(endpoint.compliance_tags or []),
            test_case.test_type,
            len(test_case.assertions or []),
            str(response_schemas)[:2000],
            str(test_case.assertions or [])[:1000],
        )

        result = agent.call_json(system=system_prompt, user=user_prompt)

        if result.get("parse_error"):
            return []

        raw_suggestions = result.get("suggestions", [])
        validated = []  # type: List[Dict[str, Any]]
        for s in raw_suggestions:
            if not isinstance(s, dict):
                continue
            if "type" not in s or "field" not in s:
                continue
            validated.append({
                "type": s.get("type", "json_path"),
                "field": s.get("field", ""),
                "operator": s.get("operator", "exists"),
                "expected": s.get("expected"),
                "reason": s.get("reason", "LLM onerisi"),
                "priority": s.get("priority", PRIORITY_MEDIUM),
                "category": s.get("category", CAT_FUNCTIONAL),
            })
        return validated

    except Exception as exc:
        logger.warning("LLM assertion suggestion failed (non-blocking): %s", exc)
        return []


# ═══════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════

def suggest_assertions(
    db: Session,
    project_id: str,
    test_case_id: str,
) -> Dict[str, Any]:
    """
    Analyze a test case and its endpoint schema to suggest additional assertions.

    Returns a dict with test_case_id, current_assertion_count, suggestions list,
    and coverage_improvement estimate.
    """
    # Load test case
    test_case = db.query(ApiTestCase).filter(
        ApiTestCase.id == test_case_id,
        ApiTestCase.project_id == project_id,
    ).first()
    if test_case is None:
        return {
            "test_case_id": test_case_id,
            "current_assertion_count": 0,
            "suggestions": [],
            "coverage_improvement": "Test case bulunamadi",
        }

    # Load linked endpoint (if any)
    endpoint = None  # type: Optional[ApiEndpoint]
    if test_case.endpoint_id:
        endpoint = db.query(ApiEndpoint).filter(
            ApiEndpoint.id == test_case.endpoint_id,
        ).first()

    current_count = len(test_case.assertions or [])

    # Rule-based suggestions (fast, no LLM)
    suggestions = _get_rule_based_suggestions(test_case, endpoint)

    # LLM-enhanced suggestions (optional, wrapped in try/except)
    llm_suggestions = _get_llm_suggestions(test_case, endpoint)
    if llm_suggestions:
        # Deduplicate: skip LLM suggestions that overlap with rule-based
        existing_fields = {s["field"] for s in suggestions}
        for ls in llm_suggestions:
            if ls["field"] not in existing_fields:
                suggestions.append(ls)
                existing_fields.add(ls["field"])

    # Sort by priority
    priority_order = {
        PRIORITY_CRITICAL: 0,
        PRIORITY_HIGH: 1,
        PRIORITY_MEDIUM: 2,
        PRIORITY_LOW: 3,
    }
    suggestions.sort(key=lambda s: priority_order.get(s.get("priority", ""), 99))

    # Coverage improvement estimate
    total_after = current_count + len(suggestions)
    if current_count == 0 and total_after > 0:
        improvement = "Sifir assertion'dan %d'e cikarilarak test coverage onemli olcude arttirilir" % total_after
    elif total_after > current_count:
        pct = round((len(suggestions) / max(total_after, 1)) * 100)
        improvement = (
            "Bu %d assertion eklenerek test coverage ~%%%d arttirilabilir"
            % (len(suggestions), pct)
        )
    else:
        improvement = "Mevcut assertion'lar yeterli gorunuyor"

    return {
        "test_case_id": test_case_id,
        "current_assertion_count": current_count,
        "suggestions": suggestions,
        "coverage_improvement": improvement,
    }


def bulk_suggest(
    db: Session,
    project_id: str,
    test_case_ids: Optional[List[str]] = None,
    test_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run assertion analysis for multiple test cases.

    If test_case_ids is None, analyze all tests in the project.
    If test_type is provided, filter by test type.

    Returns a summary with total suggestions and per-test breakdown.
    """
    query = db.query(ApiTestCase).filter(
        ApiTestCase.project_id == project_id,
    )

    if test_case_ids:
        query = query.filter(ApiTestCase.id.in_(test_case_ids))
    if test_type:
        query = query.filter(ApiTestCase.test_type == test_type)

    test_cases = query.all()

    results = []  # type: List[Dict[str, Any]]
    total_suggestions = 0

    for tc in test_cases:
        result = suggest_assertions(db, project_id, tc.id)
        suggestion_count = len(result.get("suggestions", []))
        total_suggestions += suggestion_count
        results.append({
            "test_case_id": tc.id,
            "title": tc.title,
            "test_type": tc.test_type,
            "current_assertions": result["current_assertion_count"],
            "suggestion_count": suggestion_count,
            "suggestions": result["suggestions"],
        })

    # Sort by suggestion count descending (most needy first)
    results.sort(key=lambda r: r["suggestion_count"], reverse=True)

    return {
        "total_test_cases": len(test_cases),
        "total_suggestions": total_suggestions,
        "avg_suggestions_per_test": round(
            total_suggestions / max(len(test_cases), 1), 1,
        ),
        "results": results,
    }


def get_assertion_stats(
    db: Session,
    project_id: str,
) -> Dict[str, Any]:
    """
    Return assertion statistics for a project.

    Includes total tests, total assertions, average per test,
    tests with no assertions, type distribution, and estimated
    suggestion potential.
    """
    test_cases = db.query(ApiTestCase).filter(
        ApiTestCase.project_id == project_id,
    ).all()

    total_tests = len(test_cases)
    total_assertions = 0
    tests_with_no_assertions = 0
    tests_below_threshold = 0  # < 3 assertions
    type_distribution = {}  # type: Dict[str, int]

    for tc in test_cases:
        assertions = tc.assertions or []
        count = len(assertions)
        total_assertions += count

        if count == 0:
            tests_with_no_assertions += 1
        if count < 3:
            tests_below_threshold += 1

        for a in assertions:
            a_type = a.get("type", "unknown")
            type_distribution[a_type] = type_distribution.get(a_type, 0) + 1

    avg_assertions = round(
        total_assertions / max(total_tests, 1), 1,
    )

    # Estimate suggestion potential: tests below threshold * ~3 suggestions each
    suggestion_potential = (tests_below_threshold * 3) + (tests_with_no_assertions * 2)

    return {
        "total_tests": total_tests,
        "total_assertions": total_assertions,
        "avg_assertions_per_test": avg_assertions,
        "tests_with_no_assertions": tests_with_no_assertions,
        "tests_below_threshold": tests_below_threshold,
        "assertion_type_distribution": type_distribution,
        "suggestion_potential": suggestion_potential,
    }
