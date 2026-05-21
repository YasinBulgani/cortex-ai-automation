"""Intent Graph — Analyst çıktısı."""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ActorRole(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str
    description: str | None = None
    permissions: list[str] = Field(default_factory=list)


class ComplianceRef(BaseModel):
    framework: str
    article: str
    note: str | None = None


class AcceptanceCriterion(BaseModel):
    id: str
    given: str
    when: str
    then: str
    priority: int = Field(3, ge=1, le=5)


class IntentGraph(BaseModel):
    model_config = ConfigDict(extra="allow", validate_assignment=True)

    domain: str
    feature_area: str
    title: str
    summary: str = ""

    actors: list[ActorRole] = Field(default_factory=list)
    goals: list[str] = Field(default_factory=list)
    acceptance_criteria: list[AcceptanceCriterion] = Field(default_factory=list)

    data_requirements: dict[str, Any] = Field(default_factory=dict)
    precondition_apis: list[str] = Field(default_factory=list)

    risk_level: RiskLevel = RiskLevel.MEDIUM
    risk_factors: list[str] = Field(default_factory=list)
    compliance_refs: list[ComplianceRef] = Field(default_factory=list)

    language: str = "tr-TR"
    source_notes: str = ""

    @field_validator("domain")
    @classmethod
    def _norm_domain(cls, v: str) -> str:
        return v.strip().lower().replace(" ", "_")

    @field_validator("feature_area")
    @classmethod
    def _norm_area(cls, v: str) -> str:
        return v.strip().lower().replace(" ", "_")

    @property
    def is_critical(self) -> bool:
        return self.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)

    def to_state_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "feature_area": self.feature_area,
            "actors": [a.name for a in self.actors],
            "goals": list(self.goals),
            "acceptance_criteria": [
                f"{ac.given}; {ac.when}; {ac.then}" for ac in self.acceptance_criteria
            ],
            "data_requirements": self.data_requirements,
            "risk_level": self.risk_level.value,
            "compliance_refs": [
                f"{r.framework}.{r.article}" for r in self.compliance_refs
            ],
        }
