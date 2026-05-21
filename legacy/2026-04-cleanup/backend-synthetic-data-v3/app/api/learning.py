"""
Continuous Learning API — analyzes generation history and provides rule improvement suggestions.
"""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.database import get_db
from app.models.schema_model import DetectedSchema, GenerationRule, GenerationHistory
from app.core.learning_engine import LearningEngine

router = APIRouter(prefix="/api/learn", tags=["Continuous Learning"])
engine = LearningEngine()


@router.get("/{schema_id}")
async def learn_from_schema(schema_id: str, db: AsyncSession = Depends(get_db)):
    """
    Analyze generation history for a schema and return improvement suggestions.
    """
    # Load schema
    schema_res = await db.execute(
        select(DetectedSchema).where(DetectedSchema.id == schema_id)
    )
    schema_rec = schema_res.scalar_one_or_none()
    if not schema_rec:
        raise HTTPException(404, "Şema bulunamadı")

    # Load rules
    rules_res = await db.execute(
        select(GenerationRule).where(GenerationRule.schema_id == schema_id)
    )
    rules = [
        {"column_name": r.column_name, "rule_type": r.rule_type, "rule_config": r.rule_config}
        for r in rules_res.scalars().all()
    ]

    # Load generation history previews
    hist_res = await db.execute(
        select(GenerationHistory)
        .where(GenerationHistory.project_id == schema_rec.project_id)
        .order_by(GenerationHistory.created_at.desc())
        .limit(10)
    )
    history_previews = []
    for h in hist_res.scalars().all():
        if h.generated_data_preview:
            history_previews.append(h.generated_data_preview)

    # Build schema dict
    schema_dict = {"table_name": schema_rec.table_name, "columns": schema_rec.columns}

    # Analyze
    result = engine.analyze_schema(schema_dict, rules, history_previews)
    result["schema_id"] = schema_id
    result["table_name"] = schema_rec.table_name
    return result


class ApplyRequest(BaseModel):
    schema_id: str
    suggestions: list[dict]


@router.post("/apply")
async def apply_suggestions(req: ApplyRequest, db: AsyncSession = Depends(get_db)):
    """Apply learning suggestions to existing rules."""
    schema_id = req.schema_id

    # Delete existing rules
    existing_res = await db.execute(
        select(GenerationRule).where(GenerationRule.schema_id == schema_id)
    )
    existing_rules = existing_res.scalars().all()
    old_rules = [
        {"column_name": r.column_name, "rule_type": r.rule_type, "rule_config": r.rule_config}
        for r in existing_rules
    ]

    for rule_rec in existing_rules:
        await db.delete(rule_rec)

    # Apply suggestions
    updated_rules = engine.apply_suggestions(old_rules, req.suggestions)

    # Re-insert updated rules
    for rule_data in updated_rules:
        db.add(GenerationRule(
            schema_id=schema_id,
            column_name=rule_data["column_name"],
            rule_type=rule_data["rule_type"],
            rule_config=rule_data.get("rule_config", {}),
        ))

    await db.flush()
    return {"status": "ok", "updated_count": len(updated_rules), "learned_count": len(req.suggestions)}
