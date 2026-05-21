"""Pydantic schemas for differential privacy endpoints."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Privatize ────────────────────────────────────────────────────────

class PrivatizeRequest(BaseModel):
    data: List[Dict[str, Any]] = Field(..., description="Dataset to privatize")
    column_config: Dict[str, Dict[str, Any]] = Field(
        ...,
        description=(
            "Per-column privacy config. "
            "Example: {'bakiye': {'type': 'numeric', 'sensitivity': 1000000, 'mechanism': 'laplace'}}"
        ),
    )
    epsilon: float = Field(
        default=1.0, gt=0, le=100,
        description="Privacy budget (lower = more private, 0.1-10 typical)",
    )
    delta: float = Field(
        default=1e-5, gt=0, lt=1,
        description="Probability of privacy breach",
    )


class PrivatizeResponse(BaseModel):
    privatized_data: List[Dict[str, Any]] = Field(default_factory=list)
    columns_processed: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    budget_consumed: float = 0.0
    remaining_budget: float = 0.0


# ── k-Anonymity ─────────────────────────────────────────────────────

class KAnonymityRequest(BaseModel):
    data: List[Dict[str, Any]] = Field(..., description="Dataset to check")
    quasi_identifiers: List[str] = Field(
        ..., description="Quasi-identifier column names"
    )
    k: int = Field(default=5, ge=1, description="Minimum group size")


class KAnonymityResponse(BaseModel):
    satisfies_k: bool = False
    k_achieved: int = 0
    violating_groups: int = 0
    total_groups: int = 0


# ── l-Diversity ──────────────────────────────────────────────────────

class LDiversityRequest(BaseModel):
    data: List[Dict[str, Any]] = Field(..., description="Dataset to check")
    quasi_identifiers: List[str] = Field(
        ..., description="Quasi-identifier column names"
    )
    sensitive_attr: str = Field(..., description="Sensitive attribute column name")
    l: int = Field(default=3, ge=1, description="Minimum distinct sensitive values per group")


class LDiversityResponse(BaseModel):
    satisfies_l: bool = False
    l_achieved: int = 0
    violations: int = 0


# ── Re-identification Risk ──────────────────────────────────────────

class ReidentificationRequest(BaseModel):
    original: List[Dict[str, Any]] = Field(..., description="Original dataset")
    synthetic: List[Dict[str, Any]] = Field(..., description="Synthetic dataset")
    quasi_identifiers: List[str] = Field(
        ..., description="Quasi-identifier column names"
    )


class ReidentificationResponse(BaseModel):
    overall_risk: float = Field(0.0, ge=0.0, le=1.0)
    max_risk: float = Field(0.0, ge=0.0, le=1.0)
    risky_records_pct: float = 0.0
    recommendation: str = ""


# ── Privacy Report ──────────────────────────────────────────────────

class PrivacyReportRequest(BaseModel):
    data: List[Dict[str, Any]] = Field(..., description="Dataset to evaluate")
    original: Optional[List[Dict[str, Any]]] = Field(
        None, description="Original dataset for re-identification risk"
    )
    config: Optional[Dict[str, Dict[str, Any]]] = Field(
        None, description="Privacy config that was applied"
    )
    epsilon: float = Field(
        default=1.0, gt=0, le=100,
        description="Epsilon value used or planned",
    )


class PrivacyReportResponse(BaseModel):
    epsilon: float = 1.0
    delta: float = 1e-5
    budget_spent: float = 0.0
    k_anonymity: Dict[str, Any] = Field(default_factory=dict)
    l_diversity: Optional[Dict[str, Any]] = None
    reidentification_risk: Optional[float] = None
    pii_columns_detected: List[str] = Field(default_factory=list)
    pii_columns_protected: List[str] = Field(default_factory=list)
    kvkk_compliant: bool = False
    kvkk_issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


# ── Config Suggestion ────────────────────────────────────────────────

class PrivacyConfigSuggestion(BaseModel):
    column: str
    mechanism: str
    sensitivity: Optional[float] = None
    reason: str = ""


class SuggestConfigRequest(BaseModel):
    data: List[Dict[str, Any]] = Field(..., description="Sample data rows")
    epsilon: float = Field(default=1.0, gt=0, le=100)


class SuggestConfigResponse(BaseModel):
    suggestions: List[PrivacyConfigSuggestion] = Field(default_factory=list)
    detected_pii: List[str] = Field(default_factory=list)
    column_config: Dict[str, Dict[str, Any]] = Field(
        default_factory=dict,
        description="Ready-to-use column config for /privacy/privatize",
    )


# ── TCKN Validation ─────────────────────────────────────────────────

class TCKNValidateRequest(BaseModel):
    tckn: str = Field(..., min_length=11, max_length=11, description="Turkish ID number")


class TCKNValidateResponse(BaseModel):
    valid: bool = False
    tckn: str = ""
    message: str = ""
