"""DSL Sözlüğü için Pydantic şemaları.

Kaynak YAML formatı: packages/dsl/schema/action.schema.json (JSON Schema draft-07).
Bu modeller onun Pydantic V2 karşılığıdır.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class DslParameter(BaseModel):
    name: str
    type: str
    description: Optional[str] = None
    required: bool = True
    default: Optional[Any] = None
    examples: Optional[List[Any]] = None


class DslImplementation(BaseModel):
    """Tek bir dilde cümleciğin kod konumu ve pattern'i."""

    source_file: str
    # Python / TypeScript
    module: Optional[str] = None
    function: Optional[str] = None
    # Java
    cls: Optional[str] = Field(default=None, alias="class")
    method: Optional[str] = None
    # Opsiyonel ham pattern (auto-extracted YAML'ler için)
    pattern: Optional[str] = None

    model_config = {"populate_by_name": True}


class DslDeprecation(BaseModel):
    replacement: str
    since: Optional[str] = None
    reason: Optional[str] = None


class DslAction(BaseModel):
    """Katalogdaki tek bir cümlecik (atomik test eylemi)."""

    id: str
    category: str
    description: str
    aliases: Dict[str, List[str]] = Field(default_factory=dict)
    parameters: List[DslParameter] = Field(default_factory=list)
    implementations: Dict[str, DslImplementation] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    since: Optional[str] = None
    deprecated: Optional[DslDeprecation | bool] = None
    examples: List[str] = Field(default_factory=list)
    notes: Optional[str] = None
    # Katalog dosyasından gelen izleme verisi (disk -> bellek tarafından set edilir)
    source_yaml: Optional[str] = None


class DslCategory(BaseModel):
    """Üst / alt kategori özeti (UI sol panelde listelemek için)."""

    id: str
    count: int
    top_level: str


class DslStats(BaseModel):
    """Katalog genel istatistikleri."""

    total: int
    unique_ids: int
    by_top_category: Dict[str, int] = Field(default_factory=dict)
    by_full_category: Dict[str, int] = Field(default_factory=dict)
    by_implementation: Dict[str, int] = Field(default_factory=dict)
    by_source_file: Dict[str, int] = Field(default_factory=dict)
    top_tags: List[Dict[str, Any]] = Field(default_factory=list)
    aliases: Dict[str, int] = Field(default_factory=dict)
    loaded_at: Optional[str] = None


class DslActionListResponse(BaseModel):
    items: List[DslAction]
    total: int
    page: int
    page_size: int


class DslSearchHit(BaseModel):
    action: DslAction
    matched_language: str
    matched_alias: str
    # AI / hybrid arama için ekstra sinyaller — lexical aramada None kalır
    score: Optional[float] = None
    source: Optional[str] = None  # "lexical" | "semantic" | "hybrid" | "llm_rerank"
    reason: Optional[str] = None  # LLM rerank tarafından üretilen kısa TR gerekçe


class DslSearchResponse(BaseModel):
    query: str
    total: int
    items: List[DslSearchHit]
    # Aramanın hangi modla yapıldığı (UI için) — "lexical" | "semantic" | "hybrid"
    mode: Optional[str] = None
    # Index metadatası (debug)
    index_info: Optional[Dict[str, Any]] = None


class DslReloadResponse(BaseModel):
    status: str
    total_before: int
    total_after: int
    loaded_at: str
