"""
Pydantic şemaları paketi.

Tüm API request/response şemaları buradan import edilir.
"""

from app.schemas.dataset import (
    # Dataset şemaları
    DatasetCreate,
    DatasetResponse,
    DatasetDetailResponse,
    DatasetListResponse,
    # ColumnProfile şemaları
    ColumnProfileResponse,
    # Rule şemaları
    RuleResponse,
    RuleListResponse,
    # Relationship şemaları
    RelationshipResponse,
    # Generation şemaları
    GenerationRequest,
    GenerationResponse,
    # Senaryo ve analiz şemaları
    ScenarioRequest,
    AnalysisResponse,
)

__all__ = [
    "DatasetCreate",
    "DatasetResponse",
    "DatasetDetailResponse",
    "DatasetListResponse",
    "ColumnProfileResponse",
    "RuleResponse",
    "RuleListResponse",
    "RelationshipResponse",
    "GenerationRequest",
    "GenerationResponse",
    "ScenarioRequest",
    "AnalysisResponse",
]
