"""
Schema & Analysis API router.
"""
import os
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.schema_model import Project, DetectedSchema, GenerationRule
from app.core.analyzer import SchemaAnalyzer
from app.core.classifier import ColumnClassifier
from app.core.rule_engine import RuleEngine
from app.config import get_settings

router = APIRouter(prefix="/api/schemas", tags=["Schema Analysis"])

analyzer = SchemaAnalyzer()
classifier = ColumnClassifier()
rule_engine = RuleEngine()
settings = get_settings()


@router.post("/analyze")
async def analyze_file(
    file: UploadFile = File(...),
    project_name: str = "Yeni Proje",
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a CSV or JSON file → analyze schema → classify columns → infer rules.
    Returns the full analyzed schema with classification and rules.
    """
    content = await file.read()
    filename = file.filename or "upload"

    # Detect format
    if filename.endswith(".json"):
        schema = analyzer.analyze_json(content, filename)
    else:
        schema = analyzer.analyze_csv(content, filename)

    # Classify columns
    schema = classifier.classify_schema(schema)

    # Infer rules
    rules = rule_engine.infer_rules(schema)

    # Create or get project
    project = Project(name=project_name)
    db.add(project)
    await db.flush()

    # Save schema
    db_schema = DetectedSchema(
        project_id=project.id,
        table_name=schema["table_name"],
        source_type=schema["source_type"],
        source_info=schema["source_info"],
        row_count=schema["row_count"],
        columns=schema["columns"],
        relationships=schema.get("relationships", []),
    )
    db.add(db_schema)
    await db.flush()

    # Save rules
    for rule in rules:
        db_rule = GenerationRule(
            schema_id=db_schema.id,
            column_name=rule["column_name"],
            rule_type=rule["rule_type"],
            rule_config=rule.get("rule_config", {}),
        )
        db.add(db_rule)

    await db.flush()

    return {
        "project_id": str(project.id),
        "schema_id": str(db_schema.id),
        "schema": schema,
        "rules": rules,
        "pii_summary": schema.get("pii_summary", {}),
    }


@router.get("/projects")
async def list_projects(db: AsyncSession = Depends(get_db)):
    """List all projects."""
    result = await db.execute(select(Project).order_by(Project.created_at.desc()))
    projects = result.scalars().all()
    return [
        {
            "id": str(p.id),
            "name": p.name,
            "description": p.description,
            "created_at": str(p.created_at),
        }
        for p in projects
    ]


@router.get("/all")
async def list_all_schemas(db: AsyncSession = Depends(get_db)):
    """List all detected schemas for the UI."""
    result = await db.execute(select(DetectedSchema).order_by(DetectedSchema.created_at.desc()))
    schemas = result.scalars().all()
    return [
        {
            "id": str(s.id),
            "table_name": s.table_name,
            "row_count": s.row_count,
            "source_type": s.source_type,
            "columns_count": len(s.columns),
            "created_at": str(s.created_at)
        }
        for s in schemas
    ]


@router.get("/{schema_id}")
async def get_schema(schema_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve an analyzed schema with its rules."""
    result = await db.execute(
        select(DetectedSchema).where(DetectedSchema.id == schema_id)
    )
    schema = result.scalar_one_or_none()
    if not schema:
        raise HTTPException(404, "Şema bulunamadı")

    # Get rules
    rules_result = await db.execute(
        select(GenerationRule).where(GenerationRule.schema_id == schema.id)
    )
    rules = rules_result.scalars().all()

    return {
        "id": str(schema.id),
        "table_name": schema.table_name,
        "source_type": schema.source_type,
        "row_count": schema.row_count,
        "columns": schema.columns,
        "relationships": schema.relationships,
        "rules": [
            {
                "id": str(r.id),
                "column_name": r.column_name,
                "rule_type": r.rule_type,
                "rule_config": r.rule_config,
                "is_active": r.is_active,
            }
            for r in rules
        ],
    }


@router.put("/{schema_id}/rules")
async def update_rules(
    schema_id: str,
    rules: list[dict],
    db: AsyncSession = Depends(get_db)
):
    """Update generation rules for a schema."""
    sid = schema_id

    # Delete existing rules
    existing = await db.execute(
        select(GenerationRule).where(GenerationRule.schema_id == sid)
    )
    for rule in existing.scalars().all():
        await db.delete(rule)

    # Insert new rules
    for rule_data in rules:
        db.add(GenerationRule(
            schema_id=schema_id,
            column_name=rule_data["column_name"],
            rule_type=rule_data["rule_type"],
            rule_config=rule_data.get("rule_config", {}),
        ))

    return {"status": "ok", "updated_count": len(rules)}
