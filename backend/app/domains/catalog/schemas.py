from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, model_validator
from typing_extensions import Self

from app.domains.catalog.schema_v1 import parse_and_validate_snapshot


class DatasetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None


class DatasetOut(BaseModel):
    id: str
    name: str
    description: Optional[str]
    created_at: object
    updated_at: object


class DatasetVersionCreate(BaseModel):
    """İlk sürüm + şema anlık görüntüsü oluşturur (v1 sözleşmesi)."""

    snapshot: Dict[str, Any] = Field(default_factory=dict)
    profile: Optional[Dict[str, Any]] = None
    pii_flags: Optional[Dict[str, Any]] = None

    @model_validator(mode="after")
    def validate_snapshot_v1(self) -> Self:
        if not self.snapshot:
            raise ValueError("snapshot boş olamaz; version ve fields gerekli")
        self.snapshot = parse_and_validate_snapshot(self.snapshot)
        return self


class DatasetVersionOut(BaseModel):
    id: str
    dataset_id: str
    version: int
    status: str
    created_at: object


class SchemaSnapshotOut(BaseModel):
    id: str
    dataset_version_id: str
    snapshot: Dict[str, Any]
    profile: Optional[Dict[str, Any]]
    pii_flags: Optional[Dict[str, Any]]
