"""Plan catalog — single source of truth for plan limits and metadata.

Plan codes (free | starter | pro | enterprise) align with the frontend
billing page contract at apps/web/app/(dashboard)/admin/billing/page.tsx.

Limits use ``-1`` to denote unlimited.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional


UNLIMITED = -1


@dataclass(frozen=True)
class PlanLimits:
    project_count: int
    scenario_count: int
    run_count_month: int
    team_size: int
    storage_mb: int
    ai_token_spend_usd: float


@dataclass(frozen=True)
class Plan:
    code: str
    label: str
    monthly_price_usd: float
    limits: PlanLimits
    features: tuple[str, ...]
    is_contact_sales: bool = False

    def to_dict(self) -> dict:
        d = asdict(self)
        d["limits"] = asdict(self.limits)
        return d


PLAN_CATALOG: dict[str, Plan] = {
    "free": Plan(
        code="free",
        label="Ücretsiz",
        monthly_price_usd=0.0,
        limits=PlanLimits(
            project_count=5,
            scenario_count=50,
            run_count_month=100,
            team_size=2,
            storage_mb=1024,
            ai_token_spend_usd=2.0,
        ),
        features=("5 proje", "100 koşu/ay", "2 kullanıcı", "1 GB depolama"),
    ),
    "starter": Plan(
        code="starter",
        label="Başlangıç",
        monthly_price_usd=49.0,
        limits=PlanLimits(
            project_count=25,
            scenario_count=500,
            run_count_month=1000,
            team_size=10,
            storage_mb=10 * 1024,
            ai_token_spend_usd=20.0,
        ),
        features=(
            "25 proje",
            "1000 koşu/ay",
            "10 kullanıcı",
            "10 GB depolama",
            "AI analiz",
        ),
    ),
    "pro": Plan(
        code="pro",
        label="Profesyonel",
        monthly_price_usd=199.0,
        limits=PlanLimits(
            project_count=UNLIMITED,
            scenario_count=UNLIMITED,
            run_count_month=10_000,
            team_size=25,
            storage_mb=50 * 1024,
            ai_token_spend_usd=200.0,
        ),
        features=(
            "Sınırsız proje",
            "10.000 koşu/ay",
            "25 kullanıcı",
            "50 GB depolama",
            "Öncelikli destek",
            "AI analiz + LLM-as-Judge",
        ),
    ),
    "enterprise": Plan(
        code="enterprise",
        label="Kurumsal",
        monthly_price_usd=0.0,
        limits=PlanLimits(
            project_count=UNLIMITED,
            scenario_count=UNLIMITED,
            run_count_month=UNLIMITED,
            team_size=UNLIMITED,
            storage_mb=UNLIMITED,
            ai_token_spend_usd=UNLIMITED,
        ),
        features=(
            "Sınırsız her şey",
            "On-prem / VPC",
            "SSO / LDAP",
            "SLA garantisi",
            "Dedicated AI",
        ),
        is_contact_sales=True,
    ),
}


DEFAULT_PLAN_CODE = "free"


def get_plan(code: Optional[str]) -> Plan:
    """Return the plan for a code, falling back to free for unknown codes."""
    if not code:
        return PLAN_CATALOG[DEFAULT_PLAN_CODE]
    return PLAN_CATALOG.get(code, PLAN_CATALOG[DEFAULT_PLAN_CODE])


def is_unlimited(value: float | int) -> bool:
    return value == UNLIMITED


def within_limit(used: float | int, limit: float | int) -> bool:
    """True if usage is below the configured limit, or limit is unlimited."""
    if is_unlimited(limit):
        return True
    return used < limit


def list_plans() -> list[dict]:
    return [p.to_dict() for p in PLAN_CATALOG.values()]
