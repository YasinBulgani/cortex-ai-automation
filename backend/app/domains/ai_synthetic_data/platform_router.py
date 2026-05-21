"""
Synthetic-Data Platform Router (Faz 3.B — ADR-0003).

Platform-v4'ten taşınan özellikleri ifşa eden FastAPI endpoint'leri:
    POST /synthetic-platform/schemas/analyze  — CSV/JSON yükle → schema + PII
    GET  /synthetic-platform/scenarios        — banking senaryo listesi
    POST /synthetic-platform/schemas/{id}/rules/infer — kurallar üret
    POST /synthetic-platform/learning/analyze/{schema_id} — geçmişten öneri
    GET  /synthetic-platform/projects         — CRUD (list + create)
    POST /synthetic-platform/projects
    GET  /synthetic-platform/projects/{id}

Ana üretim endpoint'leri (POST /synthetic/generate vs) router.py'de kalır.
"""
from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.deps import get_current_user
from app.infra.database import get_db
from app.infra.models import User
from app.domains.ai_synthetic_data.platform import (
    SchemaAnalyzer,
    ColumnClassifier,
    RuleEngine,
    LearningEngine,
    ScenarioManager,
    SyntheticProject,
    SyntheticDetectedSchema,
    SyntheticGenerationRule,
    SyntheticGenerationHistory,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/synthetic-platform", tags=["synthetic-platform"])


# ─── Pydantic schemas ────────────────────────────────────────────────────────

class AnalyzeResponse(BaseModel):
    table_name: str
    source_type: str
    row_count: int
    columns: list[dict]
    pii_summary: dict
    relationships: list[dict] = Field(default_factory=list)


class ScenarioSummary(BaseModel):
    key: str
    name: str
    name_en: str
    description: str
    icon: str


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = ""


class ProjectOut(BaseModel):
    id: str
    name: str
    description: str
    owner_id: str | None
    created_at: str
    schema_count: int = 0

    model_config = {"from_attributes": True}


class InferRulesResponse(BaseModel):
    schema_id: str
    rules: list[dict]
    rule_count: int


class LearningAnalyzeResponse(BaseModel):
    status: str
    sample_rows: int = 0
    insights: list[dict] = Field(default_factory=list)
    suggestions: list[dict] = Field(default_factory=list)
    confidence: float = 0.0
    message: str = ""


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/schemas/analyze", response_model=AnalyzeResponse, status_code=status.HTTP_200_OK)
async def analyze_schema(
    file: UploadFile = File(..., description="CSV veya JSON dosya"),
    user: User = Depends(get_current_user),
) -> AnalyzeResponse:
    """
    Yüklenen CSV/JSON'u analiz et → şema + sınıflandırma + PII özeti.

    Kaynak: Platform-v4 `schemas/analyze` — Faz 3.B gap analysis'in
    "backend'de eksik" birinci özelliği.
    """
    content = await file.read()
    filename = file.filename or "upload"

    analyzer = SchemaAnalyzer()
    classifier = ColumnClassifier()

    try:
        if filename.lower().endswith(".csv"):
            schema = analyzer.analyze_csv(content, filename)
        elif filename.lower().endswith(".json"):
            schema = analyzer.analyze_json(content, filename)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sadece .csv ve .json dosyaları destekleniyor",
            )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Dosya parse edilemedi: {exc}",
        ) from exc
    except Exception as exc:
        logger.exception("analyze_schema unexpected error")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analiz başarısız: {exc}",
        ) from exc

    # Classifier → PII + Faker config + description
    schema = classifier.classify_schema(schema)

    return AnalyzeResponse(
        table_name=schema["table_name"],
        source_type=schema["source_type"],
        row_count=schema["row_count"],
        columns=schema["columns"],
        pii_summary=schema.get("pii_summary", {}),
        relationships=schema.get("relationships", []),
    )


@router.get("/scenarios", response_model=list[ScenarioSummary])
def list_scenarios(
    _user: User = Depends(get_current_user),
) -> list[dict]:
    """Banking senaryo profillerini listele (default, premium, new, high_risk, corporate, fraud_test)."""
    manager = ScenarioManager()
    return manager.list_scenarios()


# ─── Projects CRUD ────────────────────────────────────────────────────────────

@router.post("/projects", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    body: ProjectCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProjectOut:
    """Yeni sentetik veri projesi oluştur."""
    project = SyntheticProject(
        id=str(uuid.uuid4()),
        name=body.name,
        description=body.description or "",
        owner_id=str(getattr(user, "id", "")) or None,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    return ProjectOut(
        id=project.id,
        name=project.name,
        description=project.description or "",
        owner_id=project.owner_id,
        created_at=project.created_at.isoformat() if project.created_at else "",
        schema_count=0,
    )


@router.get("/projects", response_model=list[ProjectOut])
def list_projects(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ProjectOut]:
    """Kullanıcının sentetik veri projelerini listele."""
    query = db.query(SyntheticProject)
    owner_id = str(getattr(user, "id", "")) or None
    if owner_id:
        query = query.filter(
            (SyntheticProject.owner_id == owner_id) | (SyntheticProject.owner_id.is_(None))
        )
    projects = query.order_by(SyntheticProject.created_at.desc()).limit(200).all()

    result = []
    for p in projects:
        count = db.query(SyntheticDetectedSchema).filter_by(project_id=p.id).count()
        result.append(ProjectOut(
            id=p.id,
            name=p.name,
            description=p.description or "",
            owner_id=p.owner_id,
            created_at=p.created_at.isoformat() if p.created_at else "",
            schema_count=count,
        ))
    return result


@router.get("/projects/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProjectOut:
    """Tek proje detayı."""
    project = db.query(SyntheticProject).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Proje bulunamadı")

    count = db.query(SyntheticDetectedSchema).filter_by(project_id=project_id).count()
    return ProjectOut(
        id=project.id,
        name=project.name,
        description=project.description or "",
        owner_id=project.owner_id,
        created_at=project.created_at.isoformat() if project.created_at else "",
        schema_count=count,
    )


# ─── Rule inference ──────────────────────────────────────────────────────────

@router.post("/schemas/{schema_id}/rules/infer", response_model=InferRulesResponse)
def infer_rules(
    schema_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> InferRulesResponse:
    """Mevcut detected_schema için RuleEngine ile kurallar üret ve kaydet."""
    schema_row = db.query(SyntheticDetectedSchema).filter_by(id=schema_id).first()
    if not schema_row:
        raise HTTPException(status_code=404, detail="Schema bulunamadı")

    schema_dict = {
        "table_name": schema_row.table_name,
        "columns": schema_row.columns or [],
    }

    engine = RuleEngine()
    rules = engine.infer_rules(schema_dict)

    # Upsert: mevcut kuralları sil, yenilerini kaydet
    db.query(SyntheticGenerationRule).filter_by(schema_id=schema_id).delete()
    for rule in rules:
        db.add(SyntheticGenerationRule(
            id=str(uuid.uuid4()),
            schema_id=schema_id,
            column_name=rule["column_name"],
            rule_type=rule["rule_type"],
            rule_config=rule.get("rule_config", {}),
            is_active=True,
            learned=False,
        ))
    db.commit()

    return InferRulesResponse(
        schema_id=schema_id,
        rules=rules,
        rule_count=len(rules),
    )


# ─── Learning ────────────────────────────────────────────────────────────────

@router.post("/learning/analyze/{schema_id}", response_model=LearningAnalyzeResponse)
def analyze_learning(
    schema_id: str,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> LearningAnalyzeResponse:
    """Bir şemanın geçmiş üretim preview'lerini LearningEngine ile analiz et."""
    schema_row = db.query(SyntheticDetectedSchema).filter_by(id=schema_id).first()
    if not schema_row:
        raise HTTPException(status_code=404, detail="Schema bulunamadı")

    rules = db.query(SyntheticGenerationRule).filter_by(
        schema_id=schema_id, is_active=True
    ).all()
    rule_dicts = [
        {
            "column_name": r.column_name,
            "rule_type": r.rule_type,
            "rule_config": r.rule_config or {},
        }
        for r in rules
    ]

    # Bu proje için son 10 başarılı üretimin preview'leri
    history_previews = []
    histories = (
        db.query(SyntheticGenerationHistory)
        .filter_by(project_id=schema_row.project_id, status="success")
        .order_by(SyntheticGenerationHistory.created_at.desc())
        .limit(10)
        .all()
    )
    for h in histories:
        if h.generated_data_preview:
            history_previews.append(h.generated_data_preview)

    schema_dict = {
        "table_name": schema_row.table_name,
        "columns": schema_row.columns or [],
    }

    learning = LearningEngine()
    result = learning.analyze_schema(schema_dict, rule_dicts, history_previews)

    return LearningAnalyzeResponse(
        status=result.get("status", "no_data"),
        sample_rows=result.get("sample_rows", 0),
        insights=result.get("insights", []),
        suggestions=result.get("suggestions", []),
        confidence=result.get("confidence", 0.0),
        message=result.get("message", ""),
    )
