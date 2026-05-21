"""
OpenAPI / Swagger Spec Parser
=============================

Desteklenen formatlar:
  - OpenAPI 3.0.x
  - OpenAPI 3.1.x
  - Swagger 2.0

Akis:
  1. parse_spec()        → Raw spec oku + dogrula
  2. resolve_spec()      → $ref referanslarini coz
  3. extract_endpoints() → Tum endpoint'leri cikar
  4. analyze_risk()      → AI-assisted risk analizi
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

import yaml

logger = logging.getLogger(__name__)


# ── PII / Hassas Veri Pattern'leri ────────────────────────────────────
_PII_PATTERNS = re.compile(
    r"(password|passwd|secret|token|api_?key|authorization|credit_?card|"
    r"card_?number|cvv|cvc|ssn|tc_?kimlik|tckn|iban|account_?number|"
    r"phone|telefon|email|e_?posta|birth_?date|dogum|address|adres|"
    r"identity|kimlik|passport|pasaport|tax_?id|vergi)",
    re.IGNORECASE,
)

_FINANCIAL_PATTERNS = re.compile(
    r"(transfer|payment|odeme|havale|eft|swift|withdrawal|deposit|"
    r"balance|bakiye|transaction|islem|loan|kredi|currency|doviz|"
    r"exchange|kur|invoice|fatura|refund|iade|charge|ucret)",
    re.IGNORECASE,
)


@dataclass
class EndpointInfo:
    """Parse edilen tek bir endpoint."""
    method: str
    path: str
    operation_id: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    # Parameters
    parameters: List[dict] = field(default_factory=list)
    request_body_schema: Optional[dict] = None
    response_schemas: dict = field(default_factory=dict)

    # Security
    security_requirements: Optional[List[dict]] = None
    auth_required: bool = True

    # AI risk assessment (auto-populated)
    risk_level: str = "medium"
    has_pii: bool = False
    has_financial: bool = False
    compliance_tags: List[str] = field(default_factory=list)

    # Dependencies
    depends_on: List[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "method": self.method,
            "path": self.path,
            "operation_id": self.operation_id,
            "summary": self.summary,
            "description": self.description,
            "tags": self.tags,
            "parameters": self.parameters,
            "request_body_schema": self.request_body_schema,
            "response_schemas": self.response_schemas,
            "security_requirements": self.security_requirements,
            "auth_required": self.auth_required,
            "risk_level": self.risk_level,
            "has_pii": self.has_pii,
            "has_financial": self.has_financial,
            "compliance_tags": self.compliance_tags,
            "depends_on": self.depends_on,
        }


@dataclass
class SpecAnalysis:
    """Spec parse sonucu."""
    spec_format: str  # openapi_3.0, openapi_3.1, swagger_2.0
    version: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    servers: List[dict] = field(default_factory=list)
    endpoints: List[EndpointInfo] = field(default_factory=list)
    schemas: dict = field(default_factory=dict)
    security_schemes: dict = field(default_factory=dict)

    # Istatistikler
    endpoint_count: int = 0
    schema_count: int = 0
    pii_endpoint_count: int = 0
    financial_endpoint_count: int = 0
    critical_count: int = 0
    high_count: int = 0

    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def detect_format(spec: dict) -> str:
    """Spec formatini tespit et."""
    if "openapi" in spec:
        ver = str(spec["openapi"])
        if ver.startswith("3.1"):
            return "openapi_3.1"
        return "openapi_3.0"
    if "swagger" in spec:
        return "swagger_2.0"
    return "unknown"


def parse_raw(content: Union[str, bytes]) -> dict:
    """
    Raw string/bytes'i dict'e parse et.
    JSON veya YAML olabilir.
    """
    text = content if isinstance(content, str) else content.decode("utf-8", errors="replace")
    text = text.strip()

    # JSON dene
    if text.startswith("{") or text.startswith("["):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    # YAML dene
    try:
        result = yaml.safe_load(text)
        if isinstance(result, dict):
            return result
    except yaml.YAMLError:
        pass

    raise ValueError("Dosya JSON veya YAML olarak parse edilemedi")


def validate_spec(spec: dict) -> List[str]:
    """
    OpenAPI spec'i dogrula.
    Returns: hata mesajlari listesi (bossa gecerli)
    """
    errors: List[str] = []
    try:
        from openapi_spec_validator import validate
        validate(spec)
    except ImportError:
        errors.append("openapi-spec-validator yuklu degil, dogrulama atlandi")
    except Exception as exc:
        errors.append(f"Spec dogrulama hatasi: {exc}")
    return errors


def resolve_refs(spec: dict) -> dict:
    """
    $ref referanslarini coz (dereference).
    prance kutuphanesi varsa kullanir, yoksa basit fallback.
    """
    try:
        import prance
        import tempfile
        import os

        # prance dosya/url bekliyor, gecici dosyaya yaz
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False,
        ) as f:
            json.dump(spec, f)
            tmp_path = f.name

        try:
            parser = prance.ResolvingParser(
                tmp_path,
                strict=False,
                backend="openapi-spec-validator",
            )
            return parser.specification
        finally:
            os.unlink(tmp_path)
    except ImportError:
        logger.warning("prance yuklu degil, $ref cozumleme atlaniyor")
        return spec
    except Exception as exc:
        logger.warning("prance resolve hatasi: %s, ham spec kullaniliyor", exc)
        return spec


def _extract_schema_from_content(content: dict) -> Optional[dict]:
    """Request/response content'ten schema cikar."""
    if not content:
        return None
    # application/json tercih et
    for ct in ["application/json", "application/xml", "text/plain", "*/*"]:
        if ct in content:
            return content[ct].get("schema")
    # Ilk bulunani al
    for v in content.values():
        if isinstance(v, dict) and "schema" in v:
            return v["schema"]
    return None


def _assess_risk(endpoint: EndpointInfo) -> None:
    """
    Endpoint'in risk seviyesini belirle — PII, finansal islem, compliance.
    Kurallar:
      - DELETE/PUT + auth gerekli → en az "high"
      - Finansal anahtar kelime → "critical"
      - PII alani → "high" + KVKK
      - Auth endpoint → "critical"
    """
    # Tum metin alanlarini birlesitir
    searchable = " ".join(filter(None, [
        endpoint.path,
        endpoint.operation_id,
        endpoint.summary,
        endpoint.description,
        json.dumps(endpoint.request_body_schema or {}),
        json.dumps(endpoint.parameters),
    ]))

    # PII kontrolu
    if _PII_PATTERNS.search(searchable):
        endpoint.has_pii = True
        if "KVKK" not in endpoint.compliance_tags:
            endpoint.compliance_tags.append("KVKK")

    # Finansal islem kontrolu
    if _FINANCIAL_PATTERNS.search(searchable):
        endpoint.has_financial = True
        if "BDDK" not in endpoint.compliance_tags:
            endpoint.compliance_tags.append("BDDK")
        if "MASAK" not in endpoint.compliance_tags:
            endpoint.compliance_tags.append("MASAK")

    # Kart verisi (PCI-DSS)
    if re.search(r"card|cvv|cvc|pan|credit", searchable, re.IGNORECASE):
        if "PCI-DSS" not in endpoint.compliance_tags:
            endpoint.compliance_tags.append("PCI-DSS")

    # Risk seviyesi hesapla
    risk = "low"

    # Auth/login endpoint'leri her zaman critical
    if re.search(r"(auth|login|token|oauth|session)", endpoint.path, re.IGNORECASE):
        risk = "critical"
    elif endpoint.has_financial:
        risk = "critical"
    elif endpoint.has_pii and endpoint.method in ("POST", "PUT", "PATCH", "DELETE"):
        risk = "high"
    elif endpoint.method in ("DELETE", "PUT", "PATCH"):
        risk = "high" if endpoint.auth_required else "medium"
    elif endpoint.has_pii:
        risk = "medium"
    elif endpoint.method == "GET" and not endpoint.auth_required:
        risk = "low"
    else:
        risk = "medium"

    endpoint.risk_level = risk


def _detect_dependencies(endpoints: List[EndpointInfo]) -> None:
    """
    Endpoint'ler arasi bagimlilik grafini cikar.

    Ornek:
      POST /auth/login → token uretir
      GET /accounts/{id} → account_id gerektirir
      POST /transfers → auth_token + account_id gerektirir
    """
    # Path parametreleri iceren endpoint'leri bul
    providers: Dict[str, EndpointInfo] = {}

    for ep in endpoints:
        # POST endpoint'ler genellikle kaynak uretir
        if ep.method == "POST":
            # Path'in son segmentinden resource tipi cikar
            segments = [s for s in ep.path.split("/") if s and not s.startswith("{")]
            if segments:
                resource = segments[-1].rstrip("s")  # "users" → "user"
                providers[resource] = ep

    for ep in endpoints:
        # Path parametreleri kontrol et
        path_params = re.findall(r"\{(\w+)\}", ep.path)
        for param in path_params:
            # param: "user_id", "account_id", etc.
            resource = param.replace("_id", "").replace("Id", "")
            if resource in providers:
                provider = providers[resource]
                ep.depends_on.append({
                    "endpoint": f"{provider.method} {provider.path}",
                    "provides": param,
                    "json_path": f"$.id",
                })

        # Auth gerektiren endpoint'ler login'e bagimli
        if ep.auth_required and not re.search(
            r"(auth|login|token|register)", ep.path, re.IGNORECASE,
        ):
            for login_ep in endpoints:
                if re.search(r"(auth/login|auth/token|oauth)", login_ep.path, re.IGNORECASE):
                    ep.depends_on.append({
                        "endpoint": f"{login_ep.method} {login_ep.path}",
                        "provides": "auth_token",
                        "json_path": "$.access_token",
                    })
                    break


def extract_endpoints_openapi3(spec: dict) -> List[EndpointInfo]:
    """OpenAPI 3.x spec'ten endpoint'leri cikar."""
    endpoints: List[EndpointInfo] = []
    paths = spec.get("paths", {})
    global_security = spec.get("security", [])
    security_schemes = spec.get("components", {}).get("securitySchemes", {})

    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue

        # Path-level parameters
        path_params = path_item.get("parameters", [])

        for method in ("get", "post", "put", "delete", "patch", "head", "options"):
            operation = path_item.get(method)
            if not operation or not isinstance(operation, dict):
                continue

            # Parameters: path-level + operation-level
            op_params = list(path_params) + operation.get("parameters", [])
            params = []
            for p in op_params:
                params.append({
                    "name": p.get("name"),
                    "in": p.get("in"),
                    "required": p.get("required", False),
                    "schema": p.get("schema", {}),
                    "description": p.get("description"),
                })

            # Request body
            req_body = operation.get("requestBody", {})
            req_schema = _extract_schema_from_content(
                req_body.get("content", {}),
            ) if req_body else None

            # Response schemas
            resp_schemas: Dict[str, Any] = {}
            for status, resp_obj in operation.get("responses", {}).items():
                if isinstance(resp_obj, dict):
                    schema = _extract_schema_from_content(
                        resp_obj.get("content", {}),
                    )
                    if schema:
                        resp_schemas[str(status)] = schema

            # Security
            op_security = operation.get("security", global_security)
            auth_required = bool(op_security)

            ep = EndpointInfo(
                method=method.upper(),
                path=path,
                operation_id=operation.get("operationId"),
                summary=operation.get("summary"),
                description=operation.get("description"),
                tags=operation.get("tags", []),
                parameters=params,
                request_body_schema=req_schema,
                response_schemas=resp_schemas,
                security_requirements=op_security,
                auth_required=auth_required,
            )

            # Risk assessment
            _assess_risk(ep)
            endpoints.append(ep)

    return endpoints


def extract_endpoints_swagger2(spec: dict) -> List[EndpointInfo]:
    """Swagger 2.0 spec'ten endpoint'leri cikar."""
    endpoints: List[EndpointInfo] = []
    paths = spec.get("paths", {})
    global_security = spec.get("security", [])

    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue

        path_params = path_item.get("parameters", [])

        for method in ("get", "post", "put", "delete", "patch"):
            operation = path_item.get(method)
            if not operation or not isinstance(operation, dict):
                continue

            # Parameters
            all_params = list(path_params) + operation.get("parameters", [])
            params = []
            body_schema = None

            for p in all_params:
                if p.get("in") == "body":
                    body_schema = p.get("schema")
                else:
                    params.append({
                        "name": p.get("name"),
                        "in": p.get("in"),
                        "required": p.get("required", False),
                        "schema": {"type": p.get("type", "string")},
                        "description": p.get("description"),
                    })

            # Responses
            resp_schemas: Dict[str, Any] = {}
            for status, resp_obj in operation.get("responses", {}).items():
                if isinstance(resp_obj, dict) and "schema" in resp_obj:
                    resp_schemas[str(status)] = resp_obj["schema"]

            op_security = operation.get("security", global_security)

            ep = EndpointInfo(
                method=method.upper(),
                path=path,
                operation_id=operation.get("operationId"),
                summary=operation.get("summary"),
                description=operation.get("description"),
                tags=operation.get("tags", []),
                parameters=params,
                request_body_schema=body_schema,
                response_schemas=resp_schemas,
                security_requirements=op_security,
                auth_required=bool(op_security),
            )

            _assess_risk(ep)
            endpoints.append(ep)

    return endpoints


def parse_spec(
    content: Union[str, bytes, dict],
    *,
    resolve: bool = True,
) -> SpecAnalysis:
    """
    OpenAPI/Swagger spec'i parse et + analiz et.

    Args:
        content: Raw JSON/YAML string, bytes, veya zaten parse edilmis dict
        resolve: $ref referanslarini coz (True default)

    Returns:
        SpecAnalysis — tum endpoint'ler, schemalar, risk degerlendirmesi
    """
    analysis = SpecAnalysis(spec_format="unknown")

    # 1. Parse
    if isinstance(content, dict):
        spec = content
    else:
        try:
            spec = parse_raw(content)
        except ValueError as exc:
            analysis.errors.append(str(exc))
            return analysis

    # 2. Format tespit
    analysis.spec_format = detect_format(spec)
    if analysis.spec_format == "unknown":
        analysis.errors.append("Taninamayan spec formati. OpenAPI 3.x veya Swagger 2.0 bekleniyor.")
        return analysis

    # 3. Dogrula
    validation_errors = validate_spec(spec)
    analysis.warnings.extend(validation_errors)

    # 4. Metadata
    info = spec.get("info", {})
    analysis.title = info.get("title")
    analysis.description = info.get("description")
    analysis.version = info.get("version")
    analysis.servers = spec.get("servers", [])

    # 5. Resolve $ref'ler
    resolved = resolve_refs(spec) if resolve else spec

    # 6. Schemas
    if analysis.spec_format.startswith("openapi"):
        analysis.schemas = resolved.get("components", {}).get("schemas", {})
        analysis.security_schemes = resolved.get("components", {}).get("securitySchemes", {})
    else:
        analysis.schemas = resolved.get("definitions", {})
        analysis.security_schemes = resolved.get("securityDefinitions", {})

    analysis.schema_count = len(analysis.schemas)

    # 7. Endpoint cikarimi
    if analysis.spec_format.startswith("openapi"):
        analysis.endpoints = extract_endpoints_openapi3(resolved)
    else:
        analysis.endpoints = extract_endpoints_swagger2(resolved)

    # 8. Dependency grafleri
    _detect_dependencies(analysis.endpoints)

    # 9. Istatistikler
    analysis.endpoint_count = len(analysis.endpoints)
    analysis.pii_endpoint_count = sum(1 for e in analysis.endpoints if e.has_pii)
    analysis.financial_endpoint_count = sum(1 for e in analysis.endpoints if e.has_financial)
    analysis.critical_count = sum(1 for e in analysis.endpoints if e.risk_level == "critical")
    analysis.high_count = sum(1 for e in analysis.endpoints if e.risk_level == "high")

    return analysis
