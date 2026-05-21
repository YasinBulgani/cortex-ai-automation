"""
Export Template Servisi.

Önceden tanımlı veya kullanıcı tarafından oluşturulan şablonlar
ile sentetik veri export'u sağlar.

Özellikler:
  - ExportTemplate SQLAlchemy modeli
  - Şablon CRUD (oluştur, listele, güncelle, sil)
  - Şablona göre export: CSV, JSON, SQL, Excel
  - POST /api/templates — Yeni şablon
  - GET /api/templates — Şablon listesi
  - PUT /api/templates/{id} — Şablon güncelle
  - DELETE /api/templates/{id} — Şablon sil
  - POST /api/templates/{id}/export — Şablonla veri export et
"""

import csv
import enum
import io
import json
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    JSON,
    String,
    Text,
    func,
    desc,
)
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.models.database import Base, get_db


# ═══════════════════════════════════════════════════════════════════════
# Enum ve Model Tanımları
# ═══════════════════════════════════════════════════════════════════════


class ExportFormat(str, enum.Enum):
    """Desteklenen export formatları."""
    CSV = "csv"
    JSON = "json"
    SQL_INSERT = "sql_insert"
    SQL_COPY = "sql_copy"
    JSONL = "jsonl"          # JSON Lines
    PARQUET_SCHEMA = "parquet_schema"  # Parquet şema tanımı


class TemplateStatus(str, enum.Enum):
    """Şablon durumu."""
    ACTIVE = "active"
    DRAFT = "draft"
    ARCHIVED = "archived"


class ExportTemplate(Base):
    """Export şablonu veritabanı modeli."""

    __tablename__ = "export_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default=TemplateStatus.ACTIVE.value
    )

    # ── Şablon yapılandırması ──
    format: Mapped[str] = mapped_column(
        String(30), default=ExportFormat.CSV.value
    )
    # Hangi kolonlar dahil (boş = hepsi)
    include_columns: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    # Kolon yeniden adlandırma haritası
    column_mapping: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # Filtre koşulları (SQL WHERE benzeri)
    filters: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # Sıralama
    order_by: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    # Limit
    row_limit: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # ── Format seçenekleri ──
    csv_delimiter: Mapped[str] = mapped_column(String(5), default=",")
    csv_encoding: Mapped[str] = mapped_column(String(20), default="utf-8")
    json_indent: Mapped[int] = mapped_column(Integer, default=2)
    sql_table_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    sql_batch_size: Mapped[int] = mapped_column(Integer, default=100)
    include_headers: Mapped[bool] = mapped_column(Boolean, default=True)

    # ── İstatistikler ──
    total_exports: Mapped[int] = mapped_column(Integer, default=0)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    # ── Zaman damgaları ──
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"<ExportTemplate(id={self.id}, name='{self.name}', "
            f"format={self.format})>"
        )


# ═══════════════════════════════════════════════════════════════════════
# Pydantic Şemaları
# ═══════════════════════════════════════════════════════════════════════


class TemplateCreateRequest(BaseModel):
    """Şablon oluşturma isteği."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    format: str = Field(ExportFormat.CSV.value, description="Export formatı")
    include_columns: Optional[list[str]] = None
    column_mapping: Optional[dict[str, str]] = None
    filters: Optional[dict[str, Any]] = None
    order_by: Optional[list[str]] = None
    row_limit: Optional[int] = Field(None, ge=1)
    csv_delimiter: str = Field(",", max_length=5)
    csv_encoding: str = Field("utf-8", max_length=20)
    json_indent: int = Field(2, ge=0, le=8)
    sql_table_name: Optional[str] = None
    sql_batch_size: int = Field(100, ge=1, le=10000)
    include_headers: bool = True


class TemplateUpdateRequest(BaseModel):
    """Şablon güncelleme isteği."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    format: Optional[str] = None
    include_columns: Optional[list[str]] = None
    column_mapping: Optional[dict[str, str]] = None
    filters: Optional[dict[str, Any]] = None
    order_by: Optional[list[str]] = None
    row_limit: Optional[int] = None
    status: Optional[str] = None


class TemplateResponse(BaseModel):
    """Şablon yanıt modeli."""
    id: int
    name: str
    description: Optional[str] = None
    format: str
    status: str
    include_columns: Optional[list[str]] = None
    column_mapping: Optional[dict[str, str]] = None
    filters: Optional[dict[str, Any]] = None
    row_limit: Optional[int] = None
    total_exports: int
    is_default: bool
    created_at: str
    updated_at: str


class TemplateListResponse(BaseModel):
    """Şablon listesi yanıtı."""
    templates: list[TemplateResponse]
    total: int


# ═══════════════════════════════════════════════════════════════════════
# Export Engine
# ═══════════════════════════════════════════════════════════════════════


class ExportEngine:
    """
    Şablon tabanlı veri export motoru.

    Tanımlanan şablona göre veriyi filtreler, dönüştürür
    ve istenen formatta export eder.
    """

    @classmethod
    def apply_template(
        cls,
        data: list[dict],
        template: ExportTemplate,
    ) -> list[dict]:
        """Şablonu veriye uygula (filtreleme, kolon seçimi, mapping)."""
        result = data

        # Filtre uygula
        if template.filters:
            result = cls._apply_filters(result, template.filters)

        # Kolon seçimi
        if template.include_columns:
            result = [
                {k: row.get(k) for k in template.include_columns if k in row}
                for row in result
            ]

        # Kolon yeniden adlandırma
        if template.column_mapping:
            result = [
                {
                    template.column_mapping.get(k, k): v
                    for k, v in row.items()
                }
                for row in result
            ]

        # Sıralama
        if template.order_by:
            for col in reversed(template.order_by):
                reverse = col.startswith("-")
                col_name = col.lstrip("-")
                result.sort(
                    key=lambda r: (r.get(col_name) is None, r.get(col_name, "")),
                    reverse=reverse,
                )

        # Limit
        if template.row_limit:
            result = result[: template.row_limit]

        return result

    @classmethod
    def _apply_filters(cls, data: list[dict], filters: dict) -> list[dict]:
        """Basit filtre mekanizması."""
        result = []
        for row in data:
            match = True
            for col, condition in filters.items():
                val = row.get(col)
                if isinstance(condition, dict):
                    op = condition.get("op", "eq")
                    target = condition.get("value")
                    if op == "eq" and val != target:
                        match = False
                    elif op == "neq" and val == target:
                        match = False
                    elif op == "gt" and (val is None or val <= target):
                        match = False
                    elif op == "lt" and (val is None or val >= target):
                        match = False
                    elif op == "in" and val not in (target or []):
                        match = False
                    elif op == "contains" and (val is None or str(target) not in str(val)):
                        match = False
                else:
                    if val != condition:
                        match = False
            if match:
                result.append(row)
        return result

    @classmethod
    def export_csv(cls, data: list[dict], template: ExportTemplate) -> str:
        """CSV formatında export et."""
        if not data:
            return ""
        output = io.StringIO()
        columns = list(data[0].keys())
        writer = csv.DictWriter(
            output,
            fieldnames=columns,
            delimiter=template.csv_delimiter,
        )
        if template.include_headers:
            writer.writeheader()
        writer.writerows(data)
        return output.getvalue()

    @classmethod
    def export_json(cls, data: list[dict], template: ExportTemplate) -> str:
        """JSON formatında export et."""
        return json.dumps(data, ensure_ascii=False, indent=template.json_indent, default=str)

    @classmethod
    def export_jsonl(cls, data: list[dict], template: ExportTemplate) -> str:
        """JSON Lines formatında export et."""
        lines = [json.dumps(row, ensure_ascii=False, default=str) for row in data]
        return "\n".join(lines) + "\n"

    @classmethod
    def export_sql_insert(cls, data: list[dict], template: ExportTemplate) -> str:
        """SQL INSERT formatında export et."""
        if not data:
            return ""
        table = template.sql_table_name or "exported_data"
        columns = list(data[0].keys())
        col_str = ", ".join(columns)
        lines = []
        batch = []

        for i, row in enumerate(data):
            values = []
            for col in columns:
                val = row.get(col)
                if val is None:
                    values.append("NULL")
                elif isinstance(val, (int, float)):
                    values.append(str(val))
                else:
                    escaped = str(val).replace("'", "''")
                    values.append(f"'{escaped}'")
            batch.append(f"({', '.join(values)})")

            if len(batch) >= template.sql_batch_size or i == len(data) - 1:
                lines.append(
                    f"INSERT INTO {table} ({col_str}) VALUES\n"
                    + ",\n".join(batch) + ";"
                )
                batch = []

        return "\n\n".join(lines) + "\n"

    @classmethod
    def export_sql_copy(cls, data: list[dict], template: ExportTemplate) -> str:
        """PostgreSQL COPY formatında export et."""
        if not data:
            return ""
        table = template.sql_table_name or "exported_data"
        columns = list(data[0].keys())
        col_str = ", ".join(columns)

        lines = [f"COPY {table} ({col_str}) FROM stdin;"]
        for row in data:
            vals = []
            for col in columns:
                val = row.get(col)
                if val is None:
                    vals.append("\\N")
                else:
                    vals.append(str(val).replace("\t", "\\t").replace("\n", "\\n"))
            lines.append("\t".join(vals))
        lines.append("\\.")

        return "\n".join(lines) + "\n"

    @classmethod
    def export(
        cls,
        data: list[dict],
        template: ExportTemplate,
    ) -> tuple[str, str, str]:
        """
        Şablona göre veri export et.

        Returns:
            (content, media_type, filename_suffix)
        """
        processed = cls.apply_template(data, template)
        fmt = template.format

        if fmt == ExportFormat.CSV.value:
            content = cls.export_csv(processed, template)
            return content, "text/csv", ".csv"
        elif fmt == ExportFormat.JSON.value:
            content = cls.export_json(processed, template)
            return content, "application/json", ".json"
        elif fmt == ExportFormat.JSONL.value:
            content = cls.export_jsonl(processed, template)
            return content, "application/x-ndjson", ".jsonl"
        elif fmt == ExportFormat.SQL_INSERT.value:
            content = cls.export_sql_insert(processed, template)
            return content, "application/sql", ".sql"
        elif fmt == ExportFormat.SQL_COPY.value:
            content = cls.export_sql_copy(processed, template)
            return content, "application/sql", "_copy.sql"
        else:
            content = cls.export_json(processed, template)
            return content, "application/json", ".json"


# ═══════════════════════════════════════════════════════════════════════
# FastAPI Router
# ═══════════════════════════════════════════════════════════════════════

template_router = APIRouter(prefix="/api/templates", tags=["Export Şablonları"])


@template_router.post(
    "",
    response_model=TemplateResponse,
    status_code=201,
    summary="Şablon Oluştur",
    description="Yeni export şablonu oluşturur.",
)
async def create_template(
    request: TemplateCreateRequest,
    db: Session = Depends(get_db),
):
    """Yeni export şablonu oluştur."""
    # Format doğrulama
    valid_formats = {f.value for f in ExportFormat}
    if request.format not in valid_formats:
        raise HTTPException(
            status_code=400,
            detail=f"Geçersiz format: {request.format}. Geçerli: {sorted(valid_formats)}"
        )

    template = ExportTemplate(
        name=request.name,
        description=request.description,
        format=request.format,
        include_columns=request.include_columns,
        column_mapping=request.column_mapping,
        filters=request.filters,
        order_by=request.order_by,
        row_limit=request.row_limit,
        csv_delimiter=request.csv_delimiter,
        csv_encoding=request.csv_encoding,
        json_indent=request.json_indent,
        sql_table_name=request.sql_table_name,
        sql_batch_size=request.sql_batch_size,
        include_headers=request.include_headers,
    )
    db.add(template)
    db.commit()
    db.refresh(template)

    return _template_to_response(template)


@template_router.get(
    "",
    response_model=TemplateListResponse,
    summary="Şablon Listesi",
    description="Kayıtlı export şablonlarını listeler.",
)
async def list_templates(
    status: Optional[str] = Query(None, description="Durum filtresi"),
    format: Optional[str] = Query(None, description="Format filtresi"),
    db: Session = Depends(get_db),
):
    """Şablon listesi endpoint'i."""
    query = db.query(ExportTemplate).filter(
        ExportTemplate.status != TemplateStatus.ARCHIVED.value
    )
    if status:
        query = query.filter(ExportTemplate.status == status)
    if format:
        query = query.filter(ExportTemplate.format == format)

    templates = query.order_by(desc(ExportTemplate.created_at)).all()

    return TemplateListResponse(
        templates=[_template_to_response(t) for t in templates],
        total=len(templates),
    )


@template_router.put(
    "/{template_id}",
    response_model=TemplateResponse,
    summary="Şablon Güncelle",
    description="Mevcut export şablonunu günceller.",
)
async def update_template(
    template_id: int,
    request: TemplateUpdateRequest,
    db: Session = Depends(get_db),
):
    """Şablon güncelleme endpoint'i."""
    template = db.query(ExportTemplate).filter(ExportTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Şablon bulunamadı")

    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(template, key, value)

    db.commit()
    db.refresh(template)
    return _template_to_response(template)


@template_router.delete(
    "/{template_id}",
    summary="Şablon Sil",
    description="Export şablonunu arşivler (soft delete).",
)
async def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
):
    """Şablon silme endpoint'i."""
    template = db.query(ExportTemplate).filter(ExportTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Şablon bulunamadı")

    template.status = TemplateStatus.ARCHIVED.value
    db.commit()

    return {"message": "Şablon arşivlendi", "id": template_id}


@template_router.post(
    "/{template_id}/export",
    summary="Şablonla Export",
    description="Belirtilen dataset'i şablona göre export eder.",
)
async def export_with_template(
    template_id: int,
    dataset_id: int = Query(..., description="Export edilecek dataset ID"),
    db: Session = Depends(get_db),
):
    """Şablonla veri export endpoint'i."""
    template = db.query(ExportTemplate).filter(ExportTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Şablon bulunamadı")

    # Dataset'i getir
    from app.models.dataset import Dataset
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset bulunamadı")

    # Veriyi al
    sample_data: list[dict] = []
    if dataset.sample_data:
        sample_data = dataset.sample_data if isinstance(dataset.sample_data, list) else []

    if not sample_data:
        raise HTTPException(
            status_code=400,
            detail="Dataset'te export edilecek veri bulunamadı"
        )

    # Export et
    content, media_type, suffix = ExportEngine.export(sample_data, template)

    # İstatistik güncelle
    template.total_exports += 1
    db.commit()

    # Dosya adı oluştur
    filename = f"export_{dataset_id}_{template.name.lower().replace(' ', '_')}{suffix}"

    return StreamingResponse(
        io.BytesIO(content.encode(template.csv_encoding)),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Export-Template": template.name,
            "X-Export-Rows": str(len(sample_data)),
        },
    )


# ═══════════════════════════════════════════════════════════════════════
# Yardımcı Fonksiyonlar
# ═══════════════════════════════════════════════════════════════════════


def _template_to_response(template: ExportTemplate) -> TemplateResponse:
    """ORM modelini Pydantic response'a dönüştür."""
    return TemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        format=template.format,
        status=template.status,
        include_columns=template.include_columns,
        column_mapping=template.column_mapping,
        filters=template.filters,
        row_limit=template.row_limit,
        total_exports=template.total_exports,
        is_default=template.is_default,
        created_at=template.created_at.isoformat() if template.created_at else "",
        updated_at=template.updated_at.isoformat() if template.updated_at else "",
    )
