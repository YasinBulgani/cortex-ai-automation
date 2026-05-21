"""
Data Generation & Export API router.
"""
import os
import io
import time
import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from app.database import get_db
from app.models.schema_model import DetectedSchema, GenerationRule, GenerationHistory, Project
from app.core.generator import SyntheticGenerator
from app.core.scenarios import ScenarioManager
from app.config import get_settings

router = APIRouter(prefix="/api/generate", tags=["Data Generation"])

generator = SyntheticGenerator()
scenario_mgr = ScenarioManager()
settings = get_settings()


class GenerateRequest(BaseModel):
    schema_id: str
    row_count: int = 1000
    scenario: str = "default"
    format: str = "json"  # json, csv, sql


class ScenarioGenerateRequest(BaseModel):
    project_id: str
    scenario: str = "default"
    row_counts: dict = {}  # table_name → count
    format: str = "json"


class AIQueryRequest(BaseModel):
    schema_id: str
    prompt: str


@router.get("/scenarios")
async def list_scenarios():
    """List all available banking scenarios."""
    return scenario_mgr.list_scenarios()


@router.post("")
async def generate_data(req: GenerateRequest, db: AsyncSession = Depends(get_db)):
    """Generate synthetic data for a single schema."""
    start = time.time()

    # Load schema
    result = await db.execute(
        select(DetectedSchema).where(DetectedSchema.id == req.schema_id)
    )
    schema_record = result.scalar_one_or_none()
    if not schema_record:
        raise HTTPException(404, "Şema bulunamadı")

    # Load rules
    rules_result = await db.execute(
        select(GenerationRule).where(
            GenerationRule.schema_id == schema_record.id,
            GenerationRule.is_active == True
        )
    )
    rules = [
        {
            "column_name": r.column_name,
            "rule_type": r.rule_type,
            "rule_config": r.rule_config,
        }
        for r in rules_result.scalars().all()
    ]

    # Apply scenario overrides
    if req.scenario != "default":
        rules = scenario_mgr.apply_scenario(req.scenario, rules, schema_record.table_name)

    # Build schema dict
    schema_dict = {
        "table_name": schema_record.table_name,
        "columns": schema_record.columns,
    }

    # Generate
    df = generator.generate(schema_dict, rules, req.row_count)
    duration = int((time.time() - start) * 1000)

    # Preview (first 20 rows)
    preview = json.loads(df.head(20).to_json(orient="records", date_format="iso", default_handler=str))

    # Save history
    history = GenerationHistory(
        project_id=schema_record.project_id,
        schema_ids=[str(schema_record.id)],
        row_count=req.row_count,
        scenario=req.scenario,
        format=req.format,
        status="completed",
        generated_data_preview=preview,
        duration_ms=duration,
    )
    db.add(history)
    await db.flush()

    # Format response
    if req.format == "csv":
        output = io.StringIO()
        df.to_csv(output, index=False)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={schema_record.table_name}_synthetic.csv"}
        )
    elif req.format == "sql":
        sql_lines = _dataframe_to_sql(df, schema_record.table_name)
        return StreamingResponse(
            iter([sql_lines]),
            media_type="text/plain",
            headers={"Content-Disposition": f"attachment; filename={schema_record.table_name}_synthetic.sql"}
        )
    else:
        return {
            "generation_id": str(history.id),
            "table_name": schema_record.table_name,
            "row_count": len(df),
            "scenario": req.scenario,
            "duration_ms": duration,
            "preview": preview,
            "columns": list(df.columns),
        }


@router.post("/scenario")
async def generate_scenario(req: ScenarioGenerateRequest, db: AsyncSession = Depends(get_db)):
    """Generate multi-table data with a banking scenario."""
    start = time.time()

    # Load all schemas for the project
    result = await db.execute(
        select(DetectedSchema).where(
            DetectedSchema.project_id == req.project_id
        )
    )
    schemas = result.scalars().all()
    if not schemas:
        raise HTTPException(404, "Bu projede şema bulunamadı")

    all_schemas = []
    all_rules = {}

    for s in schemas:
        schema_dict = {"table_name": s.table_name, "columns": s.columns}
        all_schemas.append(schema_dict)

        # Load rules for this schema
        rules_res = await db.execute(
            select(GenerationRule).where(
                GenerationRule.schema_id == s.id,
                GenerationRule.is_active == True
            )
        )
        rules = [
            {"column_name": r.column_name, "rule_type": r.rule_type, "rule_config": r.rule_config}
            for r in rules_res.scalars().all()
        ]

        # Apply scenario
        if req.scenario != "default":
            rules = scenario_mgr.apply_scenario(req.scenario, rules, s.table_name)

        all_rules[s.table_name] = rules

    # Row counts
    row_counts = {}
    for s in all_schemas:
        row_counts[s["table_name"]] = req.row_counts.get(s["table_name"], 1000)

    # Detect relationships
    relationships = []
    for s in schemas:
        for rel in (s.relationships or []):
            relationships.append(rel)

    # Generate all tables
    generated = generator.generate_multi_table(
        all_schemas, all_rules, relationships, row_counts
    )

    duration = int((time.time() - start) * 1000)

    # Build response with previews
    result_tables = {}
    for table_name, df in generated.items():
        result_tables[table_name] = {
            "row_count": len(df),
            "columns": list(df.columns),
            "preview": json.loads(df.head(10).to_json(orient="records", date_format="iso", default_handler=str)),
        }

    return {
        "scenario": req.scenario,
        "tables": result_tables,
        "duration_ms": duration,
    }


import re

@router.post("/ai-query")
async def generate_from_ai(req: AIQueryRequest, db: AsyncSession = Depends(get_db)):
    """Parse natural language prompt to set generation parameters and run generation."""
    prompt = req.prompt.lower()
    
    # 1. Parse row count
    row_count = 100
    match = re.search(r'\b(\d+)\b', prompt)
    if match:
        row_count = int(match.group(1))
    elif "yüz" in prompt: row_count = 100
    elif "bin" in prompt: row_count = 1000
    
    # 2. Parse scenario
    scenario = "default"
    if any(w in prompt for w in ["premium", "zengin", "vip", "yüksek bakiye"]):
        scenario = "premium_customer"
    elif any(w in prompt for w in ["yeni", "son", "katılan"]):
        scenario = "new_customer"
    elif any(w in prompt for w in ["risk", "gecikme", "kötü", "batık"]):
        scenario = "high_risk"
    elif any(w in prompt for w in ["kurumsal", "şirket", "ticari", "kobi"]):
        scenario = "corporate"
    elif any(w in prompt for w in ["dolandırıcı", "fraud", "şüpheli", "anormal"]):
        scenario = "fraud_test"
        
    interpretation = f"{row_count} satır - {scenario} senaryosu uygulanarak üretildi"
    
    # Run generation
    gen_req = GenerateRequest(
        schema_id=req.schema_id, 
        row_count=row_count, 
        scenario=scenario, 
        format="json"
    )
    result = await generate_data(gen_req, db)
    
    if isinstance(result, dict) and "preview" in result:
        result["ai_interpretation"] = interpretation
    
    return result


@router.get("/history")
async def get_history(db: AsyncSession = Depends(get_db)):
    """Get generation history."""
    result = await db.execute(
        select(GenerationHistory).order_by(GenerationHistory.created_at.desc()).limit(50)
    )
    return [
        {
            "id": str(h.id),
            "row_count": h.row_count,
            "scenario": h.scenario,
            "format": h.format,
            "status": h.status,
            "duration_ms": h.duration_ms,
            "created_at": str(h.created_at),
        }
        for h in result.scalars().all()
    ]


def _dataframe_to_sql(df, table_name: str) -> str:
    """Convert a DataFrame to INSERT statements."""
    lines = []
    cols = ", ".join(df.columns)
    for _, row in df.iterrows():
        vals = ", ".join(
            f"'{str(v)}'" if v is not None else "NULL"
            for v in row.values
        )
        lines.append(f"INSERT INTO {table_name} ({cols}) VALUES ({vals});")
    return "\n".join(lines)
