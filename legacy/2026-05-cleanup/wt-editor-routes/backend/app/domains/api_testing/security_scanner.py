"""
OWASP API Security Top 10 (2023) Scanner
=========================================

Banking API endpoint'leri icin guvenlik taramasi.
Rule-based statik analiz + opsiyonel LLM-enhanced deep analysis.

OWASP API Top 10 (2023):
  API1  — Broken Object Level Authorization (BOLA)
  API2  — Broken Authentication
  API3  — Broken Object Property Level Authorization
  API4  — Unrestricted Resource Consumption
  API5  — Broken Function Level Authorization (BFLA)
  API6  — Unrestricted Access to Sensitive Business Flows
  API7  — Server Side Request Forgery (SSRF)
  API8  — Security Misconfiguration
  API9  — Improper Inventory Management
  API10 — Unsafe Consumption of APIs
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from sqlalchemy.orm import Session

from app.domains.api_testing.models import ApiEndpoint, ApiSpec, ApiTestCase

logger = logging.getLogger(__name__)


# ============================================================================
# OWASP CATEGORY DEFINITIONS
# ============================================================================

OWASP_CATEGORIES: Dict[str, str] = {
    "API1:2023": "Broken Object Level Authorization",
    "API2:2023": "Broken Authentication",
    "API3:2023": "Broken Object Property Level Authorization",
    "API4:2023": "Unrestricted Resource Consumption",
    "API5:2023": "Broken Function Level Authorization",
    "API6:2023": "Unrestricted Access to Sensitive Business Flows",
    "API7:2023": "Server Side Request Forgery",
    "API8:2023": "Security Misconfiguration",
    "API9:2023": "Improper Inventory Management",
    "API10:2023": "Unsafe Consumption of APIs",
}

# Severity weights for security score calculation
_SEVERITY_WEIGHTS: Dict[str, float] = {
    "critical": 25.0,
    "high": 15.0,
    "medium": 8.0,
    "low": 3.0,
    "info": 0.0,
}

# Banking-sensitive path patterns
_FINANCIAL_PATTERNS = re.compile(
    r"(transfer|payment|havale|eft|odeme|kredi|credit|withdraw|deposit"
    r"|bakiye|balance|hesap|account|fatura|invoice|pos|atm)",
    re.IGNORECASE,
)

_AUTH_PATTERNS = re.compile(
    r"(auth|login|logout|token|session|otp|mfa|2fa|password|sifre|kimlik)",
    re.IGNORECASE,
)

_ADMIN_PATTERNS = re.compile(
    r"(admin|role|permission|yetki|izin|management|config|setting)",
    re.IGNORECASE,
)

_PII_PATTERNS = re.compile(
    r"(user|kullanici|profile|profil|kyc|identity|tckn|email|phone|address)",
    re.IGNORECASE,
)

_SSRF_PARAM_PATTERNS = re.compile(
    r"(url|uri|link|redirect|callback|webhook|fetch|proxy|target|dest|next)",
    re.IGNORECASE,
)

_ID_PATH_PATTERN = re.compile(r"\{[^}]*id[^}]*\}", re.IGNORECASE)


# ============================================================================
# HELPER: severity from risk factors
# ============================================================================

def _is_banking_sensitive(path: str) -> bool:
    """Check if the path matches banking-sensitive patterns."""
    return bool(_FINANCIAL_PATTERNS.search(path))


def _count_schema_properties(schema: Optional[dict]) -> int:
    """Count top-level properties in a JSON schema."""
    if not schema:
        return 0
    props = schema.get("properties", {})
    if not props:
        # Try nested content -> application/json -> schema -> properties
        content = schema.get("content", {})
        json_ct = content.get("application/json", {})
        nested = json_ct.get("schema", {})
        props = nested.get("properties", {})
    return len(props)


def _has_path_id_param(path: str) -> bool:
    """Check if path contains an ID-like path parameter."""
    return bool(_ID_PATH_PATTERN.search(path))


def _get_param_names(parameters: Optional[list]) -> List[str]:
    """Extract parameter names from endpoint parameters."""
    if not parameters:
        return []
    return [p.get("name", "") for p in parameters if isinstance(p, dict)]


# ============================================================================
# RULE-BASED CHECKS
# ============================================================================

def _check_bola(
    endpoint: ApiEndpoint,
) -> List[Dict[str, Any]]:
    """API1:2023 - Broken Object Level Authorization (BOLA)."""
    findings = []  # type: List[Dict[str, Any]]
    path = endpoint.path or ""
    method = (endpoint.method or "").upper()

    has_id = _has_path_id_param(path)
    no_auth = not endpoint.auth_required
    is_banking = _is_banking_sensitive(path)

    if has_id and no_auth:
        severity = "critical" if is_banking else "high"
        findings.append({
            "owasp_category": "API1:2023",
            "owasp_name": OWASP_CATEGORIES["API1:2023"],
            "severity": severity,
            "title": "BOLA — ID-based resource without authentication",
            "description": (
                "Endpoint '%s %s' accepts an object ID in the path but does "
                "not require authentication. An attacker can enumerate IDs to "
                "access other users' resources." % (method, path)
            ),
            "recommendation": (
                "Enforce authentication and verify the authenticated user owns "
                "the requested resource. Implement per-object authorization checks."
            ),
            "confidence": 0.9,
            "banking_impact": (
                "Yetkisiz erisim ile musteri hesap bilgileri, bakiye ve "
                "islem gecmisi ifsa olabilir."
                if is_banking
                else "Kullanici verilerine yetkisiz erisim riski."
            ),
        })
    elif has_id and method in ("PUT", "PATCH", "DELETE"):
        findings.append({
            "owasp_category": "API1:2023",
            "owasp_name": OWASP_CATEGORIES["API1:2023"],
            "severity": "high" if is_banking else "medium",
            "title": "BOLA — Mutating operation with ID parameter",
            "description": (
                "Endpoint '%s %s' allows mutation via an object ID. "
                "Ensure the server validates object ownership." % (method, path)
            ),
            "recommendation": (
                "Add server-side ownership validation. Use the authenticated "
                "user's context to verify access to the target resource."
            ),
            "confidence": 0.7,
            "banking_impact": (
                "Yetkisiz hesap guncelleme veya silme islemi yapilabilir."
                if is_banking
                else "Baska kullanicilarin verilerinin degistirilme riski."
            ),
        })

    return findings


def _check_broken_auth(
    endpoint: ApiEndpoint,
) -> List[Dict[str, Any]]:
    """API2:2023 - Broken Authentication."""
    findings = []  # type: List[Dict[str, Any]]
    path = endpoint.path or ""
    method = (endpoint.method or "").upper()
    no_auth = not endpoint.auth_required

    is_sensitive = (
        _is_banking_sensitive(path)
        or _PII_PATTERNS.search(path)
        or _ADMIN_PATTERNS.search(path)
    )

    if no_auth and is_sensitive:
        findings.append({
            "owasp_category": "API2:2023",
            "owasp_name": OWASP_CATEGORIES["API2:2023"],
            "severity": "critical" if _is_banking_sensitive(path) else "high",
            "title": "Missing authentication on sensitive endpoint",
            "description": (
                "Endpoint '%s %s' handles sensitive data but does not "
                "require authentication." % (method, path)
            ),
            "recommendation": (
                "Require strong authentication (OAuth 2.0 / JWT) for all "
                "endpoints that handle financial, PII, or administrative data."
            ),
            "confidence": 0.95,
            "banking_impact": (
                "Kimlik dogrulama olmadan finansal islemlere erisim "
                "saglanabilir — ciddi mevzuat ihlali riski (BDDK/PCI-DSS)."
            ),
        })

    # Check auth endpoints for brute-force protections
    if _AUTH_PATTERNS.search(path) and method == "POST":
        findings.append({
            "owasp_category": "API2:2023",
            "owasp_name": OWASP_CATEGORIES["API2:2023"],
            "severity": "medium",
            "title": "Authentication endpoint — verify brute-force protections",
            "description": (
                "Endpoint '%s %s' appears to be an authentication endpoint. "
                "Verify rate-limiting and account lockout mechanisms." % (method, path)
            ),
            "recommendation": (
                "Implement rate limiting, CAPTCHA after failed attempts, "
                "and account lockout policies. Use bcrypt/argon2 for password hashing."
            ),
            "confidence": 0.6,
            "banking_impact": (
                "Brute-force saldirisi ile musteri hesaplarina yetkisiz "
                "giris yapilabilir."
            ),
        })

    return findings


def _check_property_auth(
    endpoint: ApiEndpoint,
) -> List[Dict[str, Any]]:
    """API3:2023 - Broken Object Property Level Authorization (Mass Assignment)."""
    findings = []  # type: List[Dict[str, Any]]
    path = endpoint.path or ""
    method = (endpoint.method or "").upper()

    if method not in ("POST", "PUT", "PATCH"):
        return findings

    prop_count = _count_schema_properties(endpoint.request_body_schema)
    is_banking = _is_banking_sensitive(path)

    if prop_count > 10:
        findings.append({
            "owasp_category": "API3:2023",
            "owasp_name": OWASP_CATEGORIES["API3:2023"],
            "severity": "high" if is_banking else "medium",
            "title": "Mass assignment risk — large request body (%d properties)" % prop_count,
            "description": (
                "Endpoint '%s %s' accepts %d properties in its request body. "
                "Internal-only fields (role, balance, status) may be writable "
                "if not explicitly filtered." % (method, path, prop_count)
            ),
            "recommendation": (
                "Use an explicit allowlist for writable properties. "
                "Never bind user input directly to internal model fields. "
                "Reject unknown properties."
            ),
            "confidence": 0.7,
            "banking_impact": (
                "Hesap bakiyesi, kredi limiti veya kullanici rolu gibi "
                "kritik alanlar degistirilebilir."
                if is_banking
                else "Dahili alanlar manipule edilebilir."
            ),
        })
    elif prop_count > 5:
        findings.append({
            "owasp_category": "API3:2023",
            "owasp_name": OWASP_CATEGORIES["API3:2023"],
            "severity": "low",
            "title": "Moderate request body size — review for mass assignment",
            "description": (
                "Endpoint '%s %s' accepts %d properties. Review the accepted "
                "fields to ensure no sensitive properties are writable." % (method, path, prop_count)
            ),
            "recommendation": (
                "Use explicit DTOs / Pydantic models with only the "
                "intended writable fields."
            ),
            "confidence": 0.5,
            "banking_impact": "Olasi dahili alan manipulasyonu."
        })

    return findings


def _check_rate_limiting(
    endpoint: ApiEndpoint,
) -> List[Dict[str, Any]]:
    """API4:2023 - Unrestricted Resource Consumption."""
    findings = []  # type: List[Dict[str, Any]]
    path = endpoint.path or ""
    method = (endpoint.method or "").upper()

    # Check response schemas for rate-limit headers
    response_schemas = endpoint.response_schemas or {}
    has_rate_limit_headers = False

    for _code, schema in response_schemas.items():
        headers = schema.get("headers", {})
        for hname in headers:
            if "rate" in hname.lower() or "limit" in hname.lower() or "retry" in hname.lower():
                has_rate_limit_headers = True
                break

    is_banking = _is_banking_sensitive(path)
    is_auth = bool(_AUTH_PATTERNS.search(path))

    if not has_rate_limit_headers:
        severity = "high" if (is_banking or is_auth) else "medium"
        findings.append({
            "owasp_category": "API4:2023",
            "owasp_name": OWASP_CATEGORIES["API4:2023"],
            "severity": severity,
            "title": "No rate limiting indicators in API spec",
            "description": (
                "Endpoint '%s %s' does not declare rate-limit headers "
                "(X-RateLimit-Limit, Retry-After) in its response schema. "
                "Without rate limiting, the endpoint is vulnerable to abuse." % (method, path)
            ),
            "recommendation": (
                "Implement rate limiting (e.g., 100 req/min per user). "
                "Return X-RateLimit-Limit and X-RateLimit-Remaining headers. "
                "Use 429 Too Many Requests for exceeded limits."
            ),
            "confidence": 0.5,
            "banking_impact": (
                "Finansal islem endpoint'lerine sinirsiz istek gonderilebilir — "
                "DDoS ve kaynak tuketimi riski."
                if is_banking
                else "API kaynaklarinin tuketilme riski."
            ),
        })

    # Check for pagination on list endpoints
    if method == "GET" and not _has_path_id_param(path):
        params = _get_param_names(endpoint.parameters)
        has_pagination = any(
            p in ("page", "limit", "offset", "per_page", "page_size", "cursor")
            for p in params
        )
        if not has_pagination:
            findings.append({
                "owasp_category": "API4:2023",
                "owasp_name": OWASP_CATEGORIES["API4:2023"],
                "severity": "low",
                "title": "No pagination on list endpoint",
                "description": (
                    "GET '%s' does not appear to have pagination parameters. "
                    "Large result sets may cause resource exhaustion." % path
                ),
                "recommendation": (
                    "Add pagination (page/limit or cursor-based) with a "
                    "maximum page size. Default to reasonable limits."
                ),
                "confidence": 0.4,
                "banking_impact": "Buyuk veri setlerinin donmesi performans sorunlarina yol acabilir.",
            })

    return findings


def _check_bfla(
    endpoint: ApiEndpoint,
) -> List[Dict[str, Any]]:
    """API5:2023 - Broken Function Level Authorization (BFLA)."""
    findings = []  # type: List[Dict[str, Any]]
    path = endpoint.path or ""
    method = (endpoint.method or "").upper()

    is_admin = bool(_ADMIN_PATTERNS.search(path))
    no_auth = not endpoint.auth_required

    if is_admin:
        severity = "critical" if no_auth else "high"
        findings.append({
            "owasp_category": "API5:2023",
            "owasp_name": OWASP_CATEGORIES["API5:2023"],
            "severity": severity,
            "title": "Admin/role endpoint — verify function-level authorization",
            "description": (
                "Endpoint '%s %s' appears to be an administrative function. "
                "%s"
                % (
                    method, path,
                    "It does not require authentication!" if no_auth
                    else "Verify that role-based access control (RBAC) is enforced."
                )
            ),
            "recommendation": (
                "Implement RBAC — only users with admin/manager roles should "
                "access this endpoint. Deny by default."
            ),
            "confidence": 0.8 if no_auth else 0.6,
            "banking_impact": (
                "Yetkisiz kullanicilar admin islevlerine erisebilir — "
                "rol yukseltme ve sistem konfigurasyonu degisikligi riski."
            ),
        })

    # PUT/DELETE on user role paths
    if method in ("PUT", "PATCH", "DELETE") and re.search(r"role|permission|yetki", path, re.I):
        findings.append({
            "owasp_category": "API5:2023",
            "owasp_name": OWASP_CATEGORIES["API5:2023"],
            "severity": "critical",
            "title": "Role/permission mutation — verify strict authorization",
            "description": (
                "Endpoint '%s %s' modifies roles or permissions. "
                "This is a high-privilege operation." % (method, path)
            ),
            "recommendation": (
                "Enforce strict RBAC and audit logging for all role changes. "
                "Require multi-factor confirmation for privilege escalation."
            ),
            "confidence": 0.85,
            "banking_impact": (
                "Rol degisikligi ile yetkisiz para transferi veya "
                "veri erisimi saglanabilir."
            ),
        })

    return findings


def _check_sensitive_flows(
    endpoint: ApiEndpoint,
) -> List[Dict[str, Any]]:
    """API6:2023 - Unrestricted Access to Sensitive Business Flows."""
    findings = []  # type: List[Dict[str, Any]]
    path = endpoint.path or ""
    method = (endpoint.method or "").upper()

    is_financial = _is_banking_sensitive(path)

    if is_financial and method == "POST":
        findings.append({
            "owasp_category": "API6:2023",
            "owasp_name": OWASP_CATEGORIES["API6:2023"],
            "severity": "high",
            "title": "Sensitive business flow — verify anti-automation protections",
            "description": (
                "Endpoint '%s %s' triggers a sensitive banking operation. "
                "Automated abuse (e.g., rapid fund transfers, payment replay) "
                "must be prevented." % (method, path)
            ),
            "recommendation": (
                "Implement transaction signing, CAPTCHA, idempotency keys, "
                "velocity checks, and daily transaction limits."
            ),
            "confidence": 0.75,
            "banking_impact": (
                "Otomatik saldiri ile toplu para transferi, odeme tekrari "
                "veya hesap bosaltma gerceklestirilebilir."
            ),
        })

    return findings


def _check_ssrf(
    endpoint: ApiEndpoint,
) -> List[Dict[str, Any]]:
    """API7:2023 - Server Side Request Forgery (SSRF)."""
    findings = []  # type: List[Dict[str, Any]]
    path = endpoint.path or ""
    method = (endpoint.method or "").upper()

    # Check parameters for URL-like inputs
    param_names = _get_param_names(endpoint.parameters)
    ssrf_params = [p for p in param_names if _SSRF_PARAM_PATTERNS.search(p)]

    # Also check request body schema for URL fields
    body_url_fields = []  # type: List[str]
    if endpoint.request_body_schema:
        props = endpoint.request_body_schema.get("properties", {})
        if not props:
            content = endpoint.request_body_schema.get("content", {})
            json_ct = content.get("application/json", {})
            nested = json_ct.get("schema", {})
            props = nested.get("properties", {})
        for fname, fschema in props.items():
            if _SSRF_PARAM_PATTERNS.search(fname):
                body_url_fields.append(fname)
            elif isinstance(fschema, dict) and fschema.get("format") == "uri":
                body_url_fields.append(fname)

    all_ssrf_fields = ssrf_params + body_url_fields

    if all_ssrf_fields:
        findings.append({
            "owasp_category": "API7:2023",
            "owasp_name": OWASP_CATEGORIES["API7:2023"],
            "severity": "high",
            "title": "Potential SSRF — URL/redirect parameters detected: %s" % ", ".join(all_ssrf_fields),
            "description": (
                "Endpoint '%s %s' accepts URL-like parameters (%s) that "
                "could be exploited for SSRF attacks." % (method, path, ", ".join(all_ssrf_fields))
            ),
            "recommendation": (
                "Validate and sanitize all URL inputs. Use an allowlist "
                "of permitted domains. Block internal/private IP ranges "
                "(10.x, 172.16-31.x, 192.168.x, 127.x, localhost)."
            ),
            "confidence": 0.75,
            "banking_impact": (
                "Dahili bankacilik servislerine (core banking, SWIFT, EFT) "
                "yetkisiz erisim saglanabilir."
            ),
        })

    return findings


def _check_security_misconfig(
    endpoint: ApiEndpoint,
) -> List[Dict[str, Any]]:
    """API8:2023 - Security Misconfiguration."""
    findings = []  # type: List[Dict[str, Any]]
    path = endpoint.path or ""
    method = (endpoint.method or "").upper()

    # Check for debug/internal endpoints
    if re.search(r"(debug|internal|test|swagger|docs|graphql|actuator|health)", path, re.I):
        findings.append({
            "owasp_category": "API8:2023",
            "owasp_name": OWASP_CATEGORIES["API8:2023"],
            "severity": "medium",
            "title": "Potentially exposed internal/debug endpoint",
            "description": (
                "Endpoint '%s %s' appears to be an internal or debug endpoint. "
                "These should not be exposed in production." % (method, path)
            ),
            "recommendation": (
                "Disable debug endpoints in production. Use environment-based "
                "configuration to expose them only in development."
            ),
            "confidence": 0.5,
            "banking_impact": (
                "Ic servis bilgileri ve konfigurasyonlarin ifsa olma riski."
            ),
        })

    # Check for missing security requirements in spec
    if not endpoint.security_requirements and endpoint.auth_required:
        findings.append({
            "owasp_category": "API8:2023",
            "owasp_name": OWASP_CATEGORIES["API8:2023"],
            "severity": "low",
            "title": "Missing security scheme definition in spec",
            "description": (
                "Endpoint '%s %s' is marked as requiring auth but has no "
                "security requirements defined in the spec." % (method, path)
            ),
            "recommendation": (
                "Define explicit security schemes (Bearer, OAuth2, API Key) "
                "in the OpenAPI spec for documentation accuracy."
            ),
            "confidence": 0.4,
            "banking_impact": "Spec ile uygulama arasinda guvenlik uyumsuzlugu.",
        })

    # CORS / headers check for responses
    response_schemas = endpoint.response_schemas or {}
    for code, schema in response_schemas.items():
        headers = schema.get("headers", {})
        header_names_lower = [h.lower() for h in headers.keys()]
        missing_headers = []  # type: List[str]
        for expected in ("x-content-type-options", "x-frame-options", "strict-transport-security"):
            if expected not in header_names_lower:
                missing_headers.append(expected)
        if missing_headers and code.startswith("2"):
            findings.append({
                "owasp_category": "API8:2023",
                "owasp_name": OWASP_CATEGORIES["API8:2023"],
                "severity": "info",
                "title": "Missing security headers in %s response" % code,
                "description": (
                    "Response %s for '%s %s' is missing recommended security "
                    "headers: %s" % (code, method, path, ", ".join(missing_headers))
                ),
                "recommendation": (
                    "Add X-Content-Type-Options: nosniff, "
                    "X-Frame-Options: DENY, and "
                    "Strict-Transport-Security headers."
                ),
                "confidence": 0.3,
                "banking_impact": "Clickjacking ve MIME-sniffing saldiri riski.",
            })
            break  # One finding per endpoint is enough

    return findings


def _check_inventory(
    endpoint: ApiEndpoint,
    spec: Optional[ApiSpec] = None,
) -> List[Dict[str, Any]]:
    """API9:2023 - Improper Inventory Management."""
    findings = []  # type: List[Dict[str, Any]]
    path = endpoint.path or ""
    method = (endpoint.method or "").upper()

    # Check for versioning in path
    if re.search(r"/v[0-9]+/", path):
        # Old API versions may still be exposed
        version_match = re.search(r"/v([0-9]+)/", path)
        if version_match:
            version_num = int(version_match.group(1))
            if version_num < 2:
                # v1 is common and acceptable, but note it
                pass
            # Check if multiple versions exist in the same spec
            # (This would need spec-level analysis — noted as info)

    # Deprecated endpoints
    desc = (endpoint.description or "").lower()
    summary = (endpoint.summary or "").lower()
    if "deprecated" in desc or "deprecated" in summary:
        findings.append({
            "owasp_category": "API9:2023",
            "owasp_name": OWASP_CATEGORIES["API9:2023"],
            "severity": "medium",
            "title": "Deprecated endpoint still in spec",
            "description": (
                "Endpoint '%s %s' is marked as deprecated but still present "
                "in the API spec. Deprecated endpoints may have known "
                "vulnerabilities." % (method, path)
            ),
            "recommendation": (
                "Remove deprecated endpoints from production or redirect "
                "to the current version. Monitor usage and sunset gracefully."
            ),
            "confidence": 0.8,
            "banking_impact": "Eski API versiyonlari guvenlik yamalari almayabilir.",
        })

    return findings


def _check_unsafe_consumption(
    endpoint: ApiEndpoint,
) -> List[Dict[str, Any]]:
    """API10:2023 - Unsafe Consumption of APIs."""
    findings = []  # type: List[Dict[str, Any]]
    path = endpoint.path or ""
    method = (endpoint.method or "").upper()

    # Check for webhook/callback patterns
    param_names = _get_param_names(endpoint.parameters)
    has_webhook = any(
        re.search(r"(webhook|callback|notify|hook|external)", p, re.I)
        for p in param_names
    )

    body_props = {}  # type: Dict[str, Any]
    if endpoint.request_body_schema:
        body_props = endpoint.request_body_schema.get("properties", {})
        if not body_props:
            content = endpoint.request_body_schema.get("content", {})
            json_ct = content.get("application/json", {})
            nested = json_ct.get("schema", {})
            body_props = nested.get("properties", {})

    body_webhook = any(
        re.search(r"(webhook|callback|external|third.?party)", k, re.I)
        for k in body_props.keys()
    )

    if has_webhook or body_webhook:
        findings.append({
            "owasp_category": "API10:2023",
            "owasp_name": OWASP_CATEGORIES["API10:2023"],
            "severity": "medium",
            "title": "Third-party/webhook integration — validate external data",
            "description": (
                "Endpoint '%s %s' appears to consume or configure external "
                "API/webhook data. Data from third parties must be validated." % (method, path)
            ),
            "recommendation": (
                "Validate and sanitize all data received from third-party APIs. "
                "Use timeouts, circuit breakers, and TLS for external calls. "
                "Never trust external input."
            ),
            "confidence": 0.6,
            "banking_impact": (
                "Dis servislerden gelen dogrulanmamis veri ile islem "
                "manipulasyonu yapilabilir."
            ),
        })

    return findings


# ============================================================================
# BANKING-SPECIFIC COMPLIANCE CHECKS
# ============================================================================

def _check_banking_compliance(
    endpoint: ApiEndpoint,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Banking-specific checks beyond OWASP — BDDK, KVKK, PCI-DSS, MASAK.

    Returns (findings, compliance_tags)
    """
    findings = []  # type: List[Dict[str, Any]]
    compliance_tags = []  # type: List[str]
    path = endpoint.path or ""
    method = (endpoint.method or "").upper()

    is_financial = _is_banking_sensitive(path)
    has_pii = endpoint.has_pii or bool(_PII_PATTERNS.search(path))

    if is_financial:
        compliance_tags.append("BDDK")
        compliance_tags.append("PCI-DSS")

        if method in ("POST", "PUT", "PATCH", "DELETE"):
            findings.append({
                "owasp_category": "API6:2023",
                "owasp_name": OWASP_CATEGORIES["API6:2023"],
                "severity": "high",
                "title": "BDDK — Financial mutation requires transaction logging",
                "description": (
                    "Endpoint '%s %s' modifies financial data. BDDK regulations "
                    "require full audit trails for all financial transactions." % (method, path)
                ),
                "recommendation": (
                    "Ensure complete audit logging with timestamps, user identity, "
                    "IP address, and transaction details. Retain logs per BDDK requirements."
                ),
                "confidence": 0.8,
                "banking_impact": (
                    "BDDK mevzuati geregi tum finansal islemlerin kaydi zorunludur. "
                    "Eksik loglama cezai yaptirimla sonuclanabilir."
                ),
            })

    if has_pii:
        compliance_tags.append("KVKK")

        findings.append({
            "owasp_category": "API3:2023",
            "owasp_name": OWASP_CATEGORIES["API3:2023"],
            "severity": "medium",
            "title": "KVKK — Personal data endpoint requires data minimization",
            "description": (
                "Endpoint '%s %s' handles personal identifiable information. "
                "KVKK requires data minimization and explicit consent." % (method, path)
            ),
            "recommendation": (
                "Return only necessary PII fields. Implement field-level "
                "encryption for sensitive data. Log all PII access."
            ),
            "confidence": 0.7,
            "banking_impact": (
                "KVKK ihlali — kisisel verilerin korunmasi kanununa "
                "aykirilik durumunda agir para cezasi uygulanabilir."
            ),
        })

    return findings, compliance_tags


# ============================================================================
# MAIN SCAN FUNCTIONS
# ============================================================================

def _compute_security_score(findings: List[Dict[str, Any]]) -> float:
    """
    Compute a 0-100 security score based on findings.
    100 = no findings, 0 = many critical findings.
    """
    total_penalty = 0.0
    for f in findings:
        severity = f.get("severity", "info")
        penalty = _SEVERITY_WEIGHTS.get(severity, 0.0)
        confidence = f.get("confidence", 0.5)
        total_penalty += penalty * confidence

    score = max(0.0, 100.0 - total_penalty)
    return round(score, 1)


def _generate_test_suggestions_for_findings(
    endpoint: ApiEndpoint,
    findings: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Generate test suggestions based on security findings."""
    suggestions = []  # type: List[Dict[str, Any]]
    method = (endpoint.method or "").upper()
    path = endpoint.path or ""

    seen_categories = set()  # type: set

    for f in findings:
        cat = f.get("owasp_category", "")
        if cat in seen_categories:
            continue
        seen_categories.add(cat)

        if cat == "API1:2023":
            suggestions.append({
                "title": "BOLA: Access resource with different user's ID",
                "test_type": "security",
                "owasp_category": "API1:2023",
                "request_modifications": {
                    "description": "Replace the path ID with another user's resource ID",
                    "auth": "Use User A's token to access User B's resource",
                },
                "expected_behavior": "Server returns 403 Forbidden, not the resource",
            })
            suggestions.append({
                "title": "BOLA: Access resource without authentication",
                "test_type": "security",
                "owasp_category": "API1:2023",
                "request_modifications": {
                    "description": "Remove Authorization header entirely",
                },
                "expected_behavior": "Server returns 401 Unauthorized",
            })

        elif cat == "API2:2023":
            suggestions.append({
                "title": "Auth Bypass: Access sensitive endpoint without token",
                "test_type": "security",
                "owasp_category": "API2:2023",
                "request_modifications": {
                    "description": "Remove or invalidate the auth token",
                },
                "expected_behavior": "Server returns 401 Unauthorized",
            })
            suggestions.append({
                "title": "Auth: Brute-force login with common passwords",
                "test_type": "security",
                "owasp_category": "API2:2023",
                "request_modifications": {
                    "description": "Send multiple login attempts with wrong passwords",
                    "iterations": 10,
                },
                "expected_behavior": "Server returns 429 after threshold or locks account",
            })

        elif cat == "API3:2023":
            suggestions.append({
                "title": "Mass Assignment: Send extra fields in request body",
                "test_type": "security",
                "owasp_category": "API3:2023",
                "request_modifications": {
                    "description": "Add admin-only fields like 'role', 'balance', 'is_admin'",
                    "extra_fields": {"role": "admin", "balance": 999999, "is_admin": True},
                },
                "expected_behavior": "Server ignores extra fields or returns 400",
            })

        elif cat == "API4:2023":
            suggestions.append({
                "title": "Rate Limit: Rapid successive requests",
                "test_type": "security",
                "owasp_category": "API4:2023",
                "request_modifications": {
                    "description": "Send 100+ requests in quick succession",
                    "iterations": 100,
                },
                "expected_behavior": "Server returns 429 Too Many Requests after threshold",
            })

        elif cat == "API5:2023":
            suggestions.append({
                "title": "BFLA: Access admin endpoint with regular user token",
                "test_type": "security",
                "owasp_category": "API5:2023",
                "request_modifications": {
                    "description": "Use a non-admin user's token on admin endpoint",
                },
                "expected_behavior": "Server returns 403 Forbidden",
            })

        elif cat == "API6:2023":
            suggestions.append({
                "title": "Business Flow: Replay financial transaction",
                "test_type": "security",
                "owasp_category": "API6:2023",
                "request_modifications": {
                    "description": "Replay the same request with identical idempotency key",
                },
                "expected_behavior": "Server detects duplicate and returns error or same response",
            })

        elif cat == "API7:2023":
            suggestions.append({
                "title": "SSRF: Inject internal URL in parameter",
                "test_type": "security",
                "owasp_category": "API7:2023",
                "request_modifications": {
                    "description": "Set URL parameter to http://localhost/admin or http://169.254.169.254",
                },
                "expected_behavior": "Server rejects internal/private URLs",
            })

        elif cat == "API8:2023":
            suggestions.append({
                "title": "Misconfig: Check security headers in response",
                "test_type": "security",
                "owasp_category": "API8:2023",
                "request_modifications": {
                    "description": "Send normal request and inspect response headers",
                },
                "expected_behavior": "Response includes X-Content-Type-Options, HSTS, X-Frame-Options",
            })

    return suggestions


def scan_endpoint(
    db: Session,
    endpoint_id: str,
) -> Dict[str, Any]:
    """
    Scan a single API endpoint for OWASP API Top 10 vulnerabilities.

    Returns a comprehensive security analysis result.
    """
    endpoint = db.query(ApiEndpoint).filter(
        ApiEndpoint.id == endpoint_id,
    ).first()

    if not endpoint:
        return {
            "endpoint_id": endpoint_id,
            "method": "",
            "path": "",
            "risk_level": "unknown",
            "findings": [],
            "security_score": 0.0,
            "test_suggestions": [],
            "error": "Endpoint not found",
        }

    # Optionally load spec for inventory checks
    spec = None  # type: Optional[ApiSpec]
    try:
        spec = db.query(ApiSpec).filter(
            ApiSpec.id == endpoint.spec_id,
        ).first()
    except Exception:
        pass

    # Run all OWASP checks
    all_findings = []  # type: List[Dict[str, Any]]

    all_findings.extend(_check_bola(endpoint))
    all_findings.extend(_check_broken_auth(endpoint))
    all_findings.extend(_check_property_auth(endpoint))
    all_findings.extend(_check_rate_limiting(endpoint))
    all_findings.extend(_check_bfla(endpoint))
    all_findings.extend(_check_sensitive_flows(endpoint))
    all_findings.extend(_check_ssrf(endpoint))
    all_findings.extend(_check_security_misconfig(endpoint))
    all_findings.extend(_check_inventory(endpoint, spec))
    all_findings.extend(_check_unsafe_consumption(endpoint))

    # Banking compliance
    compliance_findings, compliance_tags = _check_banking_compliance(endpoint)
    all_findings.extend(compliance_findings)

    # Sort findings by severity
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    all_findings.sort(key=lambda f: severity_order.get(f.get("severity", "info"), 5))

    # Compute score
    security_score = _compute_security_score(all_findings)

    # Determine overall risk level from findings
    if any(f.get("severity") == "critical" for f in all_findings):
        risk_level = "critical"
    elif any(f.get("severity") == "high" for f in all_findings):
        risk_level = "high"
    elif any(f.get("severity") == "medium" for f in all_findings):
        risk_level = "medium"
    elif all_findings:
        risk_level = "low"
    else:
        risk_level = endpoint.risk_level or "low"

    # Generate test suggestions
    test_suggestions = _generate_test_suggestions_for_findings(endpoint, all_findings)

    return {
        "endpoint_id": endpoint.id,
        "method": endpoint.method,
        "path": endpoint.path,
        "risk_level": risk_level,
        "findings": all_findings,
        "security_score": security_score,
        "test_suggestions": test_suggestions,
    }


def scan_spec(
    db: Session,
    project_id: str,
    spec_id: str,
) -> Dict[str, Any]:
    """
    Scan all endpoints in an API spec for security vulnerabilities.

    Returns aggregated summary + per-endpoint results.
    """
    spec = db.query(ApiSpec).filter(
        ApiSpec.id == spec_id,
        ApiSpec.project_id == project_id,
    ).first()

    if not spec:
        return {
            "spec_id": spec_id,
            "spec_name": "",
            "total_endpoints": 0,
            "scanned_endpoints": 0,
            "findings_by_severity": {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
            "findings_by_owasp": {},
            "avg_security_score": 0.0,
            "endpoint_results": [],
            "error": "Spec not found",
        }

    endpoints = db.query(ApiEndpoint).filter(
        ApiEndpoint.spec_id == spec_id,
    ).all()

    endpoint_results = []  # type: List[Dict[str, Any]]
    all_findings = []  # type: List[Dict[str, Any]]
    total_score = 0.0

    for ep in endpoints:
        result = scan_endpoint(db, ep.id)
        endpoint_results.append(result)
        all_findings.extend(result.get("findings", []))
        total_score += result.get("security_score", 0.0)

    scanned = len(endpoints)
    avg_score = round(total_score / scanned, 1) if scanned > 0 else 0.0

    # Aggregate findings by severity
    findings_by_severity = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    for f in all_findings:
        sev = f.get("severity", "info")
        if sev in findings_by_severity:
            findings_by_severity[sev] += 1

    # Aggregate by OWASP category
    findings_by_owasp = {}  # type: Dict[str, int]
    for f in all_findings:
        cat = f.get("owasp_category", "unknown")
        findings_by_owasp[cat] = findings_by_owasp.get(cat, 0) + 1

    return {
        "spec_id": spec_id,
        "spec_name": spec.name,
        "total_endpoints": spec.endpoint_count or len(endpoints),
        "scanned_endpoints": scanned,
        "findings_by_severity": findings_by_severity,
        "findings_by_owasp": findings_by_owasp,
        "avg_security_score": avg_score,
        "endpoint_results": endpoint_results,
    }


def get_security_dashboard(
    db: Session,
    project_id: str,
) -> Dict[str, Any]:
    """
    Build a security dashboard for the entire project.

    Aggregates scan results, compliance status, and recommendations.
    """
    # Get all specs in the project
    specs = db.query(ApiSpec).filter(
        ApiSpec.project_id == project_id,
    ).all()

    # Get all endpoints via specs
    spec_ids = [s.id for s in specs]
    endpoints = []  # type: List[ApiEndpoint]
    if spec_ids:
        endpoints = db.query(ApiEndpoint).filter(
            ApiEndpoint.spec_id.in_(spec_ids),
        ).all()

    total_endpoints = len(endpoints)

    # Scan all endpoints
    all_findings = []  # type: List[Dict[str, Any]]
    endpoint_scores = []  # type: List[Tuple[str, str, str, float, int]]
    total_score = 0.0
    scanned = 0

    for ep in endpoints:
        result = scan_endpoint(db, ep.id)
        findings = result.get("findings", [])
        score = result.get("security_score", 100.0)
        all_findings.extend(findings)
        total_score += score
        scanned += 1
        endpoint_scores.append((
            ep.id,
            ep.method,
            ep.path,
            score,
            len(findings),
        ))

    avg_score = round(total_score / scanned, 1) if scanned > 0 else 100.0

    # Findings by severity
    findings_by_severity = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    for f in all_findings:
        sev = f.get("severity", "info")
        if sev in findings_by_severity:
            findings_by_severity[sev] += 1

    # Findings by OWASP category
    findings_by_owasp = {}  # type: Dict[str, int]
    for f in all_findings:
        cat = f.get("owasp_category", "unknown")
        findings_by_owasp[cat] = findings_by_owasp.get(cat, 0) + 1

    # Top vulnerable endpoints (sorted by score ascending = most vulnerable first)
    endpoint_scores.sort(key=lambda x: x[3])
    top_vulnerable = [
        {
            "endpoint_id": eid,
            "method": m,
            "path": p,
            "security_score": s,
            "finding_count": fc,
        }
        for eid, m, p, s, fc in endpoint_scores[:10]
        if fc > 0
    ]

    # Compliance status
    kvkk_checks = []  # type: List[str]
    bddk_checks = []  # type: List[str]
    pci_checks = []  # type: List[str]
    kvkk_passed = 0
    kvkk_failed = 0
    bddk_passed = 0
    bddk_failed = 0
    pci_passed = 0
    pci_failed = 0

    for ep in endpoints:
        path = (ep.path or "").lower()
        has_pii = ep.has_pii or bool(_PII_PATTERNS.search(path))
        is_financial = _is_banking_sensitive(path)

        if has_pii:
            check = "%s %s — PII data handling" % (ep.method, ep.path)
            if ep.auth_required:
                kvkk_passed += 1
                kvkk_checks.append("PASSED: %s" % check)
            else:
                kvkk_failed += 1
                kvkk_checks.append("FAILED: %s (no auth)" % check)

        if is_financial:
            check = "%s %s — financial operation" % (ep.method, ep.path)
            if ep.auth_required:
                bddk_passed += 1
                bddk_checks.append("PASSED: %s" % check)
                pci_passed += 1
                pci_checks.append("PASSED: %s" % check)
            else:
                bddk_failed += 1
                bddk_checks.append("FAILED: %s (no auth)" % check)
                pci_failed += 1
                pci_checks.append("FAILED: %s (no auth)" % check)

    # Generate recommendations
    recommendations = []  # type: List[str]

    if findings_by_severity.get("critical", 0) > 0:
        recommendations.append(
            "KRITIK: %d kritik guvenlik bulgunu derhal giderilmeli." % findings_by_severity["critical"]
        )
    if findings_by_severity.get("high", 0) > 0:
        recommendations.append(
            "YUKSEK: %d yuksek oncelikli bulgu sprint icerisinde ele alinmali." % findings_by_severity["high"]
        )
    if findings_by_owasp.get("API1:2023", 0) > 0:
        recommendations.append(
            "BOLA: Tum ID-bazli endpoint'lere nesne seviyesinde yetkilendirme eklenmelidir."
        )
    if findings_by_owasp.get("API2:2023", 0) > 0:
        recommendations.append(
            "Kimlik Dogrulama: Hassas endpoint'lerin tamami OAuth 2.0 / JWT ile korunmalidir."
        )
    if findings_by_owasp.get("API4:2023", 0) > 0:
        recommendations.append(
            "Rate Limiting: Tum endpoint'lere istek sinirlamasi uygulanmalidir."
        )
    if kvkk_failed > 0:
        recommendations.append(
            "KVKK: %d kisisel veri endpoint'i kimlik dogrulama gerektirir." % kvkk_failed
        )
    if bddk_failed > 0:
        recommendations.append(
            "BDDK: %d finansal islem endpoint'i guvence altina alinmalidir." % bddk_failed
        )
    if not recommendations:
        recommendations.append(
            "Genel guvenlik durumu iyi. Duzenli tarama ile devamliligi saglayin."
        )

    return {
        "total_endpoints": total_endpoints,
        "scanned_endpoints": scanned,
        "findings_by_severity": findings_by_severity,
        "findings_by_owasp": findings_by_owasp,
        "avg_security_score": avg_score,
        "top_vulnerable_endpoints": top_vulnerable,
        "compliance_status": {
            "kvkk": {
                "passed": kvkk_passed,
                "failed": kvkk_failed,
                "checks": kvkk_checks[:20],
            },
            "bddk": {
                "passed": bddk_passed,
                "failed": bddk_failed,
                "checks": bddk_checks[:20],
            },
            "pci_dss": {
                "passed": pci_passed,
                "failed": pci_failed,
                "checks": pci_checks[:20],
            },
        },
        "recommendations": recommendations,
    }


def generate_security_tests(
    db: Session,
    project_id: str,
    endpoint_id: str,
    owasp_categories: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Generate ApiTestCase records for security testing based on scan findings.

    Creates actual persisted test cases with test_type='security'.
    """
    # First scan the endpoint
    scan_result = scan_endpoint(db, endpoint_id)

    if scan_result.get("error"):
        return {
            "endpoint_id": endpoint_id,
            "generated_count": 0,
            "test_cases": [],
            "error": scan_result["error"],
        }

    findings = scan_result.get("findings", [])
    suggestions = scan_result.get("test_suggestions", [])

    # Filter by OWASP categories if specified
    if owasp_categories:
        category_set = set(owasp_categories)
        findings = [f for f in findings if f.get("owasp_category") in category_set]
        suggestions = [s for s in suggestions if s.get("owasp_category") in category_set]

    endpoint = db.query(ApiEndpoint).filter(
        ApiEndpoint.id == endpoint_id,
    ).first()

    if not endpoint:
        return {
            "endpoint_id": endpoint_id,
            "generated_count": 0,
            "test_cases": [],
            "error": "Endpoint not found",
        }

    method = endpoint.method or "GET"
    path = endpoint.path or ""

    created_cases = []  # type: List[ApiTestCase]

    for suggestion in suggestions:
        cat = suggestion.get("owasp_category", "")
        title = suggestion.get("title", "Security test")
        mods = suggestion.get("request_modifications", {})
        expected = suggestion.get("expected_behavior", "")

        # Determine regulation
        regulation = None  # type: Optional[str]
        if _is_banking_sensitive(path):
            regulation = "BDDK"
        elif _PII_PATTERNS.search(path):
            regulation = "KVKK"

        # Determine priority from the finding severity
        matching_findings = [f for f in findings if f.get("owasp_category") == cat]
        severity = "medium"
        if matching_findings:
            severity = matching_findings[0].get("severity", "medium")

        priority_map = {"critical": "P0", "high": "P1", "medium": "P2", "low": "P3"}
        priority = priority_map.get(severity, "P2")

        # Build assertions
        assertions = []  # type: List[Dict[str, Any]]
        if "401" in expected.lower() or "unauthorized" in expected.lower():
            assertions.append({
                "type": "status_code",
                "operator": "equals",
                "expected": 401,
                "message": "Should return 401 Unauthorized",
            })
        elif "403" in expected.lower() or "forbidden" in expected.lower():
            assertions.append({
                "type": "status_code",
                "operator": "equals",
                "expected": 403,
                "message": "Should return 403 Forbidden",
            })
        elif "429" in expected.lower() or "rate" in expected.lower():
            assertions.append({
                "type": "status_code",
                "operator": "equals",
                "expected": 429,
                "message": "Should return 429 Too Many Requests",
            })
        elif "400" in expected.lower() or "rejects" in expected.lower():
            assertions.append({
                "type": "status_code",
                "operator": "one_of",
                "expected": [400, 403, 422],
                "message": "Should reject invalid input",
            })

        tc = ApiTestCase(
            project_id=project_id,
            endpoint_id=endpoint_id,
            title="[Security] %s" % title,
            description=(
                "Auto-generated security test for %s.\n"
                "Expected: %s\n"
                "Modifications: %s"
                % (cat, expected, str(mods))
            ),
            test_type="security",
            priority=priority,
            owasp_category=cat,
            regulation=regulation,
            request_method=method,
            request_path=path,
            request_headers={},
            request_params={},
            request_body=mods if isinstance(mods, dict) else {},
            assertions=assertions,
            ai_generated=True,
            ai_reasoning=(
                "Generated by OWASP API Top 10 scanner for %s. "
                "Finding: %s"
                % (cat, matching_findings[0].get("title", "") if matching_findings else title)
            ),
            review_status="pending",
        )

        db.add(tc)
        created_cases.append(tc)

    if created_cases:
        db.commit()
        for tc in created_cases:
            db.refresh(tc)

    return {
        "endpoint_id": endpoint_id,
        "generated_count": len(created_cases),
        "test_cases": created_cases,
        "scan_summary": {
            "total_findings": len(scan_result.get("findings", [])),
            "security_score": scan_result.get("security_score", 0.0),
            "risk_level": scan_result.get("risk_level", "unknown"),
        },
    }
