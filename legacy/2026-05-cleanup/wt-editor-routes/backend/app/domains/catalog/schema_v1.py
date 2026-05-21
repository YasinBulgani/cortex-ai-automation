"""Şema anlık görüntüsü sözleşmesi v1 (doğrulama + normalize JSON çıktı)."""

from __future__ import annotations

import re
from enum import Enum
from typing import Any, Dict, List

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator


class FieldType(str, Enum):
    string = "string"
    integer = "integer"
    float = "float"
    boolean = "boolean"
    date = "date"


_NAME_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


class FieldSpec(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    type: FieldType
    nullable: bool = False

    @field_validator("name")
    @classmethod
    def name_identifier(cls, v: str) -> str:
        if not _NAME_RE.match(v):
            raise ValueError(
                "Geçersiz alan adı; harf veya alt çizgi ile başlamalı, "
                "yalnızca harf, rakam ve alt çizgi kullanılabilir"
            )
        return v


class SchemaSnapshotV1(BaseModel):
    version: int = 1
    fields: List[FieldSpec] = Field(min_length=1)

    @field_validator("version")
    @classmethod
    def version_must_be_one(cls, v: int) -> int:
        if v != 1:
            raise ValueError("snapshot.version şu an yalnızca 1 olabilir")
        return v

    @model_validator(mode="after")
    def unique_names(self) -> SchemaSnapshotV1:
        names = [f.name for f in self.fields]
        if len(names) != len(set(names)):
            raise ValueError("Alan adları tekrarlanamaz")
        return self


def _validation_errors_to_message(err: ValidationError) -> str:
    parts: List[str] = []
    for e in err.errors():
        loc = ".".join(str(x) for x in e.get("loc", ()) if x != "snapshot")
        msg = e.get("msg", "")
        if loc:
            parts.append(f"{loc}: {msg}")
        else:
            parts.append(msg)
    return "Şema geçersiz: " + ("; ".join(parts) if parts else str(err))


def parse_and_validate_snapshot(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ham dict'i v1 sözleşmesine göre doğrular.
    Başarıda JSONB için uygun düz dict döner (tipler JSON-serializable).
    """
    try:
        snap = SchemaSnapshotV1.model_validate(raw)
    except ValidationError as e:
        raise ValueError(_validation_errors_to_message(e)) from e
    return snap.model_dump()
