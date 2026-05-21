"""Task-level structured-output contracts for AI Gateway."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.models import AIRequest, TaskType


class SchemaContractError(RuntimeError):
    """Raised when a structured-output contract is violated at the gateway boundary."""

    def __init__(self, *, kind: str, task_type: str, detail: str):
        self.kind = kind
        self.task_type = task_type
        self.detail = detail
        super().__init__(f"{kind}:{task_type}:{detail}")


class _ActorRole(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str
    description: str | None = None
    permissions: list[str] = Field(default_factory=list)


class _AcceptanceCriterion(BaseModel):
    id: str
    given: str
    when: str
    then: str
    priority: int = Field(3, ge=1, le=5)


class _ComplianceRef(BaseModel):
    framework: str
    article: str
    note: str | None = None


class AnalyzeDocumentContract(BaseModel):
    model_config = ConfigDict(extra="allow")
    domain: str
    feature_area: str
    title: str
    summary: str = ""
    actors: list[_ActorRole] = Field(default_factory=list)
    goals: list[str] = Field(default_factory=list)
    acceptance_criteria: list[_AcceptanceCriterion] = Field(default_factory=list)
    data_requirements: dict[str, Any] = Field(default_factory=dict)
    precondition_apis: list[str] = Field(default_factory=list)
    risk_level: str = Field(pattern=r"^(low|medium|high|critical)$")
    risk_factors: list[str] = Field(default_factory=list)
    compliance_refs: list[_ComplianceRef] = Field(default_factory=list)


class _EndpointSpec(BaseModel):
    method: str
    path: str


class _Assertion(BaseModel):
    type: str
    expected: Any = None
    operator: str | None = None
    path: str | None = None
    max_ms: int | None = None


class _GeneratedTestCase(BaseModel):
    id: str = Field(min_length=3, max_length=32)
    title: str = Field(min_length=5, max_length=200)
    description: str = ""
    test_type: str = Field(pattern=r"^(positive|negative|boundary|security|compliance|performance)$")
    priority: str = Field(pattern=r"^P[0-3]$")
    endpoint: _EndpointSpec | None = None
    owasp_category: str | None = None
    regulation: str | None = None
    assertions: list[_Assertion] = Field(default_factory=list)
    ai_reasoning: str | None = None


class GenerateTestCasesContract(BaseModel):
    test_cases: list[_GeneratedTestCase] = Field(min_length=1)


class _RegressionSet(BaseModel):
    name: str
    description: str
    scenario_ids: list[str] = Field(min_length=1)
    priority: str = Field(pattern=r"^(critical|high|medium|low)$")


class SuggestRegressionContract(BaseModel):
    sets: list[_RegressionSet] = Field(min_length=1)


class _FixSuggestion(BaseModel):
    description: str
    code_change: str | None = None


class DebugTestContract(BaseModel):
    root_cause: str
    error_category: str = Field(pattern=r"^(locator|timing|data|env|flaky|logic)$")
    severity: str = Field(pattern=r"^(blocker|critical|major|minor)$")
    fix_suggestions: list[_FixSuggestion] = Field(min_length=1)
    prevention: str


_CONTRACTS: dict[TaskType, type[BaseModel]] = {
    TaskType.ANALYZE_DOCUMENT: AnalyzeDocumentContract,
    TaskType.GENERATE_TEST_CASES: GenerateTestCasesContract,
    TaskType.SUGGEST_REGRESSION: SuggestRegressionContract,
    TaskType.DEBUG_TEST: DebugTestContract,
}


def validate_structured_contract(request: AIRequest, payload: dict[str, Any] | list[Any]) -> dict[str, Any] | list[Any]:
    """Validate structured JSON payloads for high-risk tasks at the gateway boundary."""
    contract = _CONTRACTS.get(request.task_type)
    if contract is None:
        if request.json_mode:
            raise SchemaContractError(
                kind="missing_contract",
                task_type=request.task_type.value,
                detail="Gateway contract is not defined for this JSON task.",
            )
        return payload
    if request.schema_version is None:
        raise SchemaContractError(
            kind="missing_contract",
            task_type=request.task_type.value,
            detail="schema_version is required for structured gateway tasks.",
        )
    try:
        return contract.model_validate(payload).model_dump()
    except ValidationError as exc:
        raise SchemaContractError(
            kind="schema_mismatch",
            task_type=request.task_type.value,
            detail=str(exc),
        ) from exc
