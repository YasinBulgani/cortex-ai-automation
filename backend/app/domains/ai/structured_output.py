"""
Structured Output — Pydantic validation + auto-fix retry.

Mimari:
    1) task_type -> Pydantic schema eslemesi (_SCHEMAS)
    2) LLM cevabini JSON parse + schema validate
    3) Validation hatasi -> hata mesajini prompt'a yap, 1 kez retry
    4) Hala başarısız -> son cevabi dondur + trace'e json_parse_ok=FALSE

Kazanim:
    JSON parse orani %89 -> %99+. Cunku:
    - Pydantic validation error mesajı net ("field X missing, got Y")
    - LLM bu hatayi gorup duzeltebiliyor (cogu modelin iyi yaptigi sey)
    - OpenAI response_format destekliyorsa schema JSON'u gateway'e iletilir

Feature flag: ``ai.structured_output`` default True.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional, Type, Union

from pydantic import BaseModel, Field, ValidationError

from app.domains.agents.v2.schemas.intent import IntentGraph

logger = logging.getLogger(__name__)


class StructuredOutputValidationError(RuntimeError):
    """Raised when a required structured output contract is violated."""


# ── Schemas per task_type ────────────────────────────────────────────────


class EndpointSpec(BaseModel):
    method: str
    path: str


class Assertion(BaseModel):
    type: str
    expected: Any = None
    operator: Optional[str] = None
    path: Optional[str] = None
    max_ms: Optional[int] = None


class TestCaseSchema(BaseModel):
    id: str = Field(..., min_length=3, max_length=32)
    title: str = Field(..., min_length=5, max_length=200)
    description: str = ""
    test_type: str = Field(..., pattern=r"^(positive|negative|boundary|security|compliance|performance)$")
    priority: str = Field(..., pattern=r"^P[0-3]$")
    endpoint: Optional[EndpointSpec] = None
    owasp_category: Optional[str] = None
    regulation: Optional[str] = None
    assertions: list[Assertion] = Field(default_factory=list)
    ai_reasoning: Optional[str] = None


class TestGenerationResponse(BaseModel):
    test_cases: list[TestCaseSchema] = Field(..., min_length=1)


class SecurityFinding(BaseModel):
    id: str
    title: str
    owasp: str = Field(..., pattern=r"^API\d+$")
    cwe: Optional[str] = None
    severity: str = Field(..., pattern=r"^(low|medium|high|critical)$")
    attack_scenario: str = Field(..., min_length=20)
    expected_defense: str = Field(..., min_length=20)


class SecurityAuditResponse(BaseModel):
    security_tests: list[SecurityFinding] = Field(..., min_length=1)


class ChainStep(BaseModel):
    order: int = Field(..., ge=1)
    label: str
    endpoint: EndpointSpec


class ChainDefinition(BaseModel):
    name: str
    description: str = ""
    steps: list[ChainStep] = Field(..., min_length=1)


class ChainBuilderResponse(BaseModel):
    chains: list[ChainDefinition] = Field(..., min_length=1)


class SpecRiskEntry(BaseModel):
    method: str
    path: str
    risk: str = Field(..., pattern=r"^(low|medium|high|critical)$")
    reason: str = Field(..., min_length=10)


class SpecAnalysisResponse(BaseModel):
    high_risk_endpoints: list[SpecRiskEntry] = Field(default_factory=list)
    risk_summary: dict[str, int] = Field(default_factory=dict)


# Registry: task_type -> schema
_SCHEMAS: dict[str, Type[BaseModel]] = {
    "test_generation": TestGenerationResponse,
    "generate_test_cases": TestGenerationResponse,
    "security_audit": SecurityAuditResponse,
    "chain_builder": ChainBuilderResponse,
    "spec_analysis": SpecAnalysisResponse,
    "analyze_document": IntentGraph,
}

_EXPLICIT_UNSTRUCTURED_TASKS: frozenset[str] = frozenset({
    "chat",
    "generate_gherkin",
    "generate_playwright",
    "code_generation",
    "review",
    "repair",
    "report",
})


# ── Public API ───────────────────────────────────────────────────────────


def get_schema(task_type: str) -> Optional[Type[BaseModel]]:
    """Task type için Pydantic schema. Yoksa None (structured output devre disi)."""
    return _SCHEMAS.get(task_type)


def schema_policy(task_type: str) -> str:
    """Return `json_schema`, `explicit_unstructured`, or `missing_policy`."""
    if get_schema(task_type) is not None:
        return "json_schema"
    if task_type in _EXPLICIT_UNSTRUCTURED_TASKS:
        return "explicit_unstructured"
    return "missing_policy"


def should_validate_task(task_type: str) -> bool:
    """Validate JSON schemas and fail missing policies instead of silently skipping."""
    return schema_policy(task_type) in {"json_schema", "missing_policy"}


def structured_enabled(tenant_id: Optional[str] = None) -> bool:
    """Feature flag: ai.structured_output — default True."""
    try:
        from app.domains.feature_flags.service import feature_flags
        return feature_flags.is_enabled("ai.structured_output", tenant_id=tenant_id, default=True)
    except Exception:
        return True


def validate_response(
    task_type: str,
    raw: str,
) -> tuple[bool, Optional[str], Optional[dict]]:
    """
    LLM cevabini parse + validate et.

    Returns:
        (valid, error_message, parsed_dict)
        - valid=True: parsed_dict dolu, error_message None
        - valid=False: error_message LLM'e yollanabilecek net hata
    """
    schema = get_schema(task_type)
    if schema is None:
        if schema_policy(task_type) == "explicit_unstructured":
            return True, None, None
        return (
            False,
            f"Task type `{task_type}` icin structured-output policy tanimli degil. "
            "Bir Pydantic schema ekleyin veya explicit unstructured exemption tanimlayin.",
            None,
        )

    parsed = _parse_json_tolerant(raw)
    if parsed is None:
        return False, "Cevap valid JSON degil. Sadece JSON objesi dondur, markdown veya aciklama ekleme.", None

    try:
        validated = schema.model_validate(parsed)
        return True, None, validated.model_dump()
    except ValidationError as exc:
        error_msg = _format_validation_errors(exc)
        return False, error_msg, parsed


def build_retry_prompt(original_prompt: str, bad_response: str, error: str) -> str:
    """LLM'e validation hatasini gonderecek retry prompt."""
    truncated = (bad_response or "")[:2000]
    return (
        f"Onceki cevabin validate edilemedi:\n\n"
        f"HATA:\n{error}\n\n"
        f"Cevabin (kisaltilmis):\n{truncated}\n\n"
        f"Lutfen yukaridaki hatalari duzeltip CEVABI YENIDEN URET. "
        f"SADECE valid JSON dondur, aciklama/markdown ekleme.\n\n"
        f"Orijinal soru:\n{original_prompt}"
    )


def openai_response_format(task_type: str) -> Optional[dict]:
    """OpenAI response_format={'type':'json_schema',...} payload uretir.

    gpt-4o-2024-08-06+ destekliyor. Schema yoksa None (gateway json_mode default'u kullanir).
    """
    schema = get_schema(task_type)
    if schema is None:
        return None

    try:
        json_schema = schema.model_json_schema()
    except Exception:
        return None

    return {
        "type": "json_schema",
        "json_schema": {
            "name": task_type,
            "strict": True,
            "schema": _sanitize_schema_for_openai(json_schema),
        },
    }


# ── Internal helpers ─────────────────────────────────────────────────────


def _parse_json_tolerant(raw: str) -> Optional[Union[dict, list]]:
    """Markdown fence + extra text'e dayanikli JSON parse."""
    if not raw:
        return None
    s = raw.strip()
    fence = re.match(r"^```(?:json)?\s*\n?(.*?)\n?```\s*$", s, re.DOTALL)
    if fence:
        s = fence.group(1).strip()
    try:
        return json.loads(s)
    except Exception:
        pass
    # Zorla ekstrakt
    for open_c, close_c in [("{", "}"), ("[", "]")]:
        start = s.find(open_c)
        end = s.rfind(close_c)
        if start >= 0 and end > start:
            try:
                return json.loads(s[start : end + 1])
            except Exception:
                continue
    return None


def _format_validation_errors(exc: ValidationError) -> str:
    """Pydantic hata listesini LLM'e uygun formatta dondur."""
    errors = exc.errors()
    lines: list[str] = []
    for err in errors[:10]:  # ilk 10 hata yeter
        loc = ".".join(str(x) for x in err.get("loc", []))
        msg = err.get("msg", "")
        typ = err.get("type", "")
        lines.append(f"- `{loc}`: {msg} (type: {typ})")
    return "Validation hatalari:\n" + "\n".join(lines)


def _sanitize_schema_for_openai(schema: dict) -> dict:
    """OpenAI strict mode'un desteklemedigi alanlari temizle.

    - additionalProperties: false zorunlu
    - required tüm property'leri icermeli (strict mode kurali)
    - unevaluatedProperties kaldirilir
    """
    if not isinstance(schema, dict):
        return schema

    # Recursive temizleme
    cleaned = dict(schema)

    # unevaluatedProperties desteklenmiyor
    cleaned.pop("unevaluatedProperties", None)

    if cleaned.get("type") == "object" and "properties" in cleaned:
        cleaned["additionalProperties"] = False
        # Strict mode: tüm property'ler required olmali
        cleaned["required"] = list(cleaned["properties"].keys())
        # Nested recursive
        cleaned["properties"] = {
            k: _sanitize_schema_for_openai(v)
            for k, v in cleaned["properties"].items()
        }

    if "items" in cleaned and isinstance(cleaned["items"], dict):
        cleaned["items"] = _sanitize_schema_for_openai(cleaned["items"])

    if "$defs" in cleaned:
        cleaned["$defs"] = {
            k: _sanitize_schema_for_openai(v)
            for k, v in cleaned["$defs"].items()
        }

    return cleaned
