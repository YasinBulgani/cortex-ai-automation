"""Pydantic schemas for advanced synthetic data generation (KDE + CTGAN)."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── KDE Fit ─────────────────────────────────────────────────────────────

class KDEFitRequest(BaseModel):
    data: List[Dict[str, Any]] = Field(..., description="Sample data rows")
    columns: Optional[List[str]] = Field(
        None, description="Columns to fit; None = all columns"
    )


# ── Generate ────────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    count: int = Field(default=100, ge=1, le=100000, description="Number of records")
    seed: Optional[int] = Field(None, description="Random seed for reproducibility")
    generator_type: str = Field(
        default="kde",
        description="Generator type: 'kde' or 'ctgan'",
    )
    conditions: Optional[Dict[str, Any]] = Field(
        None, description="Conditional generation constraints",
    )
    sample_data: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="Sample data to fit before generating (if no prior fit)",
    )


class SyntheticRecord(BaseModel):
    """A single synthetic record — dict-like output."""
    data: Dict[str, Any] = Field(default_factory=dict)


class GenerateResponse(BaseModel):
    records: List[Dict[str, Any]] = Field(default_factory=list)
    quality_metrics: Optional[Dict[str, Any]] = None
    generator_type: str = "kde"
    duration_ms: float = 0.0
    record_count: int = 0


# ── Banking Dataset ─────────────────────────────────────────────────────

class BankingDatasetRequest(BaseModel):
    customer_count: int = Field(default=100, ge=1, le=100000)
    accounts_per_customer: int = Field(default=2, ge=1, le=20)
    transactions_per_account: int = Field(default=10, ge=0, le=1000)
    days: int = Field(default=90, ge=1, le=3650, description="Transaction time span in days")
    generator_type: str = Field(default="kde", description="'kde' or 'ctgan'")
    segment_distribution: Optional[Dict[str, float]] = Field(
        None,
        description="Customer segment weights, e.g. {'bireysel': 0.6, 'ticari': 0.2}",
    )


class FullDatasetStats(BaseModel):
    customer_count: int = 0
    account_count: int = 0
    transaction_count: int = 0
    total_volume_try: float = 0.0
    avg_balance: float = 0.0
    segments: Dict[str, int] = Field(default_factory=dict)
    account_types: Dict[str, int] = Field(default_factory=dict)
    transaction_types: Dict[str, int] = Field(default_factory=dict)


class BankingDatasetResponse(BaseModel):
    customers: List[Dict[str, Any]] = Field(default_factory=list)
    accounts: List[Dict[str, Any]] = Field(default_factory=list)
    transactions: List[Dict[str, Any]] = Field(default_factory=list)
    fk_integrity: bool = True
    stats: FullDatasetStats = Field(default_factory=FullDatasetStats)
    duration_ms: float = 0.0


# ── Quality ─────────────────────────────────────────────────────────────

class QualityCheckRequest(BaseModel):
    original: List[Dict[str, Any]] = Field(..., description="Original dataset")
    synthetic: List[Dict[str, Any]] = Field(..., description="Synthetic dataset")


class QualityMetrics(BaseModel):
    column_stats: Dict[str, Any] = Field(default_factory=dict)
    correlation_preservation: float = 0.0
    distribution_similarity: Dict[str, float] = Field(default_factory=dict)
    overall_score: float = 0.0


# ── Privacy Risk ────────────────────────────────────────────────────────

class PrivacyRiskRequest(BaseModel):
    original: List[Dict[str, Any]] = Field(..., description="Original dataset")
    synthetic: List[Dict[str, Any]] = Field(..., description="Synthetic dataset")


class PrivacyRiskResponse(BaseModel):
    risk_score: float = Field(0.0, ge=0.0, le=1.0)
    vulnerable_columns: List[str] = Field(default_factory=list)
    recommendation: str = ""


# ── Generator Info ──────────────────────────────────────────────────────

class GeneratorInfo(BaseModel):
    id: str
    name: str
    available: bool
    description: str


class GeneratorsListResponse(BaseModel):
    generators: List[GeneratorInfo] = Field(default_factory=list)
